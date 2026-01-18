#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UGV-MON Dashboard Entry Point.

Run this script to start the monitoring dashboard:
    python run.py

Environment Variables:
    UGV_MON_DEBUG: Enable debug mode (default: true)
    UGV_MON_HOST: Server host (default: 0.0.0.0)
    UGV_MON_PORT: Server port (default: 8050)
    UGV_MON_INTERFACE: Network interface (default: lo)
    UGV_MON_POLL_INTERVAL: Polling interval in ms (default: 2000)

Example:
    # Run with defaults
    python run.py
    
    # Run on different port
    UGV_MON_PORT=8080 python run.py
    
    # Production mode
    UGV_MON_DEBUG=false python run.py
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ugv_mon.app import app
from ugv_mon.config import config


def main():
    """Run the UGV-MON dashboard server."""
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    UGV-MON Dashboard v{config.app.version}                      ║
║              VIC↔OCS Real-time Communication Monitor             ║
╠══════════════════════════════════════════════════════════════════╣
║  Server: http://{config.app.host}:{config.app.port}                              ║
║  Interface: {config.network.interface:<6}                                        ║
║  Filter: {config.network.source_port}→{config.network.dest_port}                                    ║
║  Poll Interval: {config.ui.poll_interval_ms}ms                                     ║
║  Debug: {str(config.app.debug):<5}                                             ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    app.run_server(
        debug=config.app.debug,
        host=config.app.host,
        port=config.app.port,
    )


if __name__ == "__main__":
    main()
