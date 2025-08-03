# test_phase1_complete.py
import logging

def test_phase1_migration():
    """Test script to verify Phase 1 migration success"""
    
    print("🧪 Testing Phase 1 Migration...")
    
    # Test 1: Configuration
    try:
        from app.config.settings import settings
        print(f"✅ Config: SNMP Community = {settings.snmp_community}")
        print(f"✅ Config: Push Gateway = {settings.pushgateway_url}")
    except Exception as e:
        print(f"❌ Config Error: {e}")
    
    # Test 2: Database
    try:
        from app.core.database import get_db, engine
        print("✅ Database: Import successful")
    except Exception as e:
        print(f"❌ Database Error: {e}")
    
    # Test 3: Models
    try:
        from app.core.models import Device, AlertRule
        print("✅ Models: Import successful")
    except Exception as e:
        print(f"❌ Models Error: {e}")
    
    # Test 4: Schemas (THIS IS WHAT WE'RE FIXING)
    try:
        from app.core.schemas import DeviceInfo, DiscoveryResponse
        print("✅ Schemas: Import successful")
    except Exception as e:
        print(f"❌ Schemas Error: {e}")
    
    # Test 5: Logging
    try:
        from app.config.logging import logger
        logger.info("Test log message")
        print("✅ Logging: Configuration successful")
    except Exception as e:
        print(f"❌ Logging Error: {e}")
    
    # Test 6: Application startup
    try:
        from main import app
        print("✅ App: FastAPI app loads successfully") 
    except Exception as e:
        print(f"❌ App Error: {e}")

if __name__ == "__main__":
    test_phase1_migration()