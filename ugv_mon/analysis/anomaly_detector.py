"""
Anomaly Detector Module.

이상 탐지 및 알림 기능을 제공합니다.

=============================================================================
탐지 대상:
1. 높은 지터 (P95/P99 임계값 초과)
2. 패킷 손실 (시퀀스 갭)
3. 연결 타임아웃 (N초 이상 패킷 없음)
4. 체크섬 오류율 증가

Q: 왜 이상 탐지가 필요한가요?
A: 실시간 모니터링에서 자동으로 문제를 감지하여
   운영자가 빠르게 대응할 수 있도록 합니다.
   수천 개의 패킷 중 문제를 눈으로 찾기는 어렵습니다.

Q: 임계값은 어떻게 정했나요?
A: 일반적인 네트워크 품질 기준입니다:
   - 지터 < 10ms: 양호
   - 지터 10-50ms: 경고
   - 지터 > 50ms: 심각
   실제 운영 환경에 맞게 조정이 필요합니다.
=============================================================================
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict
import threading


class AnomalyType(Enum):
    """
    이상 유형 열거형.
    
    탐지된 이상의 종류를 나타냅니다.
    """
    HIGH_JITTER = "high_jitter"           # 높은 지터
    PACKET_LOSS = "packet_loss"           # 패킷 손실
    CONNECTION_TIMEOUT = "connection_timeout"  # 연결 타임아웃
    CHECKSUM_ERROR = "checksum_error"     # 체크섬 오류
    PARSE_ERROR = "parse_error"           # 파싱 오류


@dataclass
class Anomaly:
    """
    탐지된 이상 정보.
    
    Attributes:
        type: 이상 유형
        timestamp: 탐지 시간
        message: 설명 메시지
        value: 관련 수치 (지터값, 손실 수 등)
        severity: 심각도 (warning, error)
    """
    type: AnomalyType
    timestamp: datetime
    message: str
    value: Optional[float] = None
    severity: str = "warning"  # warning, error
    
    def to_dict(self) -> Dict:
        """딕셔너리 변환."""
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.strftime("%H:%M:%S"),
            "message": self.message,
            "value": self.value,
            "severity": self.severity,
        }


class AnomalyDetector:
    """
    이상 탐지기.
    
    실시간으로 패킷 품질을 모니터링하고 이상을 탐지합니다.
    
    Attributes:
        jitter_warning: 지터 경고 임계값 (ms)
        jitter_error: 지터 오류 임계값 (ms)
        timeout_sec: 연결 타임아웃 (초)
        checksum_error_threshold: 체크섬 오류율 임계값 (%)
    
    사용 예시:
        detector = AnomalyDetector()
        
        # 지터 체크
        anomaly = detector.check_jitter(jitter_ms=25.5)
        if anomaly:
            print(f"이상 감지: {anomaly.message}")
        
        # 타임아웃 체크
        anomaly = detector.check_timeout(last_packet_time)
        if anomaly:
            print("연결 타임아웃!")
    """
    
    def __init__(
        self,
        jitter_warning: float = 10.0,
        jitter_error: float = 50.0,
        timeout_sec: float = 5.0,
        checksum_error_threshold: float = 1.0
    ):
        """
        AnomalyDetector 초기화.
        
        Args:
            jitter_warning: 지터 경고 임계값 (ms)
            jitter_error: 지터 오류 임계값 (ms)
            timeout_sec: 연결 타임아웃 (초)
            checksum_error_threshold: 체크섬 오류율 임계값 (%)
        
        Q: 왜 이 기본값들인가요?
        A: 일반적인 산업용 네트워크 기준입니다:
           - 10ms: 사람이 느끼지 못하는 지연
           - 50ms: 실시간 제어에 영향 줄 수 있는 지연
           - 5초: 연결 끊김으로 간주하는 일반적인 타임아웃
           실제 VIC↔OCS 요구사항에 맞게 조정하세요.
        """
        self._jitter_warning = jitter_warning
        self._jitter_error = jitter_error
        self._timeout_sec = timeout_sec
        self._checksum_error_threshold = checksum_error_threshold
        
        # 최근 이상 기록 (UI 표시용)
        self._recent_anomalies: List[Anomaly] = []
        self._max_anomalies = 100  # 최대 저장 개수
        
        # 스레드 안전성
        self._lock = threading.Lock()
    
    def check_jitter(self, jitter_ms: float) -> Optional[Anomaly]:
        """
        지터 이상 탐지.
        
        Args:
            jitter_ms: 현재 지터 값 (밀리초)
        
        Returns:
            Anomaly 객체 (이상 감지 시) 또는 None
        
        Q: P95/P99가 아닌 개별 값을 왜 체크하나요?
        A: 실시간 알림을 위해서입니다.
           P95는 누적 통계이므로 즉각적인 문제 감지가 어렵습니다.
           개별 패킷의 지터가 높으면 바로 경고합니다.
        """
        if jitter_ms is None:
            return None
        
        anomaly = None
        
        if jitter_ms >= self._jitter_error:
            anomaly = Anomaly(
                type=AnomalyType.HIGH_JITTER,
                timestamp=datetime.now(),
                message=f"심각한 지터 감지: {jitter_ms:.1f}ms (임계값: {self._jitter_error}ms)",
                value=jitter_ms,
                severity="error"
            )
        elif jitter_ms >= self._jitter_warning:
            anomaly = Anomaly(
                type=AnomalyType.HIGH_JITTER,
                timestamp=datetime.now(),
                message=f"높은 지터 감지: {jitter_ms:.1f}ms (임계값: {self._jitter_warning}ms)",
                value=jitter_ms,
                severity="warning"
            )
        
        if anomaly:
            self._add_anomaly(anomaly)
        
        return anomaly
    
    def check_timeout(self, last_packet_time: Optional[datetime]) -> Optional[Anomaly]:
        """
        연결 타임아웃 탐지.
        
        Args:
            last_packet_time: 마지막 패킷 수신 시간
        
        Returns:
            Anomaly 객체 (타임아웃 시) 또는 None
        
        Q: 타임아웃은 왜 5초인가요?
        A: VIC↔OCS 통신이 보통 1초 미만 간격입니다.
           5초 동안 패킷이 없으면 연결 문제로 볼 수 있습니다.
           요구사항에 따라 조정하세요.
        """
        if last_packet_time is None:
            return None
        
        elapsed = (datetime.now() - last_packet_time).total_seconds()
        
        if elapsed >= self._timeout_sec:
            anomaly = Anomaly(
                type=AnomalyType.CONNECTION_TIMEOUT,
                timestamp=datetime.now(),
                message=f"연결 타임아웃: {elapsed:.1f}초 동안 패킷 없음",
                value=elapsed,
                severity="error"
            )
            self._add_anomaly(anomaly)
            return anomaly
        
        return None
    
    def check_packet_loss(self, prev_seq: int, curr_seq: int) -> Optional[Anomaly]:
        """
        패킷 손실 탐지.
        
        Args:
            prev_seq: 이전 시퀀스 번호
            curr_seq: 현재 시퀀스 번호
        
        Returns:
            Anomaly 객체 (손실 감지 시) 또는 None
        """
        # 시퀀스 갭 계산 (롤오버 고려)
        if curr_seq >= prev_seq:
            gap = curr_seq - prev_seq
        else:
            gap = (256 - prev_seq) + curr_seq
        
        if gap > 1:
            lost_count = gap - 1
            anomaly = Anomaly(
                type=AnomalyType.PACKET_LOSS,
                timestamp=datetime.now(),
                message=f"패킷 손실 감지: {lost_count}개 (seq {prev_seq} → {curr_seq})",
                value=lost_count,
                severity="warning" if lost_count < 5 else "error"
            )
            self._add_anomaly(anomaly)
            return anomaly
        
        return None
    
    def check_checksum_error(self, error_count: int, total_count: int) -> Optional[Anomaly]:
        """
        체크섬 오류율 탐지.
        
        Args:
            error_count: 체크섬 오류 수
            total_count: 총 패킷 수
        
        Returns:
            Anomaly 객체 (오류율 초과 시) 또는 None
        """
        if total_count == 0:
            return None
        
        error_rate = (error_count / total_count) * 100
        
        if error_rate >= self._checksum_error_threshold:
            anomaly = Anomaly(
                type=AnomalyType.CHECKSUM_ERROR,
                timestamp=datetime.now(),
                message=f"체크섬 오류율 증가: {error_rate:.1f}% ({error_count}/{total_count})",
                value=error_rate,
                severity="error"
            )
            self._add_anomaly(anomaly)
            return anomaly
        
        return None
    
    def _add_anomaly(self, anomaly: Anomaly) -> None:
        """
        이상 기록 추가.
        
        Args:
            anomaly: 이상 객체
        """
        with self._lock:
            self._recent_anomalies.insert(0, anomaly)
            
            # 최대 개수 초과 시 오래된 것 제거
            if len(self._recent_anomalies) > self._max_anomalies:
                self._recent_anomalies = self._recent_anomalies[:self._max_anomalies]
    
    def get_recent_anomalies(self, limit: int = 10) -> List[Anomaly]:
        """
        최근 이상 목록 반환.
        
        Args:
            limit: 최대 반환 개수
        
        Returns:
            이상 목록 (최신순)
        """
        with self._lock:
            return self._recent_anomalies[:limit]
    
    def clear_anomalies(self) -> None:
        """이상 기록 초기화."""
        with self._lock:
            self._recent_anomalies.clear()
    
    @property
    def jitter_warning(self) -> float:
        """지터 경고 임계값."""
        return self._jitter_warning
    
    @property
    def jitter_error(self) -> float:
        """지터 오류 임계값."""
        return self._jitter_error
    
    @property
    def timeout_sec(self) -> float:
        """연결 타임아웃 (초)."""
        return self._timeout_sec
