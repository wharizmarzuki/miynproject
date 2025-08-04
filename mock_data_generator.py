#!/usr/bin/env python3
"""
Mock Data Generator for SNMP Monitoring System
This script generates realistic mock data and pushes it to Prometheus Push Gateway
for testing your queries without requiring actual SNMP devices.
"""

import random
import time
import asyncio
from datetime import datetime, timedelta
from prometheus_client import Gauge, CollectorRegistry, push_to_gateway
import argparse
import sys

class MockDataGenerator:
    def __init__(self, pushgateway_url="localhost:9091"):
        self.pushgateway_url = pushgateway_url
        self.registry = CollectorRegistry()
        self.setup_metrics()
        
        # Mock device configurations
        self.mock_devices = [
            {"host": "192.168.1.1", "device_name": "Router-Core-01", "model": "ISR4431", "vendor": "Cisco"},
            {"host": "192.168.1.2", "device_name": "Switch-Access-01", "model": "WS-C2960X", "vendor": "Cisco"},
            {"host": "192.168.1.3", "device_name": "Firewall-Edge-01", "model": "ASA5516", "vendor": "Cisco"},
            {"host": "192.168.1.10", "device_name": "Server-Web-01", "model": "PowerEdge R730", "vendor": "Dell"},
            {"host": "192.168.1.11", "device_name": "Server-DB-01", "model": "ProLiant DL380", "vendor": "HP"},
        ]
        
        # Interface configurations per device
        self.interface_configs = {
            "192.168.1.1": [  # Router
                {"index": "1", "name": "GigabitEthernet0/0/0", "type": "WAN"},
                {"index": "2", "name": "GigabitEthernet0/0/1", "type": "LAN"}, 
                {"index": "3", "name": "Serial0/1/0", "type": "WAN"},
            ],
            "192.168.1.2": [  # Switch
                {"index": f"{i}", "name": f"FastEthernet0/{i}", "type": "ACCESS"} 
                for i in range(1, 25)
            ] + [
                {"index": "25", "name": "GigabitEthernet0/1", "type": "UPLINK"},
                {"index": "26", "name": "GigabitEthernet0/2", "type": "UPLINK"},
            ],
            "192.168.1.3": [  # Firewall
                {"index": "1", "name": "outside", "type": "WAN"},
                {"index": "2", "name": "inside", "type": "LAN"},
                {"index": "3", "name": "dmz", "type": "DMZ"},
            ],
            "192.168.1.10": [  # Web Server
                {"index": "1", "name": "eth0", "type": "SERVER"},
                {"index": "2", "name": "eth1", "type": "BACKUP"},
            ],
            "192.168.1.11": [  # DB Server
                {"index": "1", "name": "ens192", "type": "SERVER"},
                {"index": "2", "name": "ens224", "type": "STORAGE"},
            ]
        }
        
        # State tracking for realistic data
        self.device_states = {}
        self.interface_states = {}
        self.init_states()

    def setup_metrics(self):
        """Setup Prometheus metrics matching your application schema"""
        # Device-level metrics
        self.device_up = Gauge(
            'device_up', 
            'Device reachability status (1 = up, 0 = down)',
            ['host'],
            registry=self.registry
        )
        
        self.device_info = Gauge(
            'device_info',
            'Device information',
            ['host', 'device_name', 'model_name', 'vendor'],
            registry=self.registry
        )
        
        self.device_uptime_seconds = Gauge(
            'device_uptime_seconds',
            'System uptime in seconds',
            ['host'],
            registry=self.registry
        )
        
        self.device_cpu_utilization = Gauge(
            'device_cpu_utilization_percent',
            'CPU utilization percentage',
            ['host'],
            registry=self.registry
        )
        
        self.device_memory_utilization = Gauge(
            'device_memory_utilization_percent',
            'Memory utilization percentage', 
            ['host'],
            registry=self.registry
        )
        
        # Interface-level metrics
        self.interface_admin_status = Gauge(
            'interface_admin_status',
            'Interface administrative status',
            ['host', 'interface_index', 'interface_name'],
            registry=self.registry
        )
        
        self.interface_oper_status = Gauge(
            'interface_operational_status',
            'Interface operational status',
            ['host', 'interface_index', 'interface_name'],
            registry=self.registry
        )
        
        self.interface_octets = Gauge(
            'interface_octets_total',
            'Total octets transmitted/received',
            ['host', 'interface_index', 'interface_name', 'direction'],
            registry=self.registry
        )
        
        self.interface_errors = Gauge(
            'interface_errors_total',
            'Total interface errors',
            ['host', 'interface_index', 'interface_name', 'direction'],
            registry=self.registry
        )
        
        self.interface_discards = Gauge(
            'interface_discards_total',
            'Total interface discards',
            ['host', 'interface_index', 'interface_name', 'direction'],
            registry=self.registry
        )

    def init_states(self):
        """Initialize realistic state tracking"""
        base_time = time.time()
        
        for device in self.mock_devices:
            host = device["host"]
            
            # Device state
            self.device_states[host] = {
                "uptime_start": base_time - random.uniform(86400, 2592000),  # 1-30 days ago
                "cpu_base": random.uniform(10, 40),  # Base CPU usage
                "memory_base": random.uniform(30, 60),  # Base memory usage
                "is_up": random.choice([True] * 9 + [False]),  # 90% uptime
                "last_outage": None
            }
            
            # Interface states
            if host in self.interface_configs:
                self.interface_states[host] = {}
                for iface in self.interface_configs[host]:
                    idx = iface["index"]
                    iface_type = iface["type"]
                    
                    # Different traffic patterns based on interface type
                    if iface_type == "WAN":
                        base_traffic = random.uniform(1000000, 10000000)  # 1-10 Mbps
                    elif iface_type == "UPLINK":
                        base_traffic = random.uniform(5000000, 50000000)  # 5-50 Mbps
                    elif iface_type == "SERVER":
                        base_traffic = random.uniform(100000000, 1000000000)  # 100Mbps-1Gbps
                    else:
                        base_traffic = random.uniform(100000, 1000000)  # 100Kbps-1Mbps
                    
                    self.interface_states[host][idx] = {
                        "octets_in": random.randint(1000000, 100000000),
                        "octets_out": random.randint(1000000, 100000000),
                        "errors_in": random.randint(0, 100),
                        "errors_out": random.randint(0, 100),
                        "discards_in": random.randint(0, 50),
                        "discards_out": random.randint(0, 50),
                        "admin_status": 1,  # Usually up
                        "oper_status": random.choice([1] * 19 + [0]),  # 95% operational
                        "base_traffic": base_traffic,
                        "last_update": time.time()
                    }

    def generate_device_metrics(self):
        """Generate realistic device-level metrics"""
        current_time = time.time()
        
        for device in self.mock_devices:
            host = device["host"]
            device_name = device["device_name"]
            model = device["model"]
            vendor = device["vendor"]
            
            state = self.device_states[host]
            
            # Simulate occasional outages
            if state["is_up"] and random.random() < 0.001:  # 0.1% chance of going down
                state["is_up"] = False
                state["last_outage"] = current_time
                print(f"📉 {host} ({device_name}) went down")
            elif not state["is_up"] and random.random() < 0.1:  # 10% chance of coming back up
                state["is_up"] = True
                state["uptime_start"] = current_time
                print(f"📈 {host} ({device_name}) came back up")
            
            if state["is_up"]:
                # Device is up
                self.device_up.labels(host=host).set(1)
                
                # Device info (static)
                self.device_info.labels(
                    host=host,
                    device_name=device_name,
                    model_name=model,
                    vendor=vendor
                ).set(1)
                
                # Uptime
                uptime = current_time - state["uptime_start"]
                self.device_uptime_seconds.labels(host=host).set(uptime)
                
                # CPU utilization with realistic variation
                cpu_variation = random.uniform(-10, 10)
                cpu_spike = random.uniform(0, 30) if random.random() < 0.05 else 0  # 5% chance of spike
                cpu_usage = max(0, min(100, state["cpu_base"] + cpu_variation + cpu_spike))
                self.device_cpu_utilization.labels(host=host).set(round(cpu_usage, 2))
                
                # Memory utilization (grows slowly over time, with occasional drops from restarts)
                time_since_start = (current_time - state["uptime_start"]) / 86400  # days
                memory_growth = min(20, time_since_start * 2)  # 2% per day, max 20%
                memory_variation = random.uniform(-2, 2)
                memory_usage = max(0, min(100, state["memory_base"] + memory_growth + memory_variation))
                self.device_memory_utilization.labels(host=host).set(round(memory_usage, 2))
                
            else:
                # Device is down
                self.device_up.labels(host=host).set(0)

    def generate_interface_metrics(self):
        """Generate realistic interface-level metrics"""
        current_time = time.time()
        
        for host, interfaces in self.interface_configs.items():
            device_state = self.device_states[host]
            
            if not device_state["is_up"]:
                continue  # Skip interfaces if device is down
                
            for iface in interfaces:
                idx = iface["index"]
                name = iface["name"]
                iface_type = iface["type"]
                
                if host not in self.interface_states or idx not in self.interface_states[host]:
                    continue
                    
                state = self.interface_states[host][idx]
                time_delta = current_time - state["last_update"]
                
                # Admin and operational status
                admin_status = state["admin_status"]
                oper_status = state["oper_status"]
                
                # Simulate interface flaps (rare)
                if random.random() < 0.0001:  # Very rare flap
                    oper_status = 0 if oper_status == 1 else 1
                    state["oper_status"] = oper_status
                    print(f"🔌 Interface {host}:{name} flapped to {'UP' if oper_status else 'DOWN'}")
                
                self.interface_admin_status.labels(
                    host=host, interface_index=idx, interface_name=name
                ).set(admin_status)
                
                self.interface_oper_status.labels(
                    host=host, interface_index=idx, interface_name=name
                ).set(oper_status)
                
                if oper_status == 1:  # Only generate traffic if interface is up
                    # Generate realistic traffic patterns
                    traffic_multiplier = self.get_traffic_multiplier(iface_type)
                    base_rate_in = state["base_traffic"] * traffic_multiplier * random.uniform(0.1, 1.5)
                    base_rate_out = state["base_traffic"] * traffic_multiplier * random.uniform(0.1, 1.2)
                    
                    # Calculate octets (cumulative counters)
                    octets_in_delta = int(base_rate_in * time_delta / 8)  # Convert bits to bytes
                    octets_out_delta = int(base_rate_out * time_delta / 8)
                    
                    state["octets_in"] += octets_in_delta
                    state["octets_out"] += octets_out_delta
                    
                    # Occasional errors and discards
                    if random.random() < 0.01:  # 1% chance
                        state["errors_in"] += random.randint(1, 5)
                    if random.random() < 0.01:
                        state["errors_out"] += random.randint(1, 5)
                    if random.random() < 0.005:  # 0.5% chance
                        state["discards_in"] += random.randint(1, 3)
                    if random.random() < 0.005:
                        state["discards_out"] += random.randint(1, 3)
                    
                    # Set metrics
                    self.interface_octets.labels(
                        host=host, interface_index=idx, interface_name=name, direction="in"
                    ).set(state["octets_in"])
                    
                    self.interface_octets.labels(
                        host=host, interface_index=idx, interface_name=name, direction="out" 
                    ).set(state["octets_out"])
                    
                    self.interface_errors.labels(
                        host=host, interface_index=idx, interface_name=name, direction="in"
                    ).set(state["errors_in"])
                    
                    self.interface_errors.labels(
                        host=host, interface_index=idx, interface_name=name, direction="out"
                    ).set(state["errors_out"])
                    
                    self.interface_discards.labels(
                        host=host, interface_index=idx, interface_name=name, direction="in"
                    ).set(state["discards_in"])
                    
                    self.interface_discards.labels(
                        host=host, interface_index=idx, interface_name=name, direction="out"
                    ).set(state["discards_out"])
                
                state["last_update"] = current_time

    def get_traffic_multiplier(self, iface_type):
        """Get traffic multiplier based on time of day and interface type"""
        hour = datetime.now().hour
        
        # Business hours traffic pattern (higher during 9-17)
        if 9 <= hour <= 17:
            base_multiplier = 1.5
        elif 18 <= hour <= 22:
            base_multiplier = 1.2
        else:
            base_multiplier = 0.3
        
        # Interface type adjustments
        if iface_type in ["WAN", "UPLINK"]:
            return base_multiplier * random.uniform(0.8, 1.8)
        elif iface_type == "SERVER":
            return base_multiplier * random.uniform(0.5, 2.0)  # More variable
        else:
            return base_multiplier * random.uniform(0.1, 1.0)

    def push_metrics(self):
        """Push metrics to Prometheus Push Gateway"""
        try:
            push_to_gateway(
                gateway=self.pushgateway_url,
                job='mock_snmp_polling',
                registry=self.registry,
                grouping_key={'instance': 'mock_generator'}
            )
            return True
        except Exception as e:
            print(f"❌ Failed to push metrics: {e}")
            return False

    def generate_and_push(self):
        """Generate all metrics and push to Prometheus"""
        self.generate_device_metrics()
        self.generate_interface_metrics()
        success = self.push_metrics()
        
        if success:
            timestamp = datetime.now().strftime("%H:%M:%S")
            up_devices = sum(1 for state in self.device_states.values() if state["is_up"])
            total_devices = len(self.device_states)
            print(f"✅ [{timestamp}] Pushed metrics - {up_devices}/{total_devices} devices up")
        
        return success

    async def run_continuous(self, interval=30):
        """Run continuous mock data generation"""
        print(f"🚀 Starting mock data generator (interval: {interval}s)")
        print(f"📡 Push Gateway: {self.pushgateway_url}")
        print(f"🖥️  Mock devices: {len(self.mock_devices)}")
        
        while True:
            try:
                self.generate_and_push()
                await asyncio.sleep(interval)
            except KeyboardInterrupt:
                print("\n🛑 Stopping mock data generator...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                await asyncio.sleep(5)

def main():
    parser = argparse.ArgumentParser(description="Mock SNMP Data Generator for Prometheus")
    parser.add_argument("--pushgateway", default="localhost:9091", 
                       help="Prometheus Push Gateway URL (default: localhost:9091)")
    parser.add_argument("--interval", type=int, default=30,
                       help="Push interval in seconds (default: 30)")
    parser.add_argument("--once", action="store_true",
                       help="Generate data once and exit")
    
    args = parser.parse_args()
    
    generator = MockDataGenerator(args.pushgateway)
    
    if args.once:
        print("📊 Generating mock data once...")
        success = generator.generate_and_push()
        sys.exit(0 if success else 1)
    else:
        asyncio.run(generator.run_continuous(args.interval))

if __name__ == "__main__":
    main()