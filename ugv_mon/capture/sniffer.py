"""
Scapy-based Packet Sniffer Module.

VIC→OCS UDP 패킷을 실시간으로 캡처합니다.

=============================================================================
핵심 기능:
1. BPF(Berkeley Packet Filter) 커널 레벨 필터링
2. 별도 데몬 스레드에서 캡처 (UI 블로킹 방지)
3. 콜백 기반 패킷 전달 (Observer 패턴)

요구사항:
- root 권한 필요 (raw socket 접근)
  해결책 1: sudo python run.py
  해결책 2: sudo setcap cap_net_raw+ep $(which python3)
- scapy 패키지 설치 필요: pip install scapy

Q: 왜 Scapy를 사용하나요?
A: 1. Python에서 가장 널리 사용되는 패킷 처리 라이브러리
   2. BPF 필터 지원 (커널 레벨 필터링으로 성능 우수)
   3. 풍부한 프로토콜 지원 및 문서화
   대안: pyshark (더 고수준), dpkt (더 저수준)

Q: 왜 BPF 필터를 사용하나요?
A: 커널에서 필터링하므로 사용자 공간으로 올라오는 패킷 수 감소.
   "udp and src port 50000 and dst port 61000" 필터로
   관심 없는 패킷은 커널에서 바로 버립니다.
=============================================================================
"""

import threading
import logging
from typing import Callable, Optional
from datetime import datetime

# Scapy 경고 메시지 억제 (IPv6 등)
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ============================================================================
# Scapy Import (선택적 의존성)
# - Scapy가 설치되지 않아도 나머지 코드는 동작해야 함 (Mock 모드)
# - try-except로 import 실패를 graceful하게 처리
# ============================================================================
try:
    from scapy.all import sniff, UDP, Raw
    from scapy.packet import Packet
    SCAPY_AVAILABLE = True
except ImportError:
    # Scapy 미설치 시 타입 힌트용 더미
    SCAPY_AVAILABLE = False
    Packet = None

from .stats import CaptureStats

# 로거 설정 (__name__: 'ugv_mon.capture.sniffer')
logger = logging.getLogger(__name__)


class PacketSniffer:
    """
    UDP 패킷 스니퍼 클래스.
    
    Scapy를 사용하여 지정된 인터페이스에서 UDP 패킷을 캡처합니다.
    BPF 필터로 특정 포트의 패킷만 선택적으로 캡처합니다.
    
    Attributes:
        interface: 캡처할 네트워크 인터페이스 (예: "lo", "eno2")
        src_port: 송신 포트 (VIC 측: 50000)
        dst_port: 수신 포트 (OCS 측: 61000)
        callback: 패킷 수신 시 호출할 콜백 함수
    
    사용 예시:
        def handle_packet(raw_bytes):
            print(f"Received {len(raw_bytes)} bytes")
        
        sniffer = PacketSniffer(
            interface="lo",
            src_port=50000,
            dst_port=61000,
            callback=handle_packet
        )
        sniffer.start()
        # ... 캡처 진행 ...
        sniffer.stop()
    
    Warning:
        - root 권한이 필요합니다 (sudo 또는 setcap)
        - 콜백 함수는 빠르게 실행되어야 합니다 (캡처 스레드 블로킹 방지)
    """
    
    def __init__(
        self,
        interface: str,
        src_port: int,
        dst_port: int,
        callback: Callable[[bytes], None]
    ):
        """
        PacketSniffer 초기화.
        
        Args:
            interface: 네트워크 인터페이스명
                - "lo": 루프백 (개발/테스트용)
                - "eno2", "eno3", "eth0": 물리 인터페이스 (프로덕션)
                확인 방법: ip link show 또는 ifconfig -a
            
            src_port: 송신측 UDP 포트
                - VIC: 50000 (ICD 규격)
            
            dst_port: 수신측 UDP 포트
                - OCS: 61000 (ICD 규격)
            
            callback: 패킷 수신 시 호출할 함수
                - signature: (raw_bytes: bytes) -> None
                - 보통 PacketQueue.put을 전달
        
        Raises:
            ImportError: Scapy가 설치되지 않은 경우
        
        Q: 왜 콜백 패턴을 사용하나요?
        A: 스니퍼가 패킷을 어떻게 처리할지 알 필요가 없습니다.
           콜백으로 처리 로직을 외부에서 주입 (의존성 역전).
           테스트 시 다른 콜백을 주입할 수 있습니다.
        """
        # Scapy 설치 확인
        if not SCAPY_AVAILABLE:
            raise ImportError(
                "Scapy is not installed. Run: pip install scapy"
            )
        
        # =====================================================================
        # 인스턴스 변수 초기화
        # - _prefix: 내부 구현 상세 (외부에서 직접 접근 자제)
        # =====================================================================
        self._interface = interface
        self._src_port = src_port
        self._dst_port = dst_port
        self._callback = callback
        
        # =====================================================================
        # BPF 필터 문자열 생성
        # 형식: "udp and src port 50000 and dst port 61000"
        # 
        # Q: BPF 문법은 어디서 확인하나요?
        # A: man pcap-filter 또는 tcpdump 매뉴얼
        #    tcpdump로 먼저 테스트: tcpdump -i lo "udp and ..."
        # =====================================================================
        self._filter = f"udp and src port {src_port} and dst port {dst_port}"
        
        # =====================================================================
        # 스레드 제어
        # - _running: 캡처 루프 실행 플래그 (stop() 시 False로 설정)
        # - _thread: 캡처 스레드 객체 (join 및 상태 확인용)
        # =====================================================================
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # 캡처 통계
        self._stats = CaptureStats()
        
        logger.info(
            f"PacketSniffer initialized: interface={interface}, "
            f"filter='{self._filter}'"
        )
    
    def start(self) -> None:
        """
        패킷 캡처 시작.
        
        별도의 데몬 스레드에서 캡처 루프를 시작합니다.
        이미 실행 중이면 경고만 출력하고 아무 동작도 하지 않습니다.
        
        Note:
            - 데몬 스레드: 메인 프로세스 종료 시 자동 종료
            - start() 호출 후 즉시 반환 (비동기)
            - 실제 캡처는 _capture_loop()에서 진행
        
        Q: 왜 데몬 스레드를 사용하나요?
        A: daemon=True 설정 시 메인 스레드 종료하면 같이 종료.
           프로그램 종료 시 스니퍼가 남아있는 문제 방지.
        """
        if self._running:
            logger.warning("Sniffer is already running")
            return
        
        # 상태 초기화
        self._running = True
        self._stats.reset()
        
        # =====================================================================
        # 데몬 스레드 생성 및 시작
        # - target: 스레드에서 실행할 함수
        # - name: 디버깅용 스레드 이름 (ps, top 등에서 표시)
        # - daemon: True면 메인 종료 시 같이 종료
        # =====================================================================
        self._thread = threading.Thread(
            target=self._capture_loop,
            name="PacketSniffer",
            daemon=True
        )
        self._thread.start()
        
        logger.info(f"Sniffer started on interface '{self._interface}'")
    
    def stop(self) -> None:
        """
        패킷 캡처 중지.
        
        캡처 루프를 종료하고 스레드가 끝날 때까지 대기합니다.
        최대 2초 대기 후 타임아웃됩니다.
        
        Q: 왜 타임아웃이 필요한가요?
        A: sniff() 함수가 블로킹될 수 있습니다.
           stop_filter 콜백이 다음 패킷 수신 시까지 확인되지 않을 수 있어요.
           2초 타임아웃으로 무한 대기 방지.
        """
        if not self._running:
            logger.warning("Sniffer is not running")
            return
        
        # _running을 False로 설정하면 sniff()의 stop_filter가 True 반환
        self._running = False
        
        # 스레드 종료 대기 (최대 2초)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            
            # 타임아웃 발생 시 경고
            if self._thread.is_alive():
                logger.warning("Sniffer thread did not terminate in time")
        
        logger.info("Sniffer stopped")
    
    def is_running(self) -> bool:
        """
        스니퍼 실행 상태 확인.
        
        Returns:
            실행 중이면 True
        """
        return self._running
    
    def get_stats(self) -> CaptureStats:
        """
        캡처 통계 반환.
        
        Returns:
            CaptureStats 인스턴스 (실시간 통계)
        """
        return self._stats
    
    def _capture_loop(self) -> None:
        """
        패킷 캡처 루프 (스레드에서 실행).
        
        Scapy의 sniff() 함수를 사용하여 패킷을 캡처합니다.
        stop_filter 콜백으로 _running 플래그를 확인하여 종료합니다.
        
        Note:
            이 메서드는 직접 호출하지 않습니다.
            start()에서 스레드로 실행됩니다.
        
        예외 처리:
            - PermissionError: root 권한 없음
            - OSError: 인터페이스 없음 또는 기타 OS 오류
        """
        logger.info(f"Capture loop started, filter: {self._filter}")
        
        try:
            # =================================================================
            # Scapy sniff() 함수 - 핵심 캡처 로직
            #
            # 파라미터 설명:
            # - prn: 각 패킷마다 호출되는 콜백 (Packet Required Notifier)
            # - filter: BPF 필터 문자열 (커널 레벨 필터링)
            # - iface: 캡처할 네트워크 인터페이스
            # - store: False면 메모리에 패킷 저장 안 함 (성능 최적화)
            # - stop_filter: True 반환 시 캡처 중지
            #
            # Q: store=False가 왜 중요한가요?
            # A: True면 모든 패킷을 리스트에 저장하여 메모리 폭발.
            #    우리는 콜백으로 처리하므로 저장 불필요.
            # =================================================================
            sniff(
                prn=self._process_packet,
                filter=self._filter,
                iface=self._interface,
                store=False,
                stop_filter=lambda _: not self._running
            )
        except PermissionError:
            # raw socket 접근 권한 없음
            logger.error(
                "Permission denied. Solutions:\n"
                "  1. Run with sudo: sudo python run.py\n"
                "  2. Set capability: sudo setcap cap_net_raw+ep $(which python3)"
            )
            self._running = False
        except OSError as e:
            # 인터페이스 없음 또는 기타 OS 오류
            logger.error(f"OS error during capture: {e}")
            logger.error(f"Check interface with: ip link show")
            self._running = False
        except Exception as e:
            # 예상치 못한 오류
            logger.error(f"Unexpected error in capture loop: {e}")
            self._running = False
        finally:
            logger.info("Capture loop ended")
    
    def _process_packet(self, packet: Packet) -> None:
        """
        개별 패킷 처리.
        
        Scapy의 sniff()에서 패킷이 수신될 때마다 호출됩니다.
        UDP 페이로드를 추출하여 콜백 함수에 전달합니다.
        
        Args:
            packet: Scapy 패킷 객체 (여러 레이어로 구성)
        
        Note:
            - 이 함수는 캡처 스레드에서 실행됩니다
            - 빠르게 처리해야 패킷 드롭이 발생하지 않습니다
            - 무거운 처리는 큐에 넣고 메인 스레드에서 처리
        
        패킷 구조 (Scapy):
            Ether / IP / UDP / Raw
            - packet[UDP]: UDP 레이어
            - packet[Raw]: 페이로드 레이어 (실제 데이터)
            - packet[Raw].load: 바이트 데이터
        """
        try:
            # =================================================================
            # 패킷 레이어 확인
            # - 'in' 연산자: 해당 레이어가 패킷에 있는지 확인
            # - UDP in packet: UDP 레이어 존재 확인
            # - Raw in packet: 페이로드 존재 확인
            # =================================================================
            if UDP in packet and Raw in packet:
                # Raw 레이어에서 바이트 데이터 추출
                # bytes()로 감싸서 불변 바이트 객체로 변환
                raw_data = bytes(packet[Raw].load)
                
                # 통계 업데이트 (패킷 수, PPS 등)
                self._stats.record_packet(len(raw_data), filtered=True)
                
                # 콜백 함수 호출 (보통 PacketQueue.put)
                # 콜백에서 예외 발생해도 캡처는 계속됨
                self._callback(raw_data)
                
        except Exception as e:
            # 개별 패킷 처리 실패해도 캡처는 계속
            # 디버그 레벨로 로깅 (너무 많이 출력될 수 있음)
            logger.debug(f"Error processing packet: {e}")
    
    # =========================================================================
    # 속성 (Properties)
    # - @property: getter 메서드를 속성처럼 사용
    # - 외부에서 sniffer.interface 형태로 접근
    # =========================================================================
    
    @property
    def interface(self) -> str:
        """캡처 인터페이스명."""
        return self._interface
    
    @property
    def filter_str(self) -> str:
        """BPF 필터 문자열."""
        return self._filter
