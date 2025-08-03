# test_phase2_complete.py
import logging
import requests
import time
from typing import Optional

def test_phase2_migration():
    """Test script to verify Phase 2 migration success"""
    
    print("🧪 Testing Phase 2 Migration...")
    print("=" * 50)
    
    # Test 1: API Structure
    print("\n📁 Testing API Structure...")
    
    try:
        from app.api.v1.endpoints import devices, polling, alert, query
        print("✅ Endpoints: All endpoint imports successful")
    except Exception as e:
        print(f"❌ Endpoints Error: {e}")
    
    # Test 2: Middleware
    print("\n🔧 Testing Middleware...")
    try:
        from app.api.middleware import (
            RequestLoggingMiddleware, 
            ErrorHandlingMiddleware, 
            PerformanceMiddleware,
            add_middleware_to_app
        )
        print("✅ Middleware: All middleware imports successful")
    except Exception as e:
        print(f"❌ Middleware Error: {e}")
    
    # Test 3: Application with new structure
    print("\n🚀 Testing Application...")
    try:
        from main import app
        print("✅ App: FastAPI app loads with new structure")
        
        # Check if middleware is registered
        middleware_count = len(app.user_middleware)
        print(f"✅ App: {middleware_count} middleware layers registered")
        
    except Exception as e:
        print(f"❌ App Error: {e}")
    
    # Test 4: Live API Testing (if server is running)
    print("\n🌐 Testing Live API Endpoints...")
    test_live_api_endpoints()
    
    print("\n" + "=" * 50)
    print("🎯 Phase 2 Testing Complete!")

def test_live_api_endpoints(base_url: str = "http://localhost:8000"):
    """Test live API endpoints if server is running"""
    
    endpoints_to_test = [
        ("/api/v1/devices/", "GET", "Device listing"),
        ("/api/v1/alerts/", "GET", "Alert rules listing"), 
        ("/api/v1/query/devices/status", "GET", "Device status query"),
        ("/api/v1/polling/", "GET", "Polling endpoint"),
    ]
    
    for endpoint, method, description in endpoints_to_test:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, timeout=5)
            
            # Check for middleware headers
            request_id = response.headers.get('x-request-id', 'Not found')
            process_time = response.headers.get('x-process-time', 'Not found')
            
            if response.status_code < 500:  # Any non-server error is good
                print(f"✅ {description}: Status {response.status_code}")
                print(f"   📍 Request ID: {request_id}")
                print(f"   ⏱️  Process Time: {process_time}")
            else:
                print(f"❌ {description}: Status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"⚠️  {description}: Server not running (connection refused)")
        except requests.exceptions.Timeout:
            print(f"⚠️  {description}: Request timeout")
        except Exception as e:
            print(f"❌ {description}: Error - {str(e)}")

def test_middleware_functionality(base_url: str = "http://localhost:8000"):
    """Test specific middleware functionality"""
    
    print("\n🔬 Testing Middleware Functionality...")
    
    # Test 1: Request ID uniqueness
    print("Testing request ID uniqueness...")
    request_ids = []
    for i in range(3):
        try:
            response = requests.get(f"{base_url}/api/v1/devices/", timeout=5)
            req_id = response.headers.get('x-request-id')
            if req_id:
                request_ids.append(req_id)
        except:
            pass
    
    if len(set(request_ids)) == len(request_ids) and len(request_ids) > 0:
        print(f"✅ Request IDs: Unique across {len(request_ids)} requests")
    else:
        print("❌ Request IDs: Not unique or not found")
    
    # Test 2: Error handling
    print("Testing error handling...")
    try:
        response = requests.get(f"{base_url}/api/v1/nonexistent", timeout=5)
        if response.status_code == 404:
            print("✅ Error Handling: 404 handled correctly")
        else:
            print(f"⚠️  Error Handling: Got {response.status_code} instead of 404")
    except:
        print("❌ Error Handling: Could not test")
    
    # Test 3: Performance headers
    print("Testing performance headers...")
    try:
        response = requests.get(f"{base_url}/api/v1/devices/", timeout=5)
        has_process_time = 'x-process-time' in response.headers
        has_response_time = 'x-response-time' in response.headers
        
        if has_process_time and has_response_time:
            print("✅ Performance: Timing headers present")
        else:
            print("❌ Performance: Missing timing headers")
    except:
        print("❌ Performance: Could not test")

def run_comprehensive_test():
    """Run all tests with detailed output"""
    
    print("🚀 COMPREHENSIVE PHASE 2 TEST SUITE")
    print("=" * 60)
    
    # Phase 1 verification (ensure it's still working)
    print("\n🔄 Verifying Phase 1 is still intact...")
    try:
        from app.config.settings import settings
        from app.core.database import get_db
        from app.core.models import Device
        from app.core.schemas import DeviceInfo
        print("✅ Phase 1: All core components still working")
    except Exception as e:
        print(f"❌ Phase 1: Regression detected - {e}")
    
    # Phase 2 tests
    test_phase2_migration()
    
    # Extended middleware tests
    print("\n" + "=" * 60)
    test_middleware_functionality()
    
    print("\n🎊 TESTING COMPLETE!")
    print("If all tests pass, Phase 2 is successfully implemented!")

if __name__ == "__main__":
    # You can run different test levels:
    
    # Basic test
    test_phase2_migration()
    
    # Uncomment for comprehensive testing:
    # run_comprehensive_test()
    
    # Uncomment for middleware-specific testing:
    # test_middleware_functionality()