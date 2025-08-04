#!/usr/bin/env python3
"""
Test script to validate your Prometheus queries work with mock data
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta

class QueryTester:
    def __init__(self, prometheus_url="http://localhost:9090"):
        self.prometheus_url = prometheus_url
        self.query_endpoint = f"{prometheus_url}/api/v1/query"
        self.query_range_endpoint = f"{prometheus_url}/api/v1/query_range"

    async def test_query(self, query, description):
        """Test a single Prometheus query"""
        print(f"\n🔍 Testing: {description}")
        print(f"Query: {query}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.query_endpoint, 
                    params={"query": query}, 
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") == "success":
                    results = data.get("data", {}).get("result", [])
                    print(f"✅ Success: {len(results)} results")
                    
                    # Show sample results
                    for i, result in enumerate(results[:3]):  # Show first 3
                        metric = result.get("metric", {})
                        value = result.get("value", ["", ""])[1]
                        labels = ", ".join([f"{k}={v}" for k, v in metric.items() if not k.startswith("__")])
                        print(f"   [{i+1}] {labels} = {value}")
                    
                    if len(results) > 3:
                        print(f"   ... and {len(results) - 3} more")
                    
                    return True
                else:
                    print(f"❌ Failed: {data.get('error', 'Unknown error')}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    async def test_range_query(self, query, description, duration="5m"):
        """Test a range query"""
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=10)
        
        print(f"\n📈 Testing Range: {description}")
        print(f"Query: {query}")
        print(f"Time range: {duration}")
        
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "query": query,
                    "start": start_time.isoformat() + "Z",
                    "end": end_time.isoformat() + "Z",
                    "step": "30s"
                }
                
                response = await client.get(
                    self.query_range_endpoint,
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") == "success":
                    results = data.get("data", {}).get("result", [])
                    print(f"✅ Success: {len(results)} series")
                    
                    for i, result in enumerate(results[:2]):  # Show first 2 series
                        metric = result.get("metric", {})
                        values = result.get("values", [])
                        labels = ", ".join([f"{k}={v}" for k, v in metric.items() if not k.startswith("__")])
                        print(f"   [{i+1}] {labels}: {len(values)} data points")
                        if values:
                            print(f"       Latest: {values[-1][1]} at {datetime.fromtimestamp(float(values[-1][0]))}")
                    
                    return True
                else:
                    print(f"❌ Failed: {data.get('error', 'Unknown error')}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    async def run_all_tests(self):
        """Run all test queries that match your application"""
        print("🧪 Starting Prometheus Query Tests")
        print("=" * 50)
        
        # Test queries from your application
        test_cases = [
            # Device status queries
            ("device_up", "Device reachability status"),
            ("device_up == 1", "Devices that are UP"),
            ("device_up == 0", "Devices that are DOWN"),
            
            # Device metrics
            ("device_cpu_utilization_percent", "CPU utilization for all devices"),
            ("device_memory_utilization_percent", "Memory utilization for all devices"),
            ("device_uptime_seconds", "Device uptime"),
            ("device_info", "Device information"),
            
            # Interface metrics
            ("interface_admin_status", "Interface admin status"),
            ("interface_operational_status", "Interface operational status"),
            ("interface_octets_total", "Interface traffic counters"),
            ("interface_errors_total", "Interface error counters"),
            ("interface_discards_total", "Interface discard counters"),
            
            # Aggregated queries (like your app uses)
            ('sum(rate(interface_octets_total{direction="in"}[5m]))', "Total inbound traffic rate"),
            ('sum(rate(interface_octets_total{direction="out"}[5m]))', "Total outbound traffic rate"),
            ('sum(rate(interface_octets_total[5m]))', "Total traffic rate"),
            
            # Specific device queries
            ('device_up{host="192.168.1.1"}', "Specific device status"),
            ('interface_octets_total{host="192.168.1.1"}', "Specific device interfaces"),
            
            # High-level aggregations
            ("count(device_up == 1)", "Count of UP devices"),
            ("count(device_up == 0)", "Count of DOWN devices"),
            ("avg(device_cpu_utilization_percent)", "Average CPU utilization"),
            ("max(device_memory_utilization_percent)", "Maximum memory utilization"),
        ]
        
        passed = 0
        failed = 0
        
        for query, description in test_cases:
            success = await self.test_query(query, description)
            if success:
                passed += 1
            else:
                failed += 1
            
            await asyncio.sleep(0.5)  # Brief pause between queries
        
        # Test range queries (for your dashboard charts)
        print("\n" + "=" * 50)
        print("📊 Testing Range Queries")
        
        range_queries = [
            ('device_cpu_utilization_percent[5m]', "CPU utilization time series"),
            ('rate(interface_octets_total{direction="in"}[5m])', "Inbound traffic rate over time"),
            ('rate(interface_octets_total{direction="out"}[5m])', "Outbound traffic rate over time"),
        ]
        
        for query, description in range_queries:
            success = await self.test_range_query(query, description)
            if success:
                passed += 1
            else:
                failed += 1
        
        print("\n" + "=" * 50)
        print(f"🏁 Test Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("🎉 All tests passed! Your queries should work correctly.")
        else:
            print("⚠️  Some tests failed. Check your mock data generator and Prometheus setup.")
        
        return failed == 0

async def main():
    tester = QueryTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())