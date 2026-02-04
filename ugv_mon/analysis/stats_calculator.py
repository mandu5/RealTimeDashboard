"""실시간 통계 계산기 - pandas 기반 데이터 분석."""

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
    """실시간 통계 계산기 (pandas DataFrame 기반)."""

    def __init__(self, window_sec: int = 3600):  # 1시간으로 확장 (분석용)
        self._window_sec = window_sec
        self._lock = threading.Lock()
        
        # pandas DataFrame (메인 데이터 저장소)
        self._df = pd.DataFrame({
            "timestamp": pd.Series(dtype="datetime64[ns]"),
            "msg_code": pd.Series(dtype="int64"),
            "sequence": pd.Series(dtype="int64"),
            "size": pd.Series(dtype="int64"),
            "jitter_ms": pd.Series(dtype="float64"),
            "interval_ms": pd.Series(dtype="float64"),
        })
        
        # msg_code별 상태 (지터/손실 계산용)
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
            
            # 상태 저장
            code_data["timestamp"] = timestamp
            code_data["sequence"] = sequence
            
            # DataFrame에 추가 (loc 사용으로 FutureWarning 방지)
            self._df.loc[len(self._df)] = {
                "timestamp": timestamp,
                "msg_code": msg_code,
                "sequence": sequence,
                "size": size,
                "jitter_ms": jitter_ms,
                "interval_ms": interval_ms,
            }
            
            self._last_timestamp = timestamp
            self._last_sequence = sequence
            self._prune_old_records(timestamp)
            
            return jitter_ms

    def _calculate_jitter(self, timestamp: datetime, code_data: Dict) -> Tuple[Optional[float], Optional[float]]:
        """지터 계산 (회사 로직). Returns (jitter_ms, interval_ms)."""
        if code_data["timestamp"] is None:
            return None, None
        
        interval_ms = (timestamp - code_data["timestamp"]).total_seconds() * 1000
        
        if interval_ms > MAX_GAP_MS:
            code_data["interval"] = None
            return None, interval_ms
        
        prev_interval = code_data.get("interval")
        jitter_ms = None
        
        if prev_interval is not None and prev_interval <= MAX_GAP_MS:
            jitter_ms = abs(interval_ms - prev_interval)
            if interval_ms - prev_interval > JITTER_THRESHOLD_MS:
                jitter_ms = None
        
        code_data["interval"] = interval_ms
        return jitter_ms, interval_ms

    def _calculate_packet_loss(self, code_data: Dict, sequence: int, msg_code: int):
        """패킷 손실 계산."""
        if code_data["sequence"] is not None:
            gap = ((sequence & 0x0F) - (code_data["sequence"] & 0x0F)) % 16
            if gap > 1:
                self._loss_by_code[msg_code] = self._loss_by_code.get(msg_code, 0) + (gap - 1)

    def _prune_old_records(self, current_time: datetime):
        """윈도우 밖 기록 제거."""
        cutoff = current_time - timedelta(seconds=self._window_sec)
        self._df = self._df[self._df["timestamp"] >= cutoff]

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
            if self._df.empty:
                return 0
            one_sec_ago = datetime.now() - timedelta(seconds=1)
            return len(self._df[self._df["timestamp"] >= one_sec_ago])

    def get_jitter_percentiles(self) -> Tuple[float, float]:
        with self._lock:
            valid = self._df[
                (self._df["jitter_ms"].notna()) & 
                (self._df["jitter_ms"] <= MAX_JITTER_MS)
            ]["jitter_ms"]
            if valid.empty:
                return (0.0, 0.0)
            return (round(valid.quantile(0.95), 2), round(valid.quantile(0.99), 2))

    def get_current_jitter(self) -> float:
        with self._lock:
            valid = self._df[
                (self._df["jitter_ms"].notna()) & 
                (self._df["jitter_ms"] <= MAX_JITTER_MS)
            ]
            if valid.empty:
                return 0.0
            return round(valid["jitter_ms"].iloc[-1], 2)

    def get_average_jitter(self) -> float:
        with self._lock:
            valid = self._df[
                (self._df["jitter_ms"].notna()) & 
                (self._df["jitter_ms"] <= MAX_JITTER_MS)
            ]["jitter_ms"]
            return round(valid.mean(), 2) if not valid.empty else 0.0

    def get_packet_loss(self) -> int:
        with self._lock:
            return sum(self._loss_by_code.values())

    def get_availability(self, window_sec: int = None) -> float:
        """가용성 계산. window_sec 지정 가능 (기본: 5분)."""
        with self._lock:
            if self._df.empty:
                return 0.0
            window = window_sec or 300  # 기본 5분
            window_start = datetime.now() - timedelta(seconds=window)
            recent = self._df[self._df["timestamp"] >= window_start]
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
        """msg_code별 통계. None이면 전체 코드별 딕셔너리 반환."""
        with self._lock:
            if msg_code is not None:
                filtered = self._df[self._df["msg_code"] == msg_code]
                one_sec_ago = datetime.now() - timedelta(seconds=1)
                return {
                    "pps": len(filtered[filtered["timestamp"] >= one_sec_ago]),
                    "packet_loss": self._loss_by_code.get(msg_code, 0),
                    "avg_size": round(filtered["size"].mean(), 1) if not filtered.empty else 0,
                    "count": len(filtered),
                }
            else:
                # 전체 코드별
                result = {}
                for code in self._df["msg_code"].unique():
                    result[int(code)] = self.get_stats_by_code(int(code))
                return result

    def get_msg_code_distribution(self) -> Dict[int, int]:
        """msg_code별 패킷 수."""
        with self._lock:
            if self._df.empty:
                return {}
            return self._df["msg_code"].value_counts().to_dict()

    def get_time_series(self, msg_code: int = None, resample: str = "1S") -> pd.DataFrame:
        """시계열 데이터 반환 (차트용).
        
        Args:
            msg_code: 필터링할 코드 (None이면 전체)
            resample: 리샘플 간격 ("1S", "10S", "1T" 등)
        """
        with self._lock:
            df = self._df.copy()
            if msg_code is not None:
                df = df[df["msg_code"] == msg_code]
            if df.empty:
                return pd.DataFrame()
            
            df = df.set_index("timestamp")
            return df.resample(resample).agg({
                "size": "count",  # PPS
                "jitter_ms": "mean",
            }).rename(columns={"size": "pps"})

    # =========================================================================
    # 상태 제어
    # =========================================================================
    
    def _create_empty_df(self) -> pd.DataFrame:
        """빈 DataFrame 생성 (dtype 지정)."""
        return pd.DataFrame({
            "timestamp": pd.Series(dtype="datetime64[ns]"),
            "msg_code": pd.Series(dtype="int64"),
            "sequence": pd.Series(dtype="int64"),
            "size": pd.Series(dtype="int64"),
            "jitter_ms": pd.Series(dtype="float64"),
            "interval_ms": pd.Series(dtype="float64"),
        })

    def reset(self):
        with self._lock:
            self._df = self._create_empty_df()
            self._last_timestamp = self._last_sequence = None
            self._last_by_code.clear()
            self._loss_by_code.clear()

    def reset_stream_state(self, clear_records: bool = False, skip_samples: int = 0):
        """스트림 상태 리셋."""
        with self._lock:
            logger.info(f"[STATS] reset_stream_state: clear={clear_records}")
            self._last_by_code.clear()
            self._loss_by_code.clear()
            if clear_records:
                self._df = self._create_empty_df()

    def get_dataframe(self) -> pd.DataFrame:
        """전체 DataFrame 복사본 반환 (외부 분석용)."""
        with self._lock:
            return self._df.copy()
