from prometheus_client import Gauge, Counter, CollectorRegistry

registry = CollectorRegistry()

# Device reachability status
device_up = Gauge(
    'device_up', 
    'Device reachability status (1 = up, 0 = down)',
    ['host'],
    registry=registry
)

# Device-level metrics
device_info = Gauge(
    'device_info',
    'Device information (static info in labels, value always 1)',
    ['host', 'device_name', 'model_name', 'vendor'],  # Removed services, added vendor
    registry=registry
)

device_uptime_seconds = Gauge(
    'device_uptime_seconds',
    'System uptime in seconds',
    ['host'],  # Removed device_name (redundant)
    registry=registry
)

device_cpu_utilization = Gauge(
    'device_cpu_utilization_percent',
    'CPU utilization percentage',
    ['host'],  # Removed device_name
    registry=registry
)

device_memory_utilization = Gauge(
    'device_memory_utilization_percent', 
    'Memory utilization percentage',
    ['host'],  # Removed device_name
    registry=registry
)

# Interface-level metrics
interface_admin_status = Gauge(
    'interface_admin_status',
    'Interface administrative status (1 = up, 0 = down)',
    ['host', 'interface_index', 'interface_name'],
    registry=registry
)

interface_oper_status = Gauge(
    'interface_operational_status',
    'Interface operational status (1 = up, 0 = down)',
    ['host', 'interface_index', 'interface_name'],
    registry=registry
)

# Changed from Gauge to Counter
interface_octets = Gauge(
    'interface_octets_total',
    'Total octets transmitted/received', 
    ['host', 'interface_index', 'interface_name', 'direction'],
    registry=registry
)

# Changed from Gauge to Counter
interface_errors = Gauge(
    'interface_errors_total',
    'Total interface errors',
    ['host', 'interface_index', 'interface_name', 'direction'],
    registry=registry
)

# Changed from Gauge to Counter
interface_discards = Gauge(
    'interface_discards_total',
    'Total interface discards',
    ['host', 'interface_index', 'interface_name', 'direction'],
    registry=registry
)