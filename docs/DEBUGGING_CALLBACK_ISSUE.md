# 콜백/폴링 문제 완전 디버깅 가이드

> **증상**: UI 렌더링 정상, 2초 후 데이터 업데이트 안됨, 버튼 무반응, 에러 없음
>
> **목표**: 하루 안에 문제 해결!

---

## 📌 디버깅 전 준비

```bash
# 1. 터미널 2개 열기
# 터미널 1: 앱 실행
python3 run.py --mode live

# 터미널 2: 디버깅 코드 실행 (Python REPL)
python3
```

---

## 🔧 STEP 1: 객체 초기화 검증 (가장 중요!)

### 1.1 핵심 객체 None 체크

```python
from ugv_mon.data.live_provider import LiveDataProvider

provider = LiveDataProvider(interface="eno2")  # 회사 인터페이스명

# 핵심 객체 확인
print("=== 핵심 객체 초기화 확인 ===")
print(f"_store: {provider._store}")           # None이면 ❌
print(f"_processor: {provider._processor}")   # None이면 ❌
print(f"_packet_queue: {provider._packet_queue}")  # None이면 ❌
print(f"_parser: {provider._parser}")         # None이면 ❌
```

**결과 해석**:
| 결과 | 의미 | 해결 방법 |
|------|------|----------|
| 모두 객체 | ✅ 정상 | Step 2로 |
| 하나라도 None | ❌ 버그 | `_init_modules()` 호출 누락 또는 내용 확인 |

**버그 수정 (None인 경우)**:

```python
# live_provider.py의 __init__ 끝에 추가:
def __init__(self, interface: str = None):
    # ... 기존 코드 ...

    # 마지막에 반드시 호출!
    self._init_modules()
```

---

### 1.2 `_init_modules()` 메서드 내용 확인

```python
import inspect
from ugv_mon.data.live_provider import LiveDataProvider

source = inspect.getsource(LiveDataProvider._init_modules)
print(source)
```

**올바른 구현**:

```python
def _init_modules(self):
    self._packet_queue = PacketQueue(max_size=1000)
    self._parser = ICDParser()
    self._store = PacketStore(window_sec=3600)
    self._processor = PacketProcessor(
        self._packet_queue,  # ← 반드시 self._packet_queue!
        self._parser,
        self._store          # ← 반드시 self._store!
    )
```

---

## 🔧 STEP 2: 객체 연결(동일성) 검증

### 2.1 Queue 객체 동일성 (매우 중요!)

```python
from ugv_mon.data.live_provider import LiveDataProvider

provider = LiveDataProvider(interface="eno2")

# 두 queue가 같은 객체인지 확인
queue_provider = provider._packet_queue
queue_processor = provider._processor._queue

print("=== Queue 동일성 검사 ===")
print(f"provider._packet_queue id: {id(queue_provider)}")
print(f"processor._queue id: {id(queue_processor)}")
print(f"동일 객체 여부: {queue_provider is queue_processor}")
```

**결과 해석**:
| 결과 | 의미 |
|------|------|
| `True` | ✅ 정상 |
| `False` | ❌ **핵심 버그!** - Sniffer가 넣는 큐 ≠ Processor가 읽는 큐 |

**버그 수정 (False인 경우)**:

```python
# _init_modules()에서 반드시 self._packet_queue 전달:
self._processor = PacketProcessor(
    self._packet_queue,  # ← 새 객체 아닌 self._packet_queue!
    ...
)
```

---

### 2.2 Store 객체 동일성

```python
store_provider = provider._store
store_processor = provider._processor._store

print("=== Store 동일성 검사 ===")
print(f"동일 객체 여부: {store_provider is store_processor}")
```

---

## 🔧 STEP 3: 패킷 수신 확인

### 3.1 Queue에 패킷이 들어오는지

```python
from ugv_mon.data.live_provider import LiveDataProvider
import time

provider = LiveDataProvider(interface="eno2")
provider.start_capture()

print("3초간 패킷 수신 대기...")
time.sleep(3)

# 큐 상태 확인
queue_size = provider._packet_queue.size() if provider._packet_queue else "None"
print(f"Queue 크기: {queue_size}")

provider.stop_capture()
```

**결과 해석**:
| 결과 | 의미 | 해결 방법 |
|------|------|----------|
| `> 0` | ✅ 패킷 수신 중 | Step 4로 |
| `0` | ⚠️ 패킷 없음 | 네트워크/인터페이스 확인 |
| `None` | ❌ Queue 미초기화 | Step 1로 돌아가기 |

---

### 3.2 Sniffer 콜백 확인

```python
from ugv_mon.data.live_provider import LiveDataProvider

provider = LiveDataProvider(interface="eno2")
provider.start_capture()

print("=== Sniffer 콜백 확인 ===")
if provider._sniffer:
    # sniffer의 콜백 함수
    callback = getattr(provider._sniffer, '_callback', None)
    print(f"Sniffer callback: {callback}")
    print(f"Queue.put: {provider._packet_queue.put}")
    print(f"동일 여부: {callback == provider._packet_queue.put}")
else:
    print("❌ Sniffer가 None!")

provider.stop_capture()
```

---

## 🔧 STEP 4: 패킷 처리 확인

### 4.1 Processor가 패킷을 처리하는지

```python
from ugv_mon.data.live_provider import LiveDataProvider
import time

provider = LiveDataProvider(interface="eno2")
provider.start_capture()

time.sleep(3)

# 수동으로 process_pending 호출
print("=== Processor 동작 확인 ===")
if provider._processor:
    result = provider._processor.process_pending()
    print(f"처리된 패킷 수: {result.count}")
    print(f"파싱 성공: {result.success_count}")
    print(f"체크섬 실패: {result.checksum_fail_count}")
else:
    print("❌ _processor가 None!")

provider.stop_capture()
```

**결과 해석**:
| 결과 | 의미 |
|------|------|
| `count > 0` | ✅ 정상 처리 |
| `count = 0` | Queue가 비었거나 객체 불일치 (Step 2 재확인) |

---

### 4.2 Store에 레코드가 쌓이는지

```python
from ugv_mon.data.live_provider import LiveDataProvider
import time

provider = LiveDataProvider(interface="eno2")
provider.start_capture()

time.sleep(3)

# update_data 호출 (실제 콜백 동작 시뮬레이션)
data = provider.update_data({})

print("=== Store 레코드 확인 ===")
if provider._store:
    print(f"레코드 수: {provider._store.record_count}")
else:
    print("❌ _store가 None!")

print(f"combinedData 길이: {len(data.get('combinedData', []))}")
print(f"capturePps: {data.get('capturePps')}")

provider.stop_capture()
```

---

## 🔧 STEP 5: Dash 콜백 검증

### 5.1 콜백 등록 확인

```python
from ugv_mon.app import create_app

app = create_app()

print("=== 등록된 콜백 ===")
for key in app.callback_map:
    print(f"  {key}")
```

**반드시 있어야 하는 콜백**:

- `dashboard-data.data`
- `status-chips.children`
- `kpi-cards.children`
- `operational-status.children`
- `comm-quality-chart.figure`

---

### 5.2 콜백 함수가 provider를 참조하는지

`update_callbacks.py`에서 `register_callbacks(app, data_provider=...)` 호출 시
`data_provider`가 `LiveDataProvider` 인스턴스인지 확인.

---

## 🔧 STEP 6: 브라우저 디버깅

### 6.1 Network 탭 확인

1. 브라우저에서 대시보드 열기
2. **F12 → Network 탭** 열기
3. Filter에 `_dash` 입력
4. **2초마다 `_dash-update-component` POST 요청** 확인

**확인 사항**:
| 상태 | 의미 | 해결 |
|------|------|------|
| 요청 없음 | Interval 안 작동 | `interval-component` ID 확인 |
| 요청 있고 200 | 서버 응답 정상 | Response 내용 확인 |
| 요청 있고 500 | 서버 에러 | 터미널 에러 로그 확인 |

### 6.2 Response 데이터 확인

1. `_dash-update-component` 요청 클릭
2. **Response 탭** 선택
3. `combinedData`, `capturePps` 등 값 확인

---

## 🔧 STEP 7: 로그 삽입 디버깅

### 7.1 live_provider.py에 로그 추가

```python
import logging
logger = logging.getLogger(__name__)

def update_data(self, prev_data: Dict) -> Dict:
    logger.info("========== update_data 호출 ==========")

    with self._lock:
        # 1. Processor 확인
        if self._processor:
            result = self._processor.process_pending()
            logger.info(f"[1] 처리된 패킷: {result.count}")
        else:
            logger.error("❌ self._processor가 None!")

        # 2. Store 확인
        if self._store:
            logger.info(f"[2] Store 레코드: {self._store.record_count}")
        else:
            logger.error("❌ self._store가 None!")

        # 3. 빌드 결과 확인
        state = self._build_state()
        logger.info(f"[3] combinedData: {len(state.get('combinedData', []))}")
        logger.info(f"[4] capturePps: {state.get('capturePps')}")

        return state
```

### 7.2 로그 레벨 설정

```python
# run.py 또는 app.py 상단에:
import logging
logging.basicConfig(level=logging.INFO)
```

---

## 🔧 STEP 8: 코드 비교 확인

### 8.1 핵심 변수명 확인

```python
# 올바른 변수명:
self._packet_queue    # PacketQueue
self._store           # PacketStore
self._processor       # PacketProcessor
self._sniffer         # PacketSniffer
```

### 8.2 핵심 메서드 존재 확인

```python
import inspect
from ugv_mon.data.live_provider import LiveDataProvider

# 반드시 있어야 하는 메서드들
methods = ['_init_modules', 'update_data', '_build_state',
           '_build_ui_state', '_build_stats_state']

for m in methods:
    has_method = hasattr(LiveDataProvider, m)
    print(f"{m}: {'✅' if has_method else '❌'}")
```

---

## 📋 최종 체크리스트

| #   | 항목                     | 확인 방법 | 결과 |
| --- | ------------------------ | --------- | ---- |
| 1   | `_init_modules()` 호출됨 | Step 1.2  | ☐    |
| 2   | `_store` ≠ None          | Step 1.1  | ☐    |
| 3   | `_processor` ≠ None      | Step 1.1  | ☐    |
| 4   | `_packet_queue` ≠ None   | Step 1.1  | ☐    |
| 5   | Queue 동일성 (`True`)    | Step 2.1  | ☐    |
| 6   | Store 동일성 (`True`)    | Step 2.2  | ☐    |
| 7   | Queue에 패킷 수신        | Step 3.1  | ☐    |
| 8   | Processor 처리 count > 0 | Step 4.1  | ☐    |
| 9   | Store record_count > 0   | Step 4.2  | ☐    |
| 10  | combinedData 길이 > 0    | Step 4.2  | ☐    |
| 11  | 브라우저 POST 요청 확인  | Step 6.1  | ☐    |
| 12  | Response에 데이터 있음   | Step 6.2  | ☐    |

---

## 🎯 원인별 해결 방법 요약

### 원인 1: `_init_modules()` 호출 누락

```python
# __init__ 마지막에 추가
self._init_modules()
```

### 원인 2: Queue 객체 불일치

```python
# _init_modules()에서 self._packet_queue 사용
self._processor = PacketProcessor(
    self._packet_queue,  # ← 반드시 인스턴스 변수!
    self._parser,
    self._store
)
```

### 원인 3: 변수명 오타

```python
# 올바른 이름 사용
self._packet_queue  (O)  vs  self._queue   (X)
self._store        (O)  vs  self._pkt_store (X)
```

### 원인 4: 메서드명 불일치

```python
# update_data()에서 호출하는 메서드명 확인
return self._build_state()  # ← 메서드가 존재해야 함
```

### 원인 5: Import 경로 오류

```python
# 직접 import 사용 시 경로 확인
from ugv_mon.data.packet_store import PacketStore, PacketRecord
from ugv_mon.capture.packet_processor import PacketProcessor
```

---

## 🚀 빠른 문제 해결 순서

1. **Step 1.1 실행** → 하나라도 None이면 `_init_modules()` 확인
2. **Step 2.1 실행** → False면 객체 생성 코드 확인
3. **Step 4.2 실행** → combinedData 길이 확인
4. **Step 6 실행** → 브라우저 Network 탭 확인
5. **Step 7 실행** → 로그 추가 후 터미널 출력 확인

**이 순서대로 진행하면 30분 내에 원인 파악 가능!**
