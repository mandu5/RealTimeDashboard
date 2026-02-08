"""
UGV-MON Packet Capture Module.

Scapy 기반 실시간 패킷 캡처 기능을 제공합니다.

=============================================================================
모듈 구성:
- PacketSniffer: Scapy를 사용한 UDP 패킷 캡처 (별도 스레드)
- PacketQueue: 스레드 간 패킷 전달용 버퍼 (Producer-Consumer 패턴)
- CaptureStats: 캡처 통계 추적 (PPS, 바이트 수 등)

사용 예시:
    from ugv_mon.capture import PacketSniffer, PacketQueue, CaptureStats

    # 1. 패킷 큐 생성 (스레드 간 데이터 전달용)
    queue = PacketQueue(max_size=1000)

    # 2. 스니퍼 생성 (콜백으로 큐에 패킷 전달)
    sniffer = PacketSniffer(
        interface="lo",           # 루프백 인터페이스
        src_port=50000,           # VIC 송신 포트
        dst_port=61000,           # OCS 수신 포트
        callback=queue.put        # 패킷 수신 시 큐에 추가
    )

    # 3. 캡처 시작 (별도 데몬 스레드에서 실행)
    sniffer.start()

    # 4. 패킷 처리 (메인 스레드)
    packets = queue.get_all()

    # 5. 종료
    sniffer.stop()

Q: 왜 별도 모듈로 분리했나요?
A: 단일 책임 원칙(SRP) 적용. 캡처/큐/통계 각각 독립적으로 테스트 가능.
   또한 Live/Mock 전환 시 이 모듈만 교체하면 됩니다.

Q: root 권한이 필요한 이유는?
A: raw socket 접근이 필요하기 때문입니다.
   해결책: sudo setcap cap_net_raw+ep $(which python3)
=============================================================================
"""

# 외부에서 import할 클래스들을 명시적으로 지정
# 이렇게 하면 `from ugv_mon.capture import PacketSniffer` 형태로 사용 가능
from .packet_processor import BatchProcessResult, PacketProcessor
from .queue import PacketQueue
from .sniffer import PacketSniffer
from .stats import CaptureStats

# __all__: `from capture import *` 시 노출되는 이름 목록
# 명시적으로 지정하지 않으면 모든 public 이름이 노출됨
__all__ = ["BatchProcessResult", "CaptureStats", "PacketProcessor", "PacketQueue", "PacketSniffer"]
