"""
Statistics Calculator Module.

실시간 통계 계산 기능을 제공합니다:
- PPS (Packets Per Second)
- 지터 (P95, P99 백분위수)
- 패킷 손실률
- 가용성 (5분/1시간)

=============================================================================
슬라이딩 윈도우 방식:
- 고정 크기 윈도우 내의 데이터만 사용
- 오래된 데이터는 자동으로 만료
- 메모리 사용량 제한

Q: 왜 슬라이딩 윈도우를 사용하나요?
A: 1. 메모리 효율: 모든 데이터를 저장하면 메모리 폭발
   2. 최신성: 오래된 데이터는 현재 상태를 반영하지 않음
   3. 실시간성: 짧은 윈도우로 빠른 변화 감지

Q: P95/P99란 무엇인가요?
A: 백분위수(Percentile). P95 = 데이터의 95%가 이 값 이하.
   예: P95 지터 = 2.1ms → 95%의 패킷이 2.1ms 이하 지터
   P99는 더 극단적인 값을 나타냅니다 (이상값 감지에 유용).
=============================================================================
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import threading


@dataclass
class PacketRecord:
    """
    패킷 수신 기록.
    
    지터 및 PPS 계산에 사용됩니다.
    
    Attributes:
        timestamp: 수신 시간
        sequence: ICD 시퀀스 번호 (0-255)
        size: 패킷 크기 (bytes)
        jitter_ms: 이전 패킷과의 지터 (ms)
    """
    timestamp: datetime
    sequence: int
    size: int
    jitter_ms: Optional[float] = None


class StatsCalculator:
    """
    실시간 통계 계산기.
    
    슬라이딩 윈도우 방식으로 최신 데이터에 대한 통계를 계산합니다.
    
    Attributes:
        window_sec: 통계 윈도우 크기 (초)
    
    사용 예시:
        calculator = StatsCalculator(window_sec=60)
        
        # 패킷 수신 시마다 호출
        jitter = calculator.record_packet(
            timestamp=datetime.now(),
            sequence=packet.header.sequence,
            size=len(raw_data)
        )
        
        # 통계 조회
        p95, p99 = calculator.get_jitter_percentiles()
        loss = calculator.get_packet_loss()
    """
    
    def __init__(self, window_sec: int = 60):
        """
        StatsCalculator 초기화.
        
        Args:
            window_sec: 통계 윈도우 크기 (초)
                       기본값 60초 = 1분간 데이터로 통계 계산
        
        Q: 왜 60초인가요?
        A: 1분은 실시간 모니터링에 적절한 단위입니다.
           너무 짧으면 변동이 심하고, 너무 길면 반응이 느립니다.
        """
        self._window_sec = window_sec
        
        # =====================================================================
        # 패킷 기록 저장소
        # deque: 양방향 큐. 오래된 데이터 제거에 O(1)
        # =====================================================================
        self._records: deque = deque()
        
        # 마지막 패킷 정보 (지터 계산용)
        self._last_timestamp: Optional[datetime] = None
        self._last_sequence: Optional[int] = None
        
        # 시퀀스 롤오버 상수
        self._max_sequence = 256  # 8비트 시퀀스 (0-255)
        
        # 스레드 안전성 (LiveDataProvider와 UI 스레드 동시 접근)
        self._lock = threading.Lock()
    
    def record_packet(
        self,
        timestamp: datetime,
        sequence: int,
        size: int
    ) -> Optional[float]:
        """
        패킷 수신 기록.
        
        새 패킷이 파싱될 때마다 호출합니다.
        지터를 계산하고 반환합니다.
        
        Args:
            timestamp: 패킷 수신 시간
            sequence: ICD 시퀀스 번호 (0-255)
            size: 패킷 크기 (bytes)
        
        Returns:
            이전 패킷과의 지터 (ms), 첫 패킷이면 None
        
        Q: 지터는 어떻게 계산하나요?
        A: 현재 패킷과 이전 패킷의 시간 간격 변화량입니다.
           실제로는 간단히 수신 간격(inter-arrival time)을 사용합니다.
           |현재_간격 - 예상_간격| 이 정확한 지터지만,
           모니터링에서는 수신 간격 자체도 유용한 지표입니다.
        """
        with self._lock:
            jitter_ms = None
            
            # 이전 패킷이 있으면 지터 계산
            if self._last_timestamp is not None:
                # 시간 간격 계산 (밀리초)
                time_diff = (timestamp - self._last_timestamp).total_seconds() * 1000
                jitter_ms = abs(time_diff)  # 절대값 사용
            
            # 패킷 기록 추가
            record = PacketRecord(
                timestamp=timestamp,
                sequence=sequence,
                size=size,
                jitter_ms=jitter_ms
            )
            self._records.append(record)
            
            # 마지막 패킷 정보 업데이트
            self._last_timestamp = timestamp
            self._last_sequence = sequence
            
            # 오래된 데이터 제거 (윈도우 외부)
            self._prune_old_records(timestamp)
            
            return jitter_ms
    
    def _prune_old_records(self, current_time: datetime) -> None:
        """
        윈도우 외부의 오래된 기록 제거.
        
        Args:
            current_time: 현재 시간
        
        Q: 왜 매번 prune하나요?
        A: 메모리 누수 방지. 지속적으로 데이터가 쌓이면 문제가 됩니다.
           deque.popleft()는 O(1)이므로 성능 영향 적습니다.
        """
        cutoff = current_time - timedelta(seconds=self._window_sec)
        
        # 왼쪽(오래된 쪽)에서 제거
        while self._records and self._records[0].timestamp < cutoff:
            self._records.popleft()
    
    def get_jitter_percentiles(self) -> Tuple[float, float]:
        """
        지터 백분위수 계산 (P95, P99).
        
        Returns:
            (P95, P99) 튜플 (밀리초)
        
        Q: 백분위수는 어떻게 계산하나요?
        A: 1. 모든 지터 값을 정렬
           2. 95% 위치의 값 = P95
           3. 99% 위치의 값 = P99
        """
        with self._lock:
            # 지터 값이 있는 레코드만 추출
            jitters = [r.jitter_ms for r in self._records if r.jitter_ms is not None]
            
            if not jitters:
                return (0.0, 0.0)
            
            # 정렬
            sorted_jitters = sorted(jitters)
            n = len(sorted_jitters)
            
            # P95: 95번째 백분위수
            # 인덱스 = ceil(n * 0.95) - 1
            p95_idx = min(int(n * 0.95), n - 1)
            p95 = sorted_jitters[p95_idx]
            
            # P99: 99번째 백분위수
            p99_idx = min(int(n * 0.99), n - 1)
            p99 = sorted_jitters[p99_idx]
            
            return (round(p95, 2), round(p99, 2))
    
    def get_packet_loss(self) -> int:
        """
        패킷 손실 추정.
        
        시퀀스 번호 갭을 분석하여 손실된 패킷 수를 추정합니다.
        
        Returns:
            추정 손실 패킷 수
        
        Q: 왜 "추정"인가요?
        A: 시퀀스 갭이 반드시 손실을 의미하지는 않습니다.
           재정렬(reordering)이나 중복(duplicate)도 갭을 만들 수 있습니다.
           하지만 대부분의 경우 손실로 볼 수 있습니다.
        """
        with self._lock:
            if len(self._records) < 2:
                return 0
            
            total_loss = 0
            records_list = list(self._records)
            
            for i in range(1, len(records_list)):
                prev_seq = records_list[i - 1].sequence
                curr_seq = records_list[i].sequence
                
                # 시퀀스 갭 계산 (롤오버 고려)
                gap = self._seq_gap_with_rollover(prev_seq, curr_seq)
                
                # 갭이 1보다 크면 손실로 간주
                if gap > 1:
                    total_loss += (gap - 1)
            
            return total_loss
    
    def _seq_gap_with_rollover(self, prev_seq: int, curr_seq: int) -> int:
        """
        롤오버를 고려한 시퀀스 갭 계산.
        
        Args:
            prev_seq: 이전 시퀀스 번호 (0-255)
            curr_seq: 현재 시퀀스 번호 (0-255)
        
        Returns:
            갭 값 (정상: 1, 손실: >1)
        
        예시:
            - 10 → 11: gap = 1 (정상)
            - 10 → 15: gap = 5 (4개 손실)
            - 255 → 0: gap = 1 (롤오버, 정상)
            - 254 → 2: gap = 4 (3개 손실)
        """
        if curr_seq >= prev_seq:
            return curr_seq - prev_seq
        else:
            # 롤오버 발생 (예: 255 → 0)
            return (self._max_sequence - prev_seq) + curr_seq
    
    def get_availability(self, window_sec: Optional[int] = None) -> float:
        """
        가용성 계산 (패킷 기반).
        
        Args:
            window_sec: 계산 윈도우 (기본값: 전체 윈도우)
        
        Returns:
            가용성 백분율 (0.0 ~ 100.0)
        
        계산 방법:
            가용성 = (수신 패킷 수 / 예상 패킷 수) * 100
            예상 패킷 수 = 윈도우 시간 * 예상 PPS
        
        Q: 왜 간단한 계산인가요?
        A: 정확한 가용성 계산은 복잡합니다 (down/up 구간 추적).
           여기서는 패킷 수신률로 근사합니다.
           실제 운영에서는 타임아웃 기반 down 감지를 병행합니다.
        """
        with self._lock:
            if not self._records:
                return 100.0  # 데이터 없으면 100% 가정
            
            # 윈도우 시간 동안의 패킷 수
            now = datetime.now()
            window = window_sec or self._window_sec
            cutoff = now - timedelta(seconds=window)
            
            packets_in_window = sum(
                1 for r in self._records if r.timestamp >= cutoff
            )
            
            # 예상 패킷 수 (1000 pps 가정)
            expected_pps = 1000
            expected_packets = window * expected_pps
            
            # 실제로는 패킷 수가 예상보다 적을 수 있음
            # 최대 100%로 제한
            availability = min(
                (packets_in_window / max(expected_packets, 1)) * 100,
                100.0
            )
            
            return round(availability, 2)
    
    def get_pps(self) -> int:
        """
        현재 PPS (초당 패킷 수) 계산.
        
        최근 1초 동안의 패킷 수를 반환합니다.
        
        Returns:
            초당 패킷 수
        """
        with self._lock:
            if not self._records:
                return 0
            
            now = datetime.now()
            one_sec_ago = now - timedelta(seconds=1)
            
            return sum(1 for r in self._records if r.timestamp >= one_sec_ago)
    
    def get_average_jitter(self) -> float:
        """
        평균 지터 계산.
        
        Returns:
            평균 지터 (밀리초)
        """
        with self._lock:
            jitters = [r.jitter_ms for r in self._records if r.jitter_ms is not None]
            
            if not jitters:
                return 0.0
            
            return round(sum(jitters) / len(jitters), 2)
    
    def reset(self) -> None:
        """통계 초기화."""
        with self._lock:
            self._records.clear()
            self._last_timestamp = None
            self._last_sequence = None
    
    def get_stats_dict(self) -> dict:
        """
        전체 통계 딕셔너리 반환.
        
        UI 업데이트에 사용됩니다.
        
        Returns:
            통계 딕셔너리
        """
        p95, p99 = self.get_jitter_percentiles()
        
        return {
            "pps": self.get_pps(),
            "jitter_avg": self.get_average_jitter(),
            "jitter_p95": p95,
            "jitter_p99": p99,
            "packet_loss": self.get_packet_loss(),
            "availability": self.get_availability(),
            "record_count": len(self._records),
        }
