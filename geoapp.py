import os.path
import json
import pymongo
import boto3
import requests

# Global variables
SECRET_REGION = 'us-east-1'
SECRET_NAME = 'geodata-demo-cluster'


# Function for credentials retrieval from AWS Secrets Manager
def get_credentials(region_name, secret_name):
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager',
                            region_name=region_name)

    try:
        secret_value = client.get_secret_value(SecretId=secret_name)
        secret_json = json.loads(secret_value['SecretString'])
        username = secret_json['username']
        password = secret_json['password']
        cluster_uri = secret_json['host']
        return (username, password, cluster_uri)
    except Exception as e:
        print('Failed to retrieve secret {} because: {}'.format(secret_name, e))


# Function for connecting to Amazon DocumentDB
def get_db_client():
    try:
        # Get the Amazon DocumentDB ssl certificate
        if not os.path.exists('rds-combined-ca-bundle.pem'):
            url = 'https://s3.amazonaws.com/rds-downloads/rds-combined-ca-bundle.pem'
            data = requests.get(url, allow_redirects=True)
            with open('rds-combined-ca-bundle.pem', 'wb') as cert:
                cert.write(data.content)

        # Get Amazon DocumentDB credentials (specify the region and secret name according to your case)
        (username, password,
         cluster_uri) = get_credentials(SECRET_REGION, SECRET_NAME)
        db_client = pymongo.MongoClient(
            cluster_uri,
            ssl=True,
            retryWrites=False,
            ssl_ca_certs='rds-combined-ca-bundle.pem')
        db_client["admin"].authenticate(name=username, password=password)
    except Exception as e:
        print('Failed to create new DocumentDB client: {}'.format(e))
        raise
    return db_client


# Find the state the coordinate is part of
def geointersects(lon, lat):
    try:
        check_float_lon = isinstance(lon, float)
        check_float_lat = isinstance(lat, float)
        if check_float_lon is False or check_float_lat is False:
            print("The longitude or latitude coordinates are not correct, float type required!")
            quit()
        db_client = get_db_client()
        collection_states = db_client['geodata']['states']

        query_geointersects = {
            "loc": {
                "$geoIntersects": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    }
                }
            }
        }

        document = collection_states.find_one(query_geointersects,
                                              projection={
                                                  "_id": 0,
                                                  "name": 1
                                              })
        if document is not None:
            state_name = document['name']
            return state_name
        else:
            print("The geo location you entered was not found in the United States!")
    except Exception as e:
        print('Exception in geoIntersects: {}'.format(e))
        raise


# List the documents found within a polygon
def geowithin_list(state):
    try:
        db_client = get_db_client()
        collection_states = db_client['geodata']['states']
        collection_airports = db_client['geodata']['airports']
        state_loc = collection_states.find_one({"name": state},
                                               projection={
                                                   "_id": 0,
                                                   "loc": 1
        })
        state_loc_polygon = state_loc['loc']

        query_geowithin = {
            "loc": {
                "$geoWithin": {
                    "$geometry": state_loc_polygon
                }
            }
        }
        documents_within = collection_airports.find(query_geowithin,
                                                    projection={
                                                        "_id": 0,
                                                        "name": 1,
                                                        "type": 1,
                                                        "code": 1
                                                    }).sort("name", 1)
        location_list = []
        for doc in documents_within:
            location_list.append(doc)
        return location_list
    except Exception as e:
        print('Exception in geoWithin_list: {}'.format(e))
        raise


# Count the number of documents found within a polygon
def geowithin_count(state):
    try:
        db_client = get_db_client()
        collection_states = db_client['geodata']['states']
        collection_airports = db_client['geodata']['airports']
        state_loc = collection_states.find_one({"name": state},
                                               projection={
                                                   "_id": 0,
                                                   "loc": 1
        })
        state_loc_polygon = state_loc['loc']

        query_geowithin = {
            "loc": {
                "$geoWithin": {
                    "$geometry": state_loc_polygon
                }
            }
        }
        documents_within_count = collection_airports.count_documents(
            query_geowithin)
        return documents_within_count
    except Exception as e:
        print('Exception in geoWithin_count: {}'.format(e))
        raise


# List geodata documents in a certain proximity (in km)
def geonear(proximity, lon, lat):
    try:
        db_client = get_db_client()
        collection_airports = db_client['geodata']['airports']
        query_geonear = [{
            "$geoNear": {
                "near": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "spherical": True,
                "query": {"type": "International"},
                "distanceField": "DistanceKilometers",
                "maxDistance": (proximity * 1000),
                "distanceMultiplier": 0.001
            }
        }, {
            "$project": {
                "name": 1,
                "code": 1,
                "DistanceKilometers": 1,
                "_id": 0
            }
        }, {
            "$sort": {
                "DistanceKilometers": 1
            }
        }]
        documents_near = collection_airports.aggregate(query_geonear)
        location_list = []
        for doc in documents_near:
            location_list.append(doc)
        return location_list
    except Exception as e:
        print('Exception in geoNear: {}'.format(e))
        raise


def main():
    lon = float(input("Enter your longitude coordinate: "))
    lat = float(input("Enter your latitude coordinate: "))
    distance = int(input("Enter distance radius (in km): "))
    current_state = geointersects(lon, lat)
    airports_count = geowithin_count(current_state)
    proximity_airports = geonear(distance, lon, lat)
    print('The geolocation coordinate entered is in the state of: {}'.format(current_state))
    print("-----------------------------")
    print("I have found a number of {} airports in {}.".format(airports_count, current_state))
    print("-----------------------------")
    if proximity_airports:
        print("The following airports were found in a {} km radius:".format(distance))
        print(*proximity_airports, sep="\n")
    else:
        print("There are no airports within a {} km radius of your location.".format(distance))


if __name__ == "__main__":
    main()
