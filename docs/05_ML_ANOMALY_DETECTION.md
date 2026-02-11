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
    #         is_anomaly, triggered_rules
```

### analysis/feature_extractor.py

통계 데이터에서 ML 특성 추출

```python
class FeatureExtractor:
    def extract(self, data: Dict) -> np.ndarray
    # [pps, jitter, packet_loss, availability, msg_code_ratio...]
```

---

## 특성 벡터 (Features)

ML 모델에 입력되는 특성:

| 특성          | 설명         | 정규화       |
| ------------- | ------------ | ------------ |
| pps           | 초당 패킷 수 | 0-1 스케일링 |
| jitter_p95    | 지터 P95     | 로그 스케일  |
| packet_loss   | 패킷 손실 수 | 0-1 스케일링 |
| availability  | 가용성 %     | 0-100        |
| parse_success | 파싱 성공률  | 0-100        |
| msg_01_ratio  | 0x01 비율    | 0-1          |
| msg_25_ratio  | 0x25 비율    | 0-1          |
| msg_40_ratio  | 0x40 비율    | 0-1          |

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
    contamination=0.05,    # 이상치 비율
    random_state=42,       # 재현성
    max_samples='auto'
)
```

### 이상 점수

- **음수**: 정상 (나무 깊이가 깊음)
- **양수**: 이상 (나무 깊이가 얕음)
- **임계값**: 5σ (표준편차 5배)

---

## 규칙 기반 탐지

### 탐지 규칙

| 규칙        | 조건               | 심각도 |
| ----------- | ------------------ | ------ |
| PPS 급락    | pps < 1            | HIGH   |
| 지터 급등   | jitter_p95 > 100ms | MEDIUM |
| 가용성 저하 | availability < 80% | HIGH   |
| 패킷 손실   | packet_loss > 10   | MEDIUM |

### 앙상블 로직

```python
# 둘 중 하나라도 이상 감지 시 알람
is_anomaly = ml_result or rule_result
```

---

## 시각화 패널

### 3D 산점도 (PCA)

- 3차원 PCA 축소
- 정상(파랑) / 이상(빨강) 점
- 현재 위치 하이라이트

### 이상 타임라인

- 시간별 이상 점수
- 임계값 라인 표시
- 이상 구간 음영

### 신뢰도 게이지

- 0-100% 신뢰도
- 색상 그라데이션 (초록→빨강)

### 기여 특성 차트

- 수평 막대 그래프
- 이상에 가장 많이 기여한 특성

---

## 학습 흐름

```text
1. 데이터 수집 (최소 100개 샘플)
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

- 최소 샘플: 100개
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
