from fastapi import APIRouter, HTTPException, Depends
from influxdb_client.client.influxdb_client import InfluxDBClient
from influxdb_client.client.write.point import Point
from influxdb_client.client.write_api import SYNCHRONOUS
from config import INFLUXDB_BUCKET, INFLUXDB_ORG, INFLUXDB_TOKEN, INFLUXDB_URL
from snmp import schemas

router = APIRouter(prefix="/metric", tags=["Metric"])


def get_influxdb_client():
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    try:
        yield client
    finally:
        client.close()


@router.post("/write", response_model=None)
async def write_device_metric(
    request: schemas.DeviceMetrics,
    client: InfluxDBClient = Depends(get_influxdb_client),
):
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
        return {"message": f"Metric for {request.host} has been recorded"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write data: {str(e)}")
