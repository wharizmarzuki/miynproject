from fastapi import HTTPException, APIRouter
from influxdb_client import InfluxDBClient  # pyright: ignore[reportPrivateImportUsage]
from influxdb_client.client.write.point import Point
from influxdb_client.client.write_api import SYNCHRONOUS

from snmp.schemas import DeviceMetrics
from config import INFLUXDB_TOKEN, INFLUXDB_URL, INFLUXDB_ORG, INFLUXDB_BUCKET


token = INFLUXDB_TOKEN
org = INFLUXDB_ORG
url = INFLUXDB_URL

client = InfluxDBClient(url=url, token=token, org=org)

write_client = InfluxDBClient(url=url, token=token, org=org)

query_api = client.query_api()


router = APIRouter(prefix="/db")


async def write_device_polling(request: DeviceMetrics):
    try:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        point = (
            Point("device_metrics")
            .tag("host", request.host)
            .tag("device_name", request.device_name)
            .tag("model_name", request.model_name)
            .field("uptime", request.uptime)
            .field("cpu_utilization", float(request.cpu_utilization))
            .field("memory_utilization", float(request.memory_utilization))
        )
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write data: {str(e)}")


def query():
    query_api = client.query_api()

    query = """from(bucket: "DeviceMetric")
    |> range(start: -2d)
    |> filter(fn: (r) => r["_measurement"] == "device_metrics")
    |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    |> keep(columns: ["_time", "device_name", "host", "model_name", "cpu_utilization", "memory_utilization", "uptime"])"""
    tables = query_api.query(query, org="docs")

    clean_up = []
    for table in tables:
        for record in table.records:
            clean_up.append(record.row[2:])

    return clean_up


@router.get("/")
def print():
    print(f"Influx token is ={INFLUXDB_TOKEN}")
