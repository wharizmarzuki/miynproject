#!/usr/bin/env python3
"""
Quick debug script to see what's actually in Prometheus
"""

import asyncio
import httpx
import json

async def debug_prometheus():
    prometheus_url = "http://localhost:9090"
    
    async with httpx.AsyncClient() as client:
        print("🔍 Debugging Prometheus Data")
        print("=" * 50)
        
        # 1. Check what metrics exist
        print("1. Available metrics:")
        try:
            response = await client.get(f"{prometheus_url}/api/v1/label/__name__/values")
            if response.status_code == 200:
                data = response.json()
                metrics = data.get("data", [])
                interface_metrics = [m for m in metrics if "interface" in m or "device" in m]
                print(f"   Found {len(interface_metrics)} relevant metrics:")
                for metric in sorted(interface_metrics):
                    print(f"   - {metric}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n" + "-" * 30)
        
        # 2. Check interface_octets_total specifically
        print("2. Checking interface_octets_total:")
        try:
            response = await client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": "interface_octets_total"}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    results = data.get("data", {}).get("result", [])
                    print(f"   Found {len(results)} series")
                    for i, result in enumerate(results[:5]):  # Show first 5
                        metric = result.get("metric", {})
                        value = result.get("value", ["", ""])[1]
                        print(f"   [{i+1}] {metric} = {value}")
                else:
                    print(f"   ❌ Query failed: {data.get('error')}")
            else:
                print(f"   ❌ HTTP error: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n" + "-" * 30)
        
        # 3. Test the rate query that's failing
        print("3. Testing rate query:")
        queries = [
            'interface_octets_total{direction="in"}',
            'rate(interface_octets_total{direction="in"}[5m])',
            'sum(rate(interface_octets_total{direction="in"}[5m]))'
        ]
        
        for query in queries:
            try:
                print(f"   Query: {query}")
                response = await client.get(
                    f"{prometheus_url}/api/v1/query",
                    params={"query": query}
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        results = data.get("data", {}).get("result", [])
                        print(f"   ✅ Success: {len(results)} results")
                        if results:
                            print(f"      Sample: {results[0].get('value', ['', ''])[1]}")
                    else:
                        print(f"   ❌ Failed: {data.get('error')}")
                else:
                    print(f"   ❌ HTTP {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            print()
        
        print("\n" + "-" * 30)
        
        # 4. Check Push Gateway
        print("4. Checking Push Gateway:")
        try:
            response = await client.get("http://localhost:9091/metrics")
            if response.status_code == 200:
                content = response.text
                interface_lines = [line for line in content.split('\n') if 'interface_octets' in line and not line.startswith('#')]
                print(f"   Found {len(interface_lines)} interface_octets lines in Push Gateway")
                if interface_lines:
                    print("   Sample lines:")
                    for line in interface_lines[:3]:
                        print(f"   {line}")
            else:
                print(f"   ❌ Push Gateway HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_prometheus())