"""
Database Layer (MySQL/SQLite)
Handles connection and operations with MySQL or SQLite database.
Uses SQLite for demonstration when MySQL is not available.
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager

from app.models.sensor import SensorData, SensorDataPoint


class DatabaseManager:
    """
    Manages database connections and operations.
    
    Supports both MySQL and SQLite:
    - MySQL: Production use with full features
    - SQLite: Demonstration/testing without MySQL server
    
    This class provides methods for:
    - Creating database tables
    - Inserting sensor data
    - Querying latest sensor data
    - Managing database connections
    """
    
    def __init__(
        self,
        db_type: str = None,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        database: str = None
    ):
        """
        Initialize database connection parameters.
        
        Environment variables:
        - DB_TYPE: "mysql" or "sqlite" (default: sqlite for demo)
        - MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
        """
        self.db_type = db_type or os.getenv("DB_TYPE", "sqlite")
        
        if self.db_type == "mysql":
            self._init_mysql(
                host=host or os.getenv("MYSQL_HOST", "localhost"),
                port=int(port or os.getenv("MYSQL_PORT", "3306")),
                user=user or os.getenv("MYSQL_USER", "root"),
                password=password or os.getenv("MYSQL_PASSWORD", "password"),
                database=database or os.getenv("MYSQL_DATABASE", "energy_monitoring")
            )
        else:
            self._init_sqlite(database or "energy_monitoring.db")
    
    def _init_mysql(self, host: str, port: int, user: str, password: str, database: str):
        """Initialize MySQL connection parameters."""
        try:
            import mysql.connector
            from mysql.connector import Error
            
            self.mysql = mysql
            self.mysql_error = Error
            self.host = host
            self.port = port
            self.user = user
            self.password = password
            self.database = database
            self.connection = None
            
        except ImportError:
            print("MySQL connector not available, falling back to SQLite")
            self.db_type = "sqlite"
            self._init_sqlite("energy_monitoring.db")
    
    def _init_sqlite(self, database: str):
        """Initialize SQLite database."""
        self.db_type = "sqlite"
        self.database = database
        self.connection = None
    
    def get_connection(self):
        """Get or create a database connection."""
        if self.db_type == "sqlite":
            return self._get_sqlite_connection()
        else:
            return self._get_mysql_connection()
    
    def _get_mysql_connection(self):
        """Get MySQL connection."""
        if self.connection is None or not self.connection.is_connected():
            try:
                self.connection = self.mysql.connector.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database
                )
            except self.mysql_error as e:
                print(f"MySQL connection failed: {e}")
                print("Falling back to SQLite for demonstration")
                self.db_type = "sqlite"
                return self._get_sqlite_connection()
        return self.connection
    
    def _get_sqlite_connection(self):
        """Get SQLite connection."""
        if self.connection is None:
            self.connection = sqlite3.connect(self.database)
            self.connection.row_factory = sqlite3.Row
        return self.connection
    
    def close_connection(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def create_tables(self):
        """Create required database tables if they don't exist."""
        create_sensor_table = """
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            property_id TEXT NOT NULL,
            current REAL NOT NULL,
            voltage REAL NOT NULL,
            temperature REAL NOT NULL,
            timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        create_alerts_table = """
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            rule_id TEXT NOT NULL,
            rule_name TEXT NOT NULL,
            device_id TEXT NOT NULL,
            property_id TEXT NOT NULL,
            parameter TEXT NOT NULL,
            operator TEXT NOT NULL,
            threshold REAL NOT NULL,
            actual_value REAL NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        create_rules_table = """
        CREATE TABLE IF NOT EXISTS rules (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            parameter TEXT NOT NULL,
            operator TEXT NOT NULL,
            threshold REAL NOT NULL,
            severity TEXT NOT NULL,
            action_message TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(create_sensor_table)
            cursor.execute(create_alerts_table)
            cursor.execute(create_rules_table)
            conn.commit()
            
            db_type_name = "MySQL" if self.db_type == "mysql" else "SQLite"
            print(f"Database tables created successfully ({db_type_name})")
            
        except Exception as e:
            print(f"Error creating tables: {e}")
            raise
        finally:
            cursor.close()
    
    def write_sensor_data(self, data: SensorData) -> bool:
        """
        Insert sensor data into the database.
        
        Args:
            data: SensorData object containing the readings
            
        Returns:
            True if insert was successful, False otherwise
        """
        insert_query = """
        INSERT INTO sensor_readings (device_id, property_id, current, voltage, temperature, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            timestamp = data.timestamp or datetime.utcnow()
            timestamp_str = timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
            
            cursor.execute(insert_query, (
                data.device_id,
                data.property_id,
                data.current,
                data.voltage,
                data.temperature,
                timestamp_str
            ))
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error inserting sensor data: {e}")
            return False
        finally:
            cursor.close()
    
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
        if property_id:
            query = """
            SELECT device_id, property_id, current, voltage, temperature, timestamp
            FROM sensor_readings
            WHERE device_id = ? AND property_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """
            params = (device_id, property_id)
        else:
            query = """
            SELECT device_id, property_id, current, voltage, temperature, timestamp
            FROM sensor_readings
            WHERE device_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """
            params = (device_id,)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            # Convert row to dict for consistent handling
            row_dict = {
                "device_id": row[0],
                "property_id": row[1],
                "current": row[2],
                "voltage": row[3],
                "temperature": row[4],
                "timestamp": row[5]
            }
            
            return SensorDataPoint(
                timestamp=datetime.fromisoformat(row_dict["timestamp"]) if isinstance(row_dict["timestamp"], str) else row_dict["timestamp"],
                device_id=row_dict["device_id"],
                property_id=row_dict["property_id"],
                current=row_dict["current"],
                voltage=row_dict["voltage"],
                temperature=row_dict["temperature"]
            )
            
        except Exception as e:
            print(f"Error querying sensor data: {e}")
            return None
        finally:
            cursor.close()
    
    def get_all_latest_readings(self) -> List[SensorDataPoint]:
        """
        Fetch the latest sensor reading for all devices.
        
        Returns:
            List of SensorDataPoint objects
        """
        query = """
        SELECT device_id, property_id, current, voltage, temperature, timestamp
        FROM sensor_readings sr1
        WHERE timestamp = (
            SELECT MAX(timestamp)
            FROM sensor_readings sr2
            WHERE sr1.device_id = sr2.device_id
            AND sr1.property_id = sr2.property_id
        )
        """
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            
            readings = []
            for row in rows:
                row_dict = {
                    "device_id": row[0],
                    "property_id": row[1],
                    "current": row[2],
                    "voltage": row[3],
                    "temperature": row[4],
                    "timestamp": row[5]
                }
                readings.append(SensorDataPoint(
                    timestamp=datetime.fromisoformat(row_dict["timestamp"]) if isinstance(row_dict["timestamp"], str) else row_dict["timestamp"],
                    device_id=row_dict["device_id"],
                    property_id=row_dict["property_id"],
                    current=row_dict["current"],
                    voltage=row_dict["voltage"],
                    temperature=row_dict["temperature"]
                ))
            
            return readings
            
        except Exception as e:
            print(f"Error querying sensor data: {e}")
            return []
        finally:
            cursor.close()
    
    def save_alert(self, alert_data: dict) -> bool:
        """
        Save an alert to the database.
        
        Args:
            alert_data: Dictionary containing alert information
            
        Returns:
            True if insert was successful, False otherwise
        """
        insert_query = """
        INSERT INTO alerts (id, rule_id, rule_name, device_id, property_id, 
                           parameter, operator, threshold, actual_value, 
                           severity, message, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            timestamp = alert_data.get("timestamp")
            timestamp_str = timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
            
            cursor.execute(insert_query, (
                alert_data["id"],
                alert_data["rule_id"],
                alert_data["rule_name"],
                alert_data["device_id"],
                alert_data["property_id"],
                alert_data["parameter"],
                alert_data["operator"],
                alert_data["threshold"],
                alert_data["actual_value"],
                alert_data["severity"],
                alert_data["message"],
                timestamp_str
            ))
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error saving alert: {e}")
            return False
        finally:
            cursor.close()
    
    def get_alerts(
        self,
        device_id: str = None,
        severity: str = None,
        limit: int = 100
    ) -> List[dict]:
        """
        Retrieve alerts with optional filtering.
        
        Args:
            device_id: Optional device ID filter
            severity: Optional severity filter (warning/critical)
            limit: Maximum number of alerts to return
            
        Returns:
            List of alert dictionaries
        """
        query = "SELECT * FROM alerts"
        conditions = []
        params = []
        
        if device_id:
            conditions.append("device_id = ?")
            params.append(device_id)
        
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            
            # Convert rows to dicts
            columns = ["id", "rule_id", "rule_name", "device_id", "property_id",
                      "parameter", "operator", "threshold", "actual_value",
                      "severity", "message", "timestamp"]
            
            alerts = []
            for row in rows:
                alert = dict(zip(columns, row))
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            print(f"Error querying alerts: {e}")
            return []
        finally:
            cursor.close()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    Get or create the global database manager instance.
    
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
