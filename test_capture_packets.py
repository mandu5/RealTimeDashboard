#!/usr/bin/env python3
"""
Capture + Parser + Analysis 통합 테스트

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
    print("❌ Scapy가 설치되어 있지 않습니다.")
    print("=" * 60)
    print()
    print("설치 방법:")
    print("  pip install scapy")
    print()
    print("macOS의 경우 추가 설치:")
    print("  brew install libpcap")
    print()
    sys.exit(1)

from ugv_mon.capture import PacketSniffer, PacketQueue
from ugv_mon.parser import ICDParser
from ugv_mon.analysis import StatsCalculator, AnomalyDetector
from ugv_mon.config import config


def parse_args():
    """CLI 인자 파싱."""
    parser = argparse.ArgumentParser(
        description="Capture + Parser + Analysis 통합 테스트"
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
        default=config.network.source_port,
        help=f"소스 포트 (기본: {config.network.source_port})"
    )
    parser.add_argument(
        "--dst-port",
        type=int,
        default=config.network.dest_port,
        help=f"목적지 포트 (기본: {config.network.dest_port})"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    
    print("=" * 60)
    print("Capture + Parser + Analysis 통합 테스트")
    print("=" * 60)
    print()
    
    # 초기화
    queue = PacketQueue(max_size=100)
    parser = ICDParser()
    stats_calc = StatsCalculator(window_sec=60)  # 60초 윈도우
    anomaly_detector = AnomalyDetector(
        jitter_warning=10.0,  # 10ms 이상이면 경고
        jitter_error=50.0,    # 50ms 이상이면 에러
        timeout_sec=5.0       # 5초 이상 패킷 없으면 타임아웃
    )
    
    print(f"[INFO] Interface: {args.interface}")
    print(f"[INFO] Filter: UDP {args.src_port} → {args.dst_port}")
    print(f"[INFO] 캡처 시작...")
    print()
    
    # 스니퍼 생성 및 시작
    try:
        sniffer = PacketSniffer(
            interface=args.interface,
            src_port=args.src_port,
            dst_port=args.dst_port,
            callback=queue.put
        )
        sniffer.start()
    except PermissionError:
        print("=" * 60)
        print("❌ 권한 오류: root 권한이 필요합니다.")
        print("=" * 60)
        print()
        print("실행 방법:")
        print(f"  sudo python3 {sys.argv[0]}")
        print()
        sys.exit(1)
    except Exception as e:
        print(f"❌ 스니퍼 시작 실패: {e}")
        sys.exit(1)
    
    print("패킷 대기 중... (Ctrl+C로 종료)")
    print("-" * 60) 
    packet_count = 0
    parse_success = 0
    last_stats_time = time.time()
    last_packet_time = None
    
    try:
        while True:
            # 큐에서 캡처된 패킷 가져오기
            packets = queue.get_all()
            
            for raw_data in packets:
                packet_count += 1
                current_time = datetime.now()
                
                # 파싱
                result = parser.parse(raw_data)
                
                if result.success:
                    parse_success += 1
                    
                    # 통계 기록
                    if result.header is not None:
                        jitter_ms = stats_calc.record_packet(
                            timestamp=current_time,
                            sequence=result.header.sequence,
                            size=len(raw_data)
                        )
                        
                        # 이상 탐지
                        if jitter_ms is not None:
                            anomaly = anomaly_detector.check_jitter(jitter_ms)
                            if anomaly:
                                print(f"  ⚠️ 이상 탐지: {anomaly.message}")
                        
                        # 체크섬 에러 탐지
                        if not result.checksum_ok:
                            print(f"  ⚠️ 체크섬 에러: 패킷 무결성 검증 실패")
                        
                        last_packet_time = current_time
                   
                        print(f"\n[패킷 #{packet_count}] 크기: {len(raw_data)} bytes")
                        print(f"  체크섬: {'OK' if result.checksum_ok else 'FAIL'}")
                        print(f"  시퀀스: {result.header.sequence}")
                        print(f"  메시지코드: 0x{result.header.msg_code:02X}")
                        
                        if jitter_ms is not None:
                            print(f"  지터: {jitter_ms:.2f} ms")
                        
                        if result.payload:
                            print(f"  운용모드: {result.payload.operation_mode_label}")
                            print(f"  운용권한: {result.payload.authority_label}")
                            print(f"  주행상태: {result.payload.driving_state_label}")
                            
                            connected = [k for k, v in result.payload.devices.items() if v]
                            print(f"  연결장치: {connected}")
                            
                            emergency = [k for k, v in result.payload.emergency_status.items() if v]
                            if emergency:
                                print(f"  비상정지: {emergency}")
                else:
                    print(f"\n[패킷 #{packet_count}] 파싱 실패: {result.error}")
            
            # 주기적으로 통계 출력 (5초마다)
            current_time_sec = time.time()
            if current_time_sec - last_stats_time >= 5.0:
                stats = stats_calc.get_stats_dict()
                print("\n" + "-" * 60)
                print("📊 통계 (최근 60초)")
                print("-" * 60)
                print(f"  PPS (초당 패킷 수): {stats['pps']}")
                print(f"  평균 지터: {stats['jitter_avg']:.2f} ms")
                print(f"  지터 P95: {stats['jitter_p95']:.2f} ms")
                print(f"  지터 P99: {stats['jitter_p99']:.2f} ms")
                print(f"  패킷 손실: {stats['packet_loss']} 개")
                print(f"  가용성: {stats['availability']:.2f}%")
                
                # 이상 탐지 결과
                anomalies = anomaly_detector.get_recent_anomalies(limit=5)
                if anomalies:
                    print("\n  ⚠️ 최근 이상 탐지:")
                    for anomaly in anomalies:
                        print(f"    - [{anomaly.severity.upper()}] {anomaly.message}")
                else:
                    print("\n  ✅ 이상 없음")
                
                print("-" * 60 + "\n")
                last_stats_time = current_time_sec
            
            # 타임아웃 체크
            if last_packet_time:
                timeout_anomaly = anomaly_detector.check_timeout(last_packet_time)
                if timeout_anomaly:
                    print(f"\n⚠️ {timeout_anomaly.message}\n")
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n")
        print("-" * 60)
        print("[INFO] 캡처 종료")
    finally:
        sniffer.stop()
        
        # 통계 출력
        print()
        print("=" * 60)
        print("테스트 결과")
        print("=" * 60)
        print(f"  총 캡처 패킷: {packet_count}")
        print(f"  파싱 성공: {parse_success}")
        print(f"  파싱 실패: {packet_count - parse_success}")
        if packet_count > 0:
            print(f"  성공률: {parse_success / packet_count * 100:.1f}%")
        
        # 최종 통계 출력
        print()
        print("=" * 60)
        print("최종 통계")
        print("=" * 60)
        
        # 캡처 통계
        capture_stats = sniffer.get_stats()
        print("\n캡처 통계:")
        print(f"  총 패킷: {capture_stats.packets_total}")
        print(f"  필터 통과: {capture_stats.packets_filtered}")
        print(f"  총 바이트: {capture_stats.bytes_total}")
        
        # 분석 통계
        analysis_stats = stats_calc.get_stats_dict()
        print("\n분석 통계 (최근 60초):")
        print(f"  PPS: {analysis_stats['pps']}")
        print(f"  평균 지터: {analysis_stats['jitter_avg']:.2f} ms")
        print(f"  지터 P95: {analysis_stats['jitter_p95']:.2f} ms")
        print(f"  지터 P99: {analysis_stats['jitter_p99']:.2f} ms")
        print(f"  패킷 손실: {analysis_stats['packet_loss']} 개")
        print(f"  가용성: {analysis_stats['availability']:.2f}%")
        
        # 이상 탐지 결과
        all_anomalies = anomaly_detector.get_recent_anomalies(limit=20)
        if all_anomalies:
            print(f"\n이상 탐지 (총 {len(all_anomalies)}건):")
            for anomaly in all_anomalies:
                print(f"  [{anomaly.severity.upper()}] {anomaly.timestamp.strftime('%H:%M:%S')} - {anomaly.message}")
        else:
            print("\n이상 탐지: 없음 ✅")


if __name__ == "__main__":
    main()