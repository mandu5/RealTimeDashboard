# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UGV-MON is a Python 3.9+ real-time monitoring dashboard for VIC (Vehicle Integrated Controller) ↔ OCS (Operations Control Station) UDP communication. Built with Dash + Dash Mantine Components + Plotly. Uses Scapy for packet capture and scikit-learn (Isolation Forest) for anomaly detection.

## Commands

### Run Application
```bash
# Mock mode (default, no network privileges needed)
python3 run.py

# Live mode (requires root for packet capture)
sudo python3 run.py --mode live --interface lo
```

### Tests
```bash
pytest tests/
```

### Linting
Configured via `ruff.toml`: line length 100, double quotes, rules E/W/F/I/B/C4/UP/SIM/RUF.

## Architecture

**Layered architecture with SRP-based services:**

1. **Pipeline** (`ugv_mon/pipeline/`) — Scapy packet capture → thread-safe queue → ICD v1.0 parsing → store
2. **Store** (`ugv_mon/store/packet_store.py`) — Single deque-based source of truth for all packets
3. **Services** (`ugv_mon/services/`) — `CaptureService`, `StatsService`, `MLService`, `DashboardBuilder`, all coordinated by `ServiceProvider` (bridge/facade)
4. **Analysis** (`ugv_mon/analysis/`) — Isolation Forest + rule-based anomaly detection with feature extraction
5. **UI** (`ugv_mon/ui/`) — Components, layouts, and ML visualizations
6. **Callbacks** (`ugv_mon/callbacks/update_callbacks.py`) — All Dash callbacks; 2-second polling interval via `dcc.Interval`

**Data flow:** Interval trigger → `PacketProcessor.process_pending()` → `StatsService.update()` → `MLService.predict()` → `DashboardBuilder.build()` (25-key dict) → UI components read from `dashboard-data` Store.

**Dual mode:** Mock mode (`ugv_mon/mock/mock_data.py`) and live mode share the same interface (`DataProviderProtocol`), selected at startup.

## Key Conventions

- **Type hints required** everywhere (mypy `disallow_untyped_defs = true`)
- **Google-style docstrings** with Args/Returns/Raises sections
- Korean language for business logic comments; English for technical docs
- Callback registration pattern: `_register_*_callback()` functions
- Thread safety via locks in services and queues
- Circular import prevention: type-checking imports in `if TYPE_CHECKING:` blocks
- Models use dataclasses (`ICDHeader`, `OperationalPayload`, `ParseResult`) and enums (`MsgCode`, `DeviceID`, `OperationMode`)

## ICD Protocol

12-byte fixed header, 2-byte checksum at end. Message types: 0x01 (status), 0x10 (control), 0x25 (heartbeat), 0x40 (reserved). Operational payload: 87 bytes.

## Documentation

Detailed docs in `/docs/` covering architecture, ICD spec, KPI metrics, ML strategy, and data flow.
