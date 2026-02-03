#!/usr/bin/env python3
"""
지터 오염 디버깅 스크립트.

회사에서 시뮬레이터 테스트 시 사용:
1. 앱 실행 중 이 스크립트를 import
2. 주기적으로 get_jitter_debug_info() 호출
3. 로그에서 JITTER_SKIP 메시지 확인
cd /path/to/opus1
python -m scripts.debug_jitter
"""

import logging
from datetime import datetime, timedelta

# 로깅 설정 (디버그 레벨)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# JITTER_SKIP 로그만 보기
jitter_logger = logging.getLogger('ugv_mon.analysis.stats_calculator')
jitter_logger.setLevel(logging.DEBUG)


def get_jitter_debug_info():
    """현재 지터 디버깅 정보 출력.
    
    사용법:
        from scripts.debug_jitter import get_jitter_debug_info
        get_jitter_debug_info()
    """
    try:
        from ugv_mon.data.live_provider import LiveDataProvider
        
        # 싱글톤 인스턴스 가져오기 (앱에서 사용 중인 인스턴스)
        # NOTE: 실제 앱에서는 provider 인스턴스를 직접 전달해야 함
        print("=" * 60)
        print("지터 디버깅 정보")
        print("=" * 60)
        
        # 상수 출력
        from ugv_mon.analysis.stats_calculator import (
            MAX_GAP_MS, MAX_JITTER_MS, MAX_INTERVAL_MS, INITIAL_SKIP_COUNT
        )
        print(f"\n[상수]")
        print(f"  MAX_GAP_MS: {MAX_GAP_MS}ms (3초 이상 갭 스킵)")
        print(f"  MAX_JITTER_MS: {MAX_JITTER_MS}ms (200ms 이상 지터 필터링)")
        print(f"  MAX_INTERVAL_MS: {MAX_INTERVAL_MS}ms (2초 이상 interval 스킵)")
        print(f"  INITIAL_SKIP_COUNT: {INITIAL_SKIP_COUNT} (포트 전환 후 스킵)")
        
    except ImportError as e:
        print(f"Import 오류: {e}")


def test_jitter_defense_layers():
    """지터 방어층 테스트."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from ugv_mon.analysis.stats_calculator import (
        StatsCalculator, MAX_GAP_MS, MAX_JITTER_MS, MAX_INTERVAL_MS
    )
    
    calc = StatsCalculator(window_sec=60)
    now = datetime.now()
    
    print("\n[테스트 1: 정상 패킷]")
    for i in range(10):
        jitter = calc.record_packet(now + timedelta(milliseconds=i*10), i, 100)
        print(f"  패킷 {i}: jitter={jitter}")
    
    stats = calc.get_debug_stats()
    print(f"\n[디버그 통계]")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    print("\n[테스트 2: 큰 갭 후 패킷]")
    calc.reset()
    calc.record_packet(now, 0, 100)
    calc.record_packet(now + timedelta(seconds=5), 1, 100)  # 5초 갭
    calc.record_packet(now + timedelta(seconds=5, milliseconds=10), 2, 100)
    
    stats = calc.get_debug_stats()
    print(f"  skipped_max_gap: {stats['skipped_max_gap']}")
    
    print("\n[테스트 3: 포트 전환 시뮬레이션]")
    calc.reset()
    for i in range(5):
        calc.record_packet(now + timedelta(milliseconds=i*10), i, 100)
    
    print("  reset_stream_state() 호출")
    calc.reset_stream_state()
    
    for i in range(10):
        jitter = calc.record_packet(now + timedelta(seconds=1, milliseconds=i*10), i, 100)
        print(f"  패킷 {i}: jitter={jitter} (global_skip={calc._global_skip_count})")
    
    stats = calc.get_debug_stats()
    print(f"\n[최종 디버그 통계]")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    print("\n✅ 테스트 완료!")


if __name__ == "__main__":
    get_jitter_debug_info()
    test_jitter_defense_layers()
