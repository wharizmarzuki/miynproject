import asyncio
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from prometheus_client import generate_latest
from snmp import database, schemas, models
from services import snmp_service, influx_service
from snmp.prometheus_model import device_up, device_info, device_cpu_utilization, device_uptime_seconds, device_memory_utilization, registry

router = APIRouter(prefix="/polling", tags=["Polling"])
get_db = database.get_db
client = influx_service.client


@router.get("/")
async def poll_all_device(db: Session = Depends(get_db)):
    host_addresses = [ip[0] for ip in db.query(models.Device.ip_address).all()]
    semaphore = asyncio.Semaphore(20)

    async def limited_polling(ip):
        async with semaphore:
            await poll_device(ip)

    tasks = [limited_polling(ip) for ip in host_addresses]
    await asyncio.gather(*tasks)

    return Response(
        content=generate_latest(registry),
        media_type="text/plain; version=0.0.4"
    )

@router.get("/{host}")
async def poll_device(host: str):
    try:
        oids = list(schemas.POLLING_OIDS.values())
        result = await snmp_service.snmp_get(host, oids)

        if result and result.get("success"):
            data = result["data"]
            oid_values = {}
            polling_oids_items = list(schemas.POLLING_OIDS.items())

            for i, (key, _) in enumerate(polling_oids_items[:5]):
                oid_values[key] = data[i]["value"] if i < len(data) else None

            total_mem = float(data[5]["value"]) if len(data) > 5 else 1
            used_mem = float(data[7]["value"]) if len(data) > 7 else 0
            oid_values["memory_utilization"] = str((used_mem / total_mem) * 100) if total_mem else "0"

            device_name = oid_values.get("device_name", "Unknown")
            
            # Set metrics
            device_up.labels(host=host).set(1)
            device_info.labels(
                host=host,
                device_name=device_name,
                model_name=oid_values.get("model_name", "N/A"),
                services=oid_values.get("services", "N/A")
            ).set(1)
            
            # Convert uptime (hundredths of seconds to seconds)
            uptime_seconds = float(oid_values.get("uptime", 0)) / 100.0
            device_uptime_seconds.labels(
                host=host, 
                device_name=device_name
            ).set(uptime_seconds)
            
            device_cpu_utilization.labels(
                host=host, 
                device_name=device_name
            ).set(float(oid_values.get("cpu_utilization", 0)))
            
            device_memory_utilization.labels(
                host=host, 
                device_name=device_name
            ).set(float(oid_values.get("memory_utilization", 0)))
            
            # Generate metrics payload
            return generate_latest(registry)
            
        else:
            device_up.labels(host=host).set(0)
            return generate_latest(registry)
        
    except Exception as e:
        device_up.labels(host=host).set(0)
        return generate_latest(registry)