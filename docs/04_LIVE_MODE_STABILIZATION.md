# Live 모드 안정화 및 UI 제어 기능

## 개요

Live 모드의 환경변수 리셋 문제를 해결하고, UI에서 실시간으로 인터페이스 전환 및 연결 상태 제어 기능을 추가했습니다.

> **업데이트 (2026-01-25)**: 진입점이 `run.py` 하나로 통합되었습니다.

---

## 실행 방법

### Mock 모드
```bash
python3 run.py
python3 run.py --mode mock
```

### Live 모드
```bash
# CLI 인자 방식 (권장)
sudo python3 run.py --mode live
sudo python3 run.py --mode live --interface lo
sudo python3 run.py --mode live --interface eno2

# 환경변수 방식 (하위 호환)
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo
sudo -E python3 run.py
```

---

## 변경사항 요약

### 1. 진입점 통합

**변경 전**: `run_mock.py`, `run_live.py` 분리
**변경 후**: `run.py` 하나로 CLI 인자 지원

```bash
python3 run.py --help

options:
  --mode {mock,live}, -m    실행 모드 (기본: mock)
  --interface, -i           네트워크 인터페이스 (기본: lo)
  --port, -p                서버 포트 (기본: 8050)
  --debug                   디버그 모드 활성화
```

### 2. 모듈 레벨 초기화 코드 제거

#### `ugv_mon/app.py`
- 모듈 레벨 `app = create_app()` 제거
- `create_app()` 함수만 유지 (팩토리 함수)
- run.py에서 명시적으로 호출

#### `ugv_mon/callbacks/update_callbacks.py`
- 모듈 레벨 `_data_provider` 전역 변수 제거
- 클로저(Closure) 패턴으로 의존성 캡처
- `DataProviderProtocol` 추가 (Duck Typing)

### 3. LiveDataProvider 제어 메서드

#### `switch_interface(new_interface: str) -> bool`
- 인터페이스 전환 기능
- 기존 캡처 중지 → 새 인터페이스 설정 → 캡처 재시작
- 실패 시 이전 인터페이스로 복구

#### `toggle_connection() -> bool`
- 연결 상태 토글 (시작/중지)
- `_is_connected` 상태에 따라 자동 처리

#### `get_available_interfaces() -> List[str]`
- 사용 가능한 네트워크 인터페이스 목록 반환
- Linux: `ip link show` 명령어로 동적 조회
- macOS: `networksetup -listallhardwareports` 명령어로 동적 조회
- 실패 시 폴백: `["lo", "eno2", "eno3"]`

### 4. UI 제어 기능

#### 헤더 레이아웃 (`ugv_mon/layouts/header.py`)

**연결상태 토글 버튼**
```python
dmc.Button(
    id="connection-toggle-btn",
    variant="filled" if is_connected else "outline",
    color="green" if is_connected else "red",
)
```

**인터페이스 드롭다운**
```python
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

---

## UI에서 제어

1. **연결 상태 토글**
   - 헤더의 "연결상태" 버튼 클릭
   - Live 모드에서만 활성화
   - 클릭 시 캡처 시작/중지

2. **인터페이스 전환**
   - 헤더의 "인터페이스" 드롭다운 선택
   - Live 모드에서만 활성화
   - 선택 시 자동으로 캡처 재시작

---

## 주의사항

1. **Mock 모드 호환성**
   - Mock 모드에서는 UI 제어 기능이 비활성화됨
   - 콜백에서 `hasattr` 체크로 안전하게 처리

2. **스레드 안전성**
   - 인터페이스 전환 시 `Lock` 사용하여 동시 접근 방지
   - 기존 캡처 스레드 정리 후 새 스레드 시작

3. **에러 처리**
   - 인터페이스 전환 실패 시 이전 상태로 복구
   - 사용자에게 명확한 에러 메시지 제공 (로거)

4. **권한 요구사항**
   - Live 모드는 root 권한 필요
   - 권한 오류 시 `sudo` 사용 또는 `setcap` 설정

---

## 테스트 체크리스트

- [ ] `python3 run.py` - Mock 모드 정상 동작 확인
- [ ] `sudo python3 run.py --mode live` - Live 모드 정상 동작 확인
- [ ] `sudo python3 run.py --mode live -i eno2` - 인터페이스 지정 확인
- [ ] UI에서 연결상태 버튼 클릭 시 시작/중지 확인
- [ ] UI에서 인터페이스 드롭다운 변경 시 실제 전환 확인
- [ ] 상태가 UI에 즉시 반영되는지 확인
- [ ] Mock 모드에서 UI 제어 기능이 비활성화되는지 확인

---

## 수정된 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `run.py` | CLI 인자 지원 (`--mode`, `--interface`, `--port`) |
| `ugv_mon/app.py` | 모듈 레벨 app 인스턴스 제거 |
| `ugv_mon/callbacks/update_callbacks.py` | 전역 상태 제거, 클로저 패턴 적용 |
| `ugv_mon/data/live_provider.py` | switch_interface(), toggle_connection(), get_available_interfaces() |
| `ugv_mon/layouts/header.py` | 연결상태 버튼 및 인터페이스 드롭다운 |
