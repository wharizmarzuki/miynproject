from typing import Optional
from fastapi import Depends
from sqlalchemy import exists
from sqlalchemy.orm import Session
from snmp import models, schemas, database
from abc import ABC, abstractmethod


def extract_vendor(oid_value):
    parts = oid_value.split('.')
    try:
        idx = parts.index('4')
        if parts[idx + 1] == '1':
            vendor_id = int(parts[idx + 2])
            return schemas.VENDOR_MAPPING.get(vendor_id, f"Unknown ({vendor_id})")
    except (ValueError, IndexError):
        pass
    return "Unknown"


def format_mac_address(mac_value):
    hex_string = mac_value[2:].upper()
    
    formatted_mac = ':'.join(hex_string[i:i+2] for i in range(0, len(hex_string), 2))
    return formatted_mac


class DeviceRepository(ABC):
    @abstractmethod
    async def create_device(self, device_info: schemas.DeviceInfo) -> models.Device:
        pass

    @abstractmethod
    def get_all_devices(self) -> list[models.Device]:
        pass

    @abstractmethod
    def get_device_by_ip(self, ip: str) -> models.Device:
        pass

    @abstractmethod
    def get_device_by_mac(self, mac: str) -> Optional[models.Device]:
        pass

    @abstractmethod
    def delete_device(self, ip: str) -> None:
        pass

    @abstractmethod
    async def update_device(self, device_info: schemas.DeviceInfo) -> models.Device:
        pass

class SQLAlchemyDeviceRepository(DeviceRepository):
    def __init__(self, db: Session):
        self.db = db

    async def create_device(self, device_info: schemas.DeviceInfo) -> models.Device:
        try:
            new_device = models.Device(
                hostname=device_info.hostname,
                ip_address=device_info.ip_address,
                mac_address=format_mac_address(device_info.mac_address),
                vendor=extract_vendor(device_info.vendor),
                priority=device_info.priority
            )
            self.db.add(new_device)
            self.db.commit()
            self.db.refresh(new_device)
            return new_device
        except Exception as e:
            self.db.rollback()
            raise e

    def get_all_devices(self) -> list[models.Device]:
        return self.db.query(models.Device).all()

    def get_device_by_ip(self, ip: str) -> models.Device:
        return self.db.query(models.Device).filter(models.Device.ip_address == ip).first()

    def get_device_by_mac(self, mac: str) -> Optional[models.Device]:
        return self.db.query(models.Device).filter(models.Device.mac_address == mac).first()

    def delete_device(self, ip: str) -> None:
        self.db.query(models.Device).filter(models.Device.ip_address == ip).delete(synchronize_session=False)
        self.db.commit()

    async def update_device(self, device_info: schemas.DeviceInfo) -> models.Device:
        mac_address = format_mac_address(device_info.mac_address)
        device = self.get_device_by_mac(mac_address)

        if device:
            device.ip_address = device_info.ip_address # type: ignore
            device.hostname = device_info.hostname # type: ignore
            device.vendor = extract_vendor(device_info.vendor) # type: ignore
            self.db.commit()
            self.db.refresh(device)
            return device
        else:
            return await self.create_device(device_info)


def get_repository(db: Session = Depends(database.get_db)) -> DeviceRepository:
    return SQLAlchemyDeviceRepository(db)


async def create_device(
    device_info: schemas.DeviceInfo, 
    repo: DeviceRepository
) -> models.Device:
    return await repo.create_device(device_info)


def get_all_devices(repo: DeviceRepository) -> list[models.Device]:
    return repo.get_all_devices()


def get_device_by_ip(ip: str, repo: DeviceRepository) -> models.Device:
    return repo.get_device_by_ip(ip)


def delete_device(ip: str, repo: DeviceRepository) -> str:
    repo.delete_device(ip)
    return 'deleted'


async def update_device(
    device_info: schemas.DeviceInfo, 
    repo: DeviceRepository
) -> models.Device:
    return await repo.update_device(device_info)