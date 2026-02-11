"""
Main Application Entry Point
FastAPI-based Rule Engine microservice for IoT energy monitoring.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import analytics
from app.services.rule_engine import get_rule_engine
from app.db.mysql import get_db_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events:
    - Startup: Initialize services and database tables
    - Shutdown: Cleanup resources
    """
    # Startup: Initialize database tables
    try:
        db = get_db_manager()
        db.create_tables()
        print("Database tables initialized successfully")
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
        print("Make sure MySQL is running and credentials are correct")
    
    # Initialize rule engine
    engine = get_rule_engine()
    
    print("=" * 50)
    print("IoT Rule Engine Microservice")
    print("=" * 50)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print("-" * 50)
    
    yield
    
    # Shutdown: Cleanup
    db = get_db_manager()
    db.close_connection()
    
    print("-" * 50)
    print(f"Shutting down at: {datetime.utcnow().isoformat()}")


# Create FastAPI application
app = FastAPI(
    title="IoT Rule Engine",
    description="""
    Production-ready Rule Engine microservice for IoT-based energy monitoring.
    
    ## Features
    - Accept sensor data from IoT devices
    - Store time-series data in MySQL
    - Evaluate configurable rules against sensor data
    - Generate alerts when rule conditions are met
    
    ## Architecture
    ```
    Sensors → FastAPI → MySQL → Rule Engine → Alerts
    ```
    """,
    version="1.0.0",
    lifespan=lifespan
)


# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions globally."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc) if os.getenv("DEBUG") else "An error occurred"
        }
    )


# Health check endpoint
@app.get(
    "/",
    tags=["Health"],
    summary="Health Check",
    description="Check if the service is running"
)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status with timestamp
    """
    return {
        "status": "healthy",
        "service": "IoT Rule Engine",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


# Include routers
app.include_router(analytics.router)


# Service info endpoint
@app.get(
    "/info",
    tags=["Health"],
    summary="Service Information",
    description="Get detailed service information"
)
async def service_info():
    """
    Get detailed service information.
    
    Returns:
        Service details including available endpoints
    """
    engine = get_rule_engine()
    rules_count = len(engine.get_all_rules())
    
    return {
        "service": "IoT Rule Engine Microservice",
        "version": "1.0.0",
        "description": "Rule engine for IoT-based energy monitoring",
        "status": "running",
        "statistics": {
            "total_rules": rules_count,
            "enabled_rules": len([r for r in engine.get_all_rules() if r.enabled]),
            "total_alerts": len(engine.get_all_alerts())
        },
        "endpoints": {
            "health": "GET /",
            "info": "GET /info",
            "evaluate": "POST /analytics/evaluate",
            "alerts": "GET /analytics/alerts",
            "rules": "GET /analytics/rules",
            "create_rule": "POST /analytics/rules",
            "get_rule": "GET /analytics/rules/{rule_id}",
            "update_rule": "PUT /analytics/rules/{rule_id}",
            "delete_rule": "DELETE /analytics/rules/{rule_id}",
            "init_defaults": "POST /analytics/rules/initialize"
        },
        "documentation": "/docs",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment or use defaults
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
