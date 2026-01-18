"""
Data models and mock data generators for UGV-MON.

This module contains:
- Data models/types for ICD parsed data
- Mock data generator for UI development and testing
- Data structures for operational state, logs, and metrics

Note: In production, this will be replaced/extended with actual
Scapy capture and ICD parsing modules.
"""

from .models import DashboardState, LogEntry, DeviceStatus
from .mock_data import MockDataGenerator

__all__ = [
    "DashboardState",
    "LogEntry", 
    "DeviceStatus",
    "MockDataGenerator",
]
