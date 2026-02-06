# UGV-MON 리팩토링 마이그레이션 가이드

> **최종 업데이트**: 2026-02-06

이 문서는 로컬 환경에서 수행된 리팩토링 내용을 회사 코드에 적용할 때 참고합니다.

---

## 1. 주요 변경 내역

### 1.1 Core 패키지 통합 (중복 제거)
- **배경**: `data/models.py`와 `parser/models.py`에 동일/유사한 클래스가 중복 정의
- **조치**: `ugv_mon/core/models.py` 하나로 통합, 모든 의존성을 이곳으로 연결
- **Import 수정 예시**:
  ```python
  # Before
  from ..data.models import LogEntry
  from ..parser.models import ICDHeader
  from ..config import config

  # After
  from ..core import LogEntry, ICDHeader, config
  ```

### 1.2 Panels 단일 파일 유지
- **결정**: `panels/` 폴더 분리는 import 복잡성만 증가시켜 **롤백**.
- **현재**: `layouts/panels.py` 단일 파일로 10개 패널 함수 모두 포함.
- `main_layout.py`에서 `from .panels import ...` 그대로 사용.

### 1.3 P99 및 인터페이스 전환 기능 삭제
- **P99**: 회사에서 미사용. 모든 P99 관련 코드/UI/문서 제거. P95만 유지.
- **인터페이스 드롭다운**: `switch_interface()`, `get_available_interfaces()` 삭제.
  인터페이스는 CLI 또는 환경변수로 설정.

### 1.4 미사용 모듈 삭제
- `analysis/stats_calculator.py` -> PacketStore가 완전 대체
- `analysis/anomaly_detector.py` -> 프로덕션 미사용
- `analysis/__init__.py` -> 빈 모듈
- `EmergencyStatus` 클래스 -> `OperationalPayload.get_emergency_dict()`로 대체

### 1.5 변수명/함수명 직관화

| Before | After | 이유 |
|--------|-------|------|
| `_build_state()` | `_build_dashboard_data()` | 무엇을 빌드하는지 명확 |
| `_build_connection_state()` | `_build_connection_info()` | state가 너무 범용 |
| `_build_stats_state()` | `_build_kpi_metrics()` | KPI 용도 명확 |
| `_build_ui_state()` | `_build_ui_display_data()` | UI 렌더링용 명확 |
| `_last_by_code` | `_prev_packet_by_msgcode` | 무엇의 마지막인지 명확 |
| `_loss_by_code` | `_packet_loss_by_msgcode` | 손실 카운트 명확 |
| `ProcessedResult` | `BatchProcessResult` | 배치 처리 결과 명확 |
| `CaptureStats.get_pps()` | `get_capture_pps()` | PacketStore.get_pps()와 구분 |

### 1.6 라이브러리 호환성 (Dash Mantine Components)
- **중요**: 로컬 환경은 **DMC 2.4.1** 버전을 사용 중입니다.
- `dmc.Group`: `position="apart"` (구버전) -> `justify="space-between"` (2.x)
- `dmc.Stack`/`dmc.Group`: `spacing="xs"` (구버전) -> `gap="xs"` (2.x)
- Tabs 컴포넌트: `dmc.Tab` (구버전) -> `dmc.TabsTab` (2.x)

---

## 2. 마이그레이션 체크리스트

1. **파일 구조 동기화**
   - [ ] `ugv_mon/core/` 폴더 생성 및 파일 복사
   - [ ] `ugv_mon/analysis/` 폴더 삭제 (PacketStore로 대체됨)
   - [ ] `ugv_mon/data/models.py`, `ugv_mon/parser/models.py` 삭제 (core로 이동 확인 후)
   - [ ] `ugv_mon/config.py`, `ugv_mon/constants.py` 삭제 (core로 이동 확인 후)

2. **Import 경로 전체 치환**
   - `ugv_mon.config` -> `ugv_mon.core`
   - `ugv_mon.constants` -> `ugv_mon.core`
   - `ugv_mon.data.models` -> `ugv_mon.core`
   - `ugv_mon.parser.models` -> `ugv_mon.core`
   - `ugv_mon.analysis` -> 삭제 (PacketStore 사용)

3. **라이브러리 버전 확인**
   - `pip show dash-mantine-components`로 버전 확인
   - **2.x 버전**: 현재 코드 그대로 사용
   - **0.12.x 버전**: 롤백 필요

4. **실행 테스트**
   - `python run.py` 실행 후 `ImportError` 없는지 확인
