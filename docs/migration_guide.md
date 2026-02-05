# UGV-MON 리팩토링 마이그레이션 가이드

이 문서는 로컬 환경에서 수행된 대규모 리팩토링 내용을 회사 코드에 적용할 때 참고할 수 있도록 작성되었습니다.

---

## 1. 폴더 구조 변경 (Before & After)

가장 큰 변화는 `core` 패키지 신설과 `layouts/panels.py`의 분리입니다.

### 📂 변경 전
```
ugv_mon/
├── config.py                 # 🔴 core/ 이동
├── constants.py              # 🔴 core/ 이동
├── data/
│   ├── models.py             # 🔴 core/models.py로 통합 (삭제)
│   └── ...
├── parser/
│   ├── models.py             # 🔴 core/models.py로 통합 (삭제)
│   └── ...
└── layouts/
    └── panels.py             # 🔴 panels/ 폴더로 분리 (삭제)
```

### 📂 변경 후
```
ugv_mon/
├── core/                     # 🆕 신설
│   ├── __init__.py           # models, config, constants export
│   ├── models.py             # ✅ 통합된 데이터 모델
│   ├── config.py
│   └── constants.py
├── layouts/
│   └── panels/               # 🆕 패키지로 분리
│       ├── __init__.py
│       ├── _common.py        # 공통 스타일/헬퍼
│       ├── operational.py
│       ├── device.py
│       ├── ... (총 8개 파일)
└── ...
```

---

## 2. 주요 변경 내역

### 2.1 Core 패키지 통합 (중복 제거)
- **배경**: `data/models.py`와 `parser/models.py`에 동일하거나 유사한 클래스가 중복 정의되어 있었습니다.
- **조치**: `ugv_mon/core/models.py` 하나로 통합하고 모든 의존성을 이곳으로 연결했습니다.
- **Import 수정 예시**:
  ```python
  # Before
  from ..data.models import LogEntry
  from ..parser.models import ICDHeader
  from ..config import config
  
  # After
  from ..core import LogEntry, ICDHeader, config
  ```

### 2.2 Panels 분리 (가독성 향상)
- **배경**: `panels.py`가 500줄을 넘어 유지보수가 어려웠습니다.
- **조치**: 기능별(운용상태, 차트, 로그 등)로 개별 파일로 분리하고 `layouts/panels/__init__.py`에서 모아 export하도록 변경했습니다.
- **장점**: `main_layout.py`에서는 여전히 `from .panels import ...`를 그대로 사용할 수 있어 코드 수정이 최소화되었습니다.

### 2.3 라이브러리 호환성 (Dash Mantine Components)
- **중요**: 로컬 환경은 **DMC 2.4.1** 버전을 사용 중입니다.
- **코드 적용 사항**:
  - `dmc.Group`: `position="apart"` (구버전) ❌ → **`justify="space-between"`** ✅
  - `dmc.Stack`/`dmc.Group`: `spacing="xs"` (구버전) ❌ → **`gap="xs"`** ✅
  - Tabs 컴포넌트: `dmc.Tab` (구버전) ❌ → **`dmc.TabsTab`** ✅
- **⚠️ 주의**: 회사 환경이 DMC 0.12.x 등 구버전이라면 이 부분을 반대로 수정해야 할 수 있습니다.

---

## 3. 마이그레이션 체크리스트

회사 코드베이스에 merge할 때 다음 순서로 확인하세요.

1. **파일 구조 동기화**
   - [ ] `ugv_mon/core/` 폴더 생성 및 파일 복사
   - [ ] `ugv_mon/layouts/panels/` 폴더 생성 및 파일 복사
   - [ ] `ugv_mon/layouts/panels.py` 삭제
   - [ ] `ugv_mon/data/models.py`, `ugv_mon/parser/models.py` 삭제
   - [ ] `ugv_mon/config.py`, `ugv_mon/constants.py` 삭제 (core로 이동 확인 후)

2. **Import 경로 전체 치환 (Global Replace)**
   - `ugv_mon.config` → `ugv_mon.core`
   - `ugv_mon.constants` → `ugv_mon.core`
   - `ugv_mon.data.models` → `ugv_mon.core`
   - `ugv_mon.parser.models` → `ugv_mon.core`

3. **라이브러리 버전 확인**
   - `pip show dash-mantine-components` 명령어로 버전을 확인하세요.
   - **2.x 버전**: 현재 코드 그대로 사용
   - **0.12.x 버전**: `gap` → `spacing`, `justify` → `position`, `TabsTab` → `Tab`으로 롤백 필요

4. **실행 테스트**
   - `python run.py` 실행 후 `ImportError`가 없는지 확인
