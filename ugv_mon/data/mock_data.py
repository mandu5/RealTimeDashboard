"""
테스트용 Mock 데이터 생성기.

이 모듈은 개발 및 테스트 환경에서 실제 패킷 캡처 없이
대시보드를 테스트할 수 있는 가짜 데이터를 생성합니다.

LiveDataProvider와 동일한 인터페이스를 제공하여
앱 코드 변경 없이 Mock/Live 모드를 전환할 수 있습니다.

사용 예시:
    >>> generator = MockDataGenerator()
    >>> initial_data = generator.generate_initial_data()
    >>> updated_data = generator.update_data(initial_data)

Note:
    Mock 모드는 환경변수 UGV_MON_USE_LIVE가 설정되지 않았을 때 활성화됩니다.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List

from ..core import (
    config, DEVICE_IDS, DEVICE_NAMES, DEFAULT_INITIAL_SEQUENCE,
    LogEntry, DeviceStatus, AvailabilitySegment,
)
from ..core.models import EMERGENCY_SOURCE_NAMES


class MockDataGenerator:
    """Mock 데이터 생성기.
    
    실시간 데이터처럼 보이는 랜덤 데이터를 생성합니다.
    PPS, 지터, 로그, 장치 상태 등을 시뮬레이션합니다.
    """

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
            # 연결 상태 (5개)
            "connected": True,
            "interface": config.network.interface,
            "direction": "status",  # 4주차 추가: 캡처 방향
            "filter": f"{config.network.vic_port}→{config.network.ocs_port}",
            "lastPacketTime": now.strftime("%H:%M:%S"),
            # 통계 (9개)
            "capturePps": 1024,
            "parseSuccess": 100.0,
            "checksumFail": 0.0,
            "packetLoss": 0,
            "availability": 99.5,           # 5분 가용성
            "availabilityHourly": 98.7,     # 1시간 가용성
            "jitterCurrent": 1.8,
            "jitterP95": 2.1,
            "operationalMode": "원격 주행 (REMOTE)",
            "operationalAuthority": "OCS(운용통제기)",
            "drivingState": "전진/대기",
            "combinedData": chart_data,
            "devices": [d.to_dict() for d in devices],
            "emergencyStatus": {
                name: (name == "통신이상")
                for name in EMERGENCY_SOURCE_NAMES
            } | {"처리완료": False},
            "availabilitySegments": [s.to_dict() for s in self._availability_segments],
            # Phase 3: msg_code별 통계
            "msgCodeStats": {
                1: {"pps": 50, "packet_loss": 0, "avg_size": 100, "count": 3000},
                16: {"pps": 25, "packet_loss": 1, "avg_size": 80, "count": 1500},
                37: {"pps": 10, "packet_loss": 0, "avg_size": 120, "count": 600},
                64: {"pps": 15, "packet_loss": 0, "avg_size": 90, "count": 900},
            },
            # Phase 4: 연결 이력
            "connectionHistory": [
                {"timestamp": (now - timedelta(minutes=30)).isoformat(), "connected": True, "duration": 1800},
                {"timestamp": (now - timedelta(minutes=5)).isoformat(), "connected": False, "duration": 60},
                {"timestamp": (now - timedelta(minutes=4)).isoformat(), "connected": True, "duration": None},
            ],
            # Phase 5: 모드 전이
            "modeTransitions": [
                {"timestamp": (now - timedelta(minutes=20)).isoformat(), "from": "대기", "to": "수동"},
                {"timestamp": (now - timedelta(minutes=15)).isoformat(), "from": "수동", "to": "원격 주행 (REMOTE)"},
            ],
            # Phase 6: 비상정지 통계
            "emergencyCounts": {
                "원격 비상정지": 2,
                "신호단절 주행중": 1,
            },
            # ML 이상 탐지 데이터
            "ml": self._generate_ml_data(now),
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
        
        # ML 데이터 동적 업데이트
        prev_ml = prev_data.get("ml", {})
        updated_ml = self._update_ml_data(prev_ml, now)

        return {
            **prev_data,
            "lastPacketTime": now.strftime("%H:%M:%S"),
            "capturePps": random.randint(1000, 1100) if update_kpi else prev_data.get("capturePps", 1000),
            "jitterP95": round(random.uniform(1.5, 2.5), 1),
            "combinedData": chart_data,
            "ml": updated_ml,  # ML 데이터 업데이트
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

    def _generate_ml_data(self, now: datetime) -> Dict:
        """ML 이상 탐지 샘플 데이터 생성."""
        # 10% 확률로 이상 상태
        is_anomaly = random.random() < 0.1
        confidence = random.uniform(0.7, 0.95) if is_anomaly else random.uniform(0.1, 0.3)
        
        # 3D 산점도용 레코드 (최근 100개)
        records = []
        for i in range(100):
            ts = now - timedelta(seconds=100 - i)
            record = {
                "timestamp": ts.strftime("%H:%M:%S"),
                "jitter_current": random.uniform(1, 5) if not is_anomaly else random.uniform(3, 15),
                "pps": random.randint(90, 110) if not is_anomaly else random.randint(50, 90),
                "loss_rate": random.uniform(0, 2) if not is_anomaly else random.uniform(2, 10),
                "anomaly_score": random.uniform(-0.2, 0.1) if not is_anomaly else random.uniform(-0.8, -0.4),
            }
            records.append(record)
        
        # 타임라인용 점수 히스토리
        score_history = [
            {
                "timestamp": (now - timedelta(seconds=60 - i)).strftime("%H:%M:%S"),
                "score": random.uniform(-0.3, 0.1) if random.random() > 0.1 else random.uniform(-0.7, -0.4),
            }
            for i in range(60)
        ]
        
        # 기여 특성 (이상일 때만)
        contributing_features = []
        if is_anomaly:
            contributing_features = [
                {"name": "jitter_volatility", "z_score": random.uniform(2.5, 4.0)},
                {"name": "pps_trend", "z_score": random.uniform(-3.0, -2.0)},
                {"name": "loss_rate", "z_score": random.uniform(1.8, 2.5)},
            ]
        
        return {
            "model_status": "ready",
            "is_anomaly": is_anomaly,
            "anomaly_score": random.uniform(-0.5, -0.2) if is_anomaly else random.uniform(-0.1, 0.1),
            "confidence": confidence,
            "contributing_features": contributing_features,
            "records": records,
            "score_history": score_history,
        }

    def _update_ml_data(self, prev_ml: Dict, now: datetime) -> Dict:
        """ML 데이터 실시간 업데이트.
        
        기존 데이터를 유지하면서 새로운 포인트를 추가하고 오래된 데이터는 제거합니다.
        """
        # 이전 상태 가져오기
        prev_records = prev_ml.get("records", [])
        prev_score_history = prev_ml.get("score_history", [])
        
        # 이상 상태 확률적 변화 (5% 확률로 상태 전환)
        prev_is_anomaly = prev_ml.get("is_anomaly", False)
        if random.random() < 0.05:
            is_anomaly = not prev_is_anomaly  # 상태 전환
        else:
            is_anomaly = prev_is_anomaly  # 유지
        
        confidence = random.uniform(0.7, 0.95) if is_anomaly else random.uniform(0.1, 0.3)
        
        # 새 레코드 추가 (3D 산점도용)
        new_record = {
            "timestamp": now.strftime("%H:%M:%S"),
            "jitter_current": random.uniform(1, 5) if not is_anomaly else random.uniform(3, 15),
            "pps": random.randint(90, 110) if not is_anomaly else random.randint(50, 90),
            "loss_rate": random.uniform(0, 2) if not is_anomaly else random.uniform(2, 10),
            "anomaly_score": random.uniform(-0.2, 0.1) if not is_anomaly else random.uniform(-0.8, -0.4),
        }
        updated_records = (prev_records + [new_record])[-100:]  # 최근 100개 유지
        
        # 새 점수 추가 (타임라인용)
        new_score = {
            "timestamp": now.strftime("%H:%M:%S"),
            "score": random.uniform(-0.3, 0.1) if not is_anomaly else random.uniform(-0.7, -0.4),
        }
        updated_score_history = (prev_score_history + [new_score])[-60:]  # 최근 60개 유지
        
        # 기여 특성 (이상일 때만)
        contributing_features = []
        if is_anomaly:
            contributing_features = [
                {"name": "jitter_volatility", "z_score": random.uniform(2.5, 4.0)},
                {"name": "pps_trend", "z_score": random.uniform(-3.0, -2.0)},
                {"name": "loss_rate", "z_score": random.uniform(1.8, 2.5)},
            ]
        
        return {
            "model_status": "ready",
            "is_anomaly": is_anomaly,
            "anomaly_score": random.uniform(-0.5, -0.2) if is_anomaly else random.uniform(-0.1, 0.1),
            "confidence": confidence,
            "contributing_features": contributing_features,
            "records": updated_records,
            "score_history": updated_score_history,
        }


