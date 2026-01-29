# UGV-MON 최종 코드 리뷰 보고서

> **최종 업데이트**: 2026-01-29  
> **버전**: 1.6.0 (버그 수정 및 기능 개선)

---

## 1. 프로젝트 개요

| 항목 | 상태 |
|------|------|
| **목적** | VIC↔OCS UDP 통신 실시간 모니터링 대시보드 |
| **파일 수** | 34개 Python 파일 |
| **문서 수** | 7개 (docs/) |
| **테스트** | 33개 (100% 통과) |

---

## 2. 오늘 수정된 버그 (2026-01-29)

### 2.1 가용성이 갑자기 100%로 튀는 문제

| 항목 | 내용 |
|------|------|
| **원인** | `window_sec=60`으로 설정, 60초 지나면 레코드 삭제되어 계산 오류 |
| **해결** | `window_sec=300` (5분)으로 변경, 측정 구간 계산 로직 개선 |
| **파일** | `analysis/stats_calculator.py` |

```python
# 수정 전
def __init__(self, window_sec: int = 60):

# 수정 후
def __init__(self, window_sec: int = 300):  # 5분으로 변경
```

### 2.2 제목이 "Updating..."으로 바뀌는 문제

| 항목 | 내용 |
|------|------|
| **원인** | Dash 기본 동작 (콜백 실행 중 제목 변경) |
| **해결** | `update_title=None` 옵션 추가 |
| **파일** | `app.py` |

### 2.3 연결 버튼이 즉시 안 바뀌는 문제

| 항목 | 내용 |
|------|------|
| **원인** | `_process_packet()`에서 `self._is_connected = True` 덮어씀 |
| **해결** | 해당 라인 삭제, 버튼 콜백 분리 |
| **파일** | `live_provider.py`, `update_callbacks.py` |

---

## 3. 알려진 이슈

### 3.1 ⚠️ Print문 중복 출력 문제

**증상**: `_register_component_callback`의 print문이 2초 폴링마다 2-3번 중복 출력됨

**원인 분석**:
```
dashboard-data → update_components 콜백
         ├── Input: dashboard-data (데이터 폴링)
         ├── Input: chart-time-range (시간 범위)
         ├── Input: log-filter-msgcode (필터)
         ├── Input: log-filter-status (필터)
         └── Input: log-search-input (검색)
```

Dash는 **모든 Input이 변경될 때마다** 콜백을 실행함. 초기화 시 여러 Input이 동시에 변경되면 중복 호출 발생.

**해결 방법**:
```python
# 방법 1: callback_context로 트리거 확인
from dash import callback_context

def update_components(data, ...):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    print(f"Triggered by: {triggered_id}")  # 디버깅용
    ...

# 방법 2: prevent_initial_call 사용
@app.callback(..., prevent_initial_call=True)
```

**디버깅 방법**:
```python
# update_callbacks.py에 추가
import time
def update_components(data, ...):
    print(f"[{time.time():.3f}] update_components called, trigger: {callback_context.triggered}")
    ...
```

---

## 4. 아키텍처 평가

### 4.1 디렉토리 구조 (★★★★★)

```
ugv_mon/
├── analysis/        # 통계 분석 (2 파일)
├── callbacks/       # Dash 콜백 (1 파일)
├── capture/         # 패킷 캡처 (3 파일)
├── components/      # UI 컴포넌트 (5 파일)
├── data/            # 데이터 제공자 (3 파일)
├── layouts/         # 레이아웃 (4 파일)
├── parser/          # ICD 파서 (2 파일)
├── utils/           # 유틸리티 (1 파일)
├── app.py
├── config.py
├── constants.py
└── styles.py
```

### 4.2 데이터 흐름 (★★★★☆)

```
[Scapy] → [sniffer.py] → [queue.py] → [live_provider.py] → [callbacks] → [UI]
                                              ↓
                                      [stats_calculator.py]
```

---

## 5. 코드 품질 분석

| 파일 | LOC | 복잡도 | 품질 | 비고 |
|------|-----|--------|------|------|
| `icd_parser.py` | ~130 | 중 | ★★★★★ | 잘 구조화됨 |
| `stats_calculator.py` | ~200 | 중 | ★★★★★ | window 5분, 가용성 계산 개선됨 |
| `live_provider.py` | ~235 | 높음 | ★★★★☆ | _is_connected 로직 개선됨 |
| `update_callbacks.py` | ~200 | 중 | ★★★★☆ | 버튼 콜백 분리됨 |
| `charts.py` | ~330 | 중 | ★★★☆☆ | 함수 분리 가능 |
| `panels.py` | ~300 | 중 | ★★★☆☆ | 중복 스타일 존재 |
| `alerts.py` | ~160 | 낮음 | ★★★★★ | 깔끔한 클래스 구조 |
| `log_table.py` | ~280 | 낮음 | ★★★★☆ | 필터 기능 추가됨 |

---

## 6. 구현된 기능

### 6.1 로그 필터링/검색 ✅
- Msg Code 필터 (All, 0x01, 0x25, 0x40)
- 상태 필터 (All, 성공만, 에러만)
- 텍스트 검색 (Notes 필드)

### 6.2 인터페이스 동적 선택 ✅
- 하드코딩 → 파라미터 기반 동적 목록
- 연결 상태 버튼 즉시 반응

### 6.3 알림/경보 시스템 ✅
- `AlertManager` 클래스 (가용성<95%, 지터P99>100ms, 연결끊김 5초)
- 토스트 알림 (DMC Notification)
- 로그 파일 기록 (`logs/alerts.log`)

---

## 7. 종합 점수

| 영역 | 점수 | 비고 |
|------|------|------|
| 아키텍처 | 9/10 | 명확한 분리 |
| 코드 품질 | 8.5/10 | 버그 수정됨 |
| 테스트 | 8/10 | 33개 100% 통과 |
| 문서화 | 9/10 | 7개 문서 |
| 확장성 | 8/10 | 모듈화 Good |
| 보안 | 8/10 | debug=False |

### **종합: 8.4/10** ✅ 현업 적용 가능

---

## 8. 다음 작업

| 우선순위 | 작업 | 상태 |
|----------|------|------|
| 높음 | VCS_Simulator 연동 테스트 | 대기 |
| 중간 | 차트 확장 (P95/P99 오버레이) | 시뮬레이터 후 |
| 낮음 | Print 중복 해결 | 선택적 |

---

*최종 업데이트: 2026-01-29*
