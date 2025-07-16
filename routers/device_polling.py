import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from snmp import database, schemas, models
from services import snmp_service, influx_service

router = APIRouter(prefix="/polling", tags=["Polling"])
get_db = database.get_db
client = influx_service.client


@router.get("/")
async def poll_all_device(
    db: Session = Depends(get_db),
):
    host_addresses = [ip[0] for ip in db.query(models.Device.ip_address).all()]

    semaphore = asyncio.Semaphore(20)

    async def limited_polling(ip):
        async with semaphore:
            return await poll_device(ip)  # Pass db session

    tasks = [limited_polling(ip) for ip in host_addresses]
    results = await asyncio.gather(*tasks)

    return results


@router.get("/{host}")
async def poll_device(
    host: str,
):
    try:
        oids = list(schemas.POLLING_OIDS.values())
        result = await snmp_service.snmp_get(host, oids)

        if result and result.get("success"):
            data = result["data"]
            oid_values = {}
            polling_oids_items = list(schemas.POLLING_OIDS.items())

            for i, (key, oid) in enumerate(polling_oids_items[:5]):
                oid_values[key] = data[i]["value"] if i < len(data) else None

            total_mem = float(data[5]["value"]) if len(data) > 5 else 1
            used_mem = float(data[7]["value"]) if len(data) > 7 else 0
            oid_values["memory_utilization"] = (
                str((used_mem / total_mem) * 100) if total_mem else "0"
            )

            metric = schemas.DeviceMetrics(host=host, **oid_values)
            await influx_service.write_device_polling(metric)
            return metric

    except Exception as e:
        print(f"Error polling device {host}: {str(e)}")
        return None
