#!/usr/bin/env python3
"""
UGV-MON Dashboard Entry Point.

=============================================================================
실행 방법 (Linux에서는 python3 사용):

[1] Mock 모드 (기본값, 개발/테스트용)
    - 가짜 랜덤 데이터로 UI 테스트
    - 네트워크 권한 불필요
    
    python3 run.py

[2] Live 모드 - Local (lo 인터페이스)
    - 루프백 인터페이스에서 실제 패킷 캡처
    - VIC↔OCS 시뮬레이터 테스트용
    
    export UGV_MON_USE_LIVE=true
    export UGV_MON_INTERFACE=lo
    sudo -E python3 run.py

[3] Live 모드 - 실장비 (eno2 또는 eno3)
    - 물리 인터페이스에서 실제 VIC↔OCS 패킷 캡처
    
    export UGV_MON_USE_LIVE=true
    export UGV_MON_INTERFACE=eno2    # 또는 eno3
    sudo -E python3 run.py

[참고] sudo 없이 실행하려면 (한 번만 설정):
    sudo setcap cap_net_raw+ep $(which python3)
    
    이후:
    export UGV_MON_USE_LIVE=true
    export UGV_MON_INTERFACE=lo
    python3 run.py

환경변수:
    UGV_MON_USE_LIVE     : true면 Live 모드, 그 외 Mock 모드
    UGV_MON_INTERFACE    : 캡처 인터페이스 (기본: lo)
    UGV_MON_PORT         : 서버 포트 (기본: 8050)
    UGV_MON_POLL_INTERVAL: 폴링 간격 ms (기본: 2000)
=============================================================================
"""

import sys
import os
import logging

# =============================================================================
# 로깅 설정
# - INFO 레벨로 설정하여 주요 이벤트 출력
# - 시간, 레벨, 모듈명, 메시지 형식
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)

# =============================================================================
# 프로젝트 루트를 Python 경로에 추가
# - ugv_mon 패키지를 import할 수 있도록 설정
# =============================================================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ugv_mon.app import app
from ugv_mon.config import config


def main():
    """UGV-MON 대시보드 서버 실행."""
    
    # =========================================================================
    # 모드 확인
    # - UGV_MON_USE_LIVE 환경변수로 결정
    # =========================================================================
    use_live = os.getenv("UGV_MON_USE_LIVE", "").lower() == "true"
    interface = os.getenv("UGV_MON_INTERFACE", config.network.interface)
    
    if use_live:
        mode_str = "LIVE (실시간 캡처)"
        mode_detail = f"Interface: {interface}"
    else:
        mode_str = "MOCK (시뮬레이션)"
        mode_detail = "Random data generator"
    
    # =========================================================================
    # 시작 배너 출력
    # =========================================================================
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    UGV-MON Dashboard v{config.app.version}                      ║
║              VIC↔OCS Real-time Communication Monitor             ║
╠══════════════════════════════════════════════════════════════════╣
║  Mode: {mode_str:<20}                                  ║
║  {mode_detail:<60}  ║
║  Server: http://{config.app.host}:{config.app.port}                                     ║
║  Filter: UDP {config.network.source_port}→{config.network.dest_port}                                        ║
║  Poll Interval: {config.ui.poll_interval_ms}ms                                           ║
╚══════════════════════════════════════════════════════════════════╝

브라우저에서 접속: http://localhost:{config.app.port}
종료: Ctrl+C
    """)
    
    # =========================================================================
    # 서버 실행
    # =========================================================================
    app.run_server(
        debug=config.app.debug,
        host=config.app.host,
        port=config.app.port,
    )


if __name__ == "__main__":
    main()
