"""
특성 추출기 (Feature Extractor).

PacketStore의 원시 데이터에서 ML 모델에 입력할 특성 벡터를 추출합니다.

도메인 지식 기반 특성:
    - 기본 통계: jitter_current, jitter_p95, pps, loss_rate
    - 파생 특성: jitter_volatility, pps_trend, quality_score
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np

from ..constants import (
    FEATURE_JITTER_SCALING,
    FEATURE_LOSS_SCALING,
    FEATURE_PPS_SCALING,
    FEATURE_VOLATILITY_MIN_THRESHOLD,
    FEATURE_WEIGHT_JITTER,
    FEATURE_WEIGHT_LOSS,
    FEATURE_WEIGHT_PPS,
)


@dataclass
class FeatureVector:
    """ML 모델 입력용 특성 벡터.

    Attributes:
        timestamp: 특성 추출 시각
        features: 특성 이름-값 딕셔너리
        raw_values: 원본 값 (디버깅용)
    """
    timestamp: datetime
    features: dict[str, float]
    raw_values: Optional[dict] = None


class FeatureExtractor:
    """패킷 데이터에서 ML 특성을 추출하는 클래스.

    도메인 지식을 활용하여 이상 탐지에 유용한 특성을 설계합니다:
    - jitter_volatility: 지터 변동성 (std/mean) - 네트워크 불안정 지표
    - pps_trend: PPS 추세 (최근 vs 이전) - 성능 저하 예측
    - quality_score: 종합 품질 점수 - 노이즈 감소

    Example:
        >>> extractor = FeatureExtractor()
        >>> features = extractor.extract(packet_store)
        >>> print(features.features["jitter_volatility"])
    """

    # 특성 이름 목록 (모델 학습 시 순서 유지)
    FEATURE_NAMES: list[str] = [
        "jitter_current",
        "jitter_p95",
        "jitter_volatility",
        "pps",
        "pps_trend",
        "loss_rate",
        "quality_score",
    ]

    def __init__(self, window_sec: int = 30):
        """
        Args:
            window_sec: 특성 계산에 사용할 시간 윈도우 (초)
        """
        self._window_sec = window_sec
        self._prev_pps: Optional[int] = None

    @property
    def feature_names(self) -> list[str]:
        """특성 이름 목록 반환."""
        return self.FEATURE_NAMES.copy()

    def extract(self, stats_dict: dict) -> FeatureVector:
        """통계 딕셔너리에서 특성 벡터 추출.

        Args:
            stats_dict: PacketStore.get_stats_dict() 반환값

        Returns:
            FeatureVector: 추출된 특성 벡터
        """
        # 기본 통계 추출
        jitter_current = stats_dict.get("jitter_current", 0.0)
        jitter_p95 = stats_dict.get("jitter_p95", 0.0)
        pps = stats_dict.get("pps", 0)
        packet_loss = stats_dict.get("packet_loss", 0)

        # 파생 특성 계산
        jitter_volatility = self._calculate_jitter_volatility(
            jitter_current, jitter_p95
        )
        pps_trend = self._calculate_pps_trend(pps)
        loss_rate = self._calculate_loss_rate(pps, packet_loss)
        quality_score = self._calculate_quality_score(
            jitter_current, pps, loss_rate
        )

        features = {
            "jitter_current": float(jitter_current),
            "jitter_p95": float(jitter_p95),
            "jitter_volatility": jitter_volatility,
            "pps": float(pps),
            "pps_trend": pps_trend,
            "loss_rate": loss_rate,
            "quality_score": quality_score,
        }

        return FeatureVector(
            timestamp=datetime.now(),
            features=features,
            raw_values=stats_dict,
        )

    def extract_batch(
        self,
        stats_history: list[dict],
    ) -> np.ndarray:
        """배치 데이터에서 특성 배열 추출 (학습용).

        Args:
            stats_history: 통계 딕셔너리 리스트

        Returns:
            np.ndarray: (n_samples, n_features) 형태의 배열
        """
        features_list = []
        for stats in stats_history:
            fv = self.extract(stats)
            features_list.append(
                [fv.features[name] for name in self.FEATURE_NAMES]
            )
        return np.array(features_list)

    def _calculate_jitter_volatility(
        self,
        jitter_current: float,
        jitter_p95: float,
    ) -> float:
        """지터 변동성 계산.

        변동성 = (P95 - current) / max(P95, 1)
        값이 클수록 지터가 불안정함을 의미.
        """
        if jitter_p95 < FEATURE_VOLATILITY_MIN_THRESHOLD:
            return 0.0
        return abs(jitter_p95 - jitter_current) / max(jitter_p95, 1.0)

    def _calculate_pps_trend(self, current_pps: int) -> float:
        """PPS 추세 계산.

        추세 = (current - prev) / max(prev, 1)
        음수면 성능 저하, 양수면 성능 향상.
        """
        if self._prev_pps is None:
            self._prev_pps = current_pps
            return 0.0

        trend = 0.0 if self._prev_pps < 1 else (current_pps - self._prev_pps) / self._prev_pps

        self._prev_pps = current_pps
        return round(trend, 4)

    def _calculate_loss_rate(self, pps: int, packet_loss: int) -> float:
        """손실률 계산 (%)."""
        total = pps + packet_loss
        if total < 1:
            return 0.0
        return round((packet_loss / total) * 100, 2)

    def _calculate_quality_score(
        self,
        jitter: float,
        pps: int,
        loss_rate: float,
    ) -> float:
        """종합 품질 점수 계산 (0-100).

        가중치:
            - 지터: 40% (낮을수록 좋음)
            - PPS: 40% (높을수록 좋음, 100 기준)
            - 손실률: 20% (낮을수록 좋음)
        """
        # 지터 점수 (5ms 이하 = 100점, 50ms 이상 = 0점)
        jitter_score = max(0, min(100, 100 - (jitter / FEATURE_JITTER_SCALING)))

        # PPS 점수 (1000 PPS = 100점 기준, 라이브 환경 PPS 범위에 맞춤)
        pps_score = max(0, min(100, pps / FEATURE_PPS_SCALING))

        # 손실률 점수 (0% = 100점, 10% 이상 = 0점)
        loss_score = max(0, min(100, 100 - (loss_rate * FEATURE_LOSS_SCALING)))

        # 가중 평균
        score = (
            (jitter_score * FEATURE_WEIGHT_JITTER)
            + (pps_score * FEATURE_WEIGHT_PPS)
            + (loss_score * FEATURE_WEIGHT_LOSS)
        )
        return round(score, 1)

    def reset(self) -> None:
        """상태 초기화 (PPS 추세 계산용)."""
        self._prev_pps = None
