"""
UGV-MON ICD Parser Module.

ICD v1.0 규격에 따른 패킷 파싱 기능을 제공합니다.

=============================================================================
모듈 구성:
- ICDParser: 패킷 파싱 메인 클래스
- ICDHeader: 헤더 데이터 구조
- StatusPayload: 상태보고 페이로드 데이터 구조
- ParseResult: 파싱 결과 컨테이너

ICD v1.0 패킷 구조:
┌───────────┬─────────┬──────────┬────────────┬───────┬─────────┐
│ TimeStamp │ MSG ID  │ Reserved │ DataLength │ Data  │ Chksum  │
│ (4 bytes) │(4 bytes)│ (2 bytes)│ (2 bytes)  │(가변) │(2 bytes)│
└───────────┴─────────┴──────────┴────────────┴───────┴─────────┘

사용 예시:
    from ugv_mon.parser import ICDParser, ParseResult
    
    parser = ICDParser()
    result = parser.parse(raw_bytes)
    
    if result.success:
        print(f"시퀀스: {result.header.sequence}")
        print(f"메시지 코드: {result.header.msg_code}")
        if result.payload:
            print(f"운용 모드: {result.payload.operation_mode}")

Q: 왜 struct 모듈을 사용하나요?
A: Python의 바이트 언패킹 표준 라이브러리입니다.
   '<H'는 Little Endian 2바이트 unsigned short를 의미합니다.
=============================================================================
"""

from .models import ICDHeader, StatusPayload, ParseResult
from .icd_parser import ICDParser

__all__ = ["ICDParser", "ICDHeader", "StatusPayload", "ParseResult"]
