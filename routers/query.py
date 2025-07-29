from fastapi import APIRouter, HTTPException
import httpx
import asyncio
from typing import Dict, Any, List
from urllib.parse import quote
from collections import defaultdict
from datetime import datetime

router = APIRouter(
    prefix="/query",
    tags= ["Query"]
)

# Prometheus configuration
PROMETHEUS_URL = "http://localhost:9090"  # Adjust to your Prometheus server
PROMETHEUS_QUERY_ENDPOINT = f"{PROMETHEUS_URL}/api/v1/query"

async def query_prometheus(query: str) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient() as client:
            params = {"query": query}
            response = await client.get(PROMETHEUS_QUERY_ENDPOINT, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=500)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code)
    

@router.get("/devices")
async def get_all_devices(
    duration: str = "5m",
    start_time: str = None, # type: ignore
    end_time: str = None, # type: ignore
    step: str = "15s"
):
    try:
        query = f"{{device_name=~'.+'}}[{duration}]"
        
        if start_time and end_time:
            # Range query with step
            result = await query_prometheus(
                query,
                start=start_time, # type: ignore
                end=end_time, # type: ignore
                step=step # type: ignore
            )
        else:
            result = await query_prometheus(query)
        
        print(result)
        
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail="Prometheus query failed")
        
        compiled_devices = format_metric(result)
        
        return {
            "status": "success",
            "total_devices": len(compiled_devices),
            "devices": compiled_devices
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.get("/devices/{hostname}")
async def get_devices(
    hostname: str,
    duration: str = "5m",
    start_time: str = None, # type: ignore
    end_time: str = None, # type: ignore
    step: str = "15s"
):
    try:
        query = f"{{device_name='{hostname}'}}[{duration}]"
        
        if start_time and end_time:
            # Range query with step
            result = await query_prometheus(
                query,
                start=start_time, # type: ignore
                end=end_time, # type: ignore
                step=step # type: ignore
            )
        else:
            result = await query_prometheus(query)
        
        print(result)
        
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail="Prometheus query failed")
        
        compiled_devices = format_metric(result)
        
        return {
            "status": "success",
            "total_devices": len(compiled_devices),
            "devices": compiled_devices
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

def format_metric(prom_data):
    result = []
    for entry in prom_data['data']['result']:
        metric_meta = entry['metric']
        metric_name = metric_meta.get('__name__', '')
        device_name = metric_meta.get('device_name', 'unknown')

        timeseries = [
            { "timestamp": ts, "value": float(value) }
            for ts, value in entry['values']
        ]

        result.append({
            "metric": metric_name,
            "device_name": device_name,
            "data": timeseries
        })
    return result    