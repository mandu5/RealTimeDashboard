#!/usr/bin/env python3
"""
ICD 파싱 통합 테스트

패킷 캡처와 ICD 파싱을 연동하여 테스트합니다.
실제 VIC↔OCS 통신이 있는 환경에서 실행하세요.

사용법:
    sudo python3 test_icd_parsing.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ugv_mon.capture import PacketSniffer, PacketQueue
from ugv_mon.parser import ICDParser
import time

# 전역 변수
parser = ICDParser()
parse_count = 0
success_count = 0
checksum_fail_count = 0

def callback(data):
    """패킷 수신 콜백 - 파싱 및 결과 출력"""
    global parse_count, success_count, checksum_fail_count
    
    parse_count += 1
    result = parser.parse(data)
    
    if result.success:
        success_count += 1
        if result.checksum_ok:
            print(f'✅ [{parse_count}] Parse OK: Seq={result.header.sequence}, '
                  f'Code=0x{result.header.msg_code:02X}, Size={result.raw_size}B')
            if result.payload:
                print(f'   Mode: {result.payload.operation_mode_label}')
                print(f'   Authority: {result.payload.authority_label}')
                print(f'   Driving: {result.payload.driving_state_label}')
                devices = [k for k, v in result.payload.devices.items() if v]
                if devices:
                    print(f'   Connected Devices: {", ".join(devices)}')
        else:
            checksum_fail_count += 1
            print(f'⚠️  [{parse_count}] Checksum FAIL: Seq={result.header.sequence}')
    else:
        print(f'❌ [{parse_count}] Parse FAILED: {result.error}')

def main():
    print("=" * 60)
    print("ICD 파싱 통합 테스트")
    print("=" * 60)
    print("\n패킷 캡처 및 ICD 파싱을 시작합니다...")
    print("Ctrl+C로 중지할 수 있습니다.\n")
    
    sniffer = PacketSniffer(
        interface='lo',
        src_port=50000,
        dst_port=61000,
        callback=callback
    )
    
    try:
        sniffer.start()
        print("✅ Sniffer started on interface 'lo'")
        print("   Filter: UDP 50000→61000\n")
        
        # 30초간 캡처 (또는 Ctrl+C)
        time.sleep(30)
        
    except KeyboardInterrupt:
        print("\n\n중지 요청됨...")
    finally:
        sniffer.stop()
        print("\n" + "=" * 60)
        print("테스트 결과")
        print("=" * 60)
        print(f"총 패킷 수: {parse_count}")
        print(f"파싱 성공: {success_count}")
        print(f"체크섬 실패: {checksum_fail_count}")
        if parse_count > 0:
            print(f"성공률: {success_count/parse_count*100:.1f}%")
        
        stats = sniffer.get_stats()
        print(f"\n캡처 통계:")
        print(f"  총 캡처: {stats.packets_total}")
        print(f"  필터 통과: {stats.packets_filtered}")
        print(f"  PPS: {stats.get_pps()}")
        print(f"  총 바이트: {stats.bytes_total}")

if __name__ == "__main__":
    main()
