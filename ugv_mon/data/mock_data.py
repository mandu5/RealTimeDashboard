"""
Mock Data Generator - 테스트/개발용 가짜 데이터 생성.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List

from .models import LogEntry, DeviceStatus, AvailabilitySegment, EmergencyStatus
from ..config import config
from ..constants import DEVICE_IDS, DEVICE_NAMES, DEFAULT_INITIAL_SEQUENCE


class MockDataGenerator:
    """Mock 데이터 생성기."""

    def __init__(self):
        self._last_seq = DEFAULT_INITIAL_SEQUENCE
        self._elapsed_time = 0
        self._logs_history: List[LogEntry] = []
        self._availability_segments: List[AvailabilitySegment] = [
            AvailabilitySegment(start_sec=0, end_sec=2700, is_up=True),
            AvailabilitySegment(start_sec=2700, end_sec=2850, is_up=False),
            AvailabilitySegment(start_sec=2850, end_sec=3600, is_up=True),
        ]

    def generate_initial_data(self) -> Dict:
        """초기 데이터 생성."""
        now = datetime.now()

        # 차트 데이터 (60 포인트)
        chart_data = [
            {
                "timestamp": (now - timedelta(seconds=60 - i)).strftime("%H:%M:%S"),
                "pps": random.randint(900, 1100),
                "jitter": round(random.uniform(0.5, 2.5), 2),
            }
            for i in range(config.ui.max_chart_points)
        ]

        # 로그 엔트리 (15개)
        for i in range(15):
            log_time = now - timedelta(seconds=(15 - i) * 2)
            self._logs_history.append(LogEntry(
                timestamp=log_time,
                sequence=self._last_seq + i,
                msg_code=f"0x{random.randint(0, 255):02X}",
                parse_ok=random.random() > 0.05,
                checksum_ok=random.random() > 0.03,
                mode=random.choice(["원격 주행 (REMOTE)", "수동", "대기"]),
                authority=random.choice(["OCS(운용통제기)", "근거리조종기", "없음"]),
            ))
        self._last_seq += 14

        # 장치 상태 (constants 모듈 활용)
        devices = []
        for device_id, name in zip(DEVICE_IDS, DEVICE_NAMES):
            if name == "TCC":
                devices.append(DeviceStatus(device_id, name, connected=False, error_reason="연결 타임아웃"))
            elif name == "ACAM":
                devices.append(DeviceStatus(device_id, name, connected=True, warning=True, error_reason="응답 지연"))
            else:
                devices.append(DeviceStatus(device_id, name, connected=True))

        return {
            "connected": True,
            "interface": config.network.interface,
            "filter": f"{config.network.vic_port}→{config.network.ocs_port}",
            "lastPacketTime": now.strftime("%H:%M:%S"),
            "capturePps": 1024,
            "parseSuccess": 100.0,
            "checksumFail": 0.0,
            "packetLoss": 0,
            "availability5min": 99.98,
            "jitterP95": 2.1,
            "jitterP99": 2.4,
            "operationalMode": "원격 주행 (REMOTE)",
            "operationalAuthority": "OCS(운용통제기)",
            "drivingState": "전진/대기",
            "combinedData": chart_data,
            "devices": [d.to_dict() for d in devices],
            "emergencyStatus": EmergencyStatus(signal_lost_driving=True).to_dict(),
            "availabilitySegments": [s.to_dict() for s in self._availability_segments],
        }

    def update_data(self, prev_data: Dict) -> Dict:
        """데이터 업데이트."""
        now = datetime.now()

        # 새 차트 포인트
        new_point = {
            "timestamp": now.strftime("%H:%M:%S"),
            "pps": random.randint(900, 1100),
            "jitter": round(random.uniform(0.5, 2.5), 2),
        }
        chart_data = prev_data.get("combinedData", [])[1:] + [new_point]

        # 새 로그 엔트리
        self._last_seq += 1
        new_log = LogEntry(
            timestamp=now,
            sequence=self._last_seq,
            msg_code=f"0x{random.randint(0, 255):02X}",
            parse_ok=random.random() > 0.05,
            checksum_ok=random.random() > 0.03,
            mode=random.choice(["원격 주행 (REMOTE)", "수동", "대기"]),
            authority=random.choice(["OCS(운용통제기)", "근거리조종기", "없음"]),
        )
        self._logs_history = [new_log] + self._logs_history[:config.ui.max_log_entries - 1]

        # KPI 업데이트 (30% 확률)
        update_kpi = random.random() > 0.7

        return {
            **prev_data,
            "lastPacketTime": now.strftime("%H:%M:%S"),
            "capturePps": random.randint(1000, 1100) if update_kpi else prev_data.get("capturePps", 1000),
            "jitterP95": round(random.uniform(1.5, 2.5), 1),
            "jitterP99": round(random.uniform(2.0, 2.8), 1),
            "combinedData": chart_data,
        }

    def get_logs(self, limit: int = 50) -> List[Dict]:
        """로그 목록 반환."""
        return [log.to_dict() for log in self._logs_history[:limit]]

    def clear_logs(self) -> None:
        """로그 초기화."""
        self._logs_history = []

    @property
    def log_count(self) -> int:
        return len(self._logs_history)
