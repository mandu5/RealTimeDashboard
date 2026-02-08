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
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
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
        min_samples: int = 500,
        max_records: int = 200,
        max_history: int = 120,
    ):
        self._min_samples = min_samples
        self._max_records = max_records
        self._max_history = max_history

        # 파이프라인
        self._pipeline: Optional[object] = None  # MLPipeline
        self._rule_detector: Optional[object] = None  # RuleDetector

        # 히스토리
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

            # 기존 모델 로드 시도
            if self._pipeline.load():
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
            if not self._pipeline.is_ready:
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
        """PacketStore에서 ML용 통계 추출."""
        return {
            "jitter_current": store.last_jitter or 0,
            "jitter_p95": store.get_jitter_p95() or 0,
            "pps": store.pps,
            "loss_rate": store.packet_loss_rate,
            "parse_success_rate": store.get_parse_success_rate(),
            "checksum_fail_rate": store.get_checksum_fail_rate(),
        }

    def _build_result(self, rule_result, ml_result, ml_ready: bool) -> dict:
        """앙상블 결과 빌드."""
        rule_anomaly = rule_result.is_anomaly if rule_result else False
        ml_anomaly = ml_result.is_anomaly if ml_result else False
        final_anomaly = rule_anomaly or ml_anomaly

        # 탐지 소스 결정
        if rule_anomaly and ml_anomaly:
            detection_source = "Both"
        elif rule_anomaly:
            detection_source = "Rule"
        elif ml_anomaly:
            detection_source = "ML"
        else:
            detection_source = None

        # 신뢰도 계산
        if ml_result:
            confidence = ml_result.confidence
        elif final_anomaly:
            confidence = 0.7  # Rule만 있을 때 기본 신뢰도
        else:
            confidence = 0.0

        # 기여 특성
        contributing_features = []
        if ml_result and ml_result.contributing_features:
            contributing_features = [
                {"name": f["name"], "z_score": f["z_score"]}
                for f in ml_result.contributing_features
            ]
        elif rule_result and rule_result.violated_rules:
            for rule in rule_result.violated_rules:
                contributing_features.append({
                    "name": rule,
                    "z_score": 2.5,
                })

        return {
            "model_status": "ready" if ml_ready else "rule_only",
            "is_anomaly": final_anomaly,
            "anomaly_score": (
                ml_result.anomaly_score if ml_result
                else (-0.5 if final_anomaly else 0.0)
            ),
            "confidence": confidence,
            "detection_source": detection_source,
            "rule_violated": rule_result.violated_rules if rule_result else [],
            "contributing_features": contributing_features,
            "records": self._records[-100:],
            "score_history": self._score_history[-60:],
        }

    # =========================================================================
    # 히스토리 관리
    # =========================================================================

    def _update_records(self, stats: dict, now: datetime) -> None:
        """3D 차트용 레코드 업데이트."""
        record = {
            "timestamp": now.strftime("%H:%M:%S"),
            "jitter_current": stats.get("jitter_current", 0),
            "pps": stats.get("pps", 0),
            "loss_rate": stats.get("loss_rate", 0),
            "anomaly_score": 0,
        }
        self._records.append(record)
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

    def _update_score_history(self, score: float, now: datetime) -> None:
        """타임라인용 점수 히스토리 업데이트."""
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
        self._records.clear()
        self._score_history.clear()

    # =========================================================================
    # 프로퍼티
    # =========================================================================

    @property
    def is_ready(self) -> bool:
        """ML 모델 학습 완료 여부."""
        if self._pipeline:
            return self._pipeline.is_ready
        return False
