# AGENTS.md - Context & Rules for AI Agents

This file provides context and rules for AI agents (and human developers) working on the **UGV-MON** project.
Follow these guidelines to ensure consistency and quality.

## 1. Project Overview
**UGV-MON** is a real-time monitoring dashboard for VIC (Vehicle Interface Controller) ↔ OCS (Operator Control Station) UDP communication.
- **Tech Stack**: Python 3.8+, Dash (Plotly), Scapy (Packet Capture).
- **Core Function**: Captures UDP packets, parses ICD v1.0, calculates quality metrics (Jitter, Loss), and visualizes them.
- **Modes**:
  - `MOCK`: Generates random data for UI development (Default).
  - `LIVE`: Captures real packets from network interface (Requires `sudo`).

## 2. Environment & Commands

### Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run Application
**Development (Mock Mode)**
```bash
python3 run.py
# Access at http://localhost:8050
```

**Production/Test (Live Mode)**
```bash
# Requires root privileges for packet capture
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo  # or eno2, eno3
sudo -E python3 run.py
```

### Testing
There is no `pytest` suite currently. Use the provided integration script:
```bash
# Tests Capture + Parser + Analysis flow
sudo python3 test_capture_packets.py
```

## 3. Code Style & Standards

### Formatting & Linting
- **Indentation**: 4 spaces.
- **Line Length**: Soft limit 88-100 characters.
- **Imports**: Grouped and sorted:
  1. Standard Library (`os`, `sys`, `logging`, `dataclasses`)
  2. Third Party (`dash`, `scapy`, `plotly`)
  3. Local (`ugv_mon.config`, `ugv_mon.capture`)
  - Use absolute imports for `ugv_mon` packages where possible, or consistent relative imports within modules.

### Type Hinting
- **Strict Usage**: Use Python type hints for all function arguments and return values.
- Use `dataclasses` for configuration and data structures.
```python
def process_packet(data: bytes) -> ParseResult:
    ...
```

### Naming Conventions
- **Classes**: `PascalCase` (e.g., `PacketSniffer`, `LiveDataProvider`)
- **Functions/Variables**: `snake_case` (e.g., `start_capture`, `jitter_ms`)
- **Constants**: `UPPER_CASE` (mostly found in `config.py` or module level).
- **Private**: `_prefix` for internal methods.

### Docstrings
- Use triple quotes `"""`.
- Follow **Google Style** docstrings for functions and classes.
- Include `Args:`, `Returns:`, and `Raises:` sections.

### Error Handling
- Use specific exceptions (avoid bare `except:`).
- Log errors using `logging.getLogger(__name__)`.
- In Live mode, ensure network permission errors are caught and explained to the user (e.g., suggest `sudo`).

## 4. Architecture Guidelines
- **Separation of Concerns**:
  - `capture/`: Network interaction only.
  - `parser/`: Byte parsing logic only (No side effects).
  - `analysis/`: Statistical calculations.
  - `components/` & `layouts/`: Dash UI code.
- **State Management**: Dash is stateless. Use `dcc.Store` for client-side state or the `data_provider` abstraction for server-side data streaming.

## 5. Development Workflow
1. **Mock First**: Develop UI features using Mock mode first.
2. **Integration**: Verify with `test_capture_packets.py`.
3. **Live Verification**: Final check with `sudo` and loopback/real interface.
