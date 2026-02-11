"""
InfluxDB Database Layer
Handles connection and operations with InfluxDB time-series database.
"""

import os
from typing import Optional, List
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.read_api import QueryApi

from app.models.sensor import SensorData, SensorDataPoint


class InfluxDBManager:
    """
    Manages InfluxDB connections and operations.
    
    This class provides methods for:
    - Writing sensor data to InfluxDB
    - Reading latest sensor data from InfluxDB
    - Managing InfluxDB client lifecycle
    """
    
    def __init__(
        self,
        url: str = None,
        token: str = None,
        org: str = None,
        bucket: str = None
    ):
        """
        Initialize InfluxDB connection parameters.
        
        Environment variables can be used as fallback:
        - INFLUXDB_URL
        - INFLUXDB_TOKEN
        - INFLUXDB_ORG
        - INFLUXDB_BUCKET
        """
        self.url = url or os.getenv("INFLUXDB_URL", "http://localhost:8086")
        self.token = token or os.getenv("INFLUXDB_TOKEN", "my-super-secret-token")
        self.org = org or os.getenv("INFLUXDB_ORG", "energy-org")
        self.bucket = bucket or os.getenv("INFLUXDB_BUCKET", "sensor-data")
        
        # Initialize InfluxDB client
        self.client = InfluxDBClient(
            url=self.url,
            token=self.token,
            org=self.org
        )
        
        # Get write and query APIs
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
    
    def write_sensor_data(self, data: SensorData) -> bool:
        """
        Write sensor data point to InfluxDB.
        
        Args:
            data: SensorData object containing the readings
            
        Returns:
            True if write was successful, False otherwise
        """
        try:
            # Create a data point with measurements
            point = (
                Point("sensor_reading")
                .tag("device_id", data.device_id)
                .tag("property_id", data.property_id)
                .field("current", data.current)
                .field("voltage", data.voltage)
                .field("temperature", data.temperature)
                .time(data.timestamp or datetime.utcnow())
            )
            
            # Write to InfluxDB
            self.write_api.write(
                bucket=self.bucket,
                org=self.org,
                record=point
            )
            return True
            
        except Exception as e:
            print(f"Error writing to InfluxDB: {e}")
            return False
    
    def get_latest_reading(
        self,
        device_id: str,
        property_id: str = None
    ) -> Optional[SensorDataPoint]:
        """
        Fetch the latest sensor reading for a device.
        
        Args:
            device_id: Device to query readings for
            property_id: Optional specific property to query
            
        Returns:
            SensorDataPoint if found, None otherwise
        """
        try:
            # Build flux query
            from influxdb_client import Point
            from flux import flux
            
            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start:)
                |> -1h filter(fn: (r) => r["_measurement"] == "sensor_reading")
                |> filter(fn: (r) => r["device_id"] == "{device_id}")
            '''
            
            if property_id:
                query = query[:-1] + f'|> filter(fn: (r) => r["property_id"] == "{property_id}")\n'
            
            query += '''
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 1)
            '''
            
            # Execute query
            result = self.query_api.query_data_frame(query)
            
            if result.empty:
                return None
            
            # Extract data from result
            row = result.iloc[0]
            
            return SensorDataPoint(
                timestamp=row["_time"],
                device_id=row["device_id"],
                property_id=row["property_id"],
                current=row["_field"] == "current" and row["_value"] or 0,
                voltage=row["_field"] == "voltage" and row["_value"] or 0,
                temperature=row["_field"] == "temperature" and row["_value"] or 0
            )
            
        except Exception as e:
            print(f"Error querying InfluxDB: {e}")
            return None
    
    def get_all_latest_readings(self) -> List[SensorDataPoint]:
        """
        Fetch the latest sensor reading for all devices.
        
        Returns:
            List of SensorDataPoint objects
        """
        try:
            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: -1h)
                |> filter(fn: (r) => r["_measurement"] == "sensor_reading")
                |> group(columns: ["device_id", "property_id"])
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 1)
            '''
            
            result = self.query_api.query_data_frame(query)
            
            if result.empty:
                return []
            
            # Process results and create SensorDataPoint objects
            readings = []
            for _, row in result.iterrows():
                readings.append(SensorDataPoint(
                    timestamp=row["_time"],
                    device_id=row["device_id"],
                    property_id=row["property_id"],
                    current=row["_field"] == "current" and row["_value"] or 0,
                    voltage=row["_field"] == "voltage" and row["_value"] or 0,
                    temperature=row["_field"] == "temperature" and row["_value"] or 0
                ))
            
            return readings
            
        except Exception as e:
            print(f"Error querying InfluxDB: {e}")
            return []
    
    def close(self):
        """Close the InfluxDB client connection."""
        if self.client:
            self.client.close()


# Global InfluxDB manager instance
_influx_manager: Optional[InfluxDBManager] = None


def get_influx_manager() -> InfluxDBManager:
    """
    Get or create the global InfluxDB manager instance.
    
    Returns:
        InfluxDBManager instance
    """
    global _influx_manager
    if _influx_manager is None:
        _influx_manager = InfluxDBManager()
    return _influx_manager
