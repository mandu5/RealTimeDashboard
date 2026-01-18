"""
Dashboard layout modules for UGV-MON.

Layouts are organized by functional area:
- header: Connection status and filter indicators
- kpi_cards: Performance metric cards
- status_panels: Operational state and emergency status
- charts: Time series visualizations
- main_layout: Full dashboard composition
"""

from .main_layout import create_main_layout

__all__ = ["create_main_layout"]
