"""
ML 이상 탐지 서비스.

ML 파이프라인과 Rule 탐지기를 앙상블하여 이상 탐지를 수행합니다.
Single Responsibility: ML/Rule 앙상블 탐지만 수행.

책임:
    1. MLPipeline 관리 (학습/예측)
    2. RuleDetector 관리
    3. 앙상블 판정 (Rule OR ML)
    4. 점수/레코드 히스토리 관리

사용 예시:
    >>> ml = MLService()
    >>> result = ml.predict(store)  # PacketStore
    >>> print(result["is_anomaly"])
"""

import logging
import threading
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from ..constants import (
    ML_DEFAULT_THRESHOLD,
    ML_DISPLAY_RECORDS,
    ML_DISPLAY_SCORES,
    ML_FALLBACK_ANOMALY_SCORE,
    ML_MAX_CHART_RECORDS,
    ML_MAX_SCORE_HISTORY,
    ML_MIN_TRAINING_SAMPLES,
    ML_RULE_ONLY_CONFIDENCE,
    ML_RULE_VIOLATED_Z_SCORE,
)

if TYPE_CHECKING:
    from ..analysis.ml_anomaly_detector import AnomalyResult
    from ..analysis.ml_pipeline import MLPipeline
    from ..analysis.rule_detector import RuleDetector, RuleResult
    from ..store.packet_store import PacketStore

logger = logging.getLogger(__name__)


class MLService:
    """ML 이상 탐지 서비스.

    Rule-Based + ML 앙상블 탐지를 수행합니다.
    - Rule: 항상 실행 (Cold Start 대응)
    - ML: 학습 완료 후 실행
    - 앙상블: 둘 중 하나라도 이상이면 최종 이상

    Args:
        min_samples: 학습에 필요한 최소 샘플 수
        max_records: 3D 차트용 최대 레코드 수
        max_history: 타임라인용 최대 히스토리 수
    """

    def __init__(
        self,
        min_samples: int = ML_MIN_TRAINING_SAMPLES,
        max_records: int = ML_MAX_CHART_RECORDS,
        max_history: int = ML_MAX_SCORE_HISTORY,
    ):
        self._min_samples = min_samples
        self._max_records = max_records
        self._max_history = max_history

        # 파이프라인
        self._pipeline: Optional["MLPipeline"] = None
        self._rule_detector: Optional["RuleDetector"] = None

        # 히스토리
        self._history_lock = threading.Lock()
        self._records: list[dict] = []  # 3D 차트용
        self._score_history: list[dict] = []  # 타임라인용

        self._init_detectors()

    def _init_detectors(self) -> None:
        """탐지기 초기화."""
        try:
            from ..analysis.ml_pipeline import MLPipeline
            from ..analysis.rule_detector import RuleDetector

            self._pipeline = MLPipeline()
            self._rule_detector = RuleDetector()

            # MLPipeline.__init__에서 _try_load_model() 자동 호출됨
            if self._pipeline.is_trained:
                logger.info("[ML] 저장된 모델 로드 완료")
            else:
                logger.info("[ML] 저장된 모델 없음, Rule 탐지만 활성화")
        except ImportError as e:
            logger.warning(f"[ML] 탐지기 로드 실패: {e}")

    # =========================================================================
    # 예측
    # =========================================================================

    def predict(self, store: "PacketStore") -> dict:
        """이상 탐지 수행.

        Args:
            store: 통계를 가져올 PacketStore

        Returns:
            ML 데이터 딕셔너리
        """
        now = datetime.now()

        if not store:
            return {"model_status": "not_ready"}

        # 현재 통계 가져오기
        current_stats = self._get_current_stats(store)

        # 레코드 히스토리 업데이트
        self._update_records(current_stats, now)

        # === Rule-Based 탐지 (항상 실행) ===
        rule_result = None
        if self._rule_detector:
            rule_result = self._rule_detector.detect(current_stats)

        # === ML 탐지 (학습 후 실행) ===
        ml_result = None
        ml_ready = False

        if self._pipeline:
            if not self._pipeline.is_trained:
                # 학습 시도
                stats_history = store.get_stats_history(limit=self._min_samples)
                if len(stats_history) >= self._min_samples:
                    self._pipeline.train(stats_history)
                    logger.info("[ML] 자동 학습 완료, 앙상블 모드 활성화")
                    ml_ready = True
            else:
                ml_ready = True

            if ml_ready:
                ml_result = self._pipeline.predict(current_stats)
                self._update_score_history(ml_result.anomaly_score, now)

        # === 앙상블 판정 ===
        return self._build_result(rule_result, ml_result, ml_ready)

    def _get_current_stats(self, store: "PacketStore") -> dict:
        """PacketStore에서 ML용 통계 추출 (Live 모드 호환)."""
        stats = store.get_stats_dict()
        if stats is None:
            stats = {}
        stats["parse_success_rate"] = store.get_parse_success_rate()
        stats["checksum_fail_rate"] = store.get_checksum_fail_rate()
        return stats

    def _build_result(
        self,
        rule_result: Optional["RuleResult"],
        ml_result: Optional["AnomalyResult"],
        ml_ready: bool,
    ) -> dict:
        """앙상블 결과 빌드."""
        rule_anomaly = rule_result.is_anomaly if rule_result else False
        ml_anomaly = ml_result.is_anomaly if ml_result else False

        # ML이 학습된 상태에서는 ML 판정을 우선 사용
        if ml_result:
            final_anomaly = ml_anomaly or rule_anomaly
        else:
            final_anomaly = rule_anomaly

        detection_source = self._determine_detection_source(rule_anomaly, ml_anomaly)
        confidence = self._calculate_confidence(
            rule_anomaly, ml_anomaly, ml_result, final_anomaly
        )
        contributing_features = self._extract_contributing_features(
            rule_result, ml_result
        )
        threshold = self._get_current_threshold()

        with self._history_lock:
            records = self._records[-ML_DISPLAY_RECORDS:]
            score_history = self._score_history[-ML_DISPLAY_SCORES:]

        return {
            "model_status": "ready" if ml_ready else "rule_only",
            "is_anomaly": final_anomaly,
            "anomaly_score": (
                ml_result.anomaly_score if ml_result
                else (ML_FALLBACK_ANOMALY_SCORE if final_anomaly else 0.0)
            ),
            "confidence": confidence,
            "threshold": threshold,
            "detection_source": detection_source,
            "rule_violated": rule_result.violated_rules if rule_result else [],
            "contributing_features": contributing_features,
            "records": records,
            "score_history": score_history,
        }

    def _determine_detection_source(
        self,
        rule_anomaly: bool,
        ml_anomaly: bool,
    ) -> Optional[str]:
        """탐지 소스 결정."""
        if rule_anomaly and ml_anomaly:
            return "Both"
        elif rule_anomaly:
            return "Rule"
        elif ml_anomaly:
            return "ML"
        return None

    def _calculate_confidence(
        self,
        rule_anomaly: bool,
        ml_anomaly: bool,
        ml_result: Optional["AnomalyResult"],
        final_anomaly: bool,
    ) -> float:
        """신뢰도 계산."""
        if ml_result:
            if ml_anomaly:
                return ml_result.confidence
            elif rule_anomaly and not ml_anomaly:
                return ML_RULE_ONLY_CONFIDENCE
            else:
                return ml_result.confidence
        elif final_anomaly:
            return ML_RULE_ONLY_CONFIDENCE
        return 0.0

    def _extract_contributing_features(
        self,
        rule_result: Optional["RuleResult"],
        ml_result: Optional["AnomalyResult"],
    ) -> list[dict]:
        """기여 특성 추출."""
        if ml_result and ml_result.contributing_features:
            return [
                {"name": f["name"], "z_score": f["z_score"]}
                for f in ml_result.contributing_features
            ]
        elif rule_result and rule_result.violated_rules:
            return [
                {"name": rule, "z_score": ML_RULE_VIOLATED_Z_SCORE}
                for rule in rule_result.violated_rules
            ]
        return []

    def _get_current_threshold(self) -> float:
        """현재 이상 탐지 임계값 반환."""
        if self._pipeline and self._pipeline.is_trained:
            status = self._pipeline.get_status()
            return status.get("threshold", ML_DEFAULT_THRESHOLD)
        return ML_DEFAULT_THRESHOLD

    # =========================================================================
    # 히스토리 관리
    # =========================================================================

    def _update_records(self, stats: dict, now: datetime) -> None:
        """3D 차트용 레코드 업데이트."""
        if stats is None:
            stats = {}
        record = {
            "timestamp": now.strftime("%H:%M:%S"),
            "jitter_current": stats.get("jitter_current", 0),
            "pps": stats.get("pps", 0),
            "loss_rate": stats.get("loss_rate", 0),
            "anomaly_score": 0,
        }
        with self._history_lock:
            self._records.append(record)
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records:]

    def _update_score_history(self, score: float, now: datetime) -> None:
        """타임라인용 점수 히스토리 업데이트."""
        with self._history_lock:
            self._score_history.append({
                "timestamp": now.strftime("%H:%M:%S"),
                "score": score,
            })
            if len(self._score_history) > self._max_history:
                self._score_history = self._score_history[-self._max_history:]

            # 레코드에 점수 반영
            if self._records:
                self._records[-1]["anomaly_score"] = score

    def reset(self) -> None:
        """히스토리 초기화."""
        with self._history_lock:
            self._records.clear()
            self._score_history.clear()
