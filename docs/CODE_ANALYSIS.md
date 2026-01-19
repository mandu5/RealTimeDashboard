# 코드 분석 보고서 - 사용되지 않는 코드 및 불필요한 파일

> **작성일**: 2026-01-20  
> **목적**: 프로젝트 내 사용되지 않는 코드, 함수, 패키지 식별 및 정리

---

## 📊 분석 결과 요약

| 카테고리 | 발견 항목 수 | 권장 조치 |
|---------|------------|----------|
| 사용되지 않는 함수 | 10개 | 삭제 또는 주석 처리 |
| 사용되지 않는 패키지 | 3개 | requirements.txt에서 제거 |
| 중복 import | 1개 | 정리 |
| 사용되지 않는 파일 | 0개 | 없음 |

---

## 🔍 상세 분석

### 1. 사용되지 않는 함수

#### 1.1 `ugv_mon/layouts/charts.py`

**함수**: `create_pps_chart()` (325-367줄)
- **상태**: ❌ 사용되지 않음
- **이유**: `create_communication_chart()`가 통합 차트를 제공하므로 불필요
- **권장 조치**: 삭제

**함수**: `create_jitter_chart()` (370-422줄)
- **상태**: ❌ 사용되지 않음
- **이유**: `create_communication_chart()`가 통합 차트를 제공하므로 불필요
- **권장 조치**: 삭제

#### 1.2 `ugv_mon/components/device_grid.py`

**함수**: `get_device_summary()` (137-150줄)
- **상태**: ❌ 사용되지 않음
- **이유**: `panels.py`에서 import하지만 실제로는 직접 계산함 (333줄)
- **권장 조치**: 삭제 또는 `panels.py`에서 실제 사용

#### 1.3 `ugv_mon/utils/helpers.py`

**함수**: `format_percentage()` (66-77줄)
- **상태**: ❌ 사용되지 않음
- **권장 조치**: 삭제 (필요 시 나중에 추가 가능)

**함수**: `format_timestamp()` (80-93줄)
- **상태**: ❌ 사용되지 않음
- **이유**: `LogEntry.to_dict()`에서 직접 `strftime()` 사용
- **권장 조치**: 삭제

**함수**: `calculate_availability()` (147-163줄)
- **상태**: ❌ 사용되지 않음
- **이유**: `StatsCalculator` 또는 `MockDataGenerator`에서 직접 계산
- **권장 조치**: 삭제

**함수**: `get_operation_mode_label()` (166-185줄)
- **상태**: ❌ 사용되지 않음
- **이유**: `ICDParser`에서 직접 매핑 처리
- **권장 조치**: 삭제 (Day 3 파서 모듈에서 처리)

**함수**: `get_authority_label()` (188-205줄)
- **상태**: ❌ 사용되지 않음
- **이유**: `ICDParser`에서 직접 매핑 처리
- **권장 조치**: 삭제

**함수**: `get_driving_state_label()` (208-225줄)
- **상태**: ❌ 사용되지 않음
- **이유**: `ICDParser`에서 직접 매핑 처리
- **권장 조치**: 삭제

**함수**: `seq_gap_with_rollover()` (228-244줄)
- **상태**: ❌ 사용되지 않음
- **이유**: `StatsCalculator`에서 직접 계산
- **권장 조치**: 삭제

---

### 2. 사용되지 않는 패키지

#### 2.1 `requirements.txt` 분석

**패키지**: `pandas==2.1.4`
- **상태**: ❌ 사용되지 않음
- **검증**: 프로젝트 전체에서 `import pandas` 또는 `from pandas` 없음
- **권장 조치**: requirements.txt에서 제거

**패키지**: `numpy==1.26.2`
- **상태**: ❌ 사용되지 않음
- **검증**: 프로젝트 전체에서 `import numpy` 또는 `from numpy` 없음
- **권장 조치**: requirements.txt에서 제거

**패키지**: `python-dateutil==2.8.2`
- **상태**: ❌ 사용되지 않음
- **검증**: 프로젝트 전체에서 `import dateutil` 또는 `from dateutil` 없음
- **권장 조치**: requirements.txt에서 제거

---

### 3. 중복/불필요한 Import

#### 3.1 `ugv_mon/layouts/panels.py`

**라인 297**: 
```python
from ..components.device_grid import create_device_grid, get_device_summary
```

**문제**: `get_device_summary`를 import하지만 실제로는 사용하지 않음 (333줄에서 직접 계산)

**권장 조치**: import에서 제거
```python
from ..components.device_grid import create_device_grid
```

---

## ✅ 사용 중인 코드 (검증 완료)

### `ugv_mon/utils/helpers.py` - 사용 중인 함수들

| 함수 | 사용 위치 | 상태 |
|------|----------|------|
| `get_status_color()` | `components/status_chip.py` | ✅ 사용 중 |
| `get_device_status_style()` | `components/device_grid.py` | ✅ 사용 중 |
| `get_chart_colors()` | `layouts/charts.py` | ✅ 사용 중 |

---

## 📝 권장 조치 사항

### 즉시 조치 (안전)

1. **`requirements.txt` 정리**
   ```diff
   - pandas==2.1.4
   - numpy==1.26.2
   - python-dateutil==2.8.2
   ```

2. **`panels.py` import 정리**
   ```python
   # 변경 전
   from ..components.device_grid import create_device_grid, get_device_summary
   
   # 변경 후
   from ..components.device_grid import create_device_grid
   ```

### 검토 후 조치 (주의 필요)

3. **`charts.py` 함수 삭제**
   - `create_pps_chart()` 삭제
   - `create_jitter_chart()` 삭제
   - **주의**: 향후 단독 차트가 필요할 수 있으므로 주석으로 보관 고려

4. **`device_grid.py` 함수 삭제**
   - `get_device_summary()` 삭제
   - 또는 `panels.py`에서 실제 사용하도록 수정

5. **`helpers.py` 함수 정리**
   - 사용되지 않는 7개 함수 삭제
   - **주의**: 향후 확장 시 필요할 수 있으므로 별도 파일로 보관 고려

---

## 🎯 정리 후 예상 효과

### 파일 크기 감소
- `charts.py`: ~100줄 감소
- `helpers.py`: ~180줄 감소
- `device_grid.py`: ~15줄 감소

### 의존성 감소
- 불필요한 패키지 3개 제거
- 설치 시간 단축
- 메모리 사용량 감소

### 코드 가독성 향상
- 실제 사용되는 코드만 남김
- 유지보수 용이성 증가

---

## ⚠️ 주의사항

1. **향후 확장성**: 삭제 전에 향후 필요 여부 검토
2. **테스트**: 삭제 후 전체 기능 테스트 필수
3. **문서화**: 삭제 이유를 주석 또는 CHANGELOG에 기록

---

## 📋 체크리스트

- [ ] `requirements.txt`에서 불필요한 패키지 제거
- [ ] `panels.py` import 정리
- [ ] `charts.py` 사용되지 않는 함수 삭제/주석 처리
- [ ] `device_grid.py` `get_device_summary()` 삭제 또는 사용
- [ ] `helpers.py` 사용되지 않는 함수 정리
- [ ] 전체 기능 테스트 실행
- [ ] CHANGELOG 업데이트

---

## 📚 참고

- **분석 도구**: `grep`, 파일 읽기
- **분석 기준**: 실제 import 및 함수 호출 여부
- **검증 방법**: 프로젝트 전체 코드 검색
