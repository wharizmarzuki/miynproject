from prometheus_client import Gauge, Counter, CollectorRegistry

registry = CollectorRegistry()

# Device reachability status
device_up = Gauge(
    'device_up', 
    'Device reachability status (1 = up, 0 = down)',
    ['host'],
    registry=registry
)

# Device-level metrics (matching your DeviceMetrics schema)
device_info = Gauge(
    'device_info',
    'Device information (static info in labels, value always 1)',
    ['host', 'device_name', 'model_name', 'services'],
    registry=registry
)

device_uptime_seconds = Gauge(
    'device_uptime_seconds',
    'System uptime in seconds',
    ['host', 'device_name'],
    registry=registry
)

device_cpu_utilization = Gauge(
    'device_cpu_utilization_percent',
    'CPU utilization percentage',
    ['host', 'device_name'],
    registry=registry
)

device_memory_utilization = Gauge(
    'device_memory_utilization_percent', 
    'Memory utilization percentage',
    ['host', 'device_name'],
    registry=registry
)

# Interface-level metrics (linked to device by host)
interface_admin_status = Gauge(
    'interface_admin_status',
    'Interface administrative status',
    ['host', 'interface_index', 'interface_name'],
    registry=registry
)

interface_oper_status = Gauge(
    'interface_operational_status',
    'Interface operational status',
    ['host', 'interface_index', 'interface_name'],
    registry=registry
)

interface_octets = Gauge(
    'interface_octets_total',
    'Total octets transmitted/received', 
    ['host', 'interface_index', 'interface_name', 'direction'],
    registry=registry
)

interface_errors = Gauge(
    'interface_errors_total',
    'Total interface errors',
    ['host', 'interface_index', 'interface_name', 'direction'],
    registry=registry
)

interface_discards = Gauge(
    'interface_discards_total',
    'Total interface discards',
    ['host', 'interface_index', 'interface_name', 'direction'],
    registry=registry
)