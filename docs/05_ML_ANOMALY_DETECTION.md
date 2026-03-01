# UGV-MON ML 이상 탐지 시스템

> **최종 업데이트**: 2026-02-08

## 개요

UGV-MON은 **Isolation Forest** 기반 ML 이상 탐지와 **규칙 기반** 탐지를 결합한 **앙상블 시스템**을 제공합니다.

---

## 시스템 구조

```text
┌─────────────────────────────────────────────────────────────┐
│                    ML 이상 탐지 시스템                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────────┐    ┌──────────────────┐             │
│   │ Isolation Forest │    │   Rule Detector   │             │
│   │ (ml_anomaly_     │    │ (rule_detector.py)│             │
│   │  detector.py)    │    │                   │             │
│   └────────┬─────────┘    └────────┬──────────┘             │
│            │                       │                        │
│            └───────────┬───────────┘                        │
│                        ▼                                    │
│              ┌──────────────────┐                           │
│              │   ML Pipeline    │                           │
│              │ (ml_pipeline.py) │                           │
│              └────────┬─────────┘                           │
│                       ▼                                     │
│              ┌──────────────────┐                           │
│              │   시각화 패널    │                           │
│              │ (ui/layouts/panels) │                           │
│              └──────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 모듈 구성

### analysis/ml_pipeline.py

메인 파이프라인 - 학습/예측 조율

```python
class MLPipeline:
    def train(self, features: np.ndarray) -> bool
    def predict(self, features: np.ndarray) -> Dict
    def get_status(self) -> dict[str, Any]  # 실제 반환 구조
```

### analysis/ml_anomaly_detector.py

Isolation Forest 기반 탐지기

```python
class MLAnomalyDetector:
    def fit(self, X: np.ndarray) -> None
    def predict(self, X: np.ndarray) -> Tuple[bool, float, Dict]
    #         is_anomaly, confidence, contributing_features
```

### analysis/rule_detector.py

규칙 기반 탐지기

```python
class RuleDetector:
    def detect(self, metrics: Dict) -> RuleResult  # is_anomaly, violated_rules 포함
    #         is_anomaly, violated_rules
```

### analysis/feature_extractor.py

통계 데이터에서 ML 특성 추출

```python
class FeatureExtractor:
    def extract(self, data: Dict) -> np.ndarray
    # [pps, jitter, packet_loss, availability, msg_code_ratio...]
```

---

## 특성 벡터 (Features, 7차원)

ML 모델에 입력되는 특성 (`feature_extractor.py`):

| 특성              | 설명                   | 계산/의미                                |
| ----------------- | ---------------------- | ---------------------------------------- |
| jitter_current    | 현재 지터 (ms)         | 패킷 간격 변동 \|현재-이전\|             |
| jitter_p95        | 지터 95백분위 (ms)     | 상위 5% 제외                             |
| jitter_volatility | 지터 변동성            | \|P95-current\|/P95, 클수록 불안정       |
| pps_trend         | PPS 추세               | (현재-prev)/prev, 음수=성능 저하         |
| loss_rate         | 손실률 (%)             | packet_loss/(pps+packet_loss)×100        |
| quality_score     | 종합 품질 점수 (0–100) | 지터 60% + 손실률 40% 가중평균 |

---

## Isolation Forest 알고리즘

### 원리

- **격리**: 이상치는 정상 데이터보다 적은 분할로 격리됨
- **비지도 학습**: 라벨 없이 패턴 학습
- **contamination**: 예상 이상치 비율 (기본 5%)

### 파라미터

```python
IsolationForest(
    n_estimators=100,      # 트리 개수
    contamination=0.10,    # 예상 이상치 비율 (constants.ML_CONTAMINATION)
    random_state=42,       # 재현성
    max_samples='auto'
)
```

### 이상 점수 (Anomaly Score)

- **출처**: `score_samples()` 반환값
- **범위**: 대략 -1 ~ 0 (정상에 가까울수록 0, 이상일수록 -1에 가까움)
- **의미**: 격리 깊이 기반. 이상치는 적은 분할로 격리되어 **점수가 낮음(음수)**.
- **임계값**: 모델 `offset_` (학습 시 결정, 기본 -0.3). `score < threshold` → 이상.

---

## 규칙 기반 탐지 (rule_detector.py)

### 탐지 규칙 (기본 임계값)

| 규칙           | 조건                     | 위반 시 라벨       |
| -------------- | ------------------------ | ------------------ |
| 지터 상한      | jitter_current > 50 ms   | jitter_high        |
| 손실률 상한    | loss_rate > 5%           | loss_high          |
| 체크섬 실패율  | checksum_fail_rate > 10% | checksum_fail      |

### 앙상블 로직 (MLService)

- ML 학습 시: `final_anomaly = ml_anomaly or rule_anomaly`
- ML 미학습(Cold Start): Rule만 사용, Rule 위반 시 confidence 0.5

---

## 시각화 패널

### 3D 산점도 (원시축, PCA 미사용)

- **축**: X=지터(ms), Y=PPS, Z=손실률(%)
- **분류**: 이상(score < threshold, 빨강), 경고(threshold~threshold+0.1, 노랑), 정상(파랑)
- 마커 크기: 이상일수록 큼 (7~18)

### 이상 타임라인

- Y축: 이상 점수 (범위 -1 ~ 0.5)
- 임계선: threshold 수평 점선
- 이상 구간: score < threshold인 연속 구간 빨간 배경

### 신뢰도 게이지 (초록→노랑→빨강)

| 구간    | 색상 | 의미                  |
| ------- | ---- | --------------------- |
| 0–30%   | 초록 | 정상/경미한 이상      |
| 30–70%  | 노랑 | 경계 구간, 주의 필요  |
| 70–100% | 빨강 | 확실한 이상, 즉시 확인 |

- **신뢰도 계산**: `sigmoid((threshold - score) / spread)`, Rule 전용 시 0 또는 0.5

### 기여 특성 차트 (Z-Score)

- |z-score| > 2.0 인 특성만 상위 3개 표시
- 색상: |z| > 3 빨강, > 2 주황, > 1.5 노랑
- Rule 위반 시: jitter_high, pps_low 등 z=2.5로 표시

---

## 학습 흐름

```text
1. 데이터 수집 (최소 500개 샘플, ML_MIN_TRAINING_SAMPLES)
        ↓
2. 특성 추출 (FeatureExtractor)
        ↓
3. 모델 학습 (MLAnomalyDetector.fit)
        ↓
4. 예측 시작 (status: "ready")
        ↓
5. 실시간 모니터링
```

### 학습 조건

- 최소 샘플: 500개
- 재학습 주기: 1시간 (선택적)

---

## 테스트

```bash
python3 -m pytest tests/test_ml_anomaly_detector.py -v
```

### 테스트 항목

- `test_detector_initialization`
- `test_fit_with_sufficient_data`
- `test_predict_normal`
- `test_predict_anomaly`
- `test_contributing_features`
- `test_pipeline_train_success`
- `test_pipeline_predict_after_train`

---

## 확장 계획

### 단기

- 적응형 임계값 자동 조정
- 시간대별 패턴 학습

### 중기

- 다중 모델 앙상블 (AutoEncoder, LSTM)
- 알람 알림 시스템

### 장기

- 예측 유지보수 (Predictive Maintenance)
- 장기 트렌드 분석
