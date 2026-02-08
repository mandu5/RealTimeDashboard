"""
PacketStore 단위 테스트.

테스트 대상:
    - 패킷 추가 및 지터 계산
    - PPS 계산
    - 패킷 손실 감지
    - 가용성 계산
    - 이력 기록 (연결, 모드, 비상정지)
"""

import pytest
from datetime import datetime, timedelta
from ugv_mon.store.packet_store import PacketStore, PacketRecord


class TestPacketRecord:
    """PacketRecord 데이터클래스 테스트."""
    
    def test_to_log_dict(self):
        """로그용 Dict 변환."""
        record = PacketRecord(
            timestamp=datetime(2026, 2, 6, 12, 0, 0),
            msg_code=0x01,
            sequence=5,
            size=100,
            jitter_ms=1.5,
            interval_ms=10.0,
            parse_ok=True,
            checksum_ok=True,
            operation_mode="자율주행",
            authority="OCS",
        )
        result = record.to_log_dict()
        
        assert result["timestamp"] == "12:00:00"
        assert result["sequence"] == 5
        assert result["msg_code"] == "0x01"
        assert result["parse_ok"] is True
        assert result["mode"] == "자율주행"
    
    def test_to_chart_point(self):
        """차트용 포인트 변환."""
        record = PacketRecord(
            timestamp=datetime(2026, 2, 6, 12, 0, 0),
            msg_code=0x01,
            sequence=5,
            size=100,
            jitter_ms=1.5,
            interval_ms=10.0,
            parse_ok=True,
            checksum_ok=True,
        )
        result = record.to_chart_point(pps=100)
        
        assert result["pps"] == 100
        assert result["jitter"] == 1.5
    
    def test_to_chart_point_high_jitter_capped(self):
        """200ms 초과 지터는 0으로 표시."""
        record = PacketRecord(
            timestamp=datetime(2026, 2, 6, 12, 0, 0),
            msg_code=0x01,
            sequence=5,
            size=100,
            jitter_ms=300.0,  # 임계값 초과
            interval_ms=10.0,
            parse_ok=True,
            checksum_ok=True,
        )
        result = record.to_chart_point(pps=100)
        
        assert result["jitter"] == 0  # 이상치는 0으로


class TestPacketStoreBasic:
    """PacketStore 기본 기능 테스트."""
    
    def test_add_single_packet(self):
        """단일 패킷 추가."""
        store = PacketStore()
        record = PacketRecord(
            timestamp=datetime.now(),
            msg_code=0x01,
            sequence=1,
            size=100,
            jitter_ms=None,
            interval_ms=None,
            parse_ok=True,
            checksum_ok=True,
        )
        
        store.add(record)
        
        assert store.record_count == 1
    
    def test_add_multiple_packets(self):
        """여러 패킷 추가 및 카운트."""
        store = PacketStore()
        now = datetime.now()
        
        for i in range(10):
            record = PacketRecord(
                timestamp=now + timedelta(milliseconds=10 * i),
                msg_code=0x01,
                sequence=i % 16,
                size=100,
                jitter_ms=None,
                interval_ms=None,
                parse_ok=True,
                checksum_ok=True,
            )
            store.add(record)
        
        assert store.record_count == 10
    
    def test_reset(self):
        """전체 초기화."""
        store = PacketStore()
        now = datetime.now()
        
        for i in range(5):
            record = PacketRecord(
                timestamp=now + timedelta(milliseconds=10 * i),
                msg_code=0x01,
                sequence=i,
                size=100,
                jitter_ms=None,
                interval_ms=None,
                parse_ok=True,
                checksum_ok=True,
            )
            store.add(record)
        
        assert store.record_count == 5
        
        store.reset()
        
        assert store.record_count == 0


class TestJitterCalculation:
    """지터 계산 테스트."""
    
    def test_first_packet_no_jitter(self):
        """첫 패킷은 지터 계산 불가."""
        store = PacketStore()
        record = PacketRecord(
            timestamp=datetime.now(),
            msg_code=0x01,
            sequence=1,
            size=100,
            jitter_ms=None,
            interval_ms=None,
            parse_ok=True,
            checksum_ok=True,
        )
        
        jitter = store.add(record)
        
        assert jitter is None
    
    def test_second_packet_no_jitter(self):
        """두 번째 패킷도 이전 간격이 없어 지터 None."""
        store = PacketStore()
        now = datetime.now()
        
        store.add(PacketRecord(
            timestamp=now,
            msg_code=0x01,
            sequence=1,
            size=100,
            jitter_ms=None,
            interval_ms=None,
            parse_ok=True,
            checksum_ok=True,
        ))
        
        jitter = store.add(PacketRecord(
            timestamp=now + timedelta(milliseconds=10),
            msg_code=0x01,
            sequence=2,
            size=100,
            jitter_ms=None,
            interval_ms=None,
            parse_ok=True,
            checksum_ok=True,
        ))
        
        assert jitter is None  # 아직 이전 간격 없음
    
    def test_third_packet_has_jitter(self):
        """세 번째 패킷부터 지터 계산 가능."""
        store = PacketStore()
        now = datetime.now()
        
        # 패킷 3개 추가 (10ms 간격)
        store.add(PacketRecord(
            timestamp=now,
            msg_code=0x01,
            sequence=1,
            size=100,
            jitter_ms=None,
            interval_ms=None,
            parse_ok=True,
            checksum_ok=True,
        ))
        
        store.add(PacketRecord(
            timestamp=now + timedelta(milliseconds=10),
            msg_code=0x01,
            sequence=2,
            size=100,
            jitter_ms=None,
            interval_ms=None,
            parse_ok=True,
            checksum_ok=True,
        ))
        
        jitter = store.add(PacketRecord(
            timestamp=now + timedelta(milliseconds=20),
            msg_code=0x01,
            sequence=3,
            size=100,
            jitter_ms=None,
            interval_ms=None,
            parse_ok=True,
            checksum_ok=True,
        ))
        
        # 간격 10ms - 10ms = 0 지터
        assert jitter == 0.0
    
    def test_jitter_with_variation(self):
        """간격 변동 시 지터 발생."""
        store = PacketStore()
        now = datetime.now()
        
        store.add(PacketRecord(
            timestamp=now,
            msg_code=0x01,
            sequence=1,
            size=100,
            jitter_ms=None,
            interval_ms=None,
            parse_ok=True,
            checksum_ok=True,
        ))
        
        store.add(PacketRecord(
            timestamp=now + timedelta(milliseconds=10),
            msg_code=0x01,
            sequence=2,
            size=100,
            jitter_ms=None,
            interval_ms=None,
            parse_ok=True,
            checksum_ok=True,
        ))
        
        # 세 번째: 12ms 간격 (10ms와 2ms 차이)
        jitter = store.add(PacketRecord(
            timestamp=now + timedelta(milliseconds=22),
            msg_code=0x01,
            sequence=3,
            size=100,
            jitter_ms=None,
            interval_ms=None,
            parse_ok=True,
            checksum_ok=True,
        ))
        
        assert jitter == 2.0


class TestPacketLoss:
    """패킷 손실 계산 테스트."""
    
    def test_no_loss_continuous_sequence(self):
        """연속 시퀀스는 손실 없음."""
        store = PacketStore()
        now = datetime.now()
        
        for i in range(5):
            store.add(PacketRecord(
                timestamp=now + timedelta(milliseconds=10 * i),
                msg_code=0x01,
                sequence=i,
                size=100,
                jitter_ms=None,
                interval_ms=None,
                parse_ok=True,
                checksum_ok=True,
            ))
        
        assert store.get_packet_loss() == 0
    
    def test_detect_single_loss(self):
        """시퀀스 갭 감지 (1개 손실)."""
        store = PacketStore()
        now = datetime.now()
        
        # 시퀀스: 0, 1, 3 (2가 손실)
        for seq in [0, 1, 3]:
            store.add(PacketRecord(
                timestamp=now + timedelta(milliseconds=10 * seq),
                msg_code=0x01,
                sequence=seq,
                size=100,
                jitter_ms=None,
                interval_ms=None,
                parse_ok=True,
                checksum_ok=True,
            ))
        
        assert store.get_packet_loss() == 1
    
    def test_detect_multiple_loss(self):
        """여러 패킷 손실 감지."""
        store = PacketStore()
        now = datetime.now()
        
        # 시퀀스: 0, 5 (1,2,3,4가 손실 = 4개)
        for seq in [0, 5]:
            store.add(PacketRecord(
                timestamp=now + timedelta(milliseconds=10 * seq),
                msg_code=0x01,
                sequence=seq,
                size=100,
                jitter_ms=None,
                interval_ms=None,
                parse_ok=True,
                checksum_ok=True,
            ))
        
        assert store.get_packet_loss() == 4
    
    def test_sequence_wrap_around(self):
        """4-bit 시퀀스 순환 (15 -> 0)."""
        store = PacketStore()
        now = datetime.now()
        
        # 시퀀스: 14, 15, 0, 1 (정상 순환)
        for seq in [14, 15, 0, 1]:
            store.add(PacketRecord(
                timestamp=now + timedelta(milliseconds=10 * seq),
                msg_code=0x01,
                sequence=seq,
                size=100,
                jitter_ms=None,
                interval_ms=None,
                parse_ok=True,
                checksum_ok=True,
            ))
        
        assert store.get_packet_loss() == 0


class TestStatistics:
    """통계 조회 테스트."""
    
    def test_get_parse_success_rate(self):
        """파싱 성공률 계산."""
        store = PacketStore()
        now = datetime.now()
        
        # 8개 성공, 2개 실패 = 80%
        for i in range(10):
            store.add(PacketRecord(
                timestamp=now + timedelta(milliseconds=10 * i),
                msg_code=0x01,
                sequence=i,
                size=100,
                jitter_ms=None,
                interval_ms=None,
                parse_ok=(i < 8),
                checksum_ok=True,
            ))
        
        assert store.get_parse_success_rate() == 80.0
    
    def test_get_checksum_fail_rate(self):
        """체크섬 실패율 계산."""
        store = PacketStore()
        now = datetime.now()
        
        # 3개 실패 / 10개 = 30%
        for i in range(10):
            store.add(PacketRecord(
                timestamp=now + timedelta(milliseconds=10 * i),
                msg_code=0x01,
                sequence=i,
                size=100,
                jitter_ms=None,
                interval_ms=None,
                parse_ok=True,
                checksum_ok=(i >= 3),
            ))
        
        assert store.get_checksum_fail_rate() == 30.0
    
    def test_get_jitter_p95(self):
        """P95 지터 계산."""
        store = PacketStore()
        now = datetime.now()
        
        # 100개 패킷, 일정 간격으로 지터 생성
        for i in range(100):
            record = PacketRecord(
                timestamp=now + timedelta(milliseconds=10 * i),
                msg_code=0x01,
                sequence=i % 16,
                size=100,
                jitter_ms=None,
                interval_ms=None,
                parse_ok=True,
                checksum_ok=True,
            )
            store.add(record)
        
        # 지터가 계산되었는지 확인 (첫 2개는 None)
        p95 = store.get_jitter_p95()
        assert isinstance(p95, float)


class TestHistoryTracking:
    """이력 추적 테스트."""
    
    def test_connection_history(self):
        """연결 상태 변경 기록."""
        store = PacketStore()
        
        store.record_connection_change(True)
        store.record_connection_change(False)
        store.record_connection_change(True)
        
        history = store.get_connection_history()
        
        assert len(history) == 3
        assert history[0]["connected"] is True
        assert history[1]["connected"] is False
        assert history[2]["connected"] is True
    
    def test_connection_history_no_duplicate(self):
        """같은 상태 중복 기록 방지."""
        store = PacketStore()
        
        store.record_connection_change(True)
        store.record_connection_change(True)  # 중복
        store.record_connection_change(True)  # 중복
        
        history = store.get_connection_history()
        
        assert len(history) == 1
    
    def test_mode_transitions(self):
        """운용 모드 전이 기록."""
        store = PacketStore()
        
        store.record_mode_transition("수동")
        store.record_mode_transition("반자동")
        store.record_mode_transition("자율주행")
        
        transitions = store.get_mode_transitions()
        
        # 첫 번째 전이는 기록 안 됨 (이전 모드 없음)
        assert len(transitions) == 2
        assert transitions[0]["from"] == "수동"
        assert transitions[0]["to"] == "반자동"
    
    def test_emergency_counts(self):
        """비상정지 원인 카운트."""
        store = PacketStore()
        
        store.record_emergency(["조종기", "비콘"])
        store.record_emergency(["조종기"])
        store.record_emergency(["자율주행모듈"])
        
        counts = store.get_emergency_counts()
        
        assert counts["조종기"] == 2
        assert counts["비콘"] == 1
        assert counts["자율주행모듈"] == 1


class TestMsgCodeStats:
    """msg_code별 통계 테스트."""
    
    def test_msg_code_distribution(self):
        """msg_code별 패킷 수."""
        store = PacketStore()
        now = datetime.now()
        
        # 0x01: 5개, 0x02: 3개
        for i in range(8):
            store.add(PacketRecord(
                timestamp=now + timedelta(milliseconds=10 * i),
                msg_code=0x01 if i < 5 else 0x02,
                sequence=i,
                size=100,
                jitter_ms=None,
                interval_ms=None,
                parse_ok=True,
                checksum_ok=True,
            ))
        
        dist = store.get_msg_code_distribution()
        
        assert dist[0x01] == 5
        assert dist[0x02] == 3
    
    def test_stats_by_code(self):
        """특정 msg_code 통계."""
        store = PacketStore()
        now = datetime.now()
        
        for i in range(5):
            store.add(PacketRecord(
                timestamp=now + timedelta(milliseconds=10 * i),
                msg_code=0x01,
                sequence=i,
                size=100 + i * 10,
                jitter_ms=None,
                interval_ms=None,
                parse_ok=True,
                checksum_ok=True,
            ))
        
        stats = store.get_stats_by_code(0x01)
        
        assert stats["count"] == 5
        assert stats["avg_size"] == 120.0  # (100+110+120+130+140)/5
