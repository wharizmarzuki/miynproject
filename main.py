from snmp import models
from fastapi import FastAPI
from snmp.database import engine
from routers import devices, device_polling, device_db
# from influxdb_client import InfluxDBClient  # pyright: ignore[reportPrivateImportUsage]

models.Base.metadata.create_all(engine)

app = FastAPI()
app.include_router(devices.router)
app.include_router(device_polling.router)
app.include_router(device_db.router)