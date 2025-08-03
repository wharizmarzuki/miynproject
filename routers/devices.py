import ipaddress
import asyncio
from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from typing import List
from snmp import schemas, database
from services import device_service, snmp_service
from services.device_service import DeviceRepository, get_repository
from services.snmp_service import SNMPClient, get_snmp_client

router = APIRouter(prefix="/device", tags=["Device"])


@router.get("/discover", response_model=schemas.DiscoveryResponse)
async def discovery(
    network: str = "192.168.254.1",
    subnet: str = "27",
    client: SNMPClient = Depends(get_snmp_client),
    repo: DeviceRepository = Depends(get_repository)  # DI here
):
    network_addr = ipaddress.IPv4Network(f"{network}/{subnet}", strict=False)
    host_addresses = [str(ip) for ip in network_addr.hosts()]

    semaphore = asyncio.Semaphore(20)

    async def limited_discovery(ip):
        async with semaphore:
            return await snmp_service.device_discovery(ip, client, repo)

    tasks = [limited_discovery(ip) for ip in host_addresses]
    results = await asyncio.gather(*tasks)

    reachable_devices = [device for device in results if device is not None]

    return schemas.DiscoveryResponse(
        total_scanned=len(host_addresses),
        devices_found=len(reachable_devices),
        devices=reachable_devices,
    )

@router.post("/", response_model=None)
async def create_device_endpoint(
    device_info: schemas.DeviceInfo,
    repo: DeviceRepository = Depends(get_repository) 
):
    try:
        await device_service.create_device(device_info, repo)
        return {"message": "Device created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[schemas.DeviceInfo])
async def get_all_devices_endpoint(
    repo: DeviceRepository = Depends(get_repository)  # DI here
):
    return device_service.get_all_devices(repo)

@router.get("/{ip}", response_model=schemas.DeviceInfo)
async def get_devices_endpoint(
    ip: str,
    repo: DeviceRepository = Depends(get_repository)  # DI here
):
    return device_service.get_device_by_ip(ip, repo)

@router.delete("/{ip}")
async def delete_devices_endpoint(
    ip: str,
    repo: DeviceRepository = Depends(get_repository)  # DI here
):
    device_service.delete_device(ip, repo)
    return {"message": "Device deleted"}