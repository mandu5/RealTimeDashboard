"""
UGV-MON Dash Application Module.

=============================================================================
Dash 앱 인스턴스를 생성하고 설정합니다.

모드 전환:
- Mock 모드: 환경변수 없이 실행 → MockDataGenerator 사용
- Live 모드: UGV_MON_USE_LIVE=true → ServiceProvider + 패킷 캡처 사용

Q: Mock과 Live의 차이점은?
A: Mock은 가짜 랜덤 데이터, Live는 실제 네트워크 패킷 캡처
   둘 다 동일한 인터페이스를 제공하므로 UI 코드 변경 불필요
=============================================================================
"""

import logging
import os

import dash

from .callbacks.update_callbacks import register_callbacks
from .config import config
from .ui.layouts.main_layout import create_main_layout

# 로거 설정
logger = logging.getLogger(__name__)


def create_app() -> dash.Dash:
    """
    Dash 앱 인스턴스 생성 및 설정.

    환경변수에 따라 Mock 또는 Live 모드로 초기화합니다:
    - Mock 모드: MockDataGenerator (기본값)
    - Live 모드: ServiceProvider + 패킷 캡처 시작

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
        update_title=None,  # "Updating..." 표시 비활성화
        title=config.app.name,
    )

    # =========================================================================
    # 데이터 제공자 초기화
    # - 환경변수에 따라 Mock 또는 Live 생성
    # =========================================================================
    use_live = os.getenv("UGV_MON_USE_LIVE", "").lower() == "true"
    interface = os.getenv("UGV_MON_INTERFACE", config.network.interface)

    if use_live:
        from .services import ServiceProvider
        data_gen = ServiceProvider(interface=interface)

        # Live 모드인 경우 패킷 캡처 시작
        logger.info("Starting packet capture for Live mode (Service Layer)...")
        success = data_gen.start_capture()

        if success:
            logger.info("✅ Packet capture started successfully (Service Layer)")
        else:
            logger.error(
                "❌ Failed to start packet capture.\n"
                "   Solutions:\n"
                "   1. Run with sudo: sudo python3 run.py --mode live\n"
                "   2. Set capability: sudo setcap cap_net_raw+ep $(which python3)\n"
                "   3. Check interface: ip link show"
            )
    else:
        from .mock.mock_data import MockDataGenerator
        data_gen = MockDataGenerator()

    # =========================================================================
    # 초기 데이터 생성 및 레이아웃 설정
    # =========================================================================
    initial_data = data_gen.generate_initial_data()
    initial_logs = data_gen.get_logs(limit=50)

    app.layout = create_main_layout(initial_data, initial_logs)

    # =========================================================================
    # 콜백 등록 (data_provider 전달)
    # =========================================================================
    register_callbacks(app, data_provider=data_gen)

    return app

