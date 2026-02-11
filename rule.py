"""
Rule Models
Pydantic models for configurable rules and alerts.
"""

from pydantic import BaseModel, Field, validator
from typing import Literal, Optional
from datetime import datetime


class RuleBase(BaseModel):
    """Base model for rule configuration."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    parameter: Literal["temperature", "voltage", "current"] = Field(
        ...,
        description="Sensor parameter to evaluate"
    )
    operator: Literal[">", "<", ">=", "<=", "=="] = Field(
        ...,
        description="Comparison operator"
    )
    threshold: float = Field(..., description="Threshold value for comparison")
    severity: Literal["warning", "critical"] = Field(
        ...,
        description="Severity level of the alert"
    )
    action_message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Message to display when rule is triggered"
    )
    enabled: bool = Field(default=True, description="Whether the rule is active")


class RuleCreate(RuleBase):
    """Model for creating a new rule."""
    pass


class Rule(RuleBase):
    """Complete rule model with ID and timestamps."""
    id: str = Field(..., description="Unique rule identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RuleUpdate(BaseModel):
    """Model for updating an existing rule."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    parameter: Optional[Literal["temperature", "voltage", "current"]] = None
    operator: Optional[Literal[">", "<", ">=", "<=", "=="]] = None
    threshold: Optional[float] = None
    severity: Optional[Literal["warning", "critical"]] = None
    action_message: Optional[str] = Field(None, min_length=1, max_length=500)
    enabled: Optional[bool] = None


class Alert(BaseModel):
    """
    Model representing a triggered alert.
    
    Attributes:
        id: Unique alert identifier
        rule_id: ID of the rule that triggered this alert
        rule_name: Name of the rule that triggered this alert
        device_id: Device that caused the alert
        property_id: Property that caused the alert
        parameter: Parameter that triggered the alert
        operator: Operator used in the rule
        threshold: Threshold value from the rule
        actual_value: Actual sensor value that triggered the alert
        severity: Severity level from the rule
        message: Alert message from the rule
        timestamp: When the alert was triggered
    """
    id: str
    rule_id: str
    rule_name: str
    device_id: str
    property_id: str
    parameter: str
    operator: str
    threshold: float
    actual_value: float
    severity: str
    message: str
    timestamp: datetime


class AlertResponse(BaseModel):
    """Response model for alert queries."""
    success: bool
    total: int
    alerts: list[Alert]
