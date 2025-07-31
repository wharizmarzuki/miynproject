from sqlalchemy import exists
from sqlalchemy.orm import Session
from snmp import models, schemas

async def create_device(device_info: schemas.DeviceInfo, db: Session) -> models.Device:
    """Business logic for creating a device"""
    try:
        new_device = models.Device(
            hostname=device_info.hostname,
            ip_address=device_info.ip_address,
            mac_address=format_mac_address(device_info.mac_address),
            vendor=extract_vendor(device_info.vendor),
            priority=device_info.priority
        )
        db.add(new_device)
        db.commit()
        db.refresh(new_device)
        return new_device
    except Exception as e:
        db.rollback()
        raise e

def get_all_devices(db: Session) -> list[models.Device]:
    """Get all registered devices"""
    return db.query(models.Device).all()

def get_device_by_ip(ip: str, db: Session) -> models.Device:
    """Get device by IP address"""
    return db.query(models.Device).filter(models.Device.ip_address == ip).first()

def delete_device(ip: str, db: Session):
    """Delete device by IP address"""
    db.query(models.Device).filter(models.Device.ip_address == ip).delete(synchronize_session=False)
    db.commit()
    return 'deleted'

async def update_device(device_info: schemas.DeviceInfo, db: Session):
    """Update device details"""
    mac_address = format_mac_address(device_info.mac_address)
    device = db.query(models.Device).filter(models.Device.mac_address == mac_address).first()
    if device:
        device.ip_address = device_info.ip_address # type: ignore
        device.hostname = device_info.hostname # type: ignore
        device.vendor = extract_vendor(device_info.vendor) # type: ignore
        db.commit()
        db.refresh(device)
        return device
    else:
        return await create_device(device_info, db)

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