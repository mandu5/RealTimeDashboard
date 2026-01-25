#!/usr/bin/env python3
"""
UGV-MON Dashboard Entry Point - Mock Mode

Mock 모드로 대시보드를 실행합니다.
가짜 랜덤 데이터를 사용하여 UI 개발 및 테스트에 사용됩니다.

실행 방법:
    python3 run_mock.py
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

# Mock 모드로 명시적으로 설정
os.environ["UGV_MON_USE_LIVE"] = "false"

from ugv_mon.app import create_app
from ugv_mon.config import config


def main():
    """UGV-MON 대시보드 서버 실행 (Mock 모드)."""
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           UGV-MON Dashboard v{config.app.version}                         ║
║         VIC↔OCS Real-time Communication Monitor              ║
╠══════════════════════════════════════════════════════════════╣
║  Mode: MOCK     (Mock Data Mode)                             ║
║  Server: http://localhost:{config.app.port}                            ║
╚══════════════════════════════════════════════════════════════╝

브라우저에서 접속: http://localhost:{config.app.port}
종료: Ctrl+C
    """)
    
    app = create_app()
    app.run(
        debug=config.app.debug,
        host=config.app.host,
        port=config.app.port,
    )


if __name__ == "__main__":
    main()
