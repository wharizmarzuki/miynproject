import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from prometheus_client import generate_latest, push_to_gateway
from snmp import database, schemas, models
from services import snmp_service
from snmp.prometheus_model import device_up, device_info, device_cpu_utilization, device_uptime_seconds, device_memory_utilization, registry, interface_admin_status, interface_octets, interface_errors, interface_discards, interface_oper_status
from config import PUSHGATEWAY_URL

router = APIRouter(prefix="/polling", tags=["Polling"])
get_db = database.get_db


@router.get("/")
async def poll_all_device(db: Session = Depends(get_db)):
    host_info = db.query(models.Device.ip_address, models.Device.vendor).all()

    semaphore = asyncio.Semaphore(20)

    async def limited_polling(ip_address: str, vendor: str):
        async with semaphore:
            await poll_device(ip_address, vendor)
            await poll_interfaces(ip_address)

    # Create tasks
    tasks = [limited_polling(ip, vendor) for ip, vendor in host_info]
    await asyncio.gather(*tasks)

    try:
        push_to_gateway(
            gateway=PUSHGATEWAY_URL,
            job='snmp_polling',
            registry=registry,
            grouping_key={'instance': 'snmp_poller'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to push metrics: {str(e)}")


@router.get("/{host}")
async def poll_device(host: str, vendor: str):
    try:
        oids = list(schemas.DEVICE_OIDS.values()) + list(schemas.VENDOR_OIDS.get(vendor, {}).values())
        result = await snmp_service.snmp_get(host, oids)

        if result and result.get("success"):
            data = result["data"]
            oid_values = {}
            polling_oids_items = list(schemas.DEVICE_OIDS.items())

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
            
            return {"status": "success", "host": host, "device_name": device_name}
            
        else:
            device_up.labels(host=host).set(0)
            return {"status": "failed", "host": host, "reason": "SNMP query failed"}
        
    except Exception as e:
        device_up.labels(host=host).set(0)
        return {"status": "error", "host": host, "error": str(e)}

@router.get("/int/{host}") 
async def poll_interfaces(host: str):
    try:
        oids = list(schemas.INTERFACE_OIDS.values())
        result = await snmp_service.snmp_bulk_walk(host, oids)
        
        if not result or not result.get("success"):
            return

        # Group results by interface index
        interfaces = {}
        for item in result["data"]:
            index = item["index"]
            if index not in interfaces:
                interfaces[index] = {}
            interfaces[index][item["base_oid"]] = item["value"]
        
        print(interfaces)
            
        processed_interfaces = 0
        for index, data in interfaces.items():
            if_name = data.get("SNMPv2-SMI::mib-2.2.2.1.2", "n/a")
           
            interface_admin_status.labels(
                host=host,
                interface_index=index,
                interface_name=if_name
            ).set(int(data.get("SNMPv2-SMI::mib-2.2.2.1.7", "0")))
            
            interface_oper_status.labels(
                host=host,
                interface_index=index,
                interface_name=if_name
            ).set(int(data.get("SNMPv2-SMI::mib-2.2.2.1.8", "0")))
           
            # Octets (traffic)
            interface_octets.labels(
                host=host,
                interface_index=index,
                interface_name=if_name,
                direction="in"
            ).set(int(data.get("SNMPv2-SMI::mib-2.2.2.1.10", "0")))
            
            interface_octets.labels(
                host=host,
                interface_index=index,
                interface_name=if_name,
                direction="out"
            ).set(int(data.get("SNMPv2-SMI::mib-2.2.2.1.16", "0")))
            
            # Errors (use a separate metric)
            interface_errors.labels(
                host=host,
                interface_index=index,
                interface_name=if_name,
                direction="in"
            ).set(int(data.get("SNMPv2-SMI::mib-2.2.2.1.14", "0")))
            
            interface_errors.labels(
                host=host,
                interface_index=index,
                interface_name=if_name,
                direction="out"
            ).set(int(data.get("SNMPv2-SMI::mib-2.2.2.1.20", "0")))
            
            # Discards (use a separate metric)
            interface_discards.labels(
                host=host,
                interface_index=index,
                interface_name=if_name,
                direction="in"
            ).set(int(data.get("SNMPv2-SMI::mib-2.2.2.1.13", "0")))  # Fixed: was "inErrors"
            
            interface_discards.labels(
                host=host,
                interface_index=index,
                interface_name=if_name,
                direction="out"
            ).set(int(data.get("SNMPv2-SMI::mib-2.2.2.1.19", "0")))
            
            processed_interfaces += 1
        
        return {
            "status": "success", 
            "host": host, 
            "interfaces_processed": processed_interfaces
        }
               
    except Exception as e:
        print(f"Interface polling error for {host}: {str(e)}")
        return {
            "status": "error", 
            "host": host, 
            "error": str(e)
        }