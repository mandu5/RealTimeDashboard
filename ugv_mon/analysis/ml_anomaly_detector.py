"""
ML 이상 탐지기 (Isolation Forest 기반).

다변량 이상 탐지를 통해 단일 변수 임계값으로는 발견할 수 없는
복합적인 이상 패턴을 탐지합니다.

왜 Isolation Forest인가:
    1. 비지도 학습 → 라벨 없이 학습 가능
    2. O(n) 시간복잡도 → 실시간 적합
    3. 이상 점수 제공 → 해석 가능
    4. sklearn 내장 → 폐쇄망 배포 용이

Example:
    >>> detector = MLAnomalyDetector(contamination=0.05)
    >>> detector.fit(training_data, feature_names)
    >>> result = detector.predict({"jitter_current": 5.0, "pps": 80, ...})
    >>> print(result.is_anomaly, result.anomaly_score)
"""

import logging
import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ..constants import (
    ML_N_ESTIMATORS,
    ML_RANDOM_STATE,
    ML_TOP_CONTRIBUTING_FEATURES,
    ML_Z_SCORE_THRESHOLD,
)

logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    """이상 탐지 결과.

    Attributes:
        is_anomaly: 이상 여부
        anomaly_score: 이상 점수 (-1 ~ 0, 낮을수록 이상)
        confidence: 신뢰도 (0 ~ 1)
        contributing_features: 주요 기여 특성 리스트
    """
    is_anomaly: bool
    anomaly_score: float
    confidence: float
    contributing_features: list[dict[str, float]] = field(default_factory=list)


class MLAnomalyDetector:
    """다변량 이상 탐지기 (Isolation Forest 기반).

    Features:
        - 비지도 학습으로 정상 패턴 학습
        - 실시간 이상 점수 제공
        - 기여 특성 분석으로 해석 가능성 확보

    Attributes:
        contamination: 예상 이상치 비율 (기본 5%)
        is_fitted: 모델 학습 완료 여부
        feature_names: 학습된 특성 이름 목록
    """

    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = ML_N_ESTIMATORS,
        random_state: int = ML_RANDOM_STATE,
    ):
        """
        Args:
            contamination: 예상 이상치 비율 (0.01 ~ 0.5)
            n_estimators: 트리 개수 (기본 100)
            random_state: 재현성을 위한 랜덤 시드
        """
        self._contamination = contamination
        self._model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1,
        )
        self._scaler = StandardScaler()
        self._is_fitted = False
        self._feature_names: list[str] = []

    @property
    def is_fitted(self) -> bool:
        """모델 학습 완료 여부."""
        return self._is_fitted

    @property
    def feature_names(self) -> list[str]:
        """학습된 특성 이름 목록."""
        return self._feature_names.copy()

    def fit(
        self,
        data: np.ndarray,
        feature_names: list[str],
    ) -> "MLAnomalyDetector":
        """모델 학습.

        Args:
            data: 학습 데이터 (n_samples, n_features)
            feature_names: 특성 이름 리스트

        Returns:
            self: 학습된 모델 인스턴스

        Raises:
            ValueError: 데이터가 비어있거나 특성 개수 불일치
        """
        if len(data) == 0:
            raise ValueError("학습 데이터가 비어있습니다.")
        if data.shape[1] != len(feature_names):
            raise ValueError(
                f"특성 개수 불일치: 데이터={data.shape[1]}, "
                f"이름={len(feature_names)}"
            )

        self._feature_names = feature_names

        # 스케일링 + 학습
        scaled_data = self._scaler.fit_transform(data)
        self._model.fit(scaled_data)
        self._is_fitted = True

        logger.info(
            f"[ML] 모델 학습 완료: {len(data)} 샘플, "
            f"{len(feature_names)} 특성"
        )
        return self

    def predict(self, features: dict[str, float]) -> AnomalyResult:
        """실시간 이상 탐지.

        Args:
            features: 특성 딕셔너리 (feature_name -> value)

        Returns:
            AnomalyResult: 탐지 결과
        """
        if not self._is_fitted:
            logger.debug("[ML] 모델이 학습되지 않아 기본 결과 반환")
            return AnomalyResult(
                is_anomaly=False,
                anomaly_score=0.0,
                confidence=0.0,
                contributing_features=[],
            )

        # 특성 벡터 생성 (학습 시 순서 유지)
        x = np.array([
            [features.get(name, 0.0) for name in self._feature_names]
        ])
        x_scaled = self._scaler.transform(x)

        # 예측 (1: 정상, -1: 이상)
        prediction = self._model.predict(x_scaled)[0]
        score = self._model.score_samples(x_scaled)[0]

        # 기여 특성 분석
        contributing = self._analyze_contribution(x_scaled[0])

        return AnomalyResult(
            is_anomaly=(prediction == -1),
            anomaly_score=round(score, 4),
            confidence=self._score_to_confidence(score),
            contributing_features=contributing,
        )

    def _analyze_contribution(
        self,
        x_scaled: np.ndarray,
    ) -> list[dict[str, float]]:
        """이상에 기여한 주요 특성 분석.

        Z-score 기반으로 정상 범위에서 벗어난 정도를 측정합니다.

        Args:
            x_scaled: 스케일링된 특성 벡터

        Returns:
            상위 3개 기여 특성 (name, z_score)
        """
        contributions = []
        for val, name in zip(x_scaled, self._feature_names):
            z_score = float(val)  # StandardScaler 출력 = Z-score
            if abs(z_score) > ML_Z_SCORE_THRESHOLD:
                contributions.append({
                    "name": name,
                    "z_score": round(z_score, 2),
                })

        # Z-score 절대값 기준 정렬
        contributions.sort(key=lambda x: abs(x["z_score"]), reverse=True)
        return contributions[:ML_TOP_CONTRIBUTING_FEATURES]

    def _score_to_confidence(self, score: float) -> float:
        """이상 점수를 신뢰도 (0~1)로 변환.

        모델의 실제 결정 경계(offset_)를 기준으로 sigmoid 스무딩 적용.
        offset에서 confidence ≈ 0.5, 그 이상 → 0, 그 이하 → 1.
        """
        threshold = float(self._model.offset_)
        spread = max(abs(threshold) * 0.5, 0.05)
        raw = (threshold - score) / spread
        confidence = 1.0 / (1.0 + np.exp(-raw))
        return round(float(confidence), 2)

    def save(self, filepath: str) -> None:
        """모델 저장.

        Args:
            filepath: 저장 경로 (.pkl)
        """
        if not self._is_fitted:
            raise RuntimeError("학습되지 않은 모델은 저장할 수 없습니다.")

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "wb") as f:
            pickle.dump({
                "model": self._model,
                "scaler": self._scaler,
                "feature_names": self._feature_names,
                "contamination": self._contamination,
            }, f)

        logger.info(f"[ML] 모델 저장: {filepath}")

    @classmethod
    def load(cls, filepath: str) -> "MLAnomalyDetector":
        """저장된 모델 로드.

        Args:
            filepath: 모델 파일 경로 (.pkl)

        Returns:
            로드된 MLAnomalyDetector 인스턴스
        """
        with open(filepath, "rb") as f:
            data = pickle.load(f)

        detector = cls(contamination=data["contamination"])
        detector._model = data["model"]
        detector._scaler = data["scaler"]
        detector._feature_names = data["feature_names"]
        detector._is_fitted = True

        logger.info(f"[ML] 모델 로드: {filepath}")
        return detector

    def get_threshold(self) -> float:
        """현재 이상 탐지 임계값 반환.

        Returns:
            score가 이 값보다 낮으면 이상으로 판정
        """
        if not self._is_fitted:
            return 0.0
        return float(self._model.offset_)
