# geoapp
Exemplify geospatial query capabilities in Amazon DocumentDB or MongoDB.
The app takes a geospatial coordinate and a distance radius as input. It identifies the US state the coordinate is part of, 
finds the number of airports located in the state and then lists the ones found in the specified radius, sorted by closest.

### Prerequisites
1. Install python requirements
```sh
pip install -r requirements.txt
```

2. Import data set into your Amazon DocumentDB cluster
```sh
mongoimport --ssl --host <DocumentDB-cluster-endpoint> --sslCAFile rds-combined-ca-bundle.pem -u <username> -p <password> -d geodata -c airports dataset/airports-us.json
  
mongoimport --ssl --host <DocumentDB-cluster-endpoint> --sslCAFile rds-combined-ca-bundle.pem -u <username> -p <password> -d geodata -c states dataset/states-us.json
```

3. Create 2dsphere index:
```sh
> use geodata
switched to db geodata
> db.airports.createIndex({"loc": "2dsphere"})
```

4. Add the Amazon DocumentDB credentials in AWS Secrets Manager.
Update the global variables, in the script, and specify the AWS region and secret name.

### Usage example:

```sh
python3 geoapp.py
Enter your longitude coordinate: -73.9341
Enter your latitude coordinate: 40.8230
Enter distance radius (in km): 40
The geolocation coordinate entered is in the state of: New York
-----------------------------
I have found a number of 29 airports in New York.
-----------------------------
The following airports were found in a 40 km radius:
{'name': 'La Guardia', 'code': 'LGA', 'DistanceKilometers': 7.84283869954285}
{'name': 'Newark Intl', 'code': 'EWR', 'DistanceKilometers': 19.840025284365467}
{'name': 'John F Kennedy Intl', 'code': 'JFK', 'DistanceKilometers': 22.389465314261685}
```
