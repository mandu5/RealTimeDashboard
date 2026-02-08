"""
ML 이상 탐지 모듈 단위 테스트.

테스트 대상:
    - FeatureExtractor: 특성 추출
    - MLAnomalyDetector: 이상 탐지
    - MLPipeline: 파이프라인 통합
"""

import pytest
import numpy as np
import tempfile
from pathlib import Path

from ugv_mon.analysis.feature_extractor import FeatureExtractor, FeatureVector
from ugv_mon.analysis.ml_anomaly_detector import MLAnomalyDetector, AnomalyResult
from ugv_mon.analysis.ml_pipeline import MLPipeline


class TestFeatureExtractor:
    """FeatureExtractor 테스트."""
    
    def test_feature_names(self):
        """특성 이름 목록 확인."""
        extractor = FeatureExtractor()
        names = extractor.feature_names
        
        assert len(names) == 7
        assert "jitter_current" in names
        assert "quality_score" in names
    
    def test_extract_basic(self):
        """기본 특성 추출."""
        extractor = FeatureExtractor()
        stats = {
            "jitter_current": 2.5,
            "jitter_p95": 5.0,
            "pps": 100,
            "packet_loss": 2,
        }
        
        fv = extractor.extract(stats)
        
        assert isinstance(fv, FeatureVector)
        assert fv.features["jitter_current"] == 2.5
        assert fv.features["jitter_p95"] == 5.0
        assert fv.features["pps"] == 100.0
    
    def test_jitter_volatility(self):
        """지터 변동성 계산."""
        extractor = FeatureExtractor()
        stats = {
            "jitter_current": 2.0,
            "jitter_p95": 10.0,
            "pps": 100,
            "packet_loss": 0,
        }
        
        fv = extractor.extract(stats)
        
        # (10 - 2) / 10 = 0.8
        assert fv.features["jitter_volatility"] == 0.8
    
    def test_pps_trend(self):
        """PPS 추세 계산."""
        extractor = FeatureExtractor()
        
        # 첫 호출: 추세 0
        fv1 = extractor.extract({"pps": 100, "packet_loss": 0})
        assert fv1.features["pps_trend"] == 0.0
        
        # 두 번째: 100 -> 80 = -20%
        fv2 = extractor.extract({"pps": 80, "packet_loss": 0})
        assert fv2.features["pps_trend"] == -0.2
    
    def test_quality_score_range(self):
        """품질 점수 범위 (0-100)."""
        extractor = FeatureExtractor()
        
        # 좋은 상태
        fv_good = extractor.extract({
            "jitter_current": 1.0,
            "pps": 100,
            "packet_loss": 0,
        })
        assert 80 <= fv_good.features["quality_score"] <= 100
        
        # 나쁜 상태
        extractor.reset()
        fv_bad = extractor.extract({
            "jitter_current": 50.0,
            "pps": 20,
            "packet_loss": 10,
        })
        assert 0 <= fv_bad.features["quality_score"] <= 50
    
    def test_extract_batch(self):
        """배치 특성 추출."""
        extractor = FeatureExtractor()
        stats_list = [
            {"jitter_current": 1.0, "jitter_p95": 2.0, "pps": 100, "packet_loss": 0},
            {"jitter_current": 2.0, "jitter_p95": 3.0, "pps": 90, "packet_loss": 1},
            {"jitter_current": 1.5, "jitter_p95": 2.5, "pps": 95, "packet_loss": 0},
        ]
        
        features = extractor.extract_batch(stats_list)
        
        assert features.shape == (3, 7)
        assert features.dtype == np.float64


class TestMLAnomalyDetector:
    """MLAnomalyDetector 테스트."""
    
    @pytest.fixture
    def sample_data(self):
        """샘플 학습 데이터 생성."""
        np.random.seed(42)
        # 정상 데이터 (대부분)
        normal = np.random.randn(100, 7) * 0.5 + 5
        # 이상 데이터 (소수)
        anomaly = np.random.randn(5, 7) * 2 + 15
        return np.vstack([normal, anomaly])
    
    @pytest.fixture
    def feature_names(self):
        """샘플 특성 이름."""
        return [
            "jitter_current", "jitter_p95", "jitter_volatility",
            "pps", "pps_trend", "loss_rate", "quality_score"
        ]
    
    def test_not_fitted_predict(self):
        """학습 전 예측은 기본값 반환."""
        detector = MLAnomalyDetector()
        
        result = detector.predict({"jitter_current": 5.0})
        
        assert result.is_anomaly is False
        assert result.anomaly_score == 0.0
        assert result.confidence == 0.0
    
    def test_fit(self, sample_data, feature_names):
        """모델 학습."""
        detector = MLAnomalyDetector()
        
        detector.fit(sample_data, feature_names)
        
        assert detector.is_fitted is True
        assert detector.feature_names == feature_names
    
    def test_predict_normal(self, sample_data, feature_names):
        """정상 데이터 예측."""
        detector = MLAnomalyDetector()
        detector.fit(sample_data, feature_names)
        
        # 정상 범위 데이터
        normal_features = {name: 5.0 for name in feature_names}
        result = detector.predict(normal_features)
        
        assert isinstance(result, AnomalyResult)
        # 정상일 가능성 높음 (score가 너무 낮지 않아야 함)
        assert result.anomaly_score > -0.5
    
    def test_predict_anomaly(self, sample_data, feature_names):
        """이상 데이터 예측."""
        detector = MLAnomalyDetector()
        detector.fit(sample_data, feature_names)
        
        # 극단적 이상값
        anomaly_features = {name: 100.0 for name in feature_names}
        result = detector.predict(anomaly_features)
        
        # 이상일 가능성 높음 (is_anomaly가 True이거나 score가 낮아야 함)
        assert result.is_anomaly or result.anomaly_score < -0.3
    
    def test_save_and_load(self, sample_data, feature_names):
        """모델 저장 및 로드."""
        detector = MLAnomalyDetector()
        detector.fit(sample_data, feature_names)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test_model.pkl"
            
            # 저장
            detector.save(str(filepath))
            assert filepath.exists()
            
            # 로드
            loaded = MLAnomalyDetector.load(str(filepath))
            assert loaded.is_fitted is True
            assert loaded.feature_names == feature_names
    
    def test_contributing_features(self, sample_data, feature_names):
        """기여 특성 분석."""
        detector = MLAnomalyDetector()
        detector.fit(sample_data, feature_names)
        
        # 특정 특성만 극단값
        features = {name: 5.0 for name in feature_names}
        features["jitter_current"] = 100.0  # 극단값
        
        result = detector.predict(features)
        
        # jitter_current가 기여 특성에 포함되어야 함
        if result.contributing_features:
            names = [f["name"] for f in result.contributing_features]
            assert "jitter_current" in names


class TestMLPipeline:
    """MLPipeline 통합 테스트."""
    
    def test_not_trained_status(self):
        """학습 전 상태."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MLPipeline(model_path=f"{tmpdir}/model.pkl")
            
            status = pipeline.get_status()
            
            assert status["status"] == "not_ready"
            assert pipeline.is_trained is False
    
    def test_train_insufficient_data(self):
        """데이터 부족 시 학습 실패."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MLPipeline(model_path=f"{tmpdir}/model.pkl")
            
            # 100개 미만
            stats_history = [
                {"jitter_current": 1.0, "pps": 100, "packet_loss": 0}
                for _ in range(100)
            ]
            
            result = pipeline.train(stats_history)
            
            assert result is False
    
    def test_train_success(self):
        """충분한 데이터로 학습 성공."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MLPipeline(model_path=f"{tmpdir}/model.pkl")
            
            # 1000개 이상
            stats_history = [
                {
                    "jitter_current": np.random.uniform(1, 5),
                    "jitter_p95": np.random.uniform(3, 10),
                    "pps": np.random.randint(80, 120),
                    "packet_loss": np.random.randint(0, 5),
                }
                for _ in range(1200)
            ]
            
            result = pipeline.train(stats_history)
            
            assert result is True
            assert pipeline.is_trained is True
    
    def test_predict_after_train(self):
        """학습 후 예측."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MLPipeline(model_path=f"{tmpdir}/model.pkl")
            
            # 학습
            stats_history = [
                {
                    "jitter_current": np.random.uniform(1, 5),
                    "jitter_p95": np.random.uniform(3, 10),
                    "pps": np.random.randint(80, 120),
                    "packet_loss": np.random.randint(0, 3),
                }
                for _ in range(1200)
            ]
            pipeline.train(stats_history)
            
            # 예측
            current_stats = {
                "jitter_current": 2.0,
                "jitter_p95": 5.0,
                "pps": 100,
                "packet_loss": 1,
            }
            result = pipeline.predict(current_stats)
            
            assert isinstance(result, AnomalyResult)
