import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.orm import Session
from snmp import models
from snmp.database import engine, get_db
from routers import devices, device_polling, query, alert
from services import snmp_service

models.Base.metadata.create_all(engine)

# async def run_discovery():
#     """Run device discovery on startup"""
#     print("Running device discovery on startup...")
#     try:
#         # Get database session
#         db_gen = get_db()
#         db: Session = next(db_gen)
        
#         # Import and call the discovery function directly
#         from routers.devices import discovery
#         result = await discovery(network="192.168.254.1", subnet="27", db=db)
        
#         print(f"Discovery completed: {result.devices_found} devices found out of {result.total_scanned} scanned")
        
#         # Close database session
#         db.close()
        
#     except Exception as e:
#         print(f"Error during startup discovery: {str(e)}")

async def run_polling():
    """Run device polling every minute"""
    while True:
        try:
            print("Running scheduled device polling...")
            
            # Get database session
            db_gen = get_db()
            db: Session = next(db_gen)
            
            # Import and call the polling function directly
            from routers.device_polling import poll_all_device
            await poll_all_device(db=db)
            
            print("Polling completed successfully")
            
            # Close database session
            db.close()
            
        except Exception as e:
            print(f"Error during scheduled polling: {str(e)}")
        
        # Wait 1 minute before next poll
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application starting up...")
    
    # # Run discovery on startup
    # await run_discovery()
    
    # Start background polling task
    print("Starting background polling task...")
    polling_task = asyncio.create_task(run_polling())
    
    yield
    
    print("Application shutting down...")
    # Cancel background task
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        print("Background polling task cancelled")

app = FastAPI(
    title="SNMP Device Monitor",
    description="SNMP device discovery and monitoring API",
    lifespan=lifespan
)

app.include_router(devices.router)
app.include_router(device_polling.router)
app.include_router(query.router)
app.include_router(alert.router)
