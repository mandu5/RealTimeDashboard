# Live 모드 안정화 및 UI 제어 기능 추가

## 개요

4주차 작업으로 Live 모드의 환경변수 리셋 문제를 해결하고, UI에서 실시간으로 인터페이스 전환 및 연결 상태 제어 기능을 추가했습니다.

## 변경사항 요약

### 1. 실행 스크립트 분리

**문제**: 환경변수를 변경해도 모듈 레벨에서 이미 초기화된 인스턴스가 사용되어 반영되지 않음

**해결**: `run.py`를 `run_mock.py`와 `run_live.py`로 완전 분리

#### 새로 생성된 파일

- **`run_mock.py`**: Mock 모드 전용 실행 스크립트
  ```bash
  python3 run_mock.py
  ```

- **`run_live.py`**: Live 모드 전용 실행 스크립트
  ```bash
  # 기본 인터페이스 (lo)
  sudo python3 run_live.py
  
  # 인터페이스 지정
  sudo python3 run_live.py --interface eno2
  sudo python3 run_live.py --interface eno3
  ```

### 2. 모듈 레벨 초기화 코드 제거

#### `ugv_mon/app.py`
- 모듈 레벨 `app = create_app()` 제거
- `create_app()` 함수만 유지 (팩토리 함수)
- 각 run 스크립트에서 명시적으로 호출

#### `ugv_mon/callbacks/update_callbacks.py`
- 모듈 레벨 `_data_provider = get_data_provider()` 제거
- `register_callbacks(app, data_provider=None)`에 `data_provider` 인자 추가
- `app.py`에서 `create_app()` 시점에 `data_provider` 생성 후 전달

### 3. LiveDataProvider 제어 메서드 추가

#### `switch_interface(new_interface: str) -> bool`
- 인터페이스 전환 기능
- 기존 캡처 중지 → 새 인터페이스 설정 → 캡처 재시작
- 실패 시 이전 인터페이스로 복구

#### `toggle_connection() -> bool`
- 연결 상태 토글 (시작/중지)
- `_is_connected` 상태에 따라 자동 처리

#### `get_available_interfaces() -> List[str]`
- 사용 가능한 네트워크 인터페이스 목록 반환
- 현재: `["lo", "eno2", "eno3"]` (하드코딩)
- 향후: 시스템 명령어로 동적 조회 가능

### 4. UI 제어 기능 추가

#### 헤더 레이아웃 변경 (`ugv_mon/layouts/header.py`)

**변경 전**: 읽기 전용 상태 칩
```python
create_status_chip("연결상태", "연결됨", "success")
create_status_chip("인터페이스", "lo", "default")
```

**변경 후**: 클릭 가능한 버튼 및 드롭다운
```python
# 연결상태 토글 버튼
dmc.Button(
    id="connection-toggle-btn",
    variant="filled" if is_connected else "outline",
    color="green" if is_connected else "red",
)

# 인터페이스 드롭다운
dmc.Select(
    id="interface-select",
    value=current_interface,
    data=[
        {"value": "lo", "label": "lo (Local)"},
        {"value": "eno2", "label": "eno2"},
        {"value": "eno3", "label": "eno3"},
    ],
)
```

#### 콜백 추가 (`ugv_mon/callbacks/update_callbacks.py`)

**인터페이스 전환 콜백**
```python
@app.callback(
    Output("dashboard-data", "data", allow_duplicate=True),
    Input("interface-select", "value"),
    State("dashboard-data", "data"),
    prevent_initial_call=True,
)
def on_interface_change(new_interface: str, current_data: Dict):
    """인터페이스 변경 처리."""
    if isinstance(_data_provider, LiveDataProvider):
        success = _data_provider.switch_interface(new_interface)
        if success:
            return _data_provider.update_data(current_data)
    raise PreventUpdate
```

**연결 상태 토글 콜백**
```python
@app.callback(
    [
        Output("dashboard-data", "data", allow_duplicate=True),
        Output("connection-toggle-btn", "children", allow_duplicate=True),
        Output("connection-toggle-btn", "variant", allow_duplicate=True),
        Output("connection-toggle-btn", "color", allow_duplicate=True),
    ],
    Input("connection-toggle-btn", "n_clicks"),
    State("dashboard-data", "data"),
    prevent_initial_call=True,
)
def on_connection_toggle(n_clicks: int, current_data: Dict):
    """연결 상태 토글 처리."""
    if isinstance(_data_provider, LiveDataProvider):
        success = _data_provider.toggle_connection()
        if success:
            # 데이터 및 버튼 상태 업데이트
            ...
```

## 사용 방법

### Mock 모드 실행
```bash
python3 run_mock.py
```

### Live 모드 실행
```bash
# 기본 인터페이스 (lo)
sudo python3 run_live.py

# 인터페이스 지정
sudo python3 run_live.py --interface eno2
sudo python3 run_live.py --interface eno3
```

### UI에서 제어

1. **연결 상태 토글**
   - 헤더의 "연결상태" 버튼 클릭
   - Live 모드에서만 활성화
   - 클릭 시 캡처 시작/중지

2. **인터페이스 전환**
   - 헤더의 "인터페이스" 드롭다운 선택
   - Live 모드에서만 활성화
   - 선택 시 자동으로 캡처 재시작

## 주의사항

1. **Mock 모드 호환성**
   - Mock 모드에서는 UI 제어 기능이 비활성화됨
   - 콜백에서 `isinstance(_data_provider, LiveDataProvider)` 체크로 안전하게 처리

2. **스레드 안전성**
   - 인터페이스 전환 시 `Lock` 사용하여 동시 접근 방지
   - 기존 캡처 스레드 정리 후 새 스레드 시작

3. **에러 처리**
   - 인터페이스 전환 실패 시 이전 상태로 복구
   - 사용자에게 명확한 에러 메시지 제공 (로거)

4. **권한 요구사항**
   - Live 모드는 root 권한 필요
   - 권한 오류 시 `sudo` 사용 또는 `setcap` 설정

## 파일 변경 목록

### 새로 생성된 파일
- `run_mock.py` - Mock 모드 실행 스크립트
- `run_live.py` - Live 모드 실행 스크립트

### 수정된 파일
- `ugv_mon/app.py` - 모듈 레벨 app 인스턴스 제거
- `ugv_mon/callbacks/update_callbacks.py` - 모듈 레벨 _data_provider 제거, UI 제어 콜백 추가
- `ugv_mon/data/live_provider.py` - switch_interface(), toggle_connection(), get_available_interfaces() 메서드 추가
- `ugv_mon/layouts/header.py` - 연결상태 버튼 및 인터페이스 드롭다운으로 변경

## 테스트 체크리스트

- [ ] `python3 run_mock.py` - Mock 모드 정상 동작 확인
- [ ] `sudo python3 run_live.py` - Live 모드 정상 동작 확인
- [ ] `sudo python3 run_live.py --interface eno2` - 인터페이스 지정 확인
- [ ] UI에서 연결상태 버튼 클릭 시 시작/중지 확인
- [ ] UI에서 인터페이스 드롭다운 변경 시 실제 전환 확인
- [ ] 상태가 UI에 즉시 반영되는지 확인
- [ ] Mock 모드에서 UI 제어 기능이 비활성화되는지 확인

## 향후 개선 사항

1. **동적 인터페이스 목록**
   - 시스템 명령어(`ip link show`)로 인터페이스 목록 동적 조회
   - `get_available_interfaces()` 메서드 개선

2. **에러 알림 UI**
   - 인터페이스 전환 실패 시 사용자에게 알림 표시
   - Dash의 `dcc.Store` 또는 `dmc.Notification` 활용

3. **연결 상태 표시 개선**
   - 연결 중/연결 끊김/에러 상태를 더 명확하게 표시
   - 아이콘 추가 고려
