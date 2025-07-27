import asyncio
from typing import Optional
from sqlalchemy.orm import Session
from pysnmp.hlapi.v3arch.asyncio import (
    get_cmd,
    bulk_cmd,
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
)
from config import SNMP_COMMUNITY
from snmp import schemas
from services import device_service

async def snmp_get(
    host: str,
    oids: list[str],
):
    community = SNMP_COMMUNITY
    port = 161
    transport_address = (host, port)
    try:
        snmpEngine = SnmpEngine()
        oid_objects = [ObjectType(ObjectIdentity(oid)) for oid in oids]
        errorIndication, errorStatus, errorIndex, varBinds = await get_cmd(
            snmpEngine,
            CommunityData(community, mpModel=1),
            await UdpTransportTarget.create(transport_address),
            ContextData(),
            *oid_objects,
        )

        if errorIndication or errorStatus or not varBinds:
            return None

        processed_data = []
        for varBind in varBinds:
            try:
                oid_name = (
                    str(varBind[0]).split("::", 1)[1]
                    if "::" in str(varBind[0])
                    else str(varBind[0])
                )
                value = varBind[1].prettyPrint()
                processed_data.append(
                    {"oid": oid_name, "value": value, "raw": f"{oid_name} = {value}"}
                )
            except Exception:
                continue

        return {
            "success": True,
            "host": transport_address[0],
            "data": processed_data,
            "raw_data": [item["raw"] for item in processed_data],
        }
    except asyncio.TimeoutError:
        return None
    except Exception:
        return None


async def snmp_bulk_walk(host: str, oids: list[str]):
    community = SNMP_COMMUNITY
    port = 161
    transport_address = (host, port)
    snmp_engine = SnmpEngine()
    oid_objects = [ObjectType(ObjectIdentity(oid)) for oid in oids]
   
    results = []
    try:
        # Await the bulk_cmd call - it returns a single result, not an iterator
        errorIndication, errorStatus, errorIndex, varBindTable = await bulk_cmd(
            snmp_engine,
            CommunityData(community, mpModel=1),
            await UdpTransportTarget.create(transport_address),
            ContextData(),
            0, 25,  # non-repeaters, max-repetitions
            *oid_objects
        )
        
        if errorIndication:
            return {"success": False, "error": str(errorIndication)}
        
        if errorStatus:
            return {"success": False, "error": f"{errorStatus.prettyPrint()} at {errorIndex and varBindTable[int(errorIndex) - 1][0] or '?'}"} # type: ignore
        
        for var_bind in varBindTable:
            oid_parts = var_bind[0].prettyPrint().split('.')
            base_oid = '.'.join(oid_parts[:-1])
            index = oid_parts[-1]
            value = var_bind[1].prettyPrint()
           
            results.append({
                "base_oid": base_oid,
                "index": index,
                "value": value
            })
           
        return {"success": True, "data": results}
       
    except Exception as e:
        return {"success": False, "error": str(e)}


async def device_discovery(
    host: str,
    db: Session, 
) -> Optional[schemas.DeviceInfo]:
    oids = list(schemas.DISCOVERY_OIDS.values())
    result = await snmp_get(host, oids)
    print(result)

    if result and result.get("success"):
        data = result["data"]
        oid_values = {}

        for i, (key, oid) in enumerate(schemas.DISCOVERY_OIDS.items()):
            oid_values[key] = data[i]["value"] if i < len(data) else None

        device_info = schemas.DeviceInfo(
            ip_address=host,
            **oid_values,
        )
        
        try:
            await device_service.update_device(device_info, db) 
            return device_info
        except Exception as e:
            print(f"Error saving device {host}: {e}")
            return device_info

    return None
