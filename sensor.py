"""
Sensor Data Models
Pydantic models for sensor data validation and serialization.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class SensorData(BaseModel):
    """
    Model representing incoming sensor data from IoT devices.
    
    Attributes:
        device_id: Unique identifier for the IoT device
        property_id: Identifier for the specific property/sensor on the device
        current: Current reading in Amperes (A)
        voltage: Voltage reading in Volts (V)
        temperature: Temperature reading in Celsius (°C)
        timestamp: Time when the reading was taken
    """
    device_id: str = Field(..., description="Unique device identifier")
    property_id: str = Field(..., description="Property or sensor identifier")
    current: float = Field(..., ge=0, description="Current reading in Amperes")
    voltage: float = Field(..., ge=0, description="Voltage reading in Volts")
    temperature: float = Field(..., description="Temperature reading in Celsius")
    timestamp: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the reading"
    )


class SensorDataResponse(BaseModel):
    """Response model for sensor data storage confirmation."""
    success: bool
    message: str
    data: SensorData


class SensorDataPoint(BaseModel):
    """Model representing a single sensor data point from InfluxDB."""
    timestamp: datetime
    device_id: str
    property_id: str
    current: float
    voltage: float
    temperature: float
