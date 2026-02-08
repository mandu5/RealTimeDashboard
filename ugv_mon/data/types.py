"""
대시보드 데이터 타입 정의.

이 모듈은 live_provider가 반환하는 데이터의 구조를 명확히 정의합니다.
TypedDict를 사용하여 타입 안전성과 IDE 자동완성을 지원합니다.

데이터 흐름:
    UDP → bytes → ParseResult → DashboardData → UI

Note:
    실제 Dict 키는 하위 호환성을 위해 flat 구조 유지.
    이 파일은 문서화와 타입 체크 목적.
"""

from typing import Optional, TypedDict


class ConnectionState(TypedDict):
    """연결 상태 (5개 키).

    Attributes:
        connected: 현재 연결 여부
        interface: 네트워크 인터페이스 (eno2, lo 등)
        direction: 캡처 방향 ("status" 또는 "control")
        filter: 포트 필터 (예: "50000→61000")
        lastPacketTime: 마지막 패킷 수신 시각 (HH:MM:SS)
    """
    connected: bool
    interface: str
    direction: str
    filter: str
    lastPacketTime: str


class StatsState(TypedDict):
    """통계 상태 (9개 키).

    Attributes:
        capturePps: 초당 패킷 수
        parseSuccess: 파싱 성공률 (%)
        checksumFail: 체크섬 실패율 (%)
        packetLoss: 누적 패킷 손실 수
        availability: 5분 가용성 (%)
        availabilityHourly: 1시간 가용성 (%)
        jitterCurrent: 현재 지터 (ms)
        jitterP95: 지터 95번째 백분위 (ms)
    """
    capturePps: int
    parseSuccess: float
    checksumFail: float
    packetLoss: int
    availability: float
    availabilityHourly: float
    jitterCurrent: float
    jitterP95: float


class OperationalState(TypedDict):
    """운용 상태 (4개 키).

    Attributes:
        operationalMode: 운용 모드 (자율주행, 원격조종 등)
        operationalAuthority: 운용 권한 (VIC, OCS)
        drivingState: 주행 상태 (정지, 주행 등)
        emergencyStatus: 비상정지 상태 딕셔너리
    """
    operationalMode: str
    operationalAuthority: str
    drivingState: str
    emergencyStatus: dict[str, bool]


class ChartDataPoint(TypedDict):
    """차트 데이터 포인트.

    Attributes:
        timestamp: 시각 (HH:MM:SS)
        pps: 초당 패킷 수
        jitter: 지터 값 (ms)
    """
    timestamp: str
    pps: int
    jitter: float


class AvailabilitySegment(TypedDict):
    """가용성 타임라인 세그먼트.

    Attributes:
        start: 시작 위치 (초)
        end: 종료 위치 (초)
        isUp: 연결 상태
    """
    start: float
    end: float
    isUp: bool


class ConnectionHistoryEntry(TypedDict):
    """연결 이력 항목.

    Attributes:
        timestamp: ISO 형식 시각
        connected: 연결 여부
        duration: 지속 시간 (초), 다음 변경 시 계산
    """
    timestamp: str
    connected: bool
    duration: Optional[float]


class ModeTransitionEntry(TypedDict):
    """운용모드 전이 항목.

    Attributes:
        timestamp: ISO 형식 시각
        from: 이전 모드
        to: 새 모드
    """
    timestamp: str
    # 'from'은 예약어라 주석으로 표시
    # from: str
    to: str


class DeviceStatus(TypedDict):
    """장치 상태.

    Attributes:
        name: 장치 이름
        connected: 연결 여부
    """
    name: str
    connected: bool


class UIState(TypedDict):
    """UI 렌더링용 상태 (8개 키).

    Attributes:
        combinedData: 차트 데이터 배열
        devices: 장치 상태 배열
        availabilitySegments: 가용성 세그먼트 배열
        msgCodeStats: msg_code별 통계
        connectionHistory: 연결 이력
        modeTransitions: 모드 전이 이력
        emergencyCounts: 비상정지 원인별 카운트
    """
    combinedData: list[ChartDataPoint]
    devices: list[DeviceStatus]
    availabilitySegments: list[AvailabilitySegment]
    msgCodeStats: dict[int, dict]
    connectionHistory: list[ConnectionHistoryEntry]
    modeTransitions: list[ModeTransitionEntry]
    emergencyCounts: dict[str, int]


class DashboardData(ConnectionState, StatsState, OperationalState, UIState):
    """전체 대시보드 데이터 (26개 키).

    이 TypedDict는 live_provider.generate_initial_data() 및
    update_data()가 반환하는 데이터의 전체 구조를 정의합니다.

    구조:
        - ConnectionState (5개): 연결 상태
        - StatsState (9개): 통계
        - OperationalState (4개): 운용 상태
        - UIState (8개): UI 렌더링용

    총 26개 키 = 5 + 9 + 4 + 8

    데이터 흐름:
        1. UDP 패킷 수신 (bytes)
        2. PacketQueue에 저장 (deque[Tuple[datetime, bytes]])
        3. ICDParser로 파싱 (ParseResult)
        4. StatsCalculator로 통계 계산 (PacketRecord)
        5. _build_state()로 DashboardData 생성
        6. Dash 콜백에서 UI 컴포넌트로 변환
    """
    pass


# 데이터 키 상수 (중복 방지용)
DATA_KEYS = {
    "connection": ["connected", "interface", "direction", "filter", "lastPacketTime"],
    "stats": [
        "capturePps", "parseSuccess", "checksumFail", "packetLoss",
        "availability", "availabilityHourly",
        "jitterCurrent", "jitterP95"
    ],
    "operational": ["operationalMode", "operationalAuthority", "drivingState", "emergencyStatus"],
    "ui": [
        "combinedData", "devices", "availabilitySegments", "msgCodeStats",
        "connectionHistory", "modeTransitions", "emergencyCounts"
    ],
}
