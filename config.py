"""
UGV-MON Dashboard Configuration
설정 파일 - 환경변수 또는 직접 수정하여 사용
"""

import os
from datetime import timedelta

class Config:
    """기본 설정"""
    
    # 애플리케이션 설정
    APP_NAME = "UGV-MON Dashboard"
    VERSION = "6.0"
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 8050))
    
    # 폴링 설정
    POLL_INTERVAL_MS = int(os.getenv('POLL_INTERVAL_MS', 2000))  # 2초
    
    # 데이터 보존 설정
    MAX_LOG_ENTRIES = int(os.getenv('MAX_LOG_ENTRIES', 200))
    MAX_CHART_POINTS = int(os.getenv('MAX_CHART_POINTS', 60))
    
    # 타임라인 설정
    TIMELINE_DURATION_SECONDS = int(os.getenv('TIMELINE_DURATION', 3600))  # 1시간
    
    # UDP 수신 설정 (실제 데이터 사용 시)
    UDP_HOST = os.getenv('UDP_HOST', '0.0.0.0')
    UDP_PORT = int(os.getenv('UDP_PORT', 61000))
    UDP_BUFFER_SIZE = int(os.getenv('UDP_BUFFER_SIZE', 4096))
    
    # 필터 설정
    FILTER_SOURCE_PORT = int(os.getenv('FILTER_SOURCE_PORT', 50000))
    FILTER_DEST_PORT = int(os.getenv('FILTER_DEST_PORT', 61000))
    
    # 인터페이스 설정
    NETWORK_INTERFACE = os.getenv('NETWORK_INTERFACE', 'eno2')
    
    # 임계값 설정
    PACKET_LOSS_THRESHOLD = int(os.getenv('PACKET_LOSS_THRESHOLD', 5))
    JITTER_WARNING_THRESHOLD = float(os.getenv('JITTER_WARNING_THRESHOLD', 10.0))  # ms
    AVAILABILITY_WARNING_THRESHOLD = float(os.getenv('AVAILABILITY_WARNING', 99.0))  # %
    
    # 알림 설정
    ENABLE_ALERTS = os.getenv('ENABLE_ALERTS', 'False').lower() == 'true'
    ALERT_EMAIL = os.getenv('ALERT_EMAIL', '')
    
    # 데이터베이스 설정 (선택사항)
    DATABASE_ENABLED = os.getenv('DATABASE_ENABLED', 'False').lower() == 'true'
    DATABASE_PATH = os.getenv('DATABASE_PATH', './data/ugv_mon.db')
    DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'sqlite')  # sqlite, postgresql, mysql
    
    # PostgreSQL (선택사항)
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'ugv_mon')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
    
    # 보안 설정
    ENABLE_AUTH = os.getenv('ENABLE_AUTH', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')
    
    # 사용자 인증 (dash-auth 사용 시)
    VALID_USERNAME_PASSWORD_PAIRS = {
        os.getenv('ADMIN_USERNAME', 'admin'): os.getenv('ADMIN_PASSWORD', 'admin123')
    }
    
    # 로깅 설정
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', './logs/ugv_mon.log')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 성능 설정
    ENABLE_CACHING = os.getenv('ENABLE_CACHING', 'True').lower() == 'true'
    CACHE_SIZE = int(os.getenv('CACHE_SIZE', 128))
    
    # Gunicorn 설정 (프로덕션)
    WORKERS = int(os.getenv('WORKERS', 4))
    WORKER_CLASS = os.getenv('WORKER_CLASS', 'sync')
    TIMEOUT = int(os.getenv('TIMEOUT', 120))


class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True
    POLL_INTERVAL_MS = 2000


class ProductionConfig(Config):
    """프로덕션 환경 설정"""
    DEBUG = False
    ENABLE_AUTH = True
    ENABLE_ALERTS = True
    DATABASE_ENABLED = True
    POLL_INTERVAL_MS = 1000  # 더 빠른 폴링


class TestingConfig(Config):
    """테스트 환경 설정"""
    DEBUG = True
    POLL_INTERVAL_MS = 5000
    MAX_LOG_ENTRIES = 50


# 환경별 설정 선택
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}

def get_config():
    """환경 변수에 따라 적절한 설정 반환"""
    env = os.getenv('FLASK_ENV', 'development')
    return config_map.get(env, DevelopmentConfig)
