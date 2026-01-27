# UGV-MON 트러블슈팅 가이드

회사 환경에서 발생할 수 있는 문제들과 해결 방법을 정리합니다.

---

## 1. Callback Output 에러

### 증상
```
a nonexistent object was used in an Output
```
- 2초마다 터미널에 에러 출력
- UI가 실시간 업데이트 안됨

### 원인
콜백의 Output에서 참조하는 컴포넌트 ID가 레이아웃에 없음.

### 확인할 컴포넌트 ID

| ID | 정의 파일 | 확인할 코드 |
|----|----------|------------|
| `status-chips` | `layouts/header.py` | `id="status-chips"` |
| `kpi-cards` | `layouts/main_layout.py` | `id="kpi-cards"` |
| `operational-status` | `layouts/panels.py` | `id="operational-status"` |
| `emergency-status` | `layouts/panels.py` | `id="emergency-status"` |
| `device-grid-container` | `layouts/panels.py` | `id="device-grid-container"` |
| `comm-quality-chart` | `layouts/panels.py` | `id="comm-quality-chart"` |
| `availability-timeline` | `layouts/panels.py` | `id="availability-timeline"` |
| `log-table` | `components/log_table.py` | `id="log-table"` |
| `log-table-title` | `components/log_table.py` | `id="log-table-title"` |
| `current-pps-display` | `layouts/panels.py` | `id="current-pps-display"` |
| `current-jitter-display` | `layouts/panels.py` | `id="current-jitter-display"` |

### 디버깅 방법

```bash
# 레이아웃 생성 테스트
python3 -c "
from ugv_mon.data.mock_data import MockDataGenerator
from ugv_mon.layouts.main_layout import create_main_layout
mock = MockDataGenerator()
layout = create_main_layout(mock.generate_initial_data(), mock.get_logs())
print('✓ Layout created successfully')
"
```

### 해결 방법
1. 해당 파일이 제대로 복사되었는지 확인
2. `id=` 부분이 정확히 일치하는지 확인
3. 오타 및 누락 확인

---

## 2. Live 모드 `.get` 에러

### 증상
```
AttributeError: 'NoneType' object has no attribute 'get'
```
- Mock 모드는 정상 동작
- Live 모드에서만 localhost 화면에 에러 표시

### 원인
Live 모드와 Mock 모드의 데이터 구조 차이. Live에서 일부 필드가 None이거나 빈 값.

### 확인할 파일
`ugv_mon/data/live_provider.py` - `_build_state()` 함수

### 디버깅 방법

```python
# run.py 상단에 추가
import logging
logging.basicConfig(
    level=logging.DEBUG,  # INFO → DEBUG로 변경
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
```

```bash
# 상세 로그로 실행
python3 run.py --mode live 2>&1 | tee live_debug.log
```

### 해결 방법

`live_provider.py`에서 None 체크 추가:
```python
def _build_state(self, devices: list) -> Dict:
    # devices가 None이거나 빈 리스트인 경우 기본값
    if not devices:
        devices = [{"name": n, "connected": False} for n in DEVICE_NAMES]
    
    # ... 나머지 코드
```

---

## 3. werkzeug 로그가 안 나옴

### 증상
```
# 이 로그들이 터미널에 안 나옴
21:35:21 [INFO] werkzeug: 127.0.0.1 - - [27/Jan/2026 21:35:21] "GET / HTTP/1.1" 200 -
```

### 원인
`run.py`의 logging 설정 누락 또는 레벨 설정 문제.

### 확인할 코드
`run.py` 25~29줄:
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
```

### 해결 방법

**방법 1**: run.py에 logging 설정 확인
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
```

**방법 2**: werkzeug 로거 명시적 설정
```python
# run.py main() 함수 시작 부분에 추가
logging.getLogger('werkzeug').setLevel(logging.INFO)
```

**방법 3**: 환경변수로 로그 레벨 설정
```bash
export FLASK_ENV=development
python3 run.py --mode mock
```

---

## 4. setcap 권한 설정 (sudo 없이 Live 모드)

### 회사 환경에서 sudo 없이 패킷 캡처

```bash
# Python 바이너리 경로 확인
which python3
# 예: /usr/bin/python3

# CAP_NET_RAW 권한 부여 (관리자가 한 번만 실행)
sudo setcap cap_net_raw+ep /usr/bin/python3

# 권한 확인
getcap /usr/bin/python3
# 출력: /usr/bin/python3 = cap_net_raw+ep

# 이제 sudo 없이 실행 가능
python3 run.py --mode live --interface eno2
```

### 주의사항
- 가상환경 사용 시 해당 venv의 python에 권한 부여 필요
- 보안상 이유로 회사 정책에 따라 관리자 승인 필요할 수 있음

---

## 5. 파일 무결성 확인

### 집과 회사 파일 비교

```bash
# 집에서 해시 생성
cd /path/to/ugv_mon
find ugv_mon -name "*.py" -exec md5sum {} \; | sort > ~/home_hashes.txt

# 회사에서 동일하게 실행
find ugv_mon -name "*.py" -exec md5sum {} \; | sort > ~/work_hashes.txt

# 차이점 확인
diff ~/home_hashes.txt ~/work_hashes.txt
```

### 핵심 파일 체크리스트

복사 후 반드시 확인할 파일:
- [ ] `run.py` (logging.basicConfig 포함)
- [ ] `ugv_mon/app.py`
- [ ] `ugv_mon/layouts/main_layout.py`
- [ ] `ugv_mon/layouts/panels.py`
- [ ] `ugv_mon/layouts/header.py`
- [ ] `ugv_mon/components/log_table.py`
- [ ] `ugv_mon/callbacks/update_callbacks.py`
- [ ] `ugv_mon/data/live_provider.py`
- [ ] `ugv_mon/data/mock_data.py`

---

## 6. 빠른 진단 스크립트

```python
#!/usr/bin/env python3
"""UGV-MON 환경 진단 스크립트."""

import sys
import os

def check_imports():
    """필수 모듈 import 테스트."""
    print("=== Import 테스트 ===")
    try:
        from ugv_mon.app import create_app
        print("✓ ugv_mon.app")
    except Exception as e:
        print(f"✗ ugv_mon.app: {e}")
    
    try:
        from ugv_mon.data.mock_data import MockDataGenerator
        print("✓ MockDataGenerator")
    except Exception as e:
        print(f"✗ MockDataGenerator: {e}")
    
    try:
        from ugv_mon.data.live_provider import LiveDataProvider
        print("✓ LiveDataProvider")
    except Exception as e:
        print(f"✗ LiveDataProvider: {e}")

def check_layout():
    """레이아웃 생성 테스트."""
    print("\n=== 레이아웃 테스트 ===")
    try:
        from ugv_mon.data.mock_data import MockDataGenerator
        from ugv_mon.layouts.main_layout import create_main_layout
        mock = MockDataGenerator()
        data = mock.generate_initial_data()
        logs = mock.get_logs()
        layout = create_main_layout(data, logs)
        print("✓ 레이아웃 생성 성공")
    except Exception as e:
        print(f"✗ 레이아웃 생성 실패: {e}")

def check_callbacks():
    """콜백 등록 테스트."""
    print("\n=== 콜백 테스트 ===")
    try:
        from ugv_mon.app import create_app
        app = create_app()
        print(f"✓ 앱 생성 성공 (콜백 {len(app.callback_map)}개)")
    except Exception as e:
        print(f"✗ 앱 생성 실패: {e}")

if __name__ == "__main__":
    check_imports()
    check_layout()
    check_callbacks()
    print("\n진단 완료.")
```

저장: `scripts/diagnose.py`

실행:
```bash
python3 scripts/diagnose.py
```

---

## 7. 자주 묻는 질문

### Q: Mock 모드는 되는데 Live 모드만 안 돼요
A: Live 모드는 추가로 scapy 라이브러리와 네트워크 권한이 필요합니다.
```bash
pip install scapy
# 그리고 setcap 또는 sudo 필요
```

### Q: 차트가 업데이트 안 돼요
A: `interval-component`가 레이아웃에 있는지 확인하세요. `layouts/main_layout.py`에서:
```python
dcc.Interval(
    id="interval-component",
    interval=config.ui.poll_interval_ms,
    n_intervals=0,
),
```

### Q: 로그 테이블이 안 나와요
A: dash-ag-grid가 설치되어 있는지 확인:
```bash
pip install dash-ag-grid
```
