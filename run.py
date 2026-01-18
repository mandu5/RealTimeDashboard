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
║  Server: http://{config.app.host}:{config.app.port}                                     ║
║  Interface: {config.network.interface:<6}                                               ║
║  Filter: {config.network.source_port}→{config.network.dest_port}                                             ║
║  Poll Interval: {config.ui.poll_interval_ms}ms                                           ║
║  Debug: {str(config.app.debug):<5}                                                    ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    app.run_server(
        debug=config.app.debug,
        host=config.app.host,
        port=config.app.port,
    )


if __name__ == "__main__":
    main()
