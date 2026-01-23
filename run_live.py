#!/usr/bin/env python3
"""
UGV-MON Dashboard Entry Point - Live Mode

Live 모드로 대시보드를 실행합니다.
실제 네트워크 패킷을 캡처하여 실시간 모니터링을 수행합니다.

실행 방법:
    # 기본 인터페이스 (lo)
    sudo python3 run_live.py
    
    # 인터페이스 지정
    sudo python3 run_live.py --interface eno2
    sudo python3 run_live.py --interface eno3
"""

import sys
import os
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Live 모드로 명시적으로 설정
os.environ["UGV_MON_USE_LIVE"] = "true"

from ugv_mon.app import create_app
from ugv_mon.config import config


def main():
    """UGV-MON 대시보드 서버 실행 (Live 모드)."""
    parser = argparse.ArgumentParser(description="UGV-MON Dashboard (Live Mode)")
    parser.add_argument(
        "--interface",
        type=str,
        default=config.network.interface,
        help=f"Network interface to capture (default: {config.network.interface})"
    )
    
    args = parser.parse_args()
    
    # 인터페이스 환경변수 설정
    os.environ["UGV_MON_INTERFACE"] = args.interface
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           UGV-MON Dashboard v{config.app.version}                         ║
║         VIC↔OCS Real-time Communication Monitor              ║
╠══════════════════════════════════════════════════════════════╣
║  Mode: LIVE     Interface: {args.interface:<10}                    ║
║  Server: http://localhost:{config.app.port}                            ║
╚══════════════════════════════════════════════════════════════╝

브라우저에서 접속: http://localhost:{config.app.port}
종료: Ctrl+C

주의: Live 모드는 root 권한이 필요합니다.
권한 오류 발생 시: sudo python3 run_live.py
    """)
    
    app = create_app()
    app.run_server(
        debug=config.app.debug,
        host=config.app.host,
        port=config.app.port,
    )


if __name__ == "__main__":
    main()
