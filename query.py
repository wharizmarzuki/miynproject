from influxdb_client import InfluxDBClient  # pyright: ignore[reportPrivateImportUsage]

token = "DAhLUMLIIMtFZStnq05Wl8eL9jFiaOeOyeHEe8hQtRKfXvgsV5ch2rTKK5w2ffjWk4euDq_y0hKSOmgH2P1urw=="
org = "docs"
url = "http://localhost:8086"

client = InfluxDBClient(url=url, token=token, org=org)

write_client = InfluxDBClient(url=url, token=token, org=org)

query_api = client.query_api()

query = """from(bucket: "DeviceMetric")
 |> range(start: -1d)
 |> filter(fn: (r) => r["_measurement"] == "device_metrics")"""
tables = query_api.query(query, org="docs")

for table in tables:
    for record in table.records:
        print(record)
