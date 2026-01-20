#!/usr/bin/env python3
"""
Live 모드 통합 테스트

LiveDataProvider가 제대로 동작하는지 테스트합니다.
실제 VIC↔OCS 통신이 있는 환경에서 실행하세요.

사용법:
    export UGV_MON_USE_LIVE=true
    export UGV_MON_INTERFACE=lo
    sudo -E python3 test_live_mode.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ugv_mon.data.live_provider import get_data_provider
import time

def main():
    print("=" * 60)
    print("Live 모드 통합 테스트")
    print("=" * 60)
    
    # Live 모드 강제 설정
    os.environ['UGV_MON_USE_LIVE'] = 'true'
    os.environ['UGV_MON_INTERFACE'] = 'lo'
    
    # 데이터 제공자 생성
    provider = get_data_provider()
    print(f"\n✅ Provider 생성: {type(provider).__name__}")
    
    # Live 모드인 경우 캡처 시작
    if hasattr(provider, 'start_capture'):
        print("\n캡처 시작 중...")
        success = provider.start_capture()
        if success:
            print("✅ 캡처 시작 성공!")
        else:
            print("❌ 캡처 시작 실패!")
            return
    
    # 초기 데이터 생성
    print("\n초기 데이터 생성 중...")
    initial_data = provider.generate_initial_data()
    print(f"✅ 초기 데이터 생성 완료")
    print(f"   연결 상태: {initial_data.get('connected')}")
    print(f"   인터페이스: {initial_data.get('interface')}")
    
    # 10초간 데이터 업데이트 테스트
    print("\n10초간 데이터 업데이트 테스트...")
    print("(Ctrl+C로 중지 가능)\n")
    
    try:
        for i in range(10):
            time.sleep(1)
            updated_data = provider.update_data(initial_data)
            
            # 주요 메트릭 출력
            pps = updated_data.get('capturePps', 0)
            connected = updated_data.get('connected', False)
            last_packet = updated_data.get('lastPacketTime', '')
            
            status = "🟢" if connected else "🔴"
            print(f"[{i+1:2d}s] {status} PPS: {pps:4d}, "
                  f"Last: {last_packet}, "
                  f"Logs: {provider.log_count}")
            
            initial_data = updated_data
            
    except KeyboardInterrupt:
        print("\n\n중지 요청됨...")
    
    # 최종 통계
    print("\n" + "=" * 60)
    print("최종 통계")
    print("=" * 60)
    final_data = provider.update_data(initial_data)
    print(f"연결 상태: {final_data.get('connected')}")
    print(f"수신 PPS: {final_data.get('capturePps')}")
    print(f"파싱 성공률: {final_data.get('parseSuccess')}%")
    print(f"체크섬 실패율: {final_data.get('checksumFail')}%")
    print(f"패킷 손실: {final_data.get('packetLoss')}")
    print(f"지터 P95: {final_data.get('jitterP95')}ms")
    print(f"지터 P99: {final_data.get('jitterP99')}ms")
    print(f"로그 개수: {provider.log_count}")
    
    # 캡처 중지
    if hasattr(provider, 'stop_capture'):
        provider.stop_capture()
        print("\n✅ 캡처 중지됨")

if __name__ == "__main__":
    main()
