"""
ML 파이프라인 관리자.

PacketStore → FeatureExtractor → MLAnomalyDetector 흐름을 관리합니다.

데이터 흐름:
    1. PacketStore에서 통계 가져오기
    2. FeatureExtractor로 특성 추출
    3. MLAnomalyDetector로 이상 탐지
    4. 결과 캐싱 및 반환
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .feature_extractor import FeatureExtractor
from .ml_anomaly_detector import AnomalyResult, MLAnomalyDetector

logger = logging.getLogger(__name__)


class MLPipeline:
    """ML 파이프라인 관리자.

    학습, 예측, 모델 저장/로드를 통합 관리합니다.

    Attributes:
        model_path: 모델 저장 경로
        is_trained: 모델 학습 완료 여부

    Example:
        >>> pipeline = MLPipeline(model_path="models/anomaly.pkl")
        >>> if pipeline.train(stats_history):
        ...     result = pipeline.predict(current_stats)
        ...     print(result.is_anomaly)
    """

    DEFAULT_MODEL_PATH = "models/anomaly_detector.pkl"
    MIN_TRAINING_SAMPLES = 500  # 최소 학습 샘플 수

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        contamination: float = 0.05,
    ):
        """
        Args:
            model_path: 모델 저장/로드 경로
            contamination: 예상 이상치 비율
        """
        self._model_path = model_path
        self._extractor = FeatureExtractor()
        self._detector = MLAnomalyDetector(contamination=contamination)

        # 캐시
        self._last_result: Optional[AnomalyResult] = None
        self._last_predict_time: Optional[datetime] = None
        self._cache_duration_sec = 1.0  # 1초 캐시

        # 학습 이력
        self._training_history: list[dict[str, Any]] = []

        # 저장된 모델 로드 시도
        self._try_load_model()

    @property
    def is_trained(self) -> bool:
        """모델 학습 완료 여부."""
        return self._detector.is_fitted

    @property
    def feature_names(self) -> list[str]:
        """사용 중인 특성 이름 목록."""
        return self._extractor.feature_names

    def train(
        self,
        stats_history: list[dict],
        save: bool = True,
    ) -> bool:
        """모델 학습.

        Args:
            stats_history: 통계 딕셔너리 히스토리
            save: 학습 후 모델 저장 여부

        Returns:
            학습 성공 여부
        """
        if len(stats_history) < self.MIN_TRAINING_SAMPLES:
            logger.warning(
                f"[ML] 학습 데이터 부족: {len(stats_history)} < "
                f"{self.MIN_TRAINING_SAMPLES}"
            )
            return False

        try:
            # 특성 추출
            features = self._extractor.extract_batch(stats_history)

            # 학습
            self._detector.fit(features, self._extractor.feature_names)

            # 학습 이력 기록
            self._training_history.append({
                "timestamp": datetime.now().isoformat(),
                "samples": len(stats_history),
                "features": len(self._extractor.feature_names),
            })

            # 모델 저장
            if save:
                self._detector.save(self._model_path)

            logger.info(
                f"[ML] 학습 완료: {len(stats_history)} 샘플"
            )
            return True

        except Exception as e:
            logger.error(f"[ML] 학습 실패: {e}")
            return False

    def predict(self, stats_dict: dict) -> AnomalyResult:
        """실시간 이상 탐지.

        Args:
            stats_dict: 현재 통계 딕셔너리

        Returns:
            AnomalyResult: 탐지 결과 (학습 안 됐으면 기본값)
        """
        # 캐시 확인
        now = datetime.now()
        if (
            self._last_result is not None
            and self._last_predict_time is not None
            and (now - self._last_predict_time).total_seconds() < self._cache_duration_sec
        ):
            return self._last_result

        # 학습 안 됐으면 기본값
        if not self.is_trained:
            return AnomalyResult(
                is_anomaly=False,
                anomaly_score=0.0,
                confidence=0.0,
                contributing_features=[],
            )

        # 특성 추출 및 예측
        fv = self._extractor.extract(stats_dict)
        result = self._detector.predict(fv.features)

        # 캐시 갱신
        self._last_result = result
        self._last_predict_time = now

        return result

    def get_status(self) -> dict[str, Any]:
        """ML 파이프라인 상태 반환.

        Returns:
            status: "ready", "training", "not_ready"
            samples: 학습에 사용된 샘플 수 (있으면)
            threshold: 이상 탐지 임계값 (있으면)
        """
        if not self.is_trained:
            return {
                "status": "not_ready",
                "message": "모델이 학습되지 않았습니다.",
            }

        return {
            "status": "ready",
            "threshold": self._detector.get_threshold(),
            "features": self._detector.feature_names,
            "training_history": self._training_history[-5:],  # 최근 5개
        }

    def reset(self) -> None:
        """파이프라인 상태 초기화."""
        self._extractor.reset()
        self._last_result = None
        self._last_predict_time = None
        logger.info("[ML] 파이프라인 초기화")

    def _try_load_model(self) -> None:
        """저장된 모델 로드 시도."""
        if Path(self._model_path).exists():
            try:
                self._detector = MLAnomalyDetector.load(self._model_path)
                logger.info(f"[ML] 저장된 모델 로드: {self._model_path}")
            except Exception as e:
                logger.warning(f"[ML] 모델 로드 실패: {e}")
