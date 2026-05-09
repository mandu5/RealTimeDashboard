#!/usr/bin/env python3
"""
UGV-MON Dashboard Entry Point.

통합 진입점: Mock/Live 모드를 CLI 또는 환경변수로 선택합니다.

사용법:
    # Mock 모드 (기본)
    python3 run.py
    python3 run.py --mode mock
    
    # Live 모드
    sudo python3 run.py --mode live --interface lo
    sudo python3 run.py --mode live --interface eno2
    
    # 환경변수 방식 (하위 호환)
    UGV_MON_USE_LIVE=true UGV_MON_INTERFACE=lo sudo -E python3 run.py
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

from ugv_mon.app import create_app
from ugv_mon.config import config


def parse_args():
    """CLI 인자 파싱."""
    parser = argparse.ArgumentParser(
        description="UGV-MON Dashboard — demo UDP telemetry monitor (mock or capture)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python3 run.py                          # Mock 모드
  python3 run.py --mode mock              # Mock 모드 (명시적)
  sudo python3 run.py --mode live         # Live 모드 (기본 인터페이스)
  sudo python3 run.py --mode live -i eno2 # Live 모드 (인터페이스 지정)
        """
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["mock", "live"],
        default=None,
        help="실행 모드: mock(기본), live(실시간 패킷 캡처)"
    )
    parser.add_argument(
        "--interface", "-i",
        type=str,
        default=None,
        help=f"네트워크 인터페이스 (기본: {config.network.interface})"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help=f"서버 포트 (기본: {config.app.port})"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=None,
        help="디버그 모드 활성화"
    )
    return parser.parse_args()


def resolve_mode(args) -> bool:
    """
    모드 결정 (CLI 인자 > 환경변수 > 기본값).
    
    Returns:
        True if Live mode, False if Mock mode
    """
    if args.mode is not None:
        return args.mode == "live"
    
    # 환경변수 폴백 (하위 호환성)
    env_live = os.getenv("UGV_MON_USE_LIVE", "").lower()
    return env_live == "true"


def resolve_interface(args) -> str:
    """인터페이스 결정 (CLI > 환경변수 > 설정)."""
    if args.interface is not None:
        return args.interface
    env_interface = os.getenv("UGV_MON_INTERFACE")
    if env_interface:
        return env_interface
    return config.network.interface


def main():
    """UGV-MON 대시보드 서버 실행."""
    args = parse_args()
    
    # 모드 및 설정 결정
    use_live = resolve_mode(args)
    interface = resolve_interface(args)
    port = args.port or config.app.port
    debug = args.debug if args.debug is not None else config.app.debug
    
    # 환경변수 설정 (app.py에서 참조)
    os.environ["UGV_MON_USE_LIVE"] = "true" if use_live else "false"
    os.environ["UGV_MON_INTERFACE"] = interface
    
    mode_str = "LIVE" if use_live else "MOCK"
    interface_display = interface if use_live else "N/A"
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           UGV-MON Dashboard v{config.app.version}                         ║
║         Demo real-time telemetry / packet monitor             ║
╠══════════════════════════════════════════════════════════════╣
║  Mode: {mode_str:<8}  Interface: {interface_display:<10}                    ║
║  Server: http://localhost:{port}                            ║
╚══════════════════════════════════════════════════════════════╝

브라우저에서 접속: http://localhost:{port}
종료: Ctrl+C
""")
    
    if use_live:
        print("주의: Live 모드는 root 권한이 필요합니다.")
        print("권한 오류 발생 시: sudo python3 run.py --mode live")
        print()
    
    app = create_app()
    app.run(
        debug=debug,
        host=config.app.host,
        port=port,
    )


if __name__ == "__main__":
    main()
