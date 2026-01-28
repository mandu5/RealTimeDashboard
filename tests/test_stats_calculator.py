"""
StatsCalculator 단위 테스트.

테스트 실행:
    python -m pytest tests/test_stats_calculator.py -v
"""

import pytest
import sys
import os
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ugv_mon.analysis.stats_calculator import StatsCalculator, PacketRecord
from ugv_mon.constants import MAX_SEQUENCE, EXPECTED_PPS


class TestStatsCalculatorBasic:
    """기본 기능 테스트."""

    def setup_method(self):
        """각 테스트 전 계산기 초기화."""
        self.calc = StatsCalculator(window_sec=60)

    def test_initial_state(self):
        """초기 상태 확인."""
        stats = self.calc.get_stats_dict()
        
        assert stats["pps"] == 0
        assert stats["jitter_avg"] == 0.0
        assert stats["jitter_p95"] == 0.0
        assert stats["jitter_p99"] == 0.0
        assert stats["packet_loss"] == 0

    def test_reset(self):
        """리셋 기능."""
        now = datetime.now()
        self.calc.record_packet(now, sequence=1, size=100)
        self.calc.record_packet(now + timedelta(milliseconds=10), sequence=2, size=100)
        
        self.calc.reset()
        stats = self.calc.get_stats_dict()
        
        assert stats["pps"] == 0


class TestJitterCalculation:
    """지터 계산 테스트."""

    def setup_method(self):
        self.calc = StatsCalculator(window_sec=60)

    def test_first_packet_no_jitter(self):
        """첫 패킷은 지터 없음."""
        now = datetime.now()
        jitter = self.calc.record_packet(now, sequence=1, size=100)
        
        assert jitter is None

    def test_jitter_calculation(self):
        """지터 계산 정확성 (간격 변동 기반)."""
        now = datetime.now()
        # 첫 번째 패킷 - 지터 없음
        self.calc.record_packet(now, sequence=1, size=100, msg_code=1)
        
        # 두 번째 패킷 (10ms 후) - 첫 간격 기록, 지터 아직 없음
        jitter2 = self.calc.record_packet(now + timedelta(milliseconds=10), sequence=2, size=100, msg_code=1)
        assert jitter2 is None  # 첫 간격만 기록됨
        
        # 세 번째 패킷 (10ms 후) - 지터 = |10 - 10| = 0
        jitter3 = self.calc.record_packet(now + timedelta(milliseconds=20), sequence=3, size=100, msg_code=1)
        assert jitter3 is not None
        assert abs(jitter3 - 0.0) < 1.0  # 동일 간격이므로 지터 거의 0

    def test_average_jitter(self):
        """평균 지터 계산 (간격 변동 기반)."""
        now = datetime.now()
        intervals = [10, 10, 10]  # ms - 동일 간격
        
        self.calc.record_packet(now, sequence=0, size=100, msg_code=1)
        for i, interval in enumerate(intervals):
            now += timedelta(milliseconds=interval)
            self.calc.record_packet(now, sequence=i+1, size=100, msg_code=1)
        
        avg = self.calc.get_average_jitter()
        # 동일 간격이므로 지터 변동 = 0
        assert avg < 1.0

    def test_jitter_percentiles(self):
        """지터 백분위 계산 (간격 변동 기반)."""
        now = datetime.now()
        
        # 100개 패킷 기록 (10ms 간격) - 동일 간격이므로 지터 모두 ~0
        self.calc.record_packet(now, sequence=0, size=100, msg_code=1)
        for i in range(100):
            now += timedelta(milliseconds=10)
            self.calc.record_packet(now, sequence=(i+1) % MAX_SEQUENCE, size=100, msg_code=1)
        
        p95, p99 = self.calc.get_jitter_percentiles()
        
        # 동일 간격이므로 P95, P99도 거의 0이어야 함
        assert p95 < 2.0
        assert p99 < 2.0


class TestPacketLossCalculation:
    """패킷 손실 계산 테스트."""

    def setup_method(self):
        self.calc = StatsCalculator(window_sec=60)

    def test_no_loss(self):
        """손실 없는 연속 시퀀스."""
        now = datetime.now()
        for i in range(10):
            self.calc.record_packet(now + timedelta(milliseconds=i*10), sequence=i, size=100)
        
        loss = self.calc.get_packet_loss()
        
        assert loss == 0

    def test_single_packet_loss(self):
        """단일 패킷 손실."""
        now = datetime.now()
        self.calc.record_packet(now, sequence=1, size=100)
        self.calc.record_packet(now + timedelta(milliseconds=10), sequence=3, size=100)  # 2 누락
        
        loss = self.calc.get_packet_loss()
        
        assert loss == 1

    def test_multiple_packet_loss(self):
        """다중 패킷 손실."""
        now = datetime.now()
        self.calc.record_packet(now, sequence=1, size=100)
        self.calc.record_packet(now + timedelta(milliseconds=10), sequence=5, size=100)  # 2,3,4 누락
        
        loss = self.calc.get_packet_loss()
        
        assert loss == 3

    def test_sequence_rollover_no_loss(self):
        """시퀀스 롤오버 (손실 없음)."""
        now = datetime.now()
        self.calc.record_packet(now, sequence=255, size=100)
        self.calc.record_packet(now + timedelta(milliseconds=10), sequence=0, size=100)
        
        loss = self.calc.get_packet_loss()
        
        assert loss == 0

    def test_sequence_rollover_with_loss(self):
        """시퀀스 롤오버 + 손실."""
        now = datetime.now()
        self.calc.record_packet(now, sequence=254, size=100)
        self.calc.record_packet(now + timedelta(milliseconds=10), sequence=2, size=100)  # 255, 0, 1 누락?
        
        loss = self.calc.get_packet_loss()
        
        # 254 -> 2: gap = (256-254) + 2 = 4, loss = 4-1 = 3
        assert loss == 3


class TestPPSCalculation:
    """PPS 계산 테스트."""

    def setup_method(self):
        self.calc = StatsCalculator(window_sec=60)

    def test_pps_empty(self):
        """빈 상태 PPS."""
        assert self.calc.get_pps() == 0

    def test_pps_recent_packets(self):
        """최근 1초 내 패킷 카운트."""
        now = datetime.now()
        
        # 1초 내에 5개 패킷
        for i in range(5):
            self.calc.record_packet(now - timedelta(milliseconds=100*i), sequence=i, size=100)
        
        pps = self.calc.get_pps()
        
        assert pps == 5


class TestAvailabilityCalculation:
    """가용성 계산 테스트."""

    def setup_method(self):
        self.calc = StatsCalculator(window_sec=60)

    def test_availability_empty(self):
        """빈 상태는 0% 가용성 (패킷 없음 = 연결 없음)."""
        avail = self.calc.get_availability()
        
        assert avail == 0.0

    def test_availability_capped_at_100(self):
        """가용성 100% 상한."""
        now = datetime.now()
        
        # 매우 많은 패킷 (비현실적으로 높은 PPS)
        for i in range(10000):
            self.calc.record_packet(now - timedelta(milliseconds=i), sequence=i % MAX_SEQUENCE, size=100)
        
        avail = self.calc.get_availability()
        
        assert avail <= 100.0


class TestWindowPruning:
    """윈도우 기반 정리 테스트."""

    def setup_method(self):
        self.calc = StatsCalculator(window_sec=10)  # 10초 윈도우

    def test_old_records_pruned(self):
        """오래된 기록 삭제."""
        now = datetime.now()
        
        # 15초 전 패킷
        old_time = now - timedelta(seconds=15)
        self.calc.record_packet(old_time, sequence=1, size=100)
        
        # 현재 패킷 (이 때 정리됨)
        self.calc.record_packet(now, sequence=2, size=100)
        
        # 통계는 최근 패킷만 반영해야 함
        stats = self.calc.get_stats_dict()
        
        # 오래된 기록이 정리되어 손실 계산에 영향 없음
        assert stats["packet_loss"] == 0


class TestSequenceGap:
    """시퀀스 갭 계산 테스트."""

    def setup_method(self):
        self.calc = StatsCalculator(window_sec=60)

    def test_normal_gap(self):
        """일반 갭."""
        gap = self.calc._seq_gap(10, 11)
        assert gap == 1

    def test_multiple_gap(self):
        """다중 갭."""
        gap = self.calc._seq_gap(10, 15)
        assert gap == 5

    def test_rollover_gap(self):
        """롤오버 갭."""
        gap = self.calc._seq_gap(255, 0)
        assert gap == 1

    def test_rollover_with_extra(self):
        """롤오버 + 추가 갭."""
        gap = self.calc._seq_gap(250, 5)
        # (256 - 250) + 5 = 11
        assert gap == 11
