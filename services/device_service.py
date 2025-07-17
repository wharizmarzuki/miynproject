from sqlalchemy.orm import Session
from snmp import models, schemas

async def create_device(device_info: schemas.DeviceInfo, db: Session) -> models.Device:
    """Business logic for creating a device"""
    try:
        new_device = models.Device(
            hostname=device_info.hostname,
            ip_address=device_info.ip_address,
            number_of_ports=int(device_info.number_of_ports),
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