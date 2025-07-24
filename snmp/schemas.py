from pydantic import BaseModel, ConfigDict, Field
from typing import List


class DeviceInfo(BaseModel):
    ip_address: str = Field(..., description="Device IP address")
    hostname: str = Field(default="Unknown", description="Device system name")
    number_of_ports: int = Field(default=0, description="Number of interfaces")
    model_config = ConfigDict(from_attributes=True)


class DeviceMetrics(BaseModel):
    status: str = Field(default="Unreacheable", description="Device Status")
    host: str = Field(..., description="Device IP address")
    uptime: str = Field(default="N/A", description="System uptime")
    device_name: str = Field(default="Unknown", description="Device system name")
    services: str = Field(default="N/A", description="System services")
    model_name: str = Field(default="N/A", description="Physical model name")
    cpu_utilization: float = Field(default=0, description="CPU utilization")
    memory_utilization: float = Field(default=0, description="Memory utilization")


class DiscoveryResponse(BaseModel):
    total_scanned: int = Field(..., description="Total IPs scanned")
    devices_found: int = Field(..., description="Number of responsive devices")
    devices: List[DeviceInfo] = Field(..., description="List of discovered devices")


# OID Mapping for easy maintenance
DISCOVERY_OIDS = {
    "device_name": "1.3.6.1.2.1.1.5.0",  # sysName
    "interface_count": "1.3.6.1.2.1.2.1.0",  # ifNumber
}

POLLING_OIDS = {
    "uptime": "1.3.6.1.2.1.1.3.0",
    "device_name": "1.3.6.1.2.1.1.5.0",
    "services": "1.3.6.1.2.1.1.7.0",
    "model_name": "1.3.6.1.2.1.47.1.1.1.1.13.1",
    "cpu_utilization": "1.3.6.1.4.1.9.9.109.1.1.1.1.5.1",
    "memory_pool_1": "1.3.6.1.4.1.9.9.48.1.1.1.5.1",
    "memory_pool_2": "1.3.6.1.4.1.9.9.48.1.1.1.5.2",
    "memory_pool_13": "1.3.6.1.4.1.9.9.48.1.1.1.5.13",
}
