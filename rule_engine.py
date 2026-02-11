"""
Rule Engine Service
Core rule evaluation logic for the IoT energy monitoring system.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from app.models.sensor import SensorData, SensorDataPoint
from app.models.rule import Rule, RuleCreate, Alert


class RuleEngine:
    """
    Rule Engine for evaluating sensor data against configurable rules.
    
    This engine:
    - Stores and manages configurable rules
    - Evaluates sensor data against rules
    - Generates alerts when rule conditions are met
    - Maintains alert history
    """
    
    def __init__(self):
        """Initialize the Rule Engine with empty rule and alert storage."""
        # In-memory rule storage (replace with database in production)
        self.rules: dict[str, Rule] = {}
        # In-memory alert storage
        self.alerts: List[Alert] = []
    
    def create_rule(self, rule_data: RuleCreate) -> Rule:
        """
        Create and store a new rule.
        
        Args:
            rule_data: RuleCreate object with rule configuration
            
        Returns:
            Created Rule object
        """
        rule_id = str(uuid.uuid4())
        rule = Rule(
            id=rule_id,
            **rule_data.model_dump()
        )
        self.rules[rule_id] = rule
        return rule
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """
        Retrieve a rule by ID.
        
        Args:
            rule_id: Unique rule identifier
            
        Returns:
            Rule object if found, None otherwise
        """
        return self.rules.get(rule_id)
    
    def get_all_rules(self) -> List[Rule]:
        """
        Retrieve all stored rules.
        
        Returns:
            List of all Rule objects
        """
        return list(self.rules.values())
    
    def delete_rule(self, rule_id: str) -> bool:
        """
        Delete a rule by ID.
        
        Args:
            rule_id: Unique rule identifier
            
        Returns:
            True if rule was deleted, False if not found
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False
    
    def evaluate_condition(self, actual_value: float, rule: Rule) -> bool:
        """
        Evaluate a single rule condition against an actual value.
        
        Args:
            actual_value: The actual sensor reading
            rule: The rule to evaluate
            
        Returns:
            True if condition is met, False otherwise
        """
        threshold = rule.threshold
        
        if rule.operator == ">":
            return actual_value > threshold
        elif rule.operator == "<":
            return actual_value < threshold
        elif rule.operator == ">=":
            return actual_value >= threshold
        elif rule.operator == "<=":
            return actual_value <= threshold
        elif rule.operator == "==":
            return actual_value == threshold
        
        return False
    
    def evaluate_sensor_data(self, data: SensorData) -> List[Alert]:
        """
        Evaluate sensor data against all enabled rules.
        
        Args:
            data: SensorData object with current readings
            
        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        
        for rule in self.rules.values():
            # Skip disabled rules
            if not rule.enabled:
                continue
            
            # Get the actual value based on the parameter
            if rule.parameter == "temperature":
                actual_value = data.temperature
            elif rule.parameter == "voltage":
                actual_value = data.voltage
            elif rule.parameter == "current":
                actual_value = data.current
            else:
                continue
            
            # Evaluate the condition
            if self.evaluate_condition(actual_value, rule):
                # Create an alert
                alert = Alert(
                    id=str(uuid.uuid4()),
                    rule_id=rule.id,
                    rule_name=rule.name,
                    device_id=data.device_id,
                    property_id=data.property_id,
                    parameter=rule.parameter,
                    operator=rule.operator,
                    threshold=rule.threshold,
                    actual_value=actual_value,
                    severity=rule.severity,
                    message=rule.action_message,
                    timestamp=datetime.utcnow()
                )
                triggered_alerts.append(alert)
                self.alerts.append(alert)
        
        return triggered_alerts
    
    def evaluate_data_point(self, data_point: SensorDataPoint) -> List[Alert]:
        """
        Evaluate a SensorDataPoint against all enabled rules.
        
        Args:
            data_point: SensorDataPoint from InfluxDB
            
        Returns:
            List of triggered alerts
        """
        # Convert SensorDataPoint to SensorData for evaluation
        data = SensorData(
            device_id=data_point.device_id,
            property_id=data_point.property_id,
            current=data_point.current,
            voltage=data_point.voltage,
            temperature=data_point.temperature,
            timestamp=data_point.timestamp
        )
        return self.evaluate_sensor_data(data)
    
    def get_alerts(
        self,
        device_id: str = None,
        severity: str = None,
        limit: int = 100
    ) -> List[Alert]:
        """
        Retrieve alerts with optional filtering.
        
        Args:
            device_id: Optional device ID filter
            severity: Optional severity filter (warning/critical)
            limit: Maximum number of alerts to return
            
        Returns:
            List of filtered alerts
        """
        filtered_alerts = self.alerts
        
        if device_id:
            filtered_alerts = [
                a for a in filtered_alerts if a.device_id == device_id
            ]
        
        if severity:
            filtered_alerts = [
                a for a in filtered_alerts if a.severity == severity
            ]
        
        # Sort by timestamp (most recent first) and limit
        filtered_alerts.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered_alerts[:limit]
    
    def get_all_alerts(self) -> List[Alert]:
        """
        Retrieve all alerts.
        
        Returns:
            List of all alerts
        """
        return sorted(self.alerts, key=lambda x: x.timestamp, reverse=True)
    
    def clear_alerts(self):
        """Clear all stored alerts."""
        self.alerts = []


# Global Rule Engine instance
_rule_engine: Optional[RuleEngine] = None


def get_rule_engine() -> RuleEngine:
    """
    Get or create the global Rule Engine instance.
    
    Returns:
        RuleEngine instance
    """
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = RuleEngine()
    return _rule_engine


def initialize_default_rules(engine: RuleEngine) -> List[Rule]:
    """
    Initialize default rules for demonstration purposes.
    
    Args:
        engine: RuleEngine instance
        
    Returns:
        List of created default rules
    """
    default_rules_data = [
        RuleCreate(
            name="High Temperature Warning",
            description="Triggered when temperature exceeds 80°C",
            parameter="temperature",
            operator=">",
            threshold=80.0,
            severity="warning",
            action_message="Temperature is high: {value}°C. Consider reducing load."
        ),
        RuleCreate(
            name="Critical Temperature Alert",
            description="Triggered when temperature exceeds 95°C",
            parameter="temperature",
            operator=">",
            threshold=95.0,
            severity="critical",
            action_message="CRITICAL: Temperature exceeded {value}°C! Immediate action required!"
        ),
        RuleCreate(
            name="High Voltage Warning",
            description="Triggered when voltage exceeds 250V",
            parameter="voltage",
            operator=">",
            threshold=250.0,
            severity="warning",
            action_message="Voltage is high: {value}V. Check power supply."
        ),
        RuleCreate(
            name="Low Voltage Warning",
            description="Triggered when voltage drops below 190V",
            parameter="voltage",
            operator="<",
            threshold=190.0,
            severity="warning",
            action_message="Voltage is low: {value}V. Check power supply."
        ),
        RuleCreate(
            name="High Current Warning",
            description="Triggered when current exceeds 20A",
            parameter="current",
            operator=">",
            threshold=20.0,
            severity="warning",
            action_message="Current is high: {value}A. Reduce electrical load."
        ),
        RuleCreate(
            name="Critical Current Alert",
            description="Triggered when current exceeds 30A",
            parameter="current",
            operator=">",
            threshold=30.0,
            severity="critical",
            action_message="CRITICAL: Current exceeded {value}A! Risk of overload!"
        ),
    ]
    
    created_rules = []
    for rule_data in default_rules_data:
        rule = engine.create_rule(rule_data)
        created_rules.append(rule)
    
    return created_rules
