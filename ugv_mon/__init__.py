"""
UGV-MON: VIC-OCS Real-time Communication Monitoring & Analysis Dashboard

This package provides a passive monitoring solution for VIC↔OCS UDP traffic,
decoding ICD v1.0 messages and presenting operational status through an
enterprise-grade Python Dash dashboard.

Architecture follows CSC structure:
- CSC-001: Data Acquisition (데이터 수집)
- CSC-002: Data Processing/Analysis (데이터 처리/분석)
- CSC-003: Data Presentation (데이터 전시)

Note: This is NOT a control system - passive monitoring only.
"""

__version__ = "1.0.0"
__author__ = "Hanwha Aerospace Autonomous SW Team"
