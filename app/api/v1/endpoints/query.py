from fastapi import APIRouter, Depends, HTTPException, Query
import httpx
import asyncio
import math
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from app.core import schemas

class IMetricsService(ABC):
    @abstractmethod
    async def query(self, query: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def query_range(
        self, 
        query: str, 
        start_time: str, 
        end_time: str, 
        step: str
    ) -> Dict[str, Any]:
        pass

class IConfigProvider(ABC):
    @abstractmethod
    def get_prometheus_url(self) -> str:
        pass

class EnvironmentConfigProvider(IConfigProvider):
    def get_prometheus_url(self) -> str:
        return "http://localhost:9090"

class PrometheusService(IMetricsService):
    def __init__(self, config: IConfigProvider):
        self.config = config
        base_url = config.get_prometheus_url()
        self.query_endpoint = f"{base_url}/api/v1/query"
        self.query_range_endpoint = f"{base_url}/api/v1/query_range"
    
    async def query(self, query: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                params = {"query": query}
                response = await client.get(self.query_endpoint, params=params, timeout=30.0)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {str(e)}")
    
    async def query_range(self, query: str, start_time: str, end_time: str, step: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "query": query,
                    "start": start_time,
                    "end": end_time,
                    "step": step
                }
                response = await client.get(self.query_range_endpoint, params=params, timeout=30.0)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {str(e)}")

def get_config() -> IConfigProvider:
    return EnvironmentConfigProvider()

def get_metrics_service(config: IConfigProvider = Depends(get_config)) -> IMetricsService:
    return PrometheusService(config)

router = APIRouter(
    prefix="/query",
    tags=["Query"]
)

@router.get("/devices/cpu-utilization")
async def get_all_devices_cpu_utilization(
    metrics_service: IMetricsService = Depends(get_metrics_service),
    duration: str = "5m",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    step: str = "15s"
):
    try:
        # Query specifically for CPU utilization metric
        query = f"device_cpu_utilization_percent[{duration}]"
        result = await metrics_service.query(query) 
        
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail="Prometheus query failed")
        
        cpu_data = format_metric(result)
        
        return {
            "status": "success",
            "metric_type": "cpu_utilization",
            "total_devices": len(cpu_data),
            "data": cpu_data
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/devices/status")
async def get_all_device_status(
    metrics_service: IMetricsService = Depends(get_metrics_service)
):
    try:
        result = await metrics_service.query("device_up")
       
        if not result:
            raise HTTPException(status_code=500, detail="Empty response from Prometheus")
           
        if result.get("status") != "success":
            error_detail = result.get("error", "Unknown Prometheus error")
            raise HTTPException(status_code=500, detail=f"Prometheus query failed: {error_detail}")
       
        # Extract the actual result array from nested structure
        prometheus_data = result.get("data", {})
        devices_result = prometheus_data.get("result", [])
        
        return {
            "status": "success",
            "metric_type": "device_up",
            "total_devices": len(devices_result),
            "data": result  # Keep original structure for compatibility
        }
   
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/devices/status/summary")
async def summary_device_status(
    metrics_service: IMetricsService = Depends(get_metrics_service)
):
    response = await get_all_device_status(metrics_service)
    print(response)
   
    # Navigate to the actual devices array in the nested structure
    prometheus_data = response["data"]["data"]
    devices = prometheus_data["result"]
   
    # Extract device status - value is in format [timestamp, "status_string"]
    up_count = 0
    down_count = 0
    
    for device in devices:
        # Get the status value (second element in the value array)
        status_value = device["value"][1]
        if status_value == "1":
            up_count += 1
        elif status_value == "0":
            down_count += 1
   
    return {
        "type": "device_status_summary",
        "payload": {
            "labels": ["Up", "Down"],
            "datasets": [{
                "label": "Device Status",
                "data": [up_count, down_count],
                "hoverOffset": 4
            }]
        }
    }

@router.get("/interfaces/{host}", response_model=schemas.PaginatedInterfaces)
async def get_interfaces(
    host: str,
    metrics_service: IMetricsService = Depends(get_metrics_service),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """Async endpoint for interface metrics"""
    # Use the injected metrics service instead of direct function call
    query = f'{{instance="{host}"}}'
    metrics_result = await metrics_service.query(query)
    
    if metrics_result.get("status") != "success":
        raise HTTPException(status_code=500, detail="Failed to query metrics")
    
    metrics = metrics_result.get("data", {}).get("result", [])
    
    interfaces = {}
    for metric in metrics: 
        labels = metric.get('metric', {})
        if 'interface_index' not in labels or 'interface_name' not in labels:
            continue
            
        idx = labels.get('interface_index')
        name = labels.get('interface_name')
        
        if idx not in interfaces:
            interfaces[idx] = {
                'index': int(idx),
                'name': name,
                'admin_status': 0,
                'oper_status': 0,
                'octets_in': 0,
                'octets_out': 0,
                'errors_in': 0,
                'errors_out': 0,
                'discards_in': 0,
                'discards_out': 0
            }
        
        value = float(metric['value'][1])
        metric_name = labels.get('__name__', '')
        
        if metric_name == 'interface_admin_status':
            interfaces[idx]['admin_status'] = int(value)
        elif metric_name == 'interface_operational_status':
            interfaces[idx]['oper_status'] = int(value)
        elif 'direction' in labels:
            direction = labels.get('direction')
            if metric_name == 'interface_octets_total':
                if direction == 'in': 
                    interfaces[idx]['octets_in'] = value
                else: 
                    interfaces[idx]['octets_out'] = value
            elif metric_name == 'interface_errors_total':
                if direction == 'in': 
                    interfaces[idx]['errors_in'] = value
                else: 
                    interfaces[idx]['errors_out'] = value
            elif metric_name == 'interface_discards_total':
                if direction == 'in': 
                    interfaces[idx]['discards_in'] = value
                else: 
                    interfaces[idx]['discards_out'] = value
    
    interface_list = list(interfaces.values())
    total = len(interface_list)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = interface_list[start:end]
    
    return schemas.PaginatedInterfaces(
        host=host,
        interfaces=[schemas.InterfaceMetric(**data) for data in paginated],
        page=page,
        per_page=per_page,
        total=total
    )

@router.post("/interface/network")
async def get_network_throughput_separated(
    metrics_service: IMetricsService = Depends(get_metrics_service),
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    step: str = "60s",
    unit: str = "mbps",
    max_points: int = 1000
):
    if not start_time or not end_time:
        end_time = datetime.now().isoformat() + "Z"
        start_time = (datetime.now() - timedelta(hours=1)).isoformat() + "Z"

    # Validate time format
    try:
        start_dt = datetime.fromisoformat(start_time.rstrip("Z"))
        end_dt = datetime.fromisoformat(end_time.rstrip("Z"))
        if end_dt <= start_dt:
            raise ValueError("end_time must be after start_time")
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid time format: {str(e)}")

    # Unit conversion setup
    unit_conversions = {
        "bps": 8,
        "kbps": 8 / 1_000,
        "mbps": 8 / 1_000_000,
        "gbps": 8 / 1_000_000_000
    }
    unit = unit.lower()
    if unit not in unit_conversions:
        raise HTTPException(status_code=400, detail=f"Invalid unit. Choose from: {list(unit_conversions.keys())}")
    conversion_factor = unit_conversions[unit]

    step_seconds = parse_duration(step)
    window = f"{max(step_seconds * 2, 300)}s" 

    queries = {
        "inbound": f'sum(rate(interface_octets_total{{direction="in"}}[{window}]))',
        "outbound": f'sum(rate(interface_octets_total{{direction="out"}}[{window}]))',
        "total": f'sum(rate(interface_octets_total[{window}]))'
    }

    # Auto-adjust step if too many data points requested
    time_range_seconds = (end_dt - start_dt).total_seconds()
    requested_points = time_range_seconds / step_seconds
    
    if requested_points > max_points:
        new_step = math.ceil(time_range_seconds / max_points)
        step = f"{new_step}s"
        step_seconds = new_step

    results = {}
    try:
        tasks = {
            direction: metrics_service.query_range(query, start_time, end_time, step)
            for direction, query in queries.items()
        }

        query_results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for direction, task_result in zip(tasks.keys(), query_results):
            if isinstance(task_result, Exception):
                results[direction] = {"error": str(task_result)}
            elif isinstance(task_result, dict) and task_result.get("status") == "success":
                all_series = task_result.get("data", {}).get("result", [])
                if not all_series:
                    results[direction] = []
                    continue
                
                # Aggregate all values across series
                aggregated_data = {}
                for series in all_series:
                    for point in series.get("values", []):
                        timestamp = point[0]
                        try:
                            value = float(point[1]) * conversion_factor
                        except (ValueError, TypeError):
                            value = 0.0
                            
                        if timestamp in aggregated_data:
                            aggregated_data[timestamp] += value
                        else:
                            aggregated_data[timestamp] = value
                
                formatted_data = [
                    {
                        "x": datetime.fromtimestamp(float(ts)).isoformat() + "Z",
                        "y": round(val, 4)
                    }
                    for ts, val in sorted(aggregated_data.items())
                ]
                results[direction] = formatted_data
            else:
                results[direction] = []

        return {
            "status": "success",
            "metric": "network_throughput_by_direction",
            "unit": unit.upper(),
            "time_range": {
                "start": start_time,
                "end": end_time,
                "step": step  
            },
            "data": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing throughput data: {str(e)}")

def parse_duration(duration: str) -> int:
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    unit = duration[-1]
    value = int(duration[:-1])
    return value * units.get(unit, 1)

def format_metric(prom_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = []
    for entry in prom_data['data']['result']:
        metric_meta = entry['metric']
        metric_name = metric_meta.get('__name__', '')
        device_name = metric_meta.get('device_name', 'unknown')

        timeseries = [
            {"timestamp": ts, "value": float(value)}
            for ts, value in entry['values']
        ]

        result.append({
            "metric": metric_name,
            "device_name": device_name,
            "data": timeseries
        })
    return result