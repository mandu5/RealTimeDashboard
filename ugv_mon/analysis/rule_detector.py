"""
Rule-Based 이상 탐지기.

네트워크 KPI 임계값 기반으로 이상을 탐지합니다.
ML이 학습되기 전에도 즉시 사용 가능합니다.

임계값 기준:
    - 지터 > 50ms → 이상
    - PPS < 50 → 이상
    - 손실률 > 5% → 이상
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RuleResult:
    """Rule-Based 탐지 결과."""

    is_anomaly: bool
    violated_rules: list[str] = field(default_factory=list)
    details: dict[str, float] = field(default_factory=dict)


class RuleDetector:
    """Rule-Based 이상 탐지기.

    네트워크 KPI 임계값을 기반으로 이상을 탐지합니다.
    학습이 필요 없어 Cold Start 문제가 없습니다.

    Attributes:
        thresholds: 각 메트릭의 임계값

    Example:
        >>> detector = RuleDetector()
        >>> result = detector.detect({"jitter_current": 80, "pps": 100, "loss_rate": 1})
        >>> print(result.is_anomaly)  # True (지터 > 50ms)
        >>> print(result.violated_rules)  # ["jitter_high"]
    """

    # 기본 임계값
    DEFAULT_THRESHOLDS: dict[str, float] = {
        "jitter_max_ms": 50.0,      # 지터 상한 (ms)
        "pps_min": 50,              # PPS 하한
        "loss_rate_max": 5.0,       # 손실률 상한 (%)
        "checksum_fail_max": 10.0,  # 체크섬 실패율 상한 (%)
    }

    def __init__(self, thresholds: Optional[dict[str, float]] = None):
        """
        Args:
            thresholds: 커스텀 임계값 (없으면 기본값 사용)
        """
        self._thresholds = {**self.DEFAULT_THRESHOLDS}
        if thresholds:
            self._thresholds.update(thresholds)

    def detect(self, stats: dict) -> RuleResult:
        """Rule-Based 이상 탐지.

        Args:
            stats: 현재 통계 딕셔너리
                - jitter_current: 현재 지터 (ms)
                - pps: 초당 패킷 수
                - loss_rate: 손실률 (%)
                - checksum_fail_rate: 체크섬 실패율 (%)

        Returns:
            RuleResult: 탐지 결과
        """
        violated = []
        details = {}

        # 지터 체크
        jitter = stats.get("jitter_current", 0) or 0
        if jitter > self._thresholds["jitter_max_ms"]:
            violated.append("jitter_high")
            details["jitter"] = jitter

        # PPS 체크
        pps = stats.get("pps", 0) or 0
        if pps < self._thresholds["pps_min"] and pps > 0:  # 0은 무시 (연결 안 됨)
            violated.append("pps_low")
            details["pps"] = pps

        # 손실률 체크
        loss_rate = stats.get("loss_rate", 0) or 0
        if loss_rate > self._thresholds["loss_rate_max"]:
            violated.append("loss_high")
            details["loss_rate"] = loss_rate

        # 체크섬 실패율 체크
        checksum_fail = stats.get("checksum_fail_rate", 0) or 0
        if checksum_fail > self._thresholds["checksum_fail_max"]:
            violated.append("checksum_fail")
            details["checksum_fail_rate"] = checksum_fail

        return RuleResult(
            is_anomaly=len(violated) > 0,
            violated_rules=violated,
            details=details,
        )
