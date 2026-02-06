#!/usr/bin/env python3
"""
Capture + Parser + PacketStore 통합 테스트.

실행:
    sudo python3 test_capture_packets.py

    # 인터페이스 지정
    sudo python3 test_capture_packets.py --interface eno2

종료:
    Ctrl+C

요구사항:
    pip install scapy
"""

import argparse
import time
import sys
from datetime import datetime

sys.path.insert(0, '.')

# Scapy 설치 확인
try:
    import scapy
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    print("=" * 60)
    print("Scapy가 설치되어 있지 않습니다.")
    print("=" * 60)
    print()
    print("설치 방법:")
    print("  pip install scapy")
    print()
    print("macOS의 경우 추가 설치:")
    print("  brew install libpcap")
    print()
    sys.exit(1)

from ugv_mon.capture import PacketSniffer, PacketQueue, PacketProcessor
from ugv_mon.parser import ICDParser
from ugv_mon.data.packet_store import PacketStore
from ugv_mon.core import config


def parse_args():
    """CLI 인자 파싱."""
    parser = argparse.ArgumentParser(
        description="Capture + Parser + PacketStore 통합 테스트"
    )
    parser.add_argument(
        "--interface", "-i",
        type=str,
        default=config.network.interface,
        help=f"캡처할 네트워크 인터페이스 (기본: {config.network.interface})"
    )
    parser.add_argument(
        "--src-port",
        type=int,
        default=config.network.vic_port,
        help=f"소스 포트 (기본: {config.network.vic_port})"
    )
    parser.add_argument(
        "--dst-port",
        type=int,
        default=config.network.ocs_port,
        help=f"목적지 포트 (기본: {config.network.ocs_port})"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 60)
    print("Capture + Parser + PacketStore 통합 테스트")
    print("=" * 60)
    print()

    # 초기화
    queue = PacketQueue(max_size=100)
    parser = ICDParser()
    store = PacketStore(window_sec=60)
    processor = PacketProcessor(queue, parser, store)

    print(f"[INFO] Interface: {args.interface}")
    print(f"[INFO] Filter: UDP {args.src_port} -> {args.dst_port}")
    print(f"[INFO] 캡처 시작...")
    print()

    # 스니퍼 생성 및 시작
    try:
        sniffer = PacketSniffer(
            interface=args.interface,
            src_port=args.src_port,
            dst_port=args.dst_port,
            callback=queue.put,
        )
        sniffer.start()
    except PermissionError:
        print("=" * 60)
        print("권한 오류: root 권한이 필요합니다.")
        print("=" * 60)
        print()
        print("실행 방법:")
        print(f"  sudo python3 {sys.argv[0]}")
        print()
        sys.exit(1)
    except Exception as e:
        print(f"스니퍼 시작 실패: {e}")
        sys.exit(1)

    print("패킷 대기 중... (Ctrl+C로 종료)")
    print("-" * 60)
    packet_count = 0
    last_stats_time = time.time()

    try:
        while True:
            # PacketProcessor로 대기 패킷 일괄 처리
            result = processor.process_pending()

            if result.count > 0:
                packet_count += result.count
                print(
                    f"\n[처리] {result.count}건 (성공: {result.success_count}, "
                    f"체크섬실패: {result.checksum_fail_count})"
                )

                if result.last_payload:
                    p = result.last_payload
                    print(f"  운용모드: {p.operation_mode}")
                    print(f"  운용권한: {p.authority}")
                    print(f"  주행상태: {p.driving_state}")
                    connected = [k for k, v in p.devices.items() if v]
                    print(f"  연결장치: {connected}")
                    if p.is_emergency:
                        print(f"  비상정지 원인: {p.get_emergency_reasons()}")

            # 주기적으로 통계 출력 (5초마다)
            current_time_sec = time.time()
            if current_time_sec - last_stats_time >= 5.0:
                stats = store.get_stats_dict()
                print("\n" + "-" * 60)
                print("통계 (최근 60초)")
                print("-" * 60)
                print(f"  PPS (초당 패킷 수): {stats['pps']}")
                print(f"  지터 (현재): {stats['jitter_current']:.2f} ms")
                print(f"  지터 P95: {stats['jitter_p95']:.2f} ms")
                print(f"  패킷 손실: {stats['packet_loss']} 개")
                print(f"  가용성: {stats['availability']:.2f}%")
                print(f"  총 레코드 수: {store.record_count}")
                print("-" * 60 + "\n")
                last_stats_time = current_time_sec

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n")
        print("-" * 60)
        print("[INFO] 캡처 종료")
    finally:
        sniffer.stop()

        # 최종 통계 출력
        print()
        print("=" * 60)
        print("테스트 결과")
        print("=" * 60)
        print(f"  총 처리 패킷: {packet_count}")
        print(f"  PacketStore 레코드: {store.record_count}")

        # 캡처 통계
        capture_stats = sniffer.get_stats()
        print("\n캡처 통계:")
        print(f"  총 패킷: {capture_stats.packets_total}")
        print(f"  필터 통과: {capture_stats.packets_filtered}")
        print(f"  총 바이트: {capture_stats.bytes_total}")

        # PacketStore 통계
        stats = store.get_stats_dict()
        print("\nPacketStore 통계:")
        print(f"  PPS: {stats['pps']}")
        print(f"  지터 (현재): {stats['jitter_current']:.2f} ms")
        print(f"  지터 P95: {stats['jitter_p95']:.2f} ms")
        print(f"  패킷 손실: {stats['packet_loss']} 개")
        print(f"  가용성: {stats['availability']:.2f}%")


if __name__ == "__main__":
    main()
