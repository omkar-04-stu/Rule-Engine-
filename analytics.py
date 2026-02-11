"""
Analytics Router
API endpoints for sensor data evaluation and alert management.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.sensor import SensorData, SensorDataResponse
from app.models.rule import (
    RuleCreate,
    Rule,
    RuleUpdate,
    Alert,
    AlertResponse
)
from app.db.mysql import get_db_manager
from app.services.rule_engine import (
    get_rule_engine,
    initialize_default_rules
)


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    responses={404: {"description": "Not found"}}
)


def get_services():
    """
    Dependency to get database and rule engine instances.
    
    Returns:
        Tuple of (mysql_manager, rule_engine)
    """
    db = get_db_manager()
    engine = get_rule_engine()
    return db, engine


@router.post(
    "/evaluate",
    response_model=SensorDataResponse,
    summary="Evaluate Sensor Data",
    description="Submit sensor data for evaluation against configured rules"
)
async def evaluate_sensor_data(
    data: SensorData,
    services=Depends(get_services)
):
    """
    Evaluate sensor data against all enabled rules.
    
    This endpoint:
    1. Accepts sensor data from IoT devices
    2. Stores the data in MySQL
    3. Evaluates the data against all enabled rules
    4. Returns triggered alerts
    
    Returns:
        SensorDataResponse with success status and the submitted data
    """
    db, engine = services
    
    # Store data in MySQL
    stored = db.write_sensor_data(data)
    
    if not stored:
        raise HTTPException(
            status_code=500,
            detail="Failed to store sensor data in database"
        )
    
    # Evaluate rules
    alerts = engine.evaluate_sensor_data(data)
    
    # Save alerts to database
    for alert in alerts:
        db.save_alert({
            "id": alert.id,
            "rule_id": alert.rule_id,
            "rule_name": alert.rule_name,
            "device_id": alert.device_id,
            "property_id": alert.property_id,
            "parameter": alert.parameter,
            "operator": alert.operator,
            "threshold": alert.threshold,
            "actual_value": alert.actual_value,
            "severity": alert.severity,
            "message": alert.message,
            "timestamp": alert.timestamp
        })
    
    return SensorDataResponse(
        success=True,
        message=f"Data stored. {len(alerts)} alert(s) triggered.",
        data=data
    )


@router.get(
    "/alerts",
    response_model=AlertResponse,
    summary="Fetch Triggered Alerts",
    description="Retrieve alerts with optional filtering by device and severity"
)
async def get_alerts(
    device_id: Optional[str] = Query(
        None,
        description="Filter alerts by device ID"
    ),
    severity: Optional[str] = Query(
        None,
        regex="^(warning|critical)$",
        description="Filter alerts by severity level"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of alerts to return"
    ),
    services=Depends(get_services)
):
    """
    Fetch triggered alerts with optional filtering.
    
    Query Parameters:
        device_id: Filter alerts by device ID
        severity: Filter by severity (warning/critical)
        limit: Maximum number of alerts (default: 100)
    
    Returns:
        AlertResponse with list of alerts and total count
    """
    db, _ = services
    
    # Get alerts from database
    alerts_data = db.get_alerts(
        device_id=device_id,
        severity=severity,
        limit=limit
    )
    
    # Convert to Alert objects
    alerts = []
    for alert_dict in alerts_data:
        alerts.append(Alert(
            id=alert_dict["id"],
            rule_id=alert_dict["rule_id"],
            rule_name=alert_dict["rule_name"],
            device_id=alert_dict["device_id"],
            property_id=alert_dict["property_id"],
            parameter=alert_dict["parameter"],
            operator=alert_dict["operator"],
            threshold=alert_dict["threshold"],
            actual_value=alert_dict["actual_value"],
            severity=alert_dict["severity"],
            message=alert_dict["message"],
            timestamp=alert_dict["timestamp"]
        ))
    
    return AlertResponse(
        success=True,
        total=len(alerts),
        alerts=alerts
    )


@router.get(
    "/rules",
    response_model=List[Rule],
    summary="List All Rules",
    description="Retrieve all configured rules"
)
async def list_rules(
    enabled_only: bool = Query(
        False,
        description="Only return enabled rules"
    ),
    services=Depends(get_services)
):
    """
    List all configured rules.
    
    Query Parameters:
        enabled_only: If true, only return enabled rules
    
    Returns:
        List of Rule objects
    """
    _, engine = services
    rules = engine.get_all_rules()
    
    if enabled_only:
        rules = [r for r in rules if r.enabled]
    
    return rules


@router.post(
    "/rules",
    response_model=Rule,
    status_code=201,
    summary="Create New Rule",
    description="Create a new configurable rule"
)
async def create_rule(
    rule_data: RuleCreate,
    services=Depends(get_services)
):
    """
    Create a new rule for monitoring sensor data.
    
    Request Body:
        RuleCreate object with rule configuration
    
    Returns:
        Created Rule object with generated ID
    """
    _, engine = services
    rule = engine.create_rule(rule_data)
    return rule


@router.get(
    "/rules/{rule_id}",
    response_model=Rule,
    summary="Get Rule by ID",
    description="Retrieve a specific rule by its ID"
)
async def get_rule(
    rule_id: str,
    services=Depends(get_services)
):
    """
    Retrieve a specific rule by ID.
    
    Path Parameters:
        rule_id: Unique rule identifier
    
    Returns:
        Rule object
    
    Raises:
        HTTPException 404: Rule not found
    """
    _, engine = services
    rule = engine.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(
            status_code=404,
            detail=f"Rule with ID {rule_id} not found"
        )
    
    return rule


@router.put(
    "/rules/{rule_id}",
    response_model=Rule,
    summary="Update Rule",
    description="Update an existing rule's configuration"
)
async def update_rule(
    rule_id: str,
    rule_update: RuleUpdate,
    services=Depends(get_services)
):
    """
    Update an existing rule.
    
    Path Parameters:
        rule_id: Unique rule identifier
    
    Request Body:
        RuleUpdate object with fields to update
    
    Returns:
        Updated Rule object
    
    Raises:
        HTTPException 404: Rule not found
    """
    _, engine = services
    existing_rule = engine.get_rule(rule_id)
    
    if not existing_rule:
        raise HTTPException(
            status_code=404,
            detail=f"Rule with ID {rule_id} not found"
        )
    
    # Update fields that are provided
    update_data = rule_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing_rule, field, value)
    
    existing_rule.updated_at = datetime.utcnow()
    return existing_rule


@router.delete(
    "/rules/{rule_id}",
    status_code=204,
    summary="Delete Rule",
    description="Delete a rule by its ID"
)
async def delete_rule(
    rule_id: str,
    services=Depends(get_services)
):
    """
    Delete a rule by ID.
    
    Path Parameters:
        rule_id: Unique rule identifier
    
    Returns:
        No content (204)
    
    Raises:
        HTTPException 404: Rule not found
    """
    _, engine = services
    deleted = engine.delete_rule(rule_id)
    
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Rule with ID {rule_id} not found"
        )


@router.post(
    "/rules/initialize",
    response_model=List[Rule],
    summary="Initialize Default Rules",
    description="Create default monitoring rules for demonstration"
)
async def initialize_default_rules_endpoint(
    services=Depends(get_services)
):
    """
    Initialize the system with default monitoring rules.
    
    Creates rules for:
    - Temperature warnings (>80°C)
    - Temperature critical (>95°C)
    - Voltage warnings (>250V)
    - Voltage warnings (<190V)
    - Current warnings (>20A)
    - Current critical (>30A)
    
    Returns:
        List of created default rules
    """
    _, engine = services
    
    # Only initialize if no rules exist
    if len(engine.get_all_rules()) > 0:
        return engine.get_all_rules()
    
    rules = initialize_default_rules(engine)
    return rules


@router.get(
    "/history/{device_id}",
    response_model=List[Alert],
    summary="Get Alert History",
    description="Get alert history for a specific device"
)
async def get_device_alert_history(
    device_id: str,
    limit: int = Query(100, ge=1, le=1000),
    services=Depends(get_services)
):
    """
    Get alert history for a specific device.
    
    Path Parameters:
        device_id: Device identifier
    
    Query Parameters:
        limit: Maximum number of alerts to return
    
    Returns:
        List of alerts for the device
    """
    db, _ = services
    
    # Get alerts from database
    alerts_data = db.get_alerts(device_id=device_id, limit=limit)
    
    # Convert to Alert objects
    alerts = []
    for alert_dict in alerts_data:
        alerts.append(Alert(
            id=alert_dict["id"],
            rule_id=alert_dict["rule_id"],
            rule_name=alert_dict["rule_name"],
            device_id=alert_dict["device_id"],
            property_id=alert_dict["property_id"],
            parameter=alert_dict["parameter"],
            operator=alert_dict["operator"],
            threshold=alert_dict["threshold"],
            actual_value=alert_dict["actual_value"],
            severity=alert_dict["severity"],
            message=alert_dict["message"],
            timestamp=alert_dict["timestamp"]
        ))
    
    return alerts
