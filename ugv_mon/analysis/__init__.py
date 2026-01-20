"""
UGV-MON Analysis Module.

통계 분석 및 이상 탐지 기능을 제공합니다.

=============================================================================
모듈 구성:
- StatsCalculator: 실시간 통계 계산 (지터, PPS, 가용성)
- AnomalyDetector: 이상 탐지 및 알림

주요 기능:
1. 지터 계산 (P95, P99 백분위수)
2. 패킷 손실 추정 (시퀀스 갭 분석)
3. 가용성 계산 (5분/1시간 슬라이딩 윈도우)
4. 이상 탐지 (지터 임계값, 손실률)

사용 예시:
    from ugv_mon.analysis import StatsCalculator, AnomalyDetector
    
    stats = StatsCalculator(window_sec=60)
    anomaly = AnomalyDetector()
    
    # 패킷 수신 시마다
    jitter = stats.record_packet(timestamp, sequence, size)
    
    # 이상 탐지
    if jitter and jitter > anomaly.jitter_threshold:
        print(f"높은 지터 감지: {jitter}ms")
    
    # 통계 조회
    p95, p99 = stats.get_jitter_percentiles()
    availability = stats.get_availability()

Q: 왜 별도 모듈로 분리했나요?
A: 단일 책임 원칙(SRP). 캡처/파싱과 분석은 다른 관심사입니다.
   테스트도 독립적으로 수행 가능합니다.
=============================================================================
"""

from .stats_calculator import StatsCalculator
from .anomaly_detector import AnomalyDetector, AnomalyType

__all__ = ["StatsCalculator", "AnomalyDetector", "AnomalyType"]
