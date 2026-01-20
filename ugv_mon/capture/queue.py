"""
Thread-safe Packet Queue Module.

캡처 스레드(Producer)와 메인 스레드(Consumer) 간의
패킷 데이터를 안전하게 전달하는 버퍼입니다.

=============================================================================
설계 패턴: Producer-Consumer
- Producer: PacketSniffer (캡처 스레드) → queue.put()
- Consumer: UI 콜백 (메인 스레드) → queue.get_all()

Q: 왜 Python 기본 queue.Queue 대신 직접 구현했나요?
A: 1. deque + maxlen으로 자동 메모리 관리 (오래된 패킷 자동 삭제)
   2. get_all()로 한 번에 모든 패킷 가져오기 (Queue는 하나씩만)
   3. 패킷 캡처에 최적화된 인터페이스 제공

Q: 왜 threading.Lock을 사용하나요?
A: 두 스레드가 동시에 deque에 접근하면 데이터 손상 가능.
   Lock으로 한 번에 하나의 스레드만 접근하도록 보장합니다.
=============================================================================
"""

import threading
from collections import deque
from typing import List, Optional
from datetime import datetime


class PacketQueue:
    """
    스레드 안전 패킷 큐.
    
    Producer-Consumer 패턴으로 패킷을 전달합니다.
    deque의 maxlen을 활용하여 메모리 사용량을 제한합니다.
    
    Attributes:
        max_size: 최대 큐 크기 (초과 시 오래된 패킷 삭제)
    
    사용 예시:
        queue = PacketQueue(max_size=500)
        
        # Producer (캡처 스레드)
        queue.put(packet_bytes)
        
        # Consumer (메인 스레드)
        packets = queue.get_all()  # 모든 패킷 한 번에 가져오기
    """
    
    def __init__(self, max_size: int = 1000):
        """
        패킷 큐 초기화.
        
        Args:
            max_size: 최대 저장 가능한 패킷 수
                      초과 시 가장 오래된 패킷이 자동 제거됨
        
        Q: 왜 기본값이 1000인가요?
        A: 1000 pps 기준 1초 분량입니다.
           UI 폴링 주기(2초)보다 충분히 큽니다.
           메모리 사용량: 약 1000 * 200bytes = 200KB (무시 가능)
        """
        # =====================================================================
        # deque(maxlen=N): 고정 크기 양방향 큐
        # - 크기가 N을 초과하면 반대쪽에서 자동 제거
        # - append(): 오른쪽 추가 → maxlen 초과 시 왼쪽 제거
        # - popleft(): 왼쪽에서 제거 (FIFO)
        # 
        # Q: 왜 list가 아닌 deque인가요?
        # A: list.pop(0)은 O(n), deque.popleft()는 O(1)
        #    1000개 패킷 처리 시 1000배 빠릅니다.
        # =====================================================================
        self._queue: deque = deque(maxlen=max_size)
        
        # =====================================================================
        # threading.Lock: 뮤텍스 (상호 배제)
        # - acquire(): 잠금 획득 (다른 스레드 대기)
        # - release(): 잠금 해제
        # - with self._lock: → acquire/release 자동 처리 (권장)
        # =====================================================================
        self._lock = threading.Lock()
        
        # 통계/디버깅용 타임스탬프
        self._last_put_time: Optional[datetime] = None
    
    def put(self, packet: bytes) -> None:
        """
        패킷을 큐에 추가.
        
        캡처 스레드(PacketSniffer)에서 호출됩니다.
        큐가 가득 차면 가장 오래된 패킷이 자동으로 제거됩니다.
        
        Args:
            packet: 원시 패킷 바이트 데이터 (UDP 페이로드)
        
        Thread Safety:
            Lock으로 보호되어 동시 접근 안전
        
        Q: 패킷이 드롭되면 어떻게 되나요?
        A: maxlen 초과 시 오래된 패킷이 자동 삭제됩니다.
           이는 의도된 동작입니다 (최신 데이터 우선).
        """
        # with문: Lock의 컨텍스트 매니저 사용
        # __enter__에서 acquire(), __exit__에서 release()
        # 예외 발생 시에도 반드시 release() 호출됨
        with self._lock:
            self._queue.append(packet)
            self._last_put_time = datetime.now()
    
    def get(self) -> Optional[bytes]:
        """
        큐에서 가장 오래된 패킷 하나를 꺼냄.
        
        FIFO(First-In-First-Out) 순서로 패킷을 반환합니다.
        큐가 비어있으면 None을 반환합니다.
        
        Returns:
            패킷 바이트 데이터 또는 None (큐가 비어있는 경우)
        
        Q: 왜 예외 대신 None을 반환하나요?
        A: 큐가 비어있는 것은 정상 상황입니다 (패킷이 아직 없음).
           예외는 진짜 오류 상황에만 사용해야 합니다.
        """
        with self._lock:
            if len(self._queue) == 0:
                return None
            # popleft(): 왼쪽(가장 오래된)에서 제거하며 반환
            return self._queue.popleft()
    
    def get_all(self) -> List[bytes]:
        """
        큐의 모든 패킷을 한 번에 꺼냄.
        
        UI 갱신 시 사용합니다. 한 번의 Lock 획득으로
        모든 패킷을 가져오므로 효율적입니다.
        
        호출 후 큐는 비워집니다.
        
        Returns:
            패킷 리스트 (비어있으면 빈 리스트 [])
        
        Q: 왜 get()을 반복 호출하지 않나요?
        A: get()은 매번 Lock을 획득/해제합니다.
           get_all()은 한 번만 Lock을 획득하므로 훨씬 빠릅니다.
        """
        with self._lock:
            # list(deque)로 복사 후 clear()로 원본 비우기
            # 이렇게 해야 Lock 해제 후에도 안전하게 사용 가능
            packets = list(self._queue)
            self._queue.clear()
            return packets
    
    def peek(self) -> Optional[bytes]:
        """
        큐의 맨 앞 패킷을 제거하지 않고 확인.
        
        디버깅이나 조건 확인 시 사용합니다.
        
        Returns:
            맨 앞 패킷 또는 None
        """
        with self._lock:
            if len(self._queue) == 0:
                return None
            # 인덱스 접근은 제거하지 않음
            return self._queue[0]
    
    def size(self) -> int:
        """
        현재 큐에 저장된 패킷 수.
        
        Returns:
            패킷 수 (정수)
        """
        with self._lock:
            return len(self._queue)
    
    def is_empty(self) -> bool:
        """
        큐가 비어있는지 확인.
        
        Returns:
            비어있으면 True
        """
        return self.size() == 0
    
    def clear(self) -> None:
        """
        큐의 모든 패킷 제거.
        
        큐를 초기화해야 할 때 호출합니다.
        예: 캡처 재시작, 수동 리셋
        """
        with self._lock:
            self._queue.clear()
    
    @property
    def last_put_time(self) -> Optional[datetime]:
        """
        마지막 패킷 추가 시간.
        
        연결 상태 확인에 사용됩니다.
        예: 5초 이상 패킷이 없으면 연결 끊김으로 판단
        
        Returns:
            마지막 put() 호출 시간 또는 None
        """
        return self._last_put_time
