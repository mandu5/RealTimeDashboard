# 리팩토링 변경 이력 (2026-01-25)

본 문서는 UGV-MON 코드 리뷰에서 발견된 모든 이슈를 해결한 변경사항을 기록합니다.

---

## 요약

| 구분 | 해결 건수 | 주요 변경 |
|------|----------|----------|
| Critical | 5건 | 진입점 통합, 전역상태 제거, 보안 수정, 리소스 누수 |
| Major | 5건 | 상수 모듈, 에러 핸들링, 단위 테스트 추가 |
| Minor | 4건 | 스타일 모듈, 로깅 레벨, Type hints 개선 |

---

## Critical Issues

### 1. 진입점 통합 (Entry Point Consolidation)
- **삭제**: `run_live.py`, `run_mock.py`
- **수정**: `run.py` - CLI 인자 지원 (`--mode`, `--interface`, `--port`)

```bash
# 새 방식 (통합 CLI)
python3 run.py --mode mock           # Mock 모드
python3 run.py --mode live -i lo     # Live 모드
python3 run.py --help                # 도움말
```

### 2. 전역 상태 제거 (Global State)
- **수정**: `ugv_mon/callbacks/update_callbacks.py`
- 전역 변수 `_data_provider` 제거
- 클로저(Closure) 패턴으로 의존성 캡처
- `DataProviderProtocol` 추가 (Duck Typing)

### 3. Debug 기본값 변경
- **수정**: `ugv_mon/config.py`
- `debug: bool = True` → `debug: bool = False`

### 4. 리소스 누수 수정
- **수정**: `ugv_mon/data/live_provider.py`
- `start_capture()` 시작 전 `_cleanup_sniffer()` 호출
- 동적 인터페이스 목록 조회 (`subprocess` 활용)

### 5. ICD 파서 시퀀스 (확인 완료)
- ICD 명세 문서 확인 결과, `data[3]`을 시퀀스로 사용하는 것이 올바름
- 변경 없음 (명세 준수)

---

## Major Issues

### 6. 상수 모듈 생성 (DRY)
- **신규**: `ugv_mon/constants.py`
- 장치 목록, 시퀀스 상수, ICD 크기, 라벨 통합
- 중복 제거: `icd_parser.py`, `live_provider.py`, `mock_data.py`, `stats_calculator.py`

### 7. 에러 핸들링 강화
- **수정**: `ugv_mon/data/live_provider.py`
- `_process_packet()`: `result.header` None 체크 추가
- 구체적 예외 타입 처리 (`PermissionError`, `OSError`)

### 8. 매직 넘버 제거
- `MAX_SEQUENCE = 256` → 상수 모듈
- `EXPECTED_PPS = 1000` → 상수 모듈
- `DEFAULT_INITIAL_SEQUENCE = 49195` → 상수 모듈

### 9. 하드코딩 인터페이스 목록 개선
- **수정**: `live_provider.py`의 `get_available_interfaces()`
- Linux/macOS 동적 조회 (`ip link`, `networksetup`)

### 10. 단위 테스트 추가
- **신규**: `tests/test_icd_parser.py` (16개 테스트)
- **신규**: `tests/test_stats_calculator.py` (20개 테스트)
- **총 36개 테스트 통과**

```bash
# 테스트 실행
pip install pytest
python -m pytest tests/ -v
```

---

## Minor Issues

### 11. 스타일 모듈
- **신규**: `ugv_mon/styles.py`
- 색상 팔레트, 폰트 설정, 공통 스타일 함수

### 12. 로깅 레벨 수정
- **수정**: `ugv_mon/capture/sniffer.py`
- `logger.debug()` → `logger.warning()` (패킷 처리 에러)

### 13. Type Hints 개선
- `DataProviderProtocol` 추가
- 함수 반환 타입 명시 개선

### 14. requirements.txt
- 추가: `pytest>=7.0.0`

---

## 삭제된 파일

| 파일 | 이유 |
|------|------|
| `run_live.py` | `run.py`로 통합 |
| `run_mock.py` | `run.py`로 통합 |
| `venv/` | 불필요 (conda 환경 사용) |

---

## 신규 파일

| 파일 | 용도 |
|------|------|
| `ugv_mon/constants.py` | 상수 정의 (DRY) |
| `ugv_mon/styles.py` | UI 스타일 상수 |
| `tests/__init__.py` | 테스트 패키지 |
| `tests/test_icd_parser.py` | ICD 파서 테스트 |
| `tests/test_stats_calculator.py` | 통계 계산기 테스트 |

---

## 사용법

```bash
# Mock 모드 (기본)
python3 run.py

# Live 모드
sudo python3 run.py --mode live --interface lo

# 환경변수 방식 (하위 호환)
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo
sudo -E python3 run.py

# 단위 테스트
python -m pytest tests/ -v
```
