# ICD Parser 디버깅 가이드

## 문제: StatusPayload 파싱 에러

### 증상
```
Payload parsing failed: status payload. init() got an unexpected keyword argument 'operation_mode'
```

이 에러는 `StatusPayload` 객체를 생성할 때 `operation_mode` 인자를 받지 못한다는 의미입니다.

---

## 단계별 디버깅 절차

### Step 1: 환경 확인

#### 1.1 Python 버전 확인
```bash
python3 --version
```
**확인 사항**: Python 3.7 이상이어야 합니다 (dataclass 지원)

**해결책**: Python 3.7 미만이면 업그레이드 필요

#### 1.2 모듈 캐시 확인 및 삭제
```bash
# 프로젝트 루트에서 실행
find ugv_mon -name "__pycache__" -type d
find ugv_mon -name "*.pyc" -type f
```

**캐시 삭제**:
```bash
find ugv_mon -name "__pycache__" -type d -exec rm -r {} + 2>/dev/null
find ugv_mon -name "*.pyc" -delete
```

---

### Step 2: 클래스 정의 확인

#### 2.1 StatusPayload 필드 확인

`test_capture_packets.py`에 다음 디버깅 코드 추가:

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from ugv_mon.parser.models import StatusPayload
import inspect

print("=" * 60)
print("StatusPayload 클래스 디버깅 정보")
print("=" * 60)

# 1. 클래스 위치 확인
print(f"\n1. 클래스 모듈: {StatusPayload.__module__}")
print(f"2. 클래스 파일: {inspect.getfile(StatusPayload)}")

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
else:
    print("   ⚠️ dataclass 필드를 확인할 수 없습니다.")

print("=" * 60)
```

#### 2.2 결과 해석

**결과 A: operation_mode 필드가 없음**
```
❌ operation_mode 필드 없음!
```
**해결책**:
1. `ugv_mon/parser/models.py` 파일 열기
2. `StatusPayload` 클래스 확인
3. `operation_mode: int` 필드가 있는지 확인
4. 없으면 추가:
```python
@dataclass
class StatusPayload:
    device_presence: int
    devices: Dict[str, bool]
    vic_state_byte: int
    operation_mode: int          # ← 이 필드가 있어야 함
    operation_mode_label: str
    # ... 나머지 필드
```

**결과 B: __dataclass_fields__가 없음**
```
⚠️ dataclass 필드가 없습니다!
```
**해결책**:
1. `models.py`에서 `@dataclass` 데코레이터 확인
2. Python 버전 확인 (3.7+ 필요)
3. 모듈 재로드:
```python
import importlib
import ugv_mon.parser.models
importlib.reload(ugv_mon.parser.models)
```

**결과 C: 필드는 있지만 __init__에 없음**
```
필드 목록에는 있지만 __init__ 시그니처에 없음
```
**해결책**:
1. 모듈 캐시 삭제 (Step 1.2 참고)
2. Python 재시작
3. 모듈 재로드

---

### Step 3: 실제 에러 발생 지점 확인

#### 3.1 icd_parser.py에 상세 디버깅 코드 추가

`ugv_mon/parser/icd_parser.py`의 `_parse_status_payload` 메서드 수정:

```python
def _parse_status_payload(self, payload: bytes) -> StatusPayload:
    """상태보고 페이로드 파싱."""
    # 장치 연결 상태
    device_presence = struct.unpack('<H', payload[0:2])[0]
    devices = {
        name: bool(device_presence & (1 << i))
        for i, name in enumerate(self.DEVICE_NAMES)
    }

    # VIC 운용 상태
    vic_state = payload[2]
    operation_mode = (vic_state >> 5) & 0x07
    authority = (vic_state >> 2) & 0x03
    driving_state = vic_state & 0x03

    # 비상정지 원인
    emergency_word = struct.unpack('<H', payload[3:5])[0]
    emergency_bits = (emergency_word >> 6) & 0x3FF
    emergency_status = {
        name: bool(emergency_bits & (1 << i))
        for i, name in enumerate(self.EMERGENCY_NAMES)
    }

    # 디버깅: 생성 전 값 확인
    print(f"\n[DEBUG] StatusPayload 생성 전 확인")
    print(f"  operation_mode 값: {operation_mode}")
    print(f"  operation_mode 타입: {type(operation_mode)}")
    
    # StatusPayload 클래스 확인
    from ugv_mon.parser.models import StatusPayload as SP
    import inspect
    
    print(f"  StatusPayload 모듈: {SP.__module__}")
    print(f"  StatusPayload 파일: {inspect.getfile(SP)}")
    
    if hasattr(SP, '__dataclass_fields__'):
        fields = list(SP.__dataclass_fields__.keys())
        print(f"  StatusPayload 필드: {fields}")
        if 'operation_mode' in fields:
            print(f"  ✅ operation_mode 필드 존재")
        else:
            print(f"  ❌ operation_mode 필드 없음!")
            print(f"  사용 가능한 필드: {fields}")
    else:
        print(f"  ⚠️ dataclass 필드를 확인할 수 없습니다.")

    try:
        payload_obj = StatusPayload(
            device_presence=device_presence,
            devices=devices,
            vic_state_byte=vic_state,
            operation_mode=operation_mode,
            operation_mode_label=self.OPERATION_MODE_LABELS.get(operation_mode, f"알 수 없음 ({operation_mode})"),
            authority=authority,
            authority_label=self.AUTHORITY_LABELS.get(authority, f"알 수 없음 ({authority})"),
            driving_state=driving_state,
            driving_state_label=self.DRIVING_STATE_LABELS.get(driving_state, f"알 수 없음 ({driving_state})"),
            emergency_word=emergency_word,
            emergency_status=emergency_status
        )
        print(f"  ✅ StatusPayload 생성 성공!")
        return payload_obj
    except TypeError as e:
        print(f"  ❌ StatusPayload 생성 실패!")
        print(f"  에러 타입: TypeError")
        print(f"  에러 메시지: {e}")
        
        # 실제 __init__ 시그니처 출력
        import inspect
        try:
            sig = inspect.signature(StatusPayload.__init__)
            print(f"  실제 __init__ 시그니처: {sig}")
        except:
            pass
        
        # 전달하려는 인자 확인
        print(f"  전달하려는 인자:")
        print(f"    - device_presence: {device_presence}")
        print(f"    - devices: {type(devices)}")
        print(f"    - vic_state_byte: {vic_state}")
        print(f"    - operation_mode: {operation_mode}")
        print(f"    - operation_mode_label: {self.OPERATION_MODE_LABELS.get(operation_mode, '알 수 없음')}")
        print(f"    - authority: {authority}")
        print(f"    - authority_label: {self.AUTHORITY_LABELS.get(authority, '알 수 없음')}")
        print(f"    - driving_state: {driving_state}")
        print(f"    - driving_state_label: {self.DRIVING_STATE_LABELS.get(driving_state, '알 수 없음')}")
        print(f"    - emergency_word: {emergency_word}")
        print(f"    - emergency_status: {type(emergency_status)}")
        
        import traceback
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"  ❌ StatusPayload 생성 실패!")
        print(f"  에러 타입: {type(e)}")
        print(f"  에러 메시지: {e}")
        import traceback
        traceback.print_exc()
        raise
```

#### 3.2 결과 해석

**결과 A: operation_mode 필드가 없음**
```
❌ operation_mode 필드 없음!
사용 가능한 필드: ['device_presence', 'devices', 'vic_state_byte', ...]
```
**해결책**: `models.py`의 `StatusPayload`에 `operation_mode: int` 필드 추가

**결과 B: TypeError 발생**
```
TypeError: __init__() got an unexpected keyword argument 'operation_mode'
```
**해결책**:
1. `models.py`의 필드 순서 확인
2. `icd_parser.py`의 인자 순서와 일치하는지 확인
3. 모듈 재로드

---

### Step 4: 모듈 Import 경로 확인

#### 4.1 Import 경로 확인

`ugv_mon/parser/icd_parser.py` 상단 확인:

```python
from .models import ICDHeader, StatusPayload, ParseResult
```

**확인 사항**:
- 상대 import 사용 (`from .models`)
- 절대 import가 아닌지 확인 (`from ugv_mon.parser.models`는 피해야 함)

#### 4.2 모듈 재로드 테스트

`test_capture_packets.py`에 추가:

```python
import importlib
import ugv_mon.parser.models
import ugv_mon.parser.icd_parser

# 모듈 재로드
print("모듈 재로드 중...")
importlib.reload(ugv_mon.parser.models)
importlib.reload(ugv_mon.parser.icd_parser)

# 재로드 후 확인
from ugv_mon.parser.models import StatusPayload
from ugv_mon.parser.icd_parser import ICDParser

import inspect
print("재로드 후 필드:", list(StatusPayload.__dataclass_fields__.keys()) if hasattr(StatusPayload, '__dataclass_fields__') else "없음")
```

---

### Step 5: 필드 순서 확인

#### 5.1 models.py 필드 순서

`ugv_mon/parser/models.py`의 `StatusPayload` 필드 순서:

```python
@dataclass
class StatusPayload:
    device_presence: int          # 1
    devices: Dict[str, bool]       # 2
    vic_state_byte: int            # 3
    operation_mode: int            # 4 ← 이 위치에 있어야 함
    operation_mode_label: str      # 5
    authority: int                 # 6
    authority_label: str           # 7
    driving_state: int             # 8
    driving_state_label: str       # 9
    emergency_word: int            # 10
    emergency_status: Dict[str, bool]  # 11
```

#### 5.2 icd_parser.py 인자 순서 확인

`ugv_mon/parser/icd_parser.py`의 `_parse_status_payload`에서 `StatusPayload` 생성 시 인자 순서가 위와 일치하는지 확인.

**참고**: dataclass는 필드 순서가 중요하지 않지만, 키워드 인자로 전달할 때는 필드 이름이 정확해야 합니다.

---

### Step 6: Python 버전 및 dataclass 확인

#### 6.1 Python 버전 확인
```bash
python3 --version
python3 -c "import sys; print(sys.version_info)"
```

**요구사항**: Python 3.7 이상

#### 6.2 dataclass 데코레이터 확인

`ugv_mon/parser/models.py` 확인:

```python
from dataclasses import dataclass  # ← import 확인

@dataclass  # ← 데코레이터 확인
class StatusPayload:
    ...
```

**확인 사항**:
- `from dataclasses import dataclass` import가 있는지
- `@dataclass` 데코레이터가 클래스 위에 있는지
- 들여쓰기가 올바른지

---

## 체크리스트

다음 항목을 순서대로 확인하세요:

- [ ] **Step 1**: Python 버전 3.7 이상 확인
- [ ] **Step 1**: `__pycache__` 및 `.pyc` 파일 삭제
- [ ] **Step 2**: `StatusPayload` 클래스에 `operation_mode: int` 필드 존재 확인
- [ ] **Step 2**: `@dataclass` 데코레이터 확인
- [ ] **Step 3**: 실제 에러 발생 지점에서 디버깅 코드 실행
- [ ] **Step 4**: Import 경로 확인 (상대 import 사용)
- [ ] **Step 5**: 필드 순서 및 이름 확인
- [ ] **Step 6**: Python 재시작 후 테스트

---

## 빠른 해결 방법 (Emergency Fix)

위 단계를 모두 거치기 어렵다면 다음을 시도하세요:

### 방법 1: 완전 초기화
```bash
# 프로젝트 루트에서 실행
find ugv_mon -name "__pycache__" -type d -exec rm -r {} + 2>/dev/null
find ugv_mon -name "*.pyc" -delete
python3 test_capture_packets.py
```

### 방법 2: models.py 재확인
`ugv_mon/parser/models.py` 파일을 열어 다음을 확인:

1. `from dataclasses import dataclass` import 확인
2. `@dataclass` 데코레이터 확인
3. `StatusPayload` 클래스에 다음 필드가 모두 있는지 확인:
   - `operation_mode: int`
   - `operation_mode_label: str`

### 방법 3: 간단한 테스트 스크립트 실행

`test_status_payload.py` 파일 생성:

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from ugv_mon.parser.models import StatusPayload

# 간단한 테스트
try:
    payload = StatusPayload(
        device_presence=1,
        devices={"VIC": True},
        vic_state_byte=0,
        operation_mode=0,
        operation_mode_label="준비 (PREP)",
        authority=0,
        authority_label="해제됨 (RELEASED)",
        driving_state=0,
        driving_state_label="알 수 없음",
        emergency_word=0,
        emergency_status={}
    )
    print("✅ StatusPayload 생성 성공!")
    print(f"operation_mode: {payload.operation_mode}")
except Exception as e:
    print(f"❌ StatusPayload 생성 실패: {e}")
    import traceback
    traceback.print_exc()
```

실행:
```bash
python3 test_status_payload.py
```

---

## 예상되는 원인 및 해결책 요약

| 원인 | 증상 | 해결책 |
|------|------|--------|
| 모듈 캐시 문제 | 오래된 클래스 정의 사용 | `__pycache__` 삭제 |
| 필드 누락 | `operation_mode` 필드 없음 | `models.py`에 필드 추가 |
| Python 버전 | dataclass 미지원 | Python 3.7+ 업그레이드 |
| Import 경로 | 잘못된 모듈 로드 | 상대 import 확인 |
| dataclass 데코레이터 누락 | dataclass 기능 미작동 | `@dataclass` 확인 |

---

## 추가 리소스

- Python dataclass 문서: https://docs.python.org/3/library/dataclasses.html
- 프로젝트 구조: `docs/02_FILE_STRUCTURE.md`
- ICD 규격: `docs/03_ICD_SPECIFICATION.md`

---

## 문제가 해결되지 않으면

1. 위의 모든 디버깅 출력을 저장
2. `models.py`와 `icd_parser.py` 파일 전체 내용 확인
3. Python 버전 및 환경 정보 수집
4. 에러 메시지 전체 스택 트레이스 확인

이 정보들을 함께 확인하면 문제를 정확히 진단할 수 있습니다.
