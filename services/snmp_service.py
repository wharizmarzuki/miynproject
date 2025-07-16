import asyncio
from fastapi import FastAPI
from typing import Optional
from sqlalchemy.orm import Session
from pysnmp.hlapi.v3arch.asyncio import (
    get_cmd,
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
)
from snmp import schemas
from routers import devices

router = FastAPI()


@router.get("/snmpget")
async def snmp_get(
    host: str,
    oids: list[str],
):
    community = config.SNMP_COMMUNITY
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


async def device_discovery(
    host: str,
    db: Session,  # Removed Depends - db is now a regular parameter
) -> Optional[schemas.DeviceInfo]:
    oids = list(schemas.DISCOVERY_OIDS.values())
    result = await snmp_get(host, oids)

    if result and result.get("success"):
        data = result["data"]
        oid_values = {}

        for i, (key, oid) in enumerate(schemas.DISCOVERY_OIDS.items()):
            oid_values[key] = data[i]["value"] if i < len(data) else None

        device_info = schemas.DeviceInfo(
            ip_address=host,
            **oid_values,
        )

        # Call create_device directly with the db session
        try:
            await devices.create_device(device_info, db)
            return device_info
        except Exception as e:
            print(f"Error saving device {host}: {e}")
            return device_info  # Return device info even if save fails

    return None
