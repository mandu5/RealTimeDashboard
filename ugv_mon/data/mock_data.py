"""
Mock data generator for UGV-MON Dashboard.

Provides simulated data for UI development and testing when
actual VIC↔OCS traffic is not available.

This module will be replaced with actual Scapy capture and ICD
parsing in Day 2-3 of the development plan.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .models import (
    DashboardState,
    LogEntry,
    DeviceStatus,
    AvailabilitySegment,
    EmergencyStatus,
    ChartDataPoint,
)
from ..config import config


class MockDataGenerator:
    """
    Generates mock dashboard data for UI testing.
    
    Simulates realistic VIC↔OCS monitoring data including:
    - Packet capture metrics (PPS, pass rate)
    - Parse quality metrics (success rate, checksum failures)
    - Operational state changes
    - Device connectivity
    - Time series data for charts
    - Log entries
    
    Usage:
        generator = MockDataGenerator()
        initial_data = generator.generate_initial_data()
        # On each poll:
        updated_data = generator.update_data(current_data)
    """
    
    def __init__(self):
        """Initialize mock data generator with default state."""
        self._last_seq = 49195
        self._elapsed_time = 0
        self._logs_history: List[LogEntry] = []
        self._availability_segments: List[AvailabilitySegment] = [
            AvailabilitySegment(start_sec=0, end_sec=2700, is_up=True),
            AvailabilitySegment(start_sec=2700, end_sec=2850, is_up=False),
            AvailabilitySegment(start_sec=2850, end_sec=3600, is_up=True),
        ]
        
    def generate_initial_data(self) -> Dict:
        """
        Generate initial dashboard data for app startup.
        
        Returns:
            Dictionary containing full dashboard state
        """
        now = datetime.now()
        
        # Generate initial chart data (60 data points)
        chart_data = []
        for i in range(config.ui.max_chart_points):
            chart_data.append({
                "timestamp": (now - timedelta(seconds=60-i)).strftime("%H:%M:%S"),
                "pps": random.randint(900, 1100),
                "jitter": round(random.uniform(0.5, 2.5), 2),
            })
        
        # Generate initial log entries
        for i in range(15):
            log_time = now - timedelta(seconds=(15-i) * 2)
            self._logs_history.append(LogEntry(
                timestamp=log_time,
                sequence=self._last_seq + i,
                msg_code=f"0x{random.randint(0, 255):02X}",
                parse_ok=random.random() > 0.05,
                checksum_ok=random.random() > 0.03,
                mode=random.choice(["원격 주행 (REMOTE)", "수동", "대기"]),
                authority=random.choice(["OCS(운용통제기)", "근거리조종기", "없음"]),
                notes="네트워크 지터 감지 (12.5ms)" if i % 10 == 0 else "",
            ))
        
        self._last_seq += 14
        
        # Device statuses
        devices = [
            DeviceStatus("vic", "VIC", connected=True),
            DeviceStatus("rdc", "RDC", connected=True),
            DeviceStatus("adc", "ADC", connected=True),
            DeviceStatus("fcam", "FCAM", connected=True),
            DeviceStatus("rcam", "RCAM", connected=True),
            DeviceStatus("aux", "AUX", connected=True, warning=True, error_reason="응답 지연 감지 (250ms 이상)"),
            DeviceStatus("scs", "SCS", connected=True),
            DeviceStatus("dip", "DIP", connected=True),
            DeviceStatus("tcc", "TCC", connected=False, error_reason="연결 타임아웃 (10초 이상 패킷 수신 없음)"),
            DeviceStatus("tm", "TM", connected=True),
        ]
        
        # Emergency status
        emergency = EmergencyStatus(signal_lost_driving=True)
        
        return {
            "connected": True,
            "interface": config.network.interface,
            "filter": f"{config.network.source_port}→{config.network.dest_port}",
            "lastPacketTime": now.strftime("%H:%M:%S"),
            "capturePps": 1024,
            "filterPass": 99.9,
            "parseSuccess": 100.0,
            "checksumFail": 0.0,
            "packetLoss": 0,
            "availability5min": 99.98,
            "availability1hour": 99.99,
            "jitterP95": 2.1,
            "jitterP99": 2.4,
            "operationalMode": "원격 주행 (REMOTE)",
            "operationalAuthority": "OCS(운용통제기)",
            "drivingState": "전진/대기",
            "combinedData": chart_data,
            "devices": [d.to_dict() for d in devices],
            "emergencyStatus": emergency.to_dict(),
            "availabilitySegments": [s.to_dict() for s in self._availability_segments],
        }
    
    def update_data(self, prev_data: Dict) -> Dict:
        """
        Update dashboard data for polling cycle.
        
        Simulates realistic data changes between poll intervals.
        
        Args:
            prev_data: Previous dashboard state dictionary
            
        Returns:
            Updated dashboard state dictionary
        """
        now = datetime.now()
        
        # Add new chart data point
        new_point = {
            "timestamp": now.strftime("%H:%M:%S"),
            "pps": random.randint(900, 1100),
            "jitter": round(random.uniform(0.5, 2.5), 2),
        }
        
        # Maintain bounded chart data
        chart_data = prev_data.get("combinedData", [])[1:] + [new_point]
        
        # Add new log entry
        self._last_seq += 1
        new_log = LogEntry(
            timestamp=now,
            sequence=self._last_seq,
            msg_code=f"0x{random.randint(0, 255):02X}",
            parse_ok=random.random() > 0.05,
            checksum_ok=random.random() > 0.03,
            mode=random.choice(["원격 주행 (REMOTE)", "수동", "대기"]),
            authority=random.choice(["OCS(운용통제기)", "근거리조종기", "없음"]),
            notes="네트워크 지터 감지 (12.5ms)" if random.random() > 0.9 else "",
        )
        
        # Maintain bounded log history
        self._logs_history = [new_log] + self._logs_history[:config.ui.max_log_entries - 1]
        
        # Occasionally update KPIs for realistic variation
        should_update_kpis = random.random() > 0.7
        
        # Update availability timeline
        self._elapsed_time += config.ui.poll_interval_ms / 1000
        is_connected = random.random() > 0.02
        self._update_availability_timeline(is_connected)
        
        return {
            **prev_data,
            "lastPacketTime": now.strftime("%H:%M:%S"),
            "capturePps": random.randint(1000, 1100) if should_update_kpis else prev_data.get("capturePps", 1000),
            "filterPass": round(random.uniform(99.5, 100), 1) if should_update_kpis else prev_data.get("filterPass", 99.9),
            "parseSuccess": round(random.uniform(99.5, 100), 1) if should_update_kpis else prev_data.get("parseSuccess", 100.0),
            "checksumFail": round(random.uniform(0, 0.5), 1) if should_update_kpis else prev_data.get("checksumFail", 0.0),
            "packetLoss": random.randint(0, 2) if should_update_kpis else prev_data.get("packetLoss", 0),
            "jitterP95": round(random.uniform(1.5, 2.5), 1),
            "jitterP99": round(random.uniform(2.0, 2.8), 1),
            "combinedData": chart_data,
            "availabilitySegments": [s.to_dict() for s in self._availability_segments],
        }
    
    def _update_availability_timeline(self, is_connected: bool) -> None:
        """
        Update availability timeline with current connection state.
        
        Manages segment creation and pruning to keep timeline bounded.
        The last segment always extends to time_window end to ensure
        the bar is always visible up to the end of the timeline.
        
        Args:
            is_connected: Current connection status
        """
        time_window = config.ui.timeline_duration_sec
        
        if not self._availability_segments:
            # Initialize with first segment extending to time_window
            end_time = min(self._elapsed_time, time_window)
            self._availability_segments.append(
                AvailabilitySegment(0, time_window, is_connected)
            )
            return
        
        last_seg = self._availability_segments[-1]
        
        # Extend or create new segment based on state change
        if (is_connected and last_seg.is_up) or (not is_connected and not last_seg.is_up):
            # Same state - extend current segment
            # Always extend to time_window to ensure visibility
            last_seg.end_sec = time_window
        else:
            # State changed - create new segment
            # New segment starts from where previous one ended
            self._availability_segments.append(
                AvailabilitySegment(
                    start_sec=last_seg.end_sec,
                    end_sec=time_window,  # Always extend to time_window
                    is_up=is_connected,
                )
            )
        
        # Prune old segments beyond time window (only if elapsed_time exceeds time_window)
        if self._elapsed_time > time_window:
            offset = self._elapsed_time - time_window
            pruned_segments = []
            
            for seg in self._availability_segments:
                # Adjust segment times relative to new window start
                new_start = max(0, seg.start_sec - offset)
                new_end = max(0, seg.end_sec - offset)
                
                # Only keep segments that are still within or partially within the window
                # Segments that start before 0 but end after 0 are kept and clipped
                if new_end > 0:
                    # Clip start to 0 if segment extends before window start
                    new_start = max(0, new_start)
                    pruned_segments.append(
                        AvailabilitySegment(
                            start_sec=new_start,
                            end_sec=new_end,
                            is_up=seg.is_up,
                        )
                    )
            
            # Ensure last segment always extends to time_window end
            # This is critical for visual continuity
            if pruned_segments:
                pruned_segments[-1].end_sec = time_window
                # Ensure last segment has valid start
                if pruned_segments[-1].start_sec >= time_window:
                    if len(pruned_segments) > 1:
                        prev_end = pruned_segments[-2].end_sec
                        pruned_segments[-1].start_sec = prev_end
                    else:
                        pruned_segments[-1].start_sec = max(0, time_window - 1)
            
            self._availability_segments = pruned_segments
        else:
            # When elapsed_time < time_window, ensure last segment extends to time_window
            # This ensures the bar is always visible to the end of the timeline
            if self._availability_segments:
                self._availability_segments[-1].end_sec = time_window
    
    def get_logs(self, limit: int = 50) -> List[Dict]:
        """
        Get recent log entries for the event table.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of log entry dictionaries
        """
        return [log.to_dict() for log in self._logs_history[:limit]]
    
    def clear_logs(self) -> None:
        """Clear all log history."""
        self._logs_history = []
    
    @property
    def log_count(self) -> int:
        """Get current number of stored log entries."""
        return len(self._logs_history)
