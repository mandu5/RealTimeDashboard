"""
스레드 안전 패킷 큐.
"""

import threading
from collections import deque
from typing import List, Optional
from datetime import datetime


class PacketQueue:
    """Producer-Consumer 패턴의 패킷 큐."""

    def __init__(self, max_size: int = 1000):
        self._queue: deque = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._last_put_time: Optional[datetime] = None
        self._last_packet: Optional[bytes] = None  # 중복 체크용

    def put(self, packet: bytes) -> None:
        """패킷 추가."""
        with self._lock:
            if packet == self._last_packet:
                return
                
            self._last_packet = packet
            self._queue.append(packet)
            self._last_put_time = datetime.now()

    def get(self) -> Optional[bytes]:
        """패킷 하나 꺼내기."""
        with self._lock:
            return self._queue.popleft() if self._queue else None

    def get_all(self) -> List[bytes]:
        """모든 패킷 꺼내기."""
        with self._lock:
            packets = list(self._queue)
            self._queue.clear()
            return packets

    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        return self.size() == 0

    def clear(self) -> None:
        with self._lock:
            self._queue.clear()

    @property
    def last_put_time(self) -> Optional[datetime]:
        return self._last_put_time
