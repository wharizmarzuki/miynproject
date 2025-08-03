from datetime import datetime
from operator import ge
from urllib import response
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import exists
from sqlalchemy.orm import Session
import httpx
from typing import Dict, Any, List
from snmp import database, models

get_db = database.get_db

router = APIRouter(
    prefix="/alerts",
    tags=["Alert Rules"]
)

PROMETHEUS_URL = "http://localhost:9090"
PROMETHEUS_RULES_ENDPOINT = f"{PROMETHEUS_URL}/api/v1/rules"

async def fetch_prometheus_rules() -> Dict[str, Any]:
    """Fetch alert rules from Prometheus"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(PROMETHEUS_RULES_ENDPOINT, timeout=30.0)
            response.raise_for_status()  
            return response.json()  
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to connect to Prometheus: {str(e)}"
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Prometheus API error: {str(e)}"
        )
    

@router.get("/discover")
async def discover_rule(db: Session = Depends(get_db)):
    try:
        response = await fetch_prometheus_rules()
        groups = response.get('data', {}).get('groups', [])
        
        rule_count = 0
        for group in groups:
            for rule in group.get('rules', []):
                if rule.get('type') != 'alerting':
                    continue

                exists = db.query(models.AlertRule).filter(models.AlertRule.name == rule.get('name')).first()
                if exists:
                    continue
                
                new_rule = models.AlertRule(
                    name=rule.get('name'),
                    duration=rule.get('duration', 0),
                    keep_firing_for=rule.get('keepFiringFor'),
                    severity=rule.get('labels', {}).get('severity'),
                    summary=rule.get('annotations', {}).get('summary', ''),
                    last_evaluation=datetime.fromisoformat(
                        rule.get('lastEvaluation').rstrip('Z')
                    ) if rule.get('lastEvaluation') else None
                )
                
                db.add(new_rule)
                rule_count += 1

        db.commit()
        return {"message": f"Discovered and inserted {rule_count} new alert rules successfully"}
    except Exception as e:
        db.rollback()
        raise e
    
@router.get("/")
def get_all_rules(db: Session = Depends(get_db)):
    return db.query(models.AlertRule).all()

@router.get("/{id}")
def get_rules(id: int,db: Session = Depends(get_db)):
    return db.query(models.AlertRule).filter(models.AlertRule.id == id).first()

@router.delete("/")
def delete_rules(id: int,db: Session = Depends(get_db)):
    db.query(models.AlertRule).filter(models.AlertRule.id == id).delete(synchronize_session=False)
    db.commit()
    return 'deleted'