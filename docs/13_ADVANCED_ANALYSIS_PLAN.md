# UGV-MON 고차원 데이터 분석 계획

> **작성일**: 2026-02-05  
> **목적**: 인턴십 마지막 2주간 진행할 고차원 분석 아이디어 정리  
> **원칙**: AI/ML은 유의미한 경우에만 사용, 과도한 사용은 마이너스

---

## 📊 현재 보유 데이터 분석

### 1. 실시간 수집 데이터

| 데이터 | 수집 빈도 | 타입 | 분석 가치 |
|--------|----------|------|----------|
| **PPS** (Packets Per Second) | 매 초 | 정수 | ⭐⭐⭐ 네트워크 부하/상태 |
| **Jitter** (P95/P99) | 매 초 | 실수 (ms) | ⭐⭐⭐ 네트워크 품질 |
| **Packet Loss** | 누적 | 정수 | ⭐⭐ 통신 신뢰성 |
| **Availability** | 5분/1시간 | % | ⭐⭐⭐ 시스템 안정성 |

### 2. 운용 상태 데이터

| 데이터 | 값 | 분석 가치 |
|--------|-----|----------|
| **Operation Mode** | 준비/무인주행/유인주행/비상정지/점검/원격 | ⭐⭐⭐ 모드별 통신 특성 |
| **Authority** | 없음/OCS/근거리조종기/VIC | ⭐⭐ 권한별 패턴 |
| **Driving State** | 정지/전진/후진/회전 | ⭐⭐ 주행 중 통신 품질 |

### 3. 이벤트 데이터

| 데이터 | 내용 | 분석 가치 |
|--------|------|----------|
| **Emergency Events** | 비상정지 원인 (10종) | ⭐⭐⭐ 패턴/예측 |
| **Mode Transitions** | 운용모드 전이 이력 | ⭐⭐ 상태 변화 분석 |
| **Connection History** | 연결/끊김 이력 | ⭐⭐⭐ 안정성 분석 |
| **Device Status** | 10개 장치 연결 상태 | ⭐⭐ 고장 패턴 |

### 4. msg_code별 통계

| msg_code | 의미 | 빈도 |
|----------|------|------|
| 0x01 | 운용 상태 메시지 | ~100 PPS |
| 0x10 | 원격 제어 메시지 | 80~110 Hz |
| 0x25 | Heartbeat | 낮음 |
| 0x40 | 기타 | 낮음 |

---

## 🎯 분석 아이디어 (우선순위순)

### Phase 1: 통계 기반 분석 (ML 불필요) ⭐⭐⭐

#### 1.1 상관관계 분석

**목적**: 지터↔패킷손실, PPS↔가용성 등 변수 간 관계 파악

```python
# 구현 예시
import pandas as pd

df = stats_calc.get_dataframe()

# 피어슨 상관계수
correlations = df[['jitter_ms', 'interval_ms', 'size']].corr()

# 시각화: 히트맵
```

**기대 결과**:
- 지터 증가 → 패킷 손실 증가 여부
- PPS 감소 → 가용성 하락 선행 지표 여부

**난이도**: 낮음 | **가치**: 높음 | **ML 필요**: ❌

---

#### 1.2 운용모드별 통신 품질 비교

**목적**: "무인주행" vs "유인주행" 등 모드별 지터/PPS 차이 분석

```python
# 구현 예시
df_with_mode = df.merge(mode_history, on='timestamp')
grouped = df_with_mode.groupby('operation_mode').agg({
    'jitter_ms': ['mean', 'std', 'quantile'],
    'pps': ['mean', 'std'],
})
```

**기대 결과**:
- 특정 모드에서 통신 품질 저하 패턴 발견
- 운용 권장사항 도출 가능

**난이도**: 낮음 | **가치**: 높음 | **ML 필요**: ❌

---

#### 1.3 시간대별 패턴 분석

**목적**: 특정 시간대에 문제가 집중되는지 분석

```python
# 구현 예시
df['hour'] = df['timestamp'].dt.hour
hourly_stats = df.groupby('hour').agg({
    'jitter_ms': 'mean',
    'packet_loss': 'sum',
})
```

**기대 결과**:
- 특정 시간대 네트워크 혼잡 패턴
- 운용 스케줄 최적화 제안

**난이도**: 낮음 | **가치**: 중간 | **ML 필요**: ❌

---

### Phase 2: 이상 탐지 (경량 ML 가능) ⭐⭐⭐

#### 2.1 통계 기반 이상 탐지 (ML 불필요)

**목적**: Z-score, IQR 기반 지터/PPS 이상치 탐지

```python
# 현재 anomaly_detector.py 확장
def detect_anomaly_zscore(value: float, history: list, threshold: float = 3.0) -> bool:
    """Z-score 기반 이상 탐지."""
    if len(history) < 30:
        return False
    mean = np.mean(history)
    std = np.std(history)
    if std == 0:
        return False
    z_score = abs(value - mean) / std
    return z_score > threshold

def detect_anomaly_iqr(value: float, history: list) -> bool:
    """IQR 기반 이상 탐지."""
    q1 = np.percentile(history, 25)
    q3 = np.percentile(history, 75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return value < lower or value > upper
```

**장점**:
- 해석 가능 (왜 이상인지 설명 가능)
- 추가 라이브러리 불필요
- 실시간 적용 가능

**난이도**: 낮음 | **가치**: 높음 | **ML 필요**: ❌

---

#### 2.2 Isolation Forest 기반 이상 탐지 (경량 ML)

**목적**: 다변량 이상 탐지 (지터+PPS+패킷손실 동시 고려)

```python
# 구현 예시 (sklearn 필요)
from sklearn.ensemble import IsolationForest

# 특성 추출
features = df[['jitter_ms', 'pps', 'packet_loss_rate']].fillna(0)

# 모델 학습 (비지도 학습)
model = IsolationForest(contamination=0.05, random_state=42)
df['anomaly'] = model.fit_predict(features)
```

**사용 조건**:
- sklearn 사전 설치 필요
- 충분한 학습 데이터 필요 (최소 1시간 이상)

**장점**:
- 복합적인 이상 패턴 탐지
- 단일 변수로는 못 잡는 이상치 발견

**단점**:
- 블랙박스 (왜 이상인지 설명 어려움)
- 오탐 가능성

**난이도**: 중간 | **가치**: 중간 | **ML 필요**: ⚠️ 신중히 검토

---

### Phase 3: 예측 분석 (ML 선택적) ⭐⭐

#### 3.1 이동평균 기반 추세 예측 (ML 불필요)

**목적**: 향후 가용성/지터 추세 예측

```python
# 단순 이동평균
df['jitter_ma_5'] = df['jitter_ms'].rolling(window=5).mean()
df['jitter_ma_20'] = df['jitter_ms'].rolling(window=20).mean()

# 추세 판단
if df['jitter_ma_5'].iloc[-1] > df['jitter_ma_20'].iloc[-1] * 1.2:
    alert("지터 상승 추세 감지")
```

**장점**:
- 단순하고 해석 가능
- 실시간 적용 가능
- 추가 라이브러리 불필요

**난이도**: 낮음 | **가치**: 중간 | **ML 필요**: ❌

---

#### 3.2 ARIMA/지수평활법 (경량 시계열 예측)

**목적**: 향후 N분 후 가용성 예측

```python
# statsmodels 필요
from statsmodels.tsa.holtwinters import ExponentialSmoothing

model = ExponentialSmoothing(
    df['availability'], 
    trend='add', 
    seasonal=None
).fit()
forecast = model.forecast(steps=10)  # 향후 10분 예측
```

**사용 조건**:
- statsmodels 사전 설치 필요
- 최소 30분 이상 데이터 필요

**난이도**: 중간 | **가치**: 중간 | **ML 필요**: ⚠️ 필요시만

---

### Phase 4: 비상정지 원인 분석 ⭐⭐⭐

#### 4.1 비상정지 선행 지표 분석 (ML 불필요)

**목적**: 비상정지 발생 전 N초간 지터/PPS 패턴 분석

```python
# 비상정지 이벤트 전 30초 데이터 추출
def get_pre_emergency_data(emergency_time: datetime, window_sec: int = 30):
    start = emergency_time - timedelta(seconds=window_sec)
    return df[(df['timestamp'] >= start) & (df['timestamp'] < emergency_time)]

# 정상 구간과 비교
normal_jitter_mean = df[df['is_normal']]['jitter_ms'].mean()
pre_emergency_jitter_mean = pre_emergency_df['jitter_ms'].mean()

if pre_emergency_jitter_mean > normal_jitter_mean * 1.5:
    print("비상정지 전 지터 상승 패턴 발견!")
```

**기대 결과**:
- 비상정지 발생 전 경고 가능한 선행 지표 발견
- "통신이상" 비상정지 예측 가능성

**난이도**: 중간 | **가치**: 매우 높음 | **ML 필요**: ❌

---

#### 4.2 비상정지 원인 클러스터링 (선택적 ML)

**목적**: 비상정지 원인별 패턴 그룹화

```python
# 각 비상정지 이벤트의 특성 추출
features = []
for event in emergency_events:
    pre_data = get_pre_emergency_data(event['timestamp'])
    features.append({
        'jitter_mean': pre_data['jitter_ms'].mean(),
        'jitter_std': pre_data['jitter_ms'].std(),
        'pps_mean': pre_data['pps'].mean(),
        'packet_loss': pre_data['packet_loss'].sum(),
    })

# K-means 클러스터링 (sklearn 필요)
from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=3).fit(features_df)
```

**주의**: 비상정지 이벤트가 충분히 많아야 의미 있음 (최소 20개 이상)

**난이도**: 높음 | **가치**: 조건부 높음 | **ML 필요**: ⚠️ 데이터 충분시만

---

## 🚫 사용하지 않을 것들 (오버엔지니어링)

### ❌ LLM 기반 로그 분석
- **이유**: 구조화된 데이터에 LLM은 과도함
- **대안**: 규칙 기반 알림으로 충분

### ❌ 딥러닝 시계열 예측 (LSTM 등)
- **이유**: 데이터 양 부족, 해석 불가
- **대안**: 이동평균/ARIMA로 충분

### ❌ 복잡한 앙상블 모델
- **이유**: 폐쇄망 환경에서 유지보수 어려움
- **대안**: 단일 해석 가능 모델

### ❌ 실시간 강화학습
- **이유**: 모니터링 시스템에 부적합
- **대안**: 규칙 기반 임계값 조정

---

## 📋 구현 우선순위 (2주 계획)

### Week 1: 통계 분석 기반 확장

| 일 | 작업 | 난이도 | ML |
|---|------|-------|-----|
| 1-2 | 상관관계 분석 구현 + 시각화 | 낮음 | ❌ |
| 3 | 운용모드별 통계 비교 | 낮음 | ❌ |
| 4-5 | Z-score/IQR 이상 탐지 강화 | 낮음 | ❌ |

### Week 2: 고급 분석 + 최종 정리

| 일 | 작업 | 난이도 | ML |
|---|------|-------|-----|
| 1-2 | 비상정지 선행 지표 분석 | 중간 | ❌ |
| 3 | 이동평균 추세 예측 | 낮음 | ❌ |
| 4 | (데이터 충분시) Isolation Forest 시도 | 중간 | ⚠️ |
| 5 | 최종 문서화 + 발표 준비 | - | - |

---

## 🔧 필요 라이브러리 (폐쇄망 설치 요청)

### 필수 (이미 있음)
- `pandas` ✅
- `numpy` ✅
- `plotly` ✅

### 선택적 (ML 사용 시)
- `scikit-learn` - Isolation Forest, K-means
- `statsmodels` - ARIMA, 지수평활법

### 설치 불필요 (사용 안 함)
- `tensorflow` / `pytorch` - 오버킬
- `transformers` - LLM 불필요
- `prophet` - 복잡도 대비 효과 낮음

---

## 📊 성공 지표

### 분석이 "유의미"하다고 판단할 기준:

1. **상관관계 분석**
   - 상관계수 |r| > 0.5인 변수 쌍 발견
   - 운용에 활용 가능한 인사이트 도출

2. **이상 탐지**
   - 기존 대비 False Positive 감소
   - 실제 문제 상황 사전 감지 사례

3. **비상정지 분석**
   - 특정 패턴 발견 (예: 지터 급증 후 30초 내 비상정지)
   - 예측 정확도 > 70%

### 분석이 "과도"하다고 판단할 기준:

- 단순 규칙으로 동일 결과 가능
- 해석 불가능한 블랙박스 결과
- 유지보수 비용 > 효과
- 데이터 부족으로 과적합

---

## 💡 핵심 원칙

> **"AI를 쓰면 좋겠다"가 아니라 "이 문제를 풀기 위해 AI가 필요한가?"**

1. **통계로 충분하면 통계로** - 해석 가능성 우선
2. **ML은 통계로 안 될 때만** - 복합 패턴, 다변량 분석
3. **딥러닝은 금지** - 데이터 양/환경 부적합
4. **모든 결과는 설명 가능해야** - "왜?"에 답할 수 있어야 함

---

## 📁 예상 산출물

1. `ugv_mon/analysis/correlation_analyzer.py` - 상관관계 분석
2. `ugv_mon/analysis/anomaly_detector.py` - 이상 탐지 강화 (기존 확장)
3. `ugv_mon/analysis/emergency_analyzer.py` - 비상정지 패턴 분석
4. `ugv_mon/layouts/analysis_panel.py` - 분석 결과 시각화 패널
5. `docs/14_ANALYSIS_RESULTS.md` - 분석 결과 문서

---

*최종 목표: 실질적으로 운용에 도움되는 분석 결과 도출*
