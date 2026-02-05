"""
실시간 통신 품질 통계 계산기.

이 모듈은 VIC-OCS 통신 패킷을 분석하여 실시간 통계를 계산합니다.

계산 항목:
    - PPS (Packets Per Second): 초당 수신 패킷 수
    - 지터 (Jitter): 패킷 도착 간격의 변동량 (ms)
    - 패킷 손실: 시퀀스 번호 기반 누락 패킷 수
    - P95/P99: 지터 백분위수

주요 임계값:
    - MAX_GAP_MS (3000ms): 스트림 재시작으로 판단하는 갭
    - MAX_JITTER_MS (200ms): 이상치로 제외할 지터 값
    - JITTER_THRESHOLD_MS (5ms): 지터 계산 스킵 임계값

사용 예시:
    >>> calc = StatsCalculator(window_sec=60)
    >>> jitter = calc.record_packet(datetime.now(), seq=1, size=100)
    >>> pps = calc.get_pps()
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List
import threading
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

MAX_GAP_MS = 3000         # 3초 이상 갭 → 스트림 재시작
MAX_JITTER_MS = 200       # 200ms 이상 지터 → 이상치
JITTER_THRESHOLD_MS = 5   # 5ms 초과 interval 변화 시 지터 스킵


class StatsCalculator:
    """실시간 통신 품질 통계 계산기.
    
    슬라이딩 윈도우 방식으로 최근 N초간의 패킷을 분석합니다.
    pandas DataFrame을 활용하여 효율적인 통계 계산을 수행합니다.
    
    Attributes:
        window_sec: 분석 윈도우 크기 (초, 기본 3600)
    """

    def __init__(self, window_sec: int = 3600):
        self._window_sec = window_sec
        self._lock = threading.Lock()
        
        # 리스트 버퍼 (실시간 추가용)
        self._records: List[Dict] = []
        
        # msg_code별 상태
        self._last_by_code: Dict[int, Dict] = {}
        self._loss_by_code: Dict[int, int] = {}
        
        # 마지막 상태
        self._last_timestamp: Optional[datetime] = None
        self._last_sequence: Optional[int] = None

    def record_packet(self, timestamp: datetime, sequence: int, size: int, msg_code: int = 0) -> Optional[float]:
        """패킷 기록 및 지터 반환."""
        with self._lock:
            if msg_code not in self._last_by_code:
                self._last_by_code[msg_code] = {"timestamp": None, "interval": None, "sequence": None}
            code_data = self._last_by_code[msg_code]
            
            self._calculate_packet_loss(code_data, sequence, msg_code)
            jitter_ms, interval_ms = self._calculate_jitter(timestamp, code_data)
            
            code_data["timestamp"] = timestamp
            code_data["sequence"] = sequence
            
            self._records.append({
                "timestamp": timestamp,
                "msg_code": msg_code,
                "sequence": sequence,
                "size": size,
                "jitter_ms": jitter_ms,
                "interval_ms": interval_ms,
            })
            
            self._last_timestamp = timestamp
            self._last_sequence = sequence
            self._prune_old_records(timestamp)
            
            return jitter_ms

    def _calculate_jitter(self, timestamp: datetime, code_data: Dict) -> Tuple[Optional[float], Optional[float]]:
        """지터 계산 (회사 로직) - 안전 버전."""
        prev_ts = code_data.get("timestamp")
        if prev_ts is None:
            # 첫 샘플
            code_data["timestamp"] = timestamp
            code_data["interval"] = None
            return None, None

        interval_ms = (timestamp - prev_ts).total_seconds() * 1000

        # timestamp는 항상 갱신
        code_data["timestamp"] = timestamp

        # 큰 갭 스킵
        if interval_ms > MAX_GAP_MS:
            code_data["interval"] = None
            return None, interval_ms

        prev_interval = code_data.get("interval")
        jitter_ms = None

        if isinstance(prev_interval, (int, float)) and prev_interval <= MAX_GAP_MS:
            diff = abs(interval_ms - prev_interval)
            if diff <= JITTER_THRESHOLD_MS:
                jitter_ms = diff

        code_data["interval"] = interval_ms
        return jitter_ms, interval_ms

    def _calculate_packet_loss(self, code_data: Dict, sequence: int, msg_code: int):
        if code_data["sequence"] is not None:
            gap = ((sequence & 0x0F) - (code_data["sequence"] & 0x0F)) % 16
            if gap > 1:
                self._loss_by_code[msg_code] = self._loss_by_code.get(msg_code, 0) + (gap - 1)

    def _prune_old_records(self, current_time: datetime):
        cutoff = current_time - timedelta(seconds=self._window_sec)
        self._records = [r for r in self._records if r["timestamp"] >= cutoff]

    def _get_df(self) -> pd.DataFrame:
        """리스트를 DataFrame으로 변환 (분석 시 호출)."""
        if not self._records:
            return pd.DataFrame(columns=["timestamp", "msg_code", "sequence", "size", "jitter_ms", "interval_ms"])
        return pd.DataFrame(self._records)

    # =========================================================================
    # 기본 통계 (기존 호환)
    # =========================================================================
    
    def get_stats_dict(self) -> dict:
        p95, p99 = self.get_jitter_percentiles()
        return {
            "pps": self.get_pps(),
            "jitter_current": self.get_current_jitter(),
            "jitter_p95": p95, "jitter_p99": p99,
            "packet_loss": self.get_packet_loss(),
            "availability": self.get_availability(),
        }

    def get_pps(self) -> int:
        with self._lock:
            if not self._records:
                return 0
            one_sec_ago = datetime.now() - timedelta(seconds=1)
            return sum(1 for r in self._records if r["timestamp"] >= one_sec_ago)

    def get_jitter_percentiles(self) -> Tuple[float, float]:
        with self._lock:
            jitters = [r["jitter_ms"] for r in self._records 
                       if r["jitter_ms"] is not None and r["jitter_ms"] <= MAX_JITTER_MS]
            if not jitters:
                return (0.0, 0.0)
            sorted_j = sorted(jitters)
            n = len(sorted_j)
            return (round(sorted_j[min(int(n * 0.95), n-1)], 2), 
                    round(sorted_j[min(int(n * 0.99), n-1)], 2))

    def get_current_jitter(self) -> float:
        with self._lock:
            for r in reversed(self._records):
                if r["jitter_ms"] is not None and r["jitter_ms"] <= MAX_JITTER_MS:
                    return round(r["jitter_ms"], 2)
            return 0.0

    def get_average_jitter(self) -> float:
        with self._lock:
            jitters = [r["jitter_ms"] for r in self._records 
                       if r["jitter_ms"] is not None and r["jitter_ms"] <= MAX_JITTER_MS]
            return round(sum(jitters) / len(jitters), 2) if jitters else 0.0

    def get_packet_loss(self) -> int:
        with self._lock:
            return sum(self._loss_by_code.values())

    def get_availability(self, window_sec: int = None) -> float:
        """가용성 계산."""
        with self._lock:
            if not self._records:
                return 0.0
            window = window_sec or 300
            window_start = datetime.now() - timedelta(seconds=window)
            recent = [r for r in self._records if r["timestamp"] >= window_start]
            if len(recent) < 2:
                return 0.0
            expected = 100 * window
            return round(min(len(recent) / expected * 100, 100), 1)

    # =========================================================================
    # 확장 분석 (Phase 2-6)
    # =========================================================================

    def get_hourly_availability(self) -> float:
        """최근 1시간 가용성."""
        return self.get_availability(window_sec=3600)

    def get_stats_by_code(self, msg_code: int = None) -> Dict:
        """msg_code별 통계."""
        with self._lock:
            if msg_code is not None:
                filtered = [r for r in self._records if r["msg_code"] == msg_code]
                one_sec_ago = datetime.now() - timedelta(seconds=1)
                sizes = [r["size"] for r in filtered]
                return {
                    "pps": sum(1 for r in filtered if r["timestamp"] >= one_sec_ago),
                    "packet_loss": self._loss_by_code.get(msg_code, 0),
                    "avg_size": round(sum(sizes) / len(sizes), 1) if sizes else 0,
                    "count": len(filtered),
                }
            else:
                codes = set(r["msg_code"] for r in self._records)
                return {code: self.get_stats_by_code(code) for code in codes}

    def get_msg_code_distribution(self) -> Dict[int, int]:
        """msg_code별 패킷 수."""
        with self._lock:
            result = {}
            for r in self._records:
                code = r["msg_code"]
                result[code] = result.get(code, 0) + 1
            return result

    def get_time_series(self, msg_code: int = None, resample: str = "1S") -> pd.DataFrame:
        """시계열 데이터 (pandas 분석용)."""
        with self._lock:
            df = self._get_df()
            if df.empty:
                return pd.DataFrame()
            if msg_code is not None:
                df = df[df["msg_code"] == msg_code]
            if df.empty:
                return pd.DataFrame()
            
            df = df.set_index("timestamp")
            return df.resample(resample).agg({
                "size": "count",
                "jitter_ms": "mean",
            }).rename(columns={"size": "pps"})

    # =========================================================================
    # 상태 제어
    # =========================================================================
    
    def reset(self):
        with self._lock:
            self._records.clear()
            self._last_timestamp = self._last_sequence = None
            self._last_by_code.clear()
            self._loss_by_code.clear()

    def reset_stream_state(self, clear_records: bool = False):
        """스트림 상태 리셋."""
        with self._lock:
            logger.info(f"[STATS] reset_stream_state: clear={clear_records}")
            self._last_by_code.clear()
            self._loss_by_code.clear()
            if clear_records:
                self._records.clear()

    def get_dataframe(self) -> pd.DataFrame:
        """전체 DataFrame 복사본 반환 (외부 분석용)."""
        with self._lock:
            return self._get_df()
