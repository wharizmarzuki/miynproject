from snmp import models
from fastapi import FastAPI
from snmp.database import engine
from routers import devices, device_polling, device_db
from prometheus_client import make_asgi_app, Counter

models.Base.metadata.create_all(engine)
metrics_app = make_asgi_app()

app = FastAPI()
app.include_router(devices.router)
app.include_router(device_polling.router)
app.include_router(device_db.router)
app.mount("/metrics", metrics_app)