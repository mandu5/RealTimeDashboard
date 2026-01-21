#!/usr/bin/env python3
"""
StatusPayload 디버깅 테스트 스크립트

사용법:
    python3 test_status_payload_debug.py

이 스크립트는 StatusPayload 클래스의 정의와 생성 가능 여부를 확인합니다.
"""

import sys
sys.path.insert(0, '.')

import inspect
from ugv_mon.parser.models import StatusPayload

def main():
    print("=" * 60)
    print("StatusPayload 클래스 디버깅 정보")
    print("=" * 60)

    # 1. 클래스 위치 확인
    print(f"\n1. 클래스 모듈: {StatusPayload.__module__}")
    try:
        print(f"2. 클래스 파일: {inspect.getfile(StatusPayload)}")
    except Exception as e:
        print(f"2. 클래스 파일: 확인 불가 ({e})")

    # 2. 필드 목록 확인
    print("\n3. 필드 목록:")
    try:
        fields = inspect.fields(StatusPayload)
        for field in fields:
            print(f"   - {field.name}: {field.type}")
    except Exception as e:
        print(f"   ⚠️ 필드 조회 실패: {e}")

    # 3. __init__ 시그니처 확인
    print("\n4. __init__ 시그니처:")
    try:
        sig = inspect.signature(StatusPayload.__init__)
        print(f"   {sig}")
    except Exception as e:
        print(f"   ⚠️ 시그니처 조회 실패: {e}")

    # 4. __init__ 파라미터 확인
    print("\n5. __init__ 파라미터:")
    try:
        sig = inspect.signature(StatusPayload.__init__)
        for param_name, param in sig.parameters.items():
            if param_name != 'self':
                print(f"   - {param_name}: {param.annotation}")
    except Exception as e:
        print(f"   ⚠️ 파라미터 조회 실패: {e}")

    # 5. dataclass 필드 확인
    print("\n6. dataclass 필드:")
    if hasattr(StatusPayload, '__dataclass_fields__'):
        for field_name, field_info in StatusPayload.__dataclass_fields__.items():
            print(f"   - {field_name}: {field_info.type}")
    else:
        print("   ⚠️ dataclass 필드가 없습니다!")
        print("   → @dataclass 데코레이터가 제대로 적용되지 않았을 수 있습니다.")

    # 6. operation_mode 필드 존재 여부 확인
    print("\n7. operation_mode 필드 확인:")
    if hasattr(StatusPayload, '__dataclass_fields__'):
        if 'operation_mode' in StatusPayload.__dataclass_fields__:
            print("   ✅ operation_mode 필드 존재")
        else:
            print("   ❌ operation_mode 필드 없음!")
            print("   → models.py의 StatusPayload 클래스에 operation_mode 필드가 있는지 확인하세요.")
            print(f"   사용 가능한 필드: {list(StatusPayload.__dataclass_fields__.keys())}")
    else:
        print("   ⚠️ dataclass 필드를 확인할 수 없습니다.")

    # 7. 실제 생성 테스트
    print("\n8. StatusPayload 생성 테스트:")
    try:
        payload = StatusPayload(
            device_presence=1,
            devices={"VIC": True, "RDC": False},
            vic_state_byte=0b00100001,  # 예시 값
            operation_mode=0,
            operation_mode_label="준비 (PREP)",
            authority=1,
            authority_label="OCS 획득 (OCS ACQUIRED)",
            driving_state=1,
            driving_state_label="원격 (REMOTE)",
            emergency_word=0,
            emergency_status={}
        )
        print("   ✅ StatusPayload 생성 성공!")
        print(f"   - operation_mode: {payload.operation_mode}")
        print(f"   - operation_mode_label: {payload.operation_mode_label}")
        print(f"   - authority: {payload.authority}")
        print(f"   - driving_state: {payload.driving_state}")
    except TypeError as e:
        print(f"   ❌ StatusPayload 생성 실패 (TypeError): {e}")
        print("\n   가능한 원인:")
        print("   1. operation_mode 필드가 models.py에 없음")
        print("   2. 필드 이름이 잘못됨")
        print("   3. 모듈 캐시 문제")
        print("\n   해결 방법:")
        print("   1. ugv_mon/parser/models.py 파일 확인")
        print("   2. __pycache__ 삭제: find ugv_mon -name '__pycache__' -type d -exec rm -r {} +")
        print("   3. Python 재시작")
    except Exception as e:
        print(f"   ❌ StatusPayload 생성 실패: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("디버깅 완료")
    print("=" * 60)
    print("\n문제가 해결되지 않으면 docs/DEBUGGING_GUIDE.md를 참고하세요.")


if __name__ == "__main__":
    main()
