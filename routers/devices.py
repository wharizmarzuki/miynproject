import ipaddress
import asyncio
from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from typing import List
from snmp import schemas, database
from services import snmp_service, device_service

router = APIRouter(prefix="/device", tags=["Device"])
get_db = database.get_db


@router.get("/discover", response_model=schemas.DiscoveryResponse)
async def discovery(
    network: str = "192.168.254.1", subnet: str = "30", db: Session = Depends(get_db)
):
    network_addr = ipaddress.IPv4Network(f"{network}/{subnet}", strict=False)
    host_addresses = [str(ip) for ip in network_addr.hosts()]

    # Limit concurrent requests
    semaphore = asyncio.Semaphore(20)

    async def limited_discovery(ip):
        async with semaphore:
            return await snmp_service.device_discovery(ip, db)  # Pass db session

    tasks = [limited_discovery(ip) for ip in host_addresses]
    results = await asyncio.gather(*tasks)

    reachable_devices = [device for device in results if device is not None]

    return schemas.DiscoveryResponse(
        total_scanned=len(host_addresses),
        devices_found=len(reachable_devices),
        devices=reachable_devices,
    )


@router.post("/", response_model=None)
async def create_device_endpoint(device_info: schemas.DeviceInfo, db: Session = Depends(get_db)):
    """HTTP endpoint for creating a device"""
    try:
        await device_service.create_device(device_info, db)
        return {"message": "Device created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[schemas.DeviceInfo])
async def get_all_devices_endpoint(db: Session = Depends(get_db)):
    """HTTP endpoint for getting all devices"""
    return device_service.get_all_devices(db)


@router.get("/{ip}", response_model=schemas.DeviceInfo)
async def get_devices_endpoint(ip: str, db: Session = Depends(get_db)):
    """HTTP endpoint for getting single devices"""
    return device_service.get_device_by_ip(ip, db)

@router.delete("/{ip}")
async def delete_devices_endpoint(ip: str, db: Session = Depends(get_db)):
    """HTTP endpoint for delete single devices"""
    return device_service.delete_device(ip, db)