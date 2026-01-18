"""
UGV-MON Dashboard Configuration Module.

Centralizes all configuration settings for the monitoring dashboard.
Settings can be overridden via environment variables for deployment flexibility.

Configuration Sections:
- Application: Server host, port, debug mode
- Network: UDP capture settings, interface, ports
- UI: Polling intervals, buffer sizes, display limits
- Thresholds: Alert thresholds for availability, jitter, loss
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AppConfig:
    """Application server configuration."""
    
    name: str = "UGV-MON Dashboard"
    version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8050


@dataclass
class NetworkConfig:
    """Network capture configuration for VIC↔OCS monitoring."""
    
    # Interface to capture on (lo for loopback, eno2/eno3 for production)
    interface: str = "lo"
    
    # UDP filter settings (VIC→OCS flow)
    source_port: int = 50000
    dest_port: int = 61000
    
    # Buffer settings
    buffer_size: int = 4096


@dataclass 
class UIConfig:
    """Dashboard UI configuration."""
    
    # Polling interval in milliseconds (dcc.Interval)
    poll_interval_ms: int = 2000
    
    # Data retention limits (bounded buffers)
    max_log_entries: int = 200
    max_chart_points: int = 60
    
    # Timeline duration in seconds
    timeline_duration_sec: int = 3600  # 1 hour
    
    # Availability calculation window (seconds)
    availability_window_5min: int = 300
    availability_window_1hour: int = 3600
    
    # Down detection threshold (seconds without packet)
    down_threshold_sec: float = 5.0


@dataclass
class ThresholdConfig:
    """Alert and warning thresholds for monitoring."""
    
    # Packet loss threshold (packets)
    packet_loss_warning: int = 5
    
    # Jitter thresholds (milliseconds)
    jitter_warning_ms: float = 10.0
    jitter_critical_ms: float = 50.0
    
    # Availability thresholds (percentage)
    availability_warning: float = 99.0
    availability_critical: float = 95.0
    
    # Checksum failure threshold (percentage)
    checksum_fail_warning: float = 1.0


@dataclass
class ICDConfig:
    """ICD v1.0 parsing configuration."""
    
    # Header structure (12 bytes total)
    header_size: int = 12
    timestamp_offset: int = 0
    timestamp_size: int = 4  # Last byte is sequence number
    msg_id_offset: int = 4
    msg_id_size: int = 4
    reserved_offset: int = 8
    reserved_size: int = 2
    data_length_offset: int = 10
    data_length_size: int = 2
    
    # Checksum
    checksum_size: int = 2
    
    # Status report specifics
    status_report_msg_code: int = 0x01
    status_report_data_size: int = 87
    
    # Endianness
    byte_order: str = "little"


@dataclass
class DeviceConfig:
    """Device connectivity configuration."""
    
    # Device list (bits 9..0 in device presence word)
    devices: List[Dict[str, str]] = field(default_factory=lambda: [
        {"id": "vic", "name": "VIC", "bit": 0},
        {"id": "rdc", "name": "RDC", "bit": 1},
        {"id": "adc", "name": "ADC", "bit": 2},
        {"id": "fcam", "name": "FCAM", "bit": 3},
        {"id": "rcam", "name": "RCAM", "bit": 4},
        {"id": "aux", "name": "AUX", "bit": 5},
        {"id": "scs", "name": "SCS", "bit": 6},
        {"id": "dip", "name": "DIP", "bit": 7},
        {"id": "tcc", "name": "TCC", "bit": 8},
        {"id": "tm", "name": "TM", "bit": 9},
    ])


@dataclass
class Config:
    """
    Master configuration container.
    
    Usage:
        from ugv_mon.config import config
        print(config.app.port)
        print(config.network.interface)
    """
    
    app: AppConfig = field(default_factory=AppConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    threshold: ThresholdConfig = field(default_factory=ThresholdConfig)
    icd: ICDConfig = field(default_factory=ICDConfig)
    device: DeviceConfig = field(default_factory=DeviceConfig)
    
    @classmethod
    def from_env(cls) -> "Config":
        """
        Create configuration from environment variables.
        
        Environment variable mapping:
        - UGV_MON_DEBUG: Enable debug mode
        - UGV_MON_HOST: Server host
        - UGV_MON_PORT: Server port
        - UGV_MON_INTERFACE: Network interface
        - UGV_MON_POLL_INTERVAL: Polling interval (ms)
        """
        config = cls()
        
        # Override from environment
        if os.getenv("UGV_MON_DEBUG"):
            config.app.debug = os.getenv("UGV_MON_DEBUG", "true").lower() == "true"
        if os.getenv("UGV_MON_HOST"):
            config.app.host = os.getenv("UGV_MON_HOST", "0.0.0.0")
        if os.getenv("UGV_MON_PORT"):
            config.app.port = int(os.getenv("UGV_MON_PORT", "8050"))
        if os.getenv("UGV_MON_INTERFACE"):
            config.network.interface = os.getenv("UGV_MON_INTERFACE", "lo")
        if os.getenv("UGV_MON_POLL_INTERVAL"):
            config.ui.poll_interval_ms = int(os.getenv("UGV_MON_POLL_INTERVAL", "2000"))
            
        return config


# Global configuration instance
config = Config.from_env()
