import ipaddress
import asyncio
from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from typing import List
from snmp import schemas, models, database
from services import snmp_service

router = APIRouter(prefix="/device", tags=["Device"])
get_db = database.get_db


@router.get("/discover", response_model=schemas.DiscoveryResponse)
async def discovery(
    network: str = "192.168.99.0", subnet: str = "26", db: Session = Depends(get_db)
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
async def create_device(device_info: schemas.DeviceInfo, db: Session = Depends(get_db)):
    try:
        new_device = models.Device(
            hostname=device_info.hostname,
            ip_address=device_info.ip_address,
            number_of_ports=int(device_info.number_of_ports),
        )
        db.add(new_device)
        db.commit()
        db.refresh(new_device)
        return None
    except Exception as e:
        print(f"Database error creating device: {e}")
        db.rollback()
        return None


@router.get("/", response_model=List[schemas.DeviceInfo])
async def retrieve_all(db: Session = Depends(get_db)):
    registered_device = db.query(models.Device).all()
    return registered_device


@router.get("/{ip}", response_model=schemas.DeviceInfo)
async def retrieve(ip: str, db: Session = Depends(get_db)):  # Added type hint
    registered_device = (
        db.query(models.Device).filter(models.Device.ip_address == ip).first()
    )  # Fixed filter
    return registered_device
