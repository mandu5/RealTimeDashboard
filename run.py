#!/usr/bin/env python3
"""
UGV-MON Dashboard Entry Point.

실행 방법:
    Mock 모드:  python3 run.py
    Live 모드:  UGV_MON_USE_LIVE=true sudo -E python3 run.py
"""

import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ugv_mon.app import app
from ugv_mon.config import config


def main():
    """UGV-MON 대시보드 서버 실행."""
    use_live = os.getenv("UGV_MON_USE_LIVE", "").lower() == "true"
    interface = os.getenv("UGV_MON_INTERFACE", config.network.interface)
    
    mode = "LIVE" if use_live else "MOCK"
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           UGV-MON Dashboard v{config.app.version}                         ║
║         VIC↔OCS Real-time Communication Monitor              ║
╠══════════════════════════════════════════════════════════════╣
║  Mode: {mode:<8}  Interface: {interface:<10}                    ║
║  Server: http://localhost:{config.app.port}                            ║
╚══════════════════════════════════════════════════════════════╝

브라우저에서 접속: http://localhost:{config.app.port}
종료: Ctrl+C
    """)
    
    app.run_server(
        debug=config.app.debug,
        host=config.app.host,
        port=config.app.port,
    )


if __name__ == "__main__":
    main()
