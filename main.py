import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.orm import Session
from app.api.v1.endpoints import polling, devices, query, alert
from app.core import models
from app.core.database import engine, get_db
from services import snmp_service
from app.config.settings import settings
from services.snmp_service import get_snmp_client
from app.config.logging import logger

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
            logger.info("Application starting up...")
            
            db_gen = get_db()
            db: Session = next(db_gen)
            
            client = get_snmp_client()

            from app.api.v1.endpoints.polling import poll_all_device
            await poll_all_device(db, client)
            
            logger.info("Running scheduled device polling...")
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error during startup discovery: {str(e)}")
        
        await asyncio.sleep(settings.polling_interval)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    
    # # Run discovery on startup
    # await run_discovery()
    
    # Start background polling task
    logger.info("Starting background polling task...")
    polling_task = asyncio.create_task(run_polling())
    
    yield
    
    logger.info("Application shutting down...")
    # Cancel background task
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        logger.error("Background polling task cancelled")

app = FastAPI(
    title="SNMP Device Monitor",
    description="SNMP device discovery and monitoring API",
    lifespan=lifespan
)
from app.api.middleware import add_middleware_to_app
add_middleware_to_app(app)

app.include_router(devices.router)
app.include_router(polling.router)
app.include_router(query.router)
app.include_router(alert.router)
