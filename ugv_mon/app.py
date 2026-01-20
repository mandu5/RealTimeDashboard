"""
UGV-MON Dash Application Module.

=============================================================================
Dash 앱 인스턴스를 생성하고 설정합니다.

모드 전환:
- Mock 모드: 환경변수 없이 실행 → MockDataGenerator 사용
- Live 모드: UGV_MON_USE_LIVE=true → LiveDataProvider + PacketSniffer 사용

Q: Mock과 Live의 차이점은?
A: Mock은 가짜 랜덤 데이터, Live는 실제 네트워크 패킷 캡처
   둘 다 동일한 인터페이스를 제공하므로 UI 코드 변경 불필요
=============================================================================
"""

import os
import logging
import dash

from .layouts.main_layout import create_main_layout
from .callbacks.update_callbacks import register_callbacks, get_data_generator
from .config import config

# 로거 설정
logger = logging.getLogger(__name__)


def create_app() -> dash.Dash:
    """
    Dash 앱 인스턴스 생성 및 설정.
    
    환경변수에 따라 Mock 또는 Live 모드로 초기화합니다:
    - Mock 모드: MockDataGenerator (기본값)
    - Live 모드: LiveDataProvider + 패킷 캡처 시작
    
    Returns:
        설정된 Dash 앱 인스턴스
    
    환경변수:
        UGV_MON_USE_LIVE: true면 Live 모드, 그 외 Mock 모드
        UGV_MON_INTERFACE: 캡처 인터페이스 (Live 모드 전용)
    """
    # =========================================================================
    # Dash 앱 생성
    # - suppress_callback_exceptions: 동적 콜백 허용
    # - 외부 스타일시트 없음 (내부망 환경)
    # =========================================================================
    app = dash.Dash(
        __name__,
        suppress_callback_exceptions=True,
        title=config.app.name,
    )
    
    # =========================================================================
    # 데이터 제공자 초기화
    # - get_data_generator()가 환경변수에 따라 Mock 또는 Live 반환
    # =========================================================================
    data_gen = get_data_generator()
    
    # =========================================================================
    # Live 모드인 경우 패킷 캡처 시작
    # - LiveDataProvider 클래스에만 start_capture() 메서드 존재
    # - hasattr()로 안전하게 확인
    # =========================================================================
    use_live = os.getenv("UGV_MON_USE_LIVE", "").lower() == "true"
    
    if use_live and hasattr(data_gen, 'start_capture'):
        logger.info("Starting packet capture for Live mode...")
        success = data_gen.start_capture()
        
        if success:
            logger.info("✅ Packet capture started successfully")
        else:
            logger.error(
                "❌ Failed to start packet capture.\n"
                "   Solutions:\n"
                "   1. Run with sudo: sudo -E python3 run.py\n"
                "   2. Set capability: sudo setcap cap_net_raw+ep $(which python3)\n"
                "   3. Check interface: ip link show"
            )
    
    # =========================================================================
    # 초기 데이터 생성 및 레이아웃 설정
    # =========================================================================
    initial_data = data_gen.generate_initial_data()
    initial_logs = data_gen.get_logs(limit=50)
    
    app.layout = create_main_layout(initial_data, initial_logs)
    
    # =========================================================================
    # 콜백 등록
    # =========================================================================
    register_callbacks(app)
    
    return app


# =============================================================================
# 모듈 레벨 앱 인스턴스
# - import ugv_mon.app으로 접근 가능
# =============================================================================
app = create_app()
