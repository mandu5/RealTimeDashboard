"""
패킷 처리 파이프라인.

큐에서 패킷을 가져와 파싱하고, 저장소에 추가합니다.

책임:
    1. queue에서 Tuple[datetime, bytes] 가져오기
    2. bytes 언패킹
    3. parser 호출 → ParseResult
    4. packet_store에 추가

데이터 흐름:
    PacketQueue → PacketProcessor → PacketStore
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .queue import PacketQueue
    from ..parser import ICDParser
    from ..data.packet_store import PacketStore, PacketRecord


@dataclass
class BatchProcessResult:
    """배치 처리 결과 요약.

    process_pending()의 반환값으로, 한 번의 폴링에서 처리된
    패킷들의 집계 결과를 담습니다.

    Attributes:
        count: 처리된 패킷 수
        success_count: 파싱 성공 수
        checksum_fail_count: 체크섬 실패 수
        last_payload: 마지막 OperationalPayload (있으면)
    """
    count: int
    success_count: int
    checksum_fail_count: int
    last_payload: Optional[object]  # OperationalPayload


class PacketProcessor:
    """패킷 처리 파이프라인.
    
    큐에서 패킷을 가져와 파싱하고 저장소에 추가합니다.
    live_provider의 _process_packets 역할을 대체합니다.
    
    Args:
        queue: 패킷 큐
        parser: ICD 파서
        store: 통합 저장소
    """
    
    def __init__(
        self, 
        queue: "PacketQueue", 
        parser: "ICDParser", 
        store: "PacketStore"
    ):
        self._queue = queue
        self._parser = parser
        self._store = store
    
    def process_pending(self) -> BatchProcessResult:
        """대기 중인 모든 패킷 처리.
        
        Returns:
            처리 결과 요약
        """
        count = 0
        success_count = 0
        checksum_fail_count = 0
        last_payload = None
        
        for capture_time, packet_bytes in self._queue.get_all():
            result = self._process_one(capture_time, packet_bytes)
            count += 1
            
            if result:
                if result.parse_ok:
                    success_count += 1
                if not result.checksum_ok:
                    checksum_fail_count += 1
                if result.last_payload:
                    last_payload = result.last_payload
        
        return BatchProcessResult(
            count=count,
            success_count=success_count,
            checksum_fail_count=checksum_fail_count,
            last_payload=last_payload,
        )
    
    def _process_one(
        self, 
        capture_time: datetime, 
        packet_bytes: bytes
    ) -> Optional["_PacketProcessResult"]:
        """단일 패킷 처리.
        
        Args:
            capture_time: 캡처 시각
            packet_bytes: 원본 바이트
            
        Returns:
            처리 결과 (실패시 None)
        """
        # 파싱
        parse_result = self._parser.parse(packet_bytes)
        
        # 기본값
        msg_code = 0
        sequence = 0
        operation_mode = "---"
        authority = "---"
        payload = None
        
        # 헤더 정보 추출
        if parse_result.header:
            msg_code = parse_result.header.msg_code
            sequence = parse_result.header.sequence
        
        # 페이로드 정보 추출
        if parse_result.payload:
            operation_mode = parse_result.payload.operation_mode
            authority = parse_result.payload.authority
            payload = parse_result.payload
            
            # 이력 기록
            self._store.record_mode_transition(operation_mode)
            
            if parse_result.payload.is_emergency:
                reasons = parse_result.payload.get_emergency_reasons()
                self._store.record_emergency(reasons)
        
        # PacketRecord 생성 및 저장
        from ..data.packet_store import PacketRecord
        
        record = PacketRecord(
            timestamp=capture_time,
            msg_code=msg_code,
            sequence=sequence,
            size=len(packet_bytes),
            jitter_ms=None,  # store.add()에서 계산
            interval_ms=None,
            parse_ok=parse_result.success,
            checksum_ok=parse_result.checksum_ok,
            operation_mode=operation_mode,
            authority=authority,
        )
        
        self._store.add(record)
        
        return _PacketProcessResult(
            parse_ok=parse_result.success,
            checksum_ok=parse_result.checksum_ok,
            last_payload=payload,
        )


@dataclass
class _PacketProcessResult:
    """단일 패킷 처리 결과 (모듈 내부용)."""
    parse_ok: bool
    checksum_ok: bool
    last_payload: Optional[object]
