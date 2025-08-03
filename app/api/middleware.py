import time
import uuid
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Log request start
        start_time = time.time()
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - Started"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Time: {process_time:.3f}s"
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        
        return response

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware for consistent error responses
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
            
        except HTTPException as http_exc:
            # FastAPI HTTPExceptions - let them pass through normally
            raise http_exc
            
        except ValueError as val_err:
            # Value errors - return 400 Bad Request
            logger.error(f"ValueError on {request.url.path}: {str(val_err)}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Bad Request",
                    "message": str(val_err),
                    "path": str(request.url.path)
                }
            )
            
        except ConnectionError as conn_err:
            # Connection errors (SNMP, Prometheus, etc.)
            logger.error(f"Connection error on {request.url.path}: {str(conn_err)}")
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service Unavailable", 
                    "message": "External service connection failed",
                    "path": str(request.url.path)
                }
            )
            
        except Exception as exc:
            # Catch-all for unexpected errors
            logger.error(f"Unhandled error on {request.url.path}: {str(exc)}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "path": str(request.url.path)
                }
            )

class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Performance monitoring middleware
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.slow_request_threshold = 2.0  # Log requests slower than 2 seconds
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Log slow requests
        if process_time > self.slow_request_threshold:
            logger.warning(
                f"SLOW REQUEST: {request.method} {request.url.path} - "
                f"Time: {process_time:.3f}s"
            )
        
        # Add timing header
        response.headers["X-Response-Time"] = f"{process_time:.3f}s"
        
        return response

def setup_cors_middleware(app):
    """
    Setup CORS middleware for frontend access
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8080",  # Vue default
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080", 
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

def add_middleware_to_app(app):
    """
    Add all middleware to the FastAPI application
    """
    
    # Add middleware in reverse order (last added = first executed)
    
    # 1. CORS (should be last/first in chain)
    setup_cors_middleware(app)
    
    # 2. Error handling (catch all errors)
    app.add_middleware(ErrorHandlingMiddleware)
    
    # 3. Performance monitoring
    app.add_middleware(PerformanceMiddleware)
    
    # 4. Request logging (should be early in chain)
    app.add_middleware(RequestLoggingMiddleware)
    
    logger.info("✅ API Middleware configured successfully")