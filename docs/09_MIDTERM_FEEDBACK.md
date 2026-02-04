# 중간발표 피드백 분석 및 답변

> **작성일**: 2026-02-04  
> **상태**: 멘토 피드백 정리

---

## 1. dcc.Store 저장 방식

**질문**: dcc.Store는 데이터를 어떤 방식으로 저장하나?

**답변**: 
- **저장 형식**: Python `dict` → **JSON 문자열**로 직렬화
- **저장 위치**: 브라우저의 `localStorage` 또는 `sessionStorage` (기본: memory)
- **제한**: JSON으로 변환되므로 `bytes`, `datetime` 객체는 직접 저장 불가 → 문자열로 변환 필요

```python
# 현재 코드 (main_layout.py)
dcc.Store(id="dashboard-data", data=initial_data)  # dict → JSON
```

**결론**: 우리 앱에서는 `dict`를 JSON으로 직렬화하여 브라우저 메모리에 저장합니다.

---

## 2. packet[Raw]가 뭐야?

**질문**: `raw_data = bytes(packet[Raw].load)` 에서 `[Raw]`는?

**답변**:
- `Raw`는 **scapy의 레이어 클래스** (실제 페이로드 데이터)
- `packet[Raw]`는 패킷에서 Raw 레이어 추출
- `.load`는 해당 레이어의 바이트 데이터

```
이더넷 패킷 구조:
┌────────────┬────────────┬────────────┬──────────────┐
│  Ethernet  │     IP     │    UDP     │     Raw      │  ← 우리가 추출하는 부분
│   헤더     │    헤더    │   헤더     │  (페이로드)  │
└────────────┴────────────┴────────────┴──────────────┘
                                        ↑
                              packet[Raw].load = ICD 데이터
```

**코드 위치**: `sniffer.py` 102줄

---

## 3. dcc.Interval과 dashboard-data

**질문**: dcc.Interval 역할? dashboard-data 의미?

**답변**:

### dcc.Interval
- **역할**: 주기적으로 콜백 트리거 (타이머 역할)
- **설정**: `interval=2000ms` → 2초마다 `update_data` 콜백 실행
- **n_intervals**: 실행 횟수 카운터

```python
dcc.Interval(
    id="interval-component",
    interval=2000,  # 2초마다
    n_intervals=0,  # 실행 횟수
)
```

### dashboard-data
- **역할**: 대시보드 전체 상태를 담는 **중앙 저장소**
- **내용**: 연결상태, PPS, 지터, 장치상태, 차트데이터 등

```python
{
    "connected": True,
    "capturePps": 100,
    "jitterP95": 5.2,
    "devices": [...],
    "combinedData": [...]  # 차트용 시계열
}
```

---

## 4. 콜백 역할 설명

| 콜백 | 역할 | 트리거 |
|------|------|--------|
| `_register_data_callback` | 2초마다 `provider.update_data()` 호출 → dashboard-data 갱신 | Interval |
| `_register_component_callback` | dashboard-data 변경 시 모든 UI 컴포넌트 갱신 | dashboard-data |
| `_register_control_callbacks` | Pause/Resume, Clear 버튼 처리 | 버튼 클릭 |
| `_register_ui_callbacks` | 인터페이스/연결/방향 전환 버튼 | 버튼 클릭 |

### 데이터 흐름
```
Interval (2초) 
    ↓
data_callback: provider.update_data() → dashboard-data 갱신
    ↓
component_callback: dashboard-data 변경 감지 → UI 전체 갱신
```

---

## 5. @app.callback이 람다 같다?

**멘토 의견**: Input/Output 방식이 람다 느낌

**설명**: 맞습니다! **선언적/반응형 프로그래밍** 패턴입니다.

```python
# 람다처럼 "입력 → 출력" 관계만 선언
@app.callback(
    Output("result", "children"),  # 출력
    Input("button", "n_clicks"),   # 입력
)
def update(n):  # 입력 → 출력 변환 함수
    return f"클릭: {n}"
```

**특징**:
- 명시적 호출 없이 **자동 실행** (입력 변경 시)
- **반응형(Reactive)**: 입력→출력 매핑만 정의
- React의 `useEffect`나 RxJS와 유사한 개념

---

## 6. deque 데이터 분석 문제

**멘토 의견**: 패킷을 deque에 쌓으면 상관관계/분석 힘들다. 패킷 꼬임 문제도 있다.

### 현재 방식
```python
self._records: deque = deque()  # 시계열 저장
```

### 멘토 우려
1. **인덱싱 어려움**: deque는 순차 접근에 최적화, 랜덤 접근 느림
2. **패킷 꼬임**: 시퀀스 번호 불일치 시 분석 어려움
3. **상관관계 분석**: msg_code별, 시간대별 그룹핑 어려움

### 개선 방안

**방안 A: 현재 방식 보완**
```python
# 딕셔너리 인덱싱 추가
self._records_by_time: Dict[str, List[PacketRecord]] = {}  # 시간대별
self._records_by_code: Dict[int, deque] = {}  # msg_code별
```

**방안 B: pandas DataFrame 전환** (추천)
```python
import pandas as pd
self._df = pd.DataFrame(columns=["timestamp", "sequence", "msg_code", "jitter"])
# → groupby, resample, rolling 등 분석 기능 활용 가능
```

**방안 C: SQLite 저장**
```python
import sqlite3
# 영구 저장 + SQL 쿼리로 분석
```

### 결론
현재 단계에서는 **방안 A (인덱싱 추가)**로 보완하고, 추후 데이터 분석 확장 시 **방안 B (pandas)**로 전환 권장.

---

## 7. 프론트/백 분리 및 폴더 구조

### 멘토 의견 1: dcc.Store가 main_layout에 있으면 프론트/백 혼재 아닌가?

**분석**:
- `dcc.Store`는 **프론트엔드 컴포넌트** (브라우저에 렌더링)
- `live_provider.py`가 **백엔드 로직** (데이터 수집/처리)
- 현재 구조는 **Dash 권장 패턴**과 일치

**결론**: 구조적으로 문제없으나, 더 명확히 분리하려면:
```
ugv_mon/
├── frontend/         # 레이아웃, 컴포넌트
│   ├── layouts/
│   └── components/
├── backend/          # 데이터 처리
│   ├── providers/
│   └── analysis/
└── callbacks/        # 연결 레이어
```

### 멘토 의견 2: live_provider.py가 data 폴더에 있는게 맞나?

**현재 구조**:
```
data/
├── live_provider.py  # 오케스트레이션
├── mock_data.py      # 목 데이터
└── models.py         # 데이터 모델
```

**개선 제안**:
```
providers/
├── live_provider.py
└── mock_provider.py
data/
├── models.py
└── constants.py
```

**결론**: 시간 있으면 폴더 구조 개선, 하지만 현재도 기능적으로 문제없음.

---

## 8. timestamp 정보 미공개 및 지터 오염

### 멘토 피드백
- `4f000000`은 timestamp인데 0이 아니라 **비공개**
- 현재 `datetime.now()`로 시간 측정 → **지터 오염 가능**
- 파이썬은 ms 단위 정밀도 보장 어려움

### 현재 코드 (sniffer.py)
```python
capture_time = datetime.now()  # 파이썬 시간
raw_data = bytes(packet[Raw].load)
self._callback((capture_time, raw_data))
```

### 기술적 한계
1. **파이썬 GIL**: 스레드 스케줄링으로 ms 단위 지연 발생
2. **OS 스케줄러**: 실시간 OS가 아님
3. **scapy 오버헤드**: 패킷 파싱에 시간 소요

### 결론 및 개선점

**지터 관련 더 이상 할 것 없음** (멘토 확인)

**제거/간소화 가능한 부분**:
1. ~~7중 방어 로직~~ → 이미 회사 로직으로 단순화됨 ✅
2. ~~global_skip_count~~ → 제거됨 ✅
3. `MAX_JITTER_MS` 필터링 → 통계용으로만 유지

**표시 방식 개선 제안**:
- 지터 값에 **"* 참고용"** 표시 추가
- 툴팁: "파이썬 datetime 기준, 실제 패킷 timestamp 미지원"

---

## 9. 가용성 그래프 10분 제한 문제

### 문제
- `timeline_duration_sec = 600` (10분) 설정
- 10분 지나면 이전 데이터가 그래프 밖으로 나감
- 연결/끊김 이력이 사라짐

### 현재 코드 (live_provider.py)
```python
self._availability_history: deque = deque(maxlen=config.ui.timeline_duration_sec)
```

### 해결 방안

**방안 A: 슬라이딩 윈도우 유지 (권장)**
- 가장 최근 10분만 표시 (현재 동작)
- **개선**: X축을 "현재 시점 기준 상대 시간"으로 표시

```python
# 예: "-10:00" ~ "0:00" (현재)
```

**방안 B: 확대/축소 기능 추가**
```python
# 사용자가 시간 범위 선택 가능
time_ranges = [600, 1800, 3600]  # 10분, 30분, 1시간
```

**방안 C: 요약 통계 표시**
- 10분 넘은 데이터는 **요약 통계**로 변환
- "지난 1시간 가용성: 98.5%"

### 구현 권장
**방안 A + C 조합**: 그래프는 10분, 상단에 요약통계 표시

---

## 10. 데이터 분석 아이디어 업데이트 (docs/07)

별도 문서로 작성 예정 → `docs/07_VISUALIZATION_IDEAS.md` 업데이트

---

## 11. docs 00-05 최신화

각 문서별 확인 및 업데이트 예정:
- `00_PROJECT_OVERVIEW.md`
- `01_ARCHITECTURE.md`
- `02_FILE_STRUCTURE.md`
- `03_ICD_SPECIFICATION.md`
- `05_KPI_DATA_ANALYSIS.md`

---

## 액션 아이템 정리

| # | 항목 | 우선순위 | 상태 |
|---|------|---------|------|
| 6 | deque 인덱싱 개선 | 중 | 검토 필요 |
| 7 | 폴더 구조 개선 | 하 | 후순위 |
| 9 | 가용성 그래프 개선 | 상 | 구현 필요 |
| 10 | docs/07 업데이트 | 상 | 진행 예정 |
| 11 | docs 00-05 최신화 | 중 | 진행 예정 |
