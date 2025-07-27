from sqlalchemy import Column, String, Integer
from .database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, unique=True)
    hostname = Column(String, unique=True)
    mac_address = Column(String, index=True)
    vendor = Column(String)
    priority = Column(Integer)
