"""
Capture Statistics Module.

패킷 캡처 중 발생하는 통계를 추적합니다:
- 총 패킷 수 (packets_total)
- 필터 통과 패킷 수 (packets_filtered)
- 총 바이트 수 (bytes_total)
- PPS (Packets Per Second) - 1초 슬라이딩 윈도우

=============================================================================
Q: 왜 dataclass를 사용하나요?
A: Python 3.7+의 dataclass는 __init__, __repr__ 등을 자동 생성합니다.
   보일러플레이트 코드를 줄이고 타입 안전성을 높입니다.

Q: PPS 계산에 왜 1초 윈도우를 사용하나요?
A: 실시간 모니터링에서 "초당 패킷 수"가 가장 직관적인 지표입니다.
   윈도우가 너무 짧으면 값이 불안정하고, 너무 길면 반응이 느립니다.
=============================================================================
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CaptureStats:
    """
    패킷 캡처 통계 클래스.
    
    캡처 중 발생하는 각종 통계를 추적하고 계산합니다.
    
    Attributes:
        packets_total: 인터페이스에서 캡처된 총 패킷 수
        packets_filtered: BPF 필터를 통과한 패킷 수
        bytes_total: 캡처된 총 바이트 수
        start_time: 캡처 시작 시간
        last_packet_time: 마지막 패킷 수신 시간
    
    사용 예시:
        stats = CaptureStats()
        stats.record_packet(size=150, filtered=True)
        print(f"PPS: {stats.get_pps()}")
    """
    
    # =========================================================================
    # 패킷 카운터
    # - 왜 int = 0 인가? dataclass는 기본값이 있는 필드를 자동으로 __init__에 포함
    # =========================================================================
    packets_total: int = 0       # 총 캡처된 패킷 수
    packets_filtered: int = 0    # BPF 필터 통과한 패킷 수
    bytes_total: int = 0         # 총 바이트 수
    
    # =========================================================================
    # 시간 정보
    # - Optional[datetime]: datetime 또는 None 가능
    # =========================================================================
    start_time: Optional[datetime] = None        # 캡처 시작 시간
    last_packet_time: Optional[datetime] = None  # 마지막 패킷 수신 시간
    
    # =========================================================================
    # PPS 계산용 내부 변수
    # - field(default=..., repr=False): __repr__에서 제외 (내부 구현 상세)
    # - _prefix: Python 관례상 "내부용" 표시
    # =========================================================================
    _pps_window_start: Optional[datetime] = field(default=None, repr=False)
    _pps_window_count: int = field(default=0, repr=False)
    _current_pps: int = field(default=0, repr=False)
    
    def record_packet(self, size: int, filtered: bool = True) -> None:
        """
        패킷 수신 기록.
        
        새 패킷이 수신될 때마다 호출하여 통계를 업데이트합니다.
        PacketSniffer._process_packet()에서 호출됩니다.
        
        Args:
            size: 패킷 크기 (바이트). len(raw_data)로 계산
            filtered: BPF 필터 통과 여부. True면 우리가 원하는 패킷
        
        Q: 왜 filtered 파라미터가 있나요?
        A: Scapy의 BPF 필터를 통과한 패킷만 True입니다.
           나중에 필터 통과율 계산에 사용됩니다.
        """
        now = datetime.now()
        
        # 총 패킷 수 증가 (필터 통과 여부와 무관하게)
        self.packets_total += 1
        self.bytes_total += size
        
        # 필터 통과 시에만 filtered 카운트 증가
        if filtered:
            self.packets_filtered += 1
        
        # 시간 정보 업데이트
        # - 첫 패킷이면 start_time 설정
        # - 매 패킷마다 last_packet_time 갱신
        if self.start_time is None:
            self.start_time = now
        self.last_packet_time = now
        
        # PPS 계산 (1초 슬라이딩 윈도우)
        self._update_pps(now)
    
    def _update_pps(self, now: datetime) -> None:
        """
        PPS(초당 패킷 수) 업데이트.
        
        1초 슬라이딩 윈도우 방식으로 PPS를 계산합니다.
        윈도우가 지나면 현재 카운트를 PPS로 확정하고 리셋합니다.
        
        Args:
            now: 현재 시간 (datetime 객체)
        
        동작 방식:
        1. 첫 패킷 → 윈도우 시작, 카운트 = 1
        2. 1초 이내 → 카운트만 증가
        3. 1초 경과 → PPS 확정, 윈도우 리셋
        
        Q: 왜 슬라이딩 윈도우인가요?
        A: 고정 윈도우(매 정초에 리셋)보다 실시간성이 좋습니다.
           예: 12:00:00.5에 시작해도 12:00:01.5에 PPS 확정
        """
        # 첫 패킷이거나 윈도우 시작이 없는 경우
        if self._pps_window_start is None:
            self._pps_window_start = now
            self._pps_window_count = 1
            return
        
        # 현재 윈도우 내의 경과 시간 계산
        # timedelta.total_seconds(): 시간차를 초 단위 float로 변환
        elapsed = (now - self._pps_window_start).total_seconds()
        
        if elapsed >= 1.0:
            # 1초가 지났으면 PPS 확정 및 윈도우 리셋
            # _current_pps: 마지막 완료된 1초 동안의 패킷 수
            self._current_pps = self._pps_window_count
            self._pps_window_start = now
            self._pps_window_count = 1
        else:
            # 아직 1초 이내면 카운트만 증가
            self._pps_window_count += 1
    
    def get_pps(self) -> int:
        """
        현재 PPS(초당 패킷 수) 반환.
        
        마지막으로 완료된 1초 윈도우의 패킷 수를 반환합니다.
        UI에서 "수신 pps" KPI 카드에 표시됩니다.
        
        Returns:
            초당 패킷 수 (정수)
        
        Q: 왜 현재 윈도우 카운트가 아닌 이전 윈도우 값인가요?
        A: 현재 윈도우는 아직 1초가 안 됐으므로 불완전합니다.
           완료된 윈도우 값이 더 정확하고 안정적입니다.
        """
        return self._current_pps
    
    def get_filter_pass_pct(self) -> float:
        """
        필터 통과율 계산.
        
        전체 패킷 중 BPF 필터를 통과한 패킷의 비율입니다.
        "필터 통과율" KPI 카드에 표시됩니다.
        
        Returns:
            필터 통과율 (0.0 ~ 100.0)
        
        Q: 왜 100.0을 기본값으로 반환하나요?
        A: 아직 패킷이 없으면 0%가 아닌 100%가 맞습니다.
           "아직 실패한 패킷이 없다"는 의미입니다.
        """
        if self.packets_total == 0:
            return 100.0  # 0으로 나누기 방지
        return (self.packets_filtered / self.packets_total) * 100.0
    
    def get_duration_sec(self) -> float:
        """
        캡처 지속 시간(초) 반환.
        
        캡처 시작부터 현재까지의 시간을 초 단위로 반환합니다.
        
        Returns:
            캡처 지속 시간 (초, 소수점 포함)
        """
        if self.start_time is None:
            return 0.0
        return (datetime.now() - self.start_time).total_seconds()
    
    def reset(self) -> None:
        """
        통계 초기화.
        
        모든 통계 값을 초기 상태로 리셋합니다.
        캡처 재시작 또는 수동 초기화 시 호출합니다.
        
        PacketSniffer.start() 내부에서 자동 호출됩니다.
        """
        self.packets_total = 0
        self.packets_filtered = 0
        self.bytes_total = 0
        self.start_time = None
        self.last_packet_time = None
        self._pps_window_start = None
        self._pps_window_count = 0
        self._current_pps = 0
    
    def to_dict(self) -> dict:
        """
        딕셔너리로 변환.
        
        UI 표시용 또는 디버깅용으로 통계를 딕셔너리로 변환합니다.
        JSON 직렬화가 필요할 때 사용합니다.
        
        Returns:
            통계 정보 딕셔너리
        """
        return {
            "packets_total": self.packets_total,
            "packets_filtered": self.packets_filtered,
            "bytes_total": self.bytes_total,
            "pps": self.get_pps(),
            "filter_pass_pct": round(self.get_filter_pass_pct(), 1),
            "duration_sec": round(self.get_duration_sec(), 1),
            "last_packet_time": (
                self.last_packet_time.strftime("%H:%M:%S") 
                if self.last_packet_time else ""
            ),
        }
