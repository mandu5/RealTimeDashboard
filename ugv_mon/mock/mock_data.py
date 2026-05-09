"""
테스트용 Mock 데이터 생성기.

=============================================================================
⚠️ DEV/MOCK ONLY — 로컬·CI·데모용. 프로덕션 데이터나 실제 장비와 무관합니다.
   운영 환경에서는 적절한 ServiceProvider 구현을 사용하세요.
=============================================================================

실제 패킷 캡처 없이 대시보드 동작을 검증하기 위한 합성 데이터를 생성합니다.

ServiceProvider와 동일한 인터페이스를 제공하여
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
from typing import Any

from ..config import config
from ..constants import (
    DEFAULT_INITIAL_SEQUENCE,
    DEVICE_IDS,
    DEVICE_NAMES,
    ML_DISPLAY_RECORDS,
    ML_DISPLAY_SCORES,
    MOCK_ANOMALY_BASE_PROBABILITY,
    MOCK_ANOMALY_TOGGLE_PROBABILITY,
)
from ..models import EMERGENCY_SOURCE_NAMES

# 로그 엔트리에 사용되는 공통 선택지
_MODES = ["원격 주행 (REMOTE)", "수동", "대기"]
_AUTHORITIES = ["OCS(운용통제기)", "근거리조종기", "없음"]


def _make_log_entry(ts: datetime, seq: int) -> dict:
    """랜덤 로그 엔트리 생성 (to_log_dict 형식)."""
    parse_ok = random.random() > 0.05
    checksum_ok = random.random() > 0.03
    return {
        "timestamp": ts.strftime("%H:%M:%S"),
        "sequence": seq,
        "msg_code": f"0x{random.randint(0, 255):02X}",
        "parse_ok": "✓" if parse_ok else "✗",
        "checksum_ok": "✓" if checksum_ok else "✗",
        "mode": random.choice(_MODES),
        "authority": random.choice(_AUTHORITIES),
        "error": "" if parse_ok else "파싱 실패",
    }


def _make_ml_record(ts: datetime, is_anomaly: bool) -> dict:
    """단일 ML 3D 산점도 레코드 생성."""
    return {
        "timestamp": ts.strftime("%H:%M:%S"),
        "jitter_current": random.uniform(3, 15) if is_anomaly else random.uniform(1, 5),
        "pps": random.randint(50, 90) if is_anomaly else random.randint(90, 110),
        "loss_rate": random.uniform(2, 10) if is_anomaly else random.uniform(0, 2),
        "anomaly_score": random.uniform(-0.8, -0.4) if is_anomaly else random.uniform(-0.2, 0.1),
    }


def _make_contributing_features(is_anomaly: bool) -> list[dict]:
    """기여 특성 생성 (이상 상태일 때만 값 있음)."""
    if not is_anomaly:
        return []
    return [
        {"name": "jitter_volatility", "z_score": random.uniform(2.5, 4.0)},
        {"name": "pps_trend", "z_score": random.uniform(-3.0, -2.0)},
        {"name": "loss_rate", "z_score": random.uniform(1.8, 2.5)},
    ]


def _build_ml_result(
    is_anomaly: bool,
    records: list[dict],
    score_history: list[dict],
) -> dict[str, Any]:
    """ML 결과 딕셔너리 조립."""
    confidence = random.uniform(0.7, 0.95) if is_anomaly else random.uniform(0.1, 0.3)
    return {
        "model_status": "ready",
        "is_anomaly": is_anomaly,
        "anomaly_score": random.uniform(-0.5, -0.2) if is_anomaly else random.uniform(-0.1, 0.1),
        "confidence": confidence,
        "contributing_features": _make_contributing_features(is_anomaly),
        "records": records,
        "score_history": score_history,
    }


class MockDataGenerator:
    """Mock 데이터 생성기.

    실시간 데이터처럼 보이는 랜덤 데이터를 생성합니다.
    PPS, 지터, 로그, 장치 상태 등을 시뮬레이션합니다.
    """

    def __init__(self):
        self._last_seq = DEFAULT_INITIAL_SEQUENCE
        self._logs_history: list[dict] = []

    def generate_initial_data(self) -> dict[str, Any]:
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
            self._logs_history.append(_make_log_entry(log_time, self._last_seq + i))
        self._last_seq += 14

        # 장치 상태 (constants 모듈 활용)
        devices = []
        for device_id, name in zip(DEVICE_IDS, DEVICE_NAMES):
            if name == "TCC":
                devices.append({"id": device_id, "name": name, "connected": False, "error_reason": "연결 타임아웃"})
            elif name == "ACAM":
                devices.append({"id": device_id, "name": name, "connected": True, "warning": True, "error_reason": "응답 지연"})
            else:
                devices.append({"id": device_id, "name": name, "connected": True})

        return {
            # 연결 상태 (5개)
            "connected": True,
            "interface": config.network.interface,
            "direction": "status",
            "filter": f"{config.network.vic_port}→{config.network.ocs_port}",
            "lastPacketTime": now.strftime("%H:%M:%S"),
            # 통계 (9개)
            "capturePps": 1024,
            "parseSuccess": 100.0,
            "checksumFail": 0.0,
            "packetLoss": 0,
            "availability": 99.5,
            "jitterCurrent": 1.8,
            "jitterP95": 2.1,
            "operationalMode": "원격 주행 (REMOTE)",
            "operationalAuthority": "OCS(운용통제기)",
            "drivingState": "전진/대기",
            "combinedData": chart_data,
            "devices": [{"name": d["name"], "connected": d["connected"]} for d in devices],
            "emergencyStatus": {
                name: (name == "통신이상")
                for name in EMERGENCY_SOURCE_NAMES
            } | {"처리완료": False},
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
            # 로그 (콜백 갱신용)
            "logs": list(reversed(self._logs_history[:50])),
        }

    def update_data(self, prev_data: dict[str, Any]) -> dict[str, Any]:
        """데이터 업데이트."""
        now = datetime.now()

        # 새 차트 포인트
        new_point = {
            "timestamp": now.strftime("%H:%M:%S"),
            "pps": random.randint(900, 1100),
            "jitter": round(random.uniform(0.5, 2.5), 2),
        }
        chart_data = [*prev_data.get("combinedData", [])[1:], new_point]

        # 새 로그 엔트리
        self._last_seq += 1
        new_log = _make_log_entry(now, self._last_seq)
        self._logs_history = [new_log, *self._logs_history[:config.ui.max_log_entries - 1]]

        # KPI 업데이트 (30% 확률)
        update_kpi = random.random() > 0.7

        # ML 데이터 동적 업데이트
        prev_ml = prev_data.get("ml", {})
        updated_ml = self._update_ml_data(prev_ml, now)

        return {
            **prev_data,
            "lastPacketTime": now.strftime("%H:%M:%S"),
            "logs": list(reversed(self._logs_history[:50])),
            "capturePps": random.randint(1000, 1100) if update_kpi else prev_data.get("capturePps", 1000),
            "jitterP95": round(random.uniform(1.5, 2.5), 1),
            "combinedData": chart_data,
            "ml": updated_ml,
        }

    def get_logs(self, limit: int = 50) -> list[dict]:
        """로그 목록 반환 (to_log_dict 형식)."""
        return list(reversed(self._logs_history[:limit]))

    def clear_logs(self) -> None:
        """로그 초기화."""
        self._logs_history = []

    def _generate_ml_data(self, now: datetime) -> dict[str, Any]:
        """ML 이상 탐지 샘플 데이터 생성 (초기화 시)."""
        is_anomaly = random.random() < MOCK_ANOMALY_BASE_PROBABILITY

        records = [
            _make_ml_record(now - timedelta(seconds=ML_DISPLAY_RECORDS - i), is_anomaly)
            for i in range(ML_DISPLAY_RECORDS)
        ]
        score_history = [
            {
                "timestamp": (now - timedelta(seconds=ML_DISPLAY_SCORES - i)).strftime("%H:%M:%S"),
                "score": random.uniform(-0.3, 0.1) if random.random() > 0.1 else random.uniform(-0.7, -0.4),
            }
            for i in range(ML_DISPLAY_SCORES)
        ]
        return _build_ml_result(is_anomaly, records, score_history)

    def _update_ml_data(self, prev_ml: dict[str, Any], now: datetime) -> dict[str, Any]:
        """ML 데이터 실시간 업데이트.

        기존 데이터를 유지하면서 새로운 포인트를 추가하고 오래된 데이터는 제거합니다.
        """
        prev_is_anomaly = prev_ml.get("is_anomaly", False)
        is_anomaly = (
            not prev_is_anomaly
            if random.random() < MOCK_ANOMALY_TOGGLE_PROBABILITY
            else prev_is_anomaly
        )

        updated_records = ([*prev_ml.get("records", []), _make_ml_record(now, is_anomaly)])[-ML_DISPLAY_RECORDS:]

        new_score = {
            "timestamp": now.strftime("%H:%M:%S"),
            "score": random.uniform(-0.7, -0.4) if is_anomaly else random.uniform(-0.3, 0.1),
        }
        updated_score_history = ([*prev_ml.get("score_history", []), new_score])[-ML_DISPLAY_SCORES:]

        return _build_ml_result(is_anomaly, updated_records, updated_score_history)
