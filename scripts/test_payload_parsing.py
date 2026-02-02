#!/usr/bin/env python3
"""
페이로드 파싱 테스트 스크립트.

제공된 Wireshark 캡처 데이터로 ICD 메시지 샘플 파싱 테스트.
"""

import struct

# Wireshark 캡처 데이터 (hex)
SAMPLES = {
    "예시1": "8b000000b1a225ff02010100000603",  # data_length=1
    "예시2": "78000000b1a240ff02012d0000000000fffeff02000b00000000000000000002000000000000000000000000000000000000000000000000004506",  # data_length=45
    "예시3": "78000000b1a201ff02015700ff0085000200000045010000000000000000004500000001000000010203040102030400000000000000000000000000000000000000000000000000020003000000040000000506070800090a0b0c0d40010203040506fa05",  # data_length=87
}

ICD_HEADER_SIZE = 12
ICD_CHECKSUM_SIZE = 2


def parse_header(data: bytes) -> dict:
    """헤더 파싱 (12 bytes)."""
    if len(data) < ICD_HEADER_SIZE:
        return {"error": "Too short"}
    
    return {
        "timestamp": struct.unpack('<I', data[0:4])[0],
        "source_id": hex(data[4]),
        "dest_id": hex(data[5]),
        "msg_code": hex(data[6]),
        "ack_flag": hex(data[7]),
        "reserved": struct.unpack('<H', data[8:10])[0],
        "data_length": struct.unpack('<H', data[10:12])[0],
    }


def parse_operational_payload(payload: bytes) -> dict:
    """운용 상태 페이로드 파싱 (87 bytes 예상)."""
    if len(payload) < 5:
        return {"error": f"Payload too short: {len(payload)}"}
    
    # 처음 2바이트: 장치 연결 목록 (Bit 9~0)
    device_bits = struct.unpack('<H', payload[0:2])[0]
    devices = {
        "VIC": bool(device_bits & 0x001),
        "RDC": bool(device_bits & 0x002),
        "ADC": bool(device_bits & 0x004),
        "FCAM": bool(device_bits & 0x008),
        "RCAM": bool(device_bits & 0x010),
        "ACAM": bool(device_bits & 0x020),
        "SCS": bool(device_bits & 0x040),
        "DIP": bool(device_bits & 0x080),
        "TCC": bool(device_bits & 0x100),
        "TM": bool(device_bits & 0x200),
    }
    
    # 3번째 바이트: 운용 상태
    status_byte = payload[2]
    OPERATION_MODES = {0: "준비", 1: "무인주행", 2: "유인주행", 3: "비상정지", 4: "점검", 5: "원격"}
    AUTHORITIES = {0: "없음", 1: "OCS", 2: "근거리조종기", 3: "VIC"}
    DRIVING_STATES = {0: "정지", 1: "전진", 2: "후진", 3: "회전"}
    
    operation_mode_raw = (status_byte >> 5) & 0x07  # Bit 7~5
    authority_raw = (status_byte >> 2) & 0x03       # Bit 3~2
    driving_state_raw = status_byte & 0x03          # Bit 1~0
    
    operation_mode = OPERATION_MODES.get(operation_mode_raw, f"Unknown({operation_mode_raw})")
    authority = AUTHORITIES.get(authority_raw, f"Unknown({authority_raw})")
    driving_state = DRIVING_STATES.get(driving_state_raw, f"Unknown({driving_state_raw})")
    
    # 4~5번째 바이트: 비상정지
    emergency_bits = struct.unpack('<H', payload[3:5])[0]
    EMERGENCY_SOURCES = ["미식별", "운전자", "원격", "장애물", "경사", "속도초과", "통신이상", "배터리", "엔진", "기타"]
    emergency_sources_raw = (emergency_bits >> 6) & 0x3FF  # Bit 15~6
    emergency_complete = bool(emergency_bits & 0x01)       # Bit 0
    
    active_sources = [EMERGENCY_SOURCES[i] for i in range(10) if (emergency_sources_raw >> i) & 1]
    
    return {
        "devices": devices,
        "device_bits_raw": f"0x{device_bits:04X}",
        "status_byte_raw": f"0x{status_byte:02X}",
        "operation_mode": operation_mode,
        "authority": authority,
        "driving_state": driving_state,
        "emergency_bits_raw": f"0x{emergency_bits:04X}",
        "emergency_sources": active_sources if active_sources else ["없음"],
        "emergency_complete": emergency_complete,
    }


def main():
    print("=" * 60)
    print("페이로드 파싱 테스트")
    print("=" * 60)
    
    for name, hex_data in SAMPLES.items():
        print(f"\n{'─' * 60}")
        print(f"📦 {name}")
        print(f"{'─' * 60}")
        
        data = bytes.fromhex(hex_data)
        print(f"Raw length: {len(data)} bytes")
        
        # 헤더 파싱
        header = parse_header(data)
        print(f"\n[헤더]")
        for k, v in header.items():
            print(f"  {k}: {v}")
        
        # 페이로드 추출
        data_length = header.get("data_length", 0)
        if data_length > 0:
            payload = data[ICD_HEADER_SIZE:-ICD_CHECKSUM_SIZE]
            print(f"\n[페이로드] {len(payload)} bytes (예상: {data_length})")
            print(f"  Raw: {payload.hex()[:60]}...")
            
            # 운용 상태 파싱 시도 (data_length=87인 경우)
            if data_length >= 5:
                print(f"\n[운용 상태 파싱 시도]")
                result = parse_operational_payload(payload)
                for k, v in result.items():
                    if k == "devices":
                        print(f"  {k}:")
                        for dev, connected in v.items():
                            print(f"    {dev}: {'●' if connected else '○'}")
                    else:
                        print(f"  {k}: {v}")
        
        # 체크섬
        checksum = struct.unpack('<H', data[-2:])[0]
        print(f"\n[체크섬] 0x{checksum:04X}")


if __name__ == "__main__":
    main()
