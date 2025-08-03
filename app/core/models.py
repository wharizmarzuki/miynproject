from sqlalchemy import Column, String, Integer, Float, DateTime
from .database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, unique=True)
    hostname = Column(String, unique=True)
    mac_address = Column(String, index=True)
    vendor = Column(String)
    priority = Column(Integer)

class AlertRule(Base):
    __tablename__ = 'alert_rules'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)          # Rule name
    duration = Column(Float, nullable=False)       # Duration in seconds
    keep_firing_for = Column(Float, nullable=True) # Keep firing duration
    severity = Column(String, nullable=True)       # Severity from labels
    summary = Column(String, nullable=False)       # Summary from annotations
    last_evaluation = Column(DateTime)            # Last evaluation timestamp
