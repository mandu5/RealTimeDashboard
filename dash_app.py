"""
UGV-MON (VIC↔OCS UDP Monitoring) Dashboard
Python Dash Implementation with Dash Mantine Components
Version 6.0
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context, ALL, dash_table
import dash_mantine_components as dmc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import random
import json

# Initialize Dash app
app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
    ]
)

# ============================================================================
# DATA GENERATOR
# ============================================================================

class DataGenerator:
    """Mock data generator for dashboard"""
    
    def __init__(self):
        self.last_seq = 49195
        self.elapsed_time = 0
        self.logs_history = []
        self.availability_segments = [
            {"start": 0, "end": 2700, "status": "up"},
            {"start": 2700, "end": 2850, "status": "down"},
            {"start": 2850, "end": 3600, "status": "up"},
        ]
        
    def generate_initial_data(self):
        """Generate initial dashboard data"""
        now = datetime.now()
        
        # Combined chart data (60 points)
        combined_data = []
        for i in range(60):
            combined_data.append({
                'timestamp': (now - timedelta(seconds=60-i)).strftime('%H:%M:%S'),
                'pps': random.randint(800, 1200),
                'jitter': round(random.uniform(0.5, 2.5), 2)
            })
        
        # Initial logs
        for i in range(15):
            log_time = now - timedelta(seconds=(15-i)*2)
            self.logs_history.append({
                'time': log_time.strftime('%H:%M:%S'),
                'seq': self.last_seq + i,
                'msg_code': f"0x{random.randint(0, 255):02X}",
                'parse_ok': random.random() > 0.05,
                'checksum_ok': random.random() > 0.03,
                'mode': random.choice(['원격 주행 (REMOTE)', '수동', '대기']),
                'authority': random.choice(['OCS(운용통제기)', '근거리조종기', '없음']),
                'notes': '네트워크 지터 감지 (12.5ms)' if i % 10 == 0 else ''
            })
        
        self.last_seq += 14
        
        return {
            'connected': True,
            'interface': 'eno2',
            'filter': '50000→61000',
            'timeRange': '0.05s',
            'lastPacketTime': now.strftime('%H:%M:%S'),
            'parseOkRate': 97.2,
            'capturePps': 1024,
            'filterPass': 99.9,
            'parseSuccess': 100.0,
            'checksumFail': 0.0,
            'packetLoss': 0,
            'availability5min': 99.98,
            'availability1hour': 99.99,
            'jitterP95': 2.1,
            'jitterP99': 2.4,
            'operationalMode': '원격 주행 (REMOTE)',
            'operationalAuthority': 'OCS(운용통제기)',
            'drivingState': '전진/대기',
            'combinedData': combined_data,
            'devices': [
                {'name': 'VIC', 'connected': True, 'warning': False},
                {'name': 'RDC', 'connected': True, 'warning': False},
                {'name': 'ADC', 'connected': True, 'warning': False},
                {'name': 'FCAM', 'connected': True, 'warning': False},
                {'name': 'RCAM', 'connected': True, 'warning': False},
                {'name': 'AUX', 'connected': True, 'warning': True},
                {'name': 'SCS', 'connected': True, 'warning': False},
                {'name': 'DIP', 'connected': True, 'warning': False},
                {'name': 'TCC', 'connected': False, 'warning': False},
                {'name': 'TM', 'connected': True, 'warning': False},
            ],
            'emergencyStatus': {
                '통신 두절': False,
                '장비고장(주행)': False,
                '장비고장(동력계)': False,
                '신호단절(주행)': True,
                '신호단절(자율)': False,
                '신호단절(항법)': False,
                '신호단절(동력계)': False,
                '신호단절(통신)': False,
                '수동정지(운용통제장치)': False,
                '수동정지(근거리조종기)': False,
            }
        }
    
    def update_data(self, prev_data):
        """Update data for polling cycle"""
        now = datetime.now()
        
        # Add new data point
        new_point = {
            'timestamp': now.strftime('%H:%M:%S'),
            'pps': random.randint(800, 1200),
            'jitter': round(random.uniform(0.5, 2.5), 2)
        }
        
        combined_data = prev_data['combinedData'][1:] + [new_point]
        
        # Add new log
        self.last_seq += 1
        new_log = {
            'time': now.strftime('%H:%M:%S'),
            'seq': self.last_seq,
            'msg_code': f"0x{random.randint(0, 255):02X}",
            'parse_ok': random.random() > 0.05,
            'checksum_ok': random.random() > 0.03,
            'mode': random.choice(['원격 주행 (REMOTE)', '수동', '대기']),
            'authority': random.choice(['OCS(운용통제기)', '근거리조종기', '없음']),
            'notes': '네트워크 지터 감지 (12.5ms)' if random.random() > 0.9 else ''
        }
        
        self.logs_history = [new_log] + self.logs_history[:199]
        
        # Update KPIs occasionally
        should_update_kpis = random.random() > 0.7
        
        # Update availability timeline
        self.elapsed_time += 2
        time_window = 3600
        is_connected = random.random() > 0.02
        
        new_segments = self.availability_segments.copy()
        if new_segments:
            last_seg = new_segments[-1]
            if (is_connected and last_seg['status'] == 'up') or (not is_connected and last_seg['status'] == 'down'):
                last_seg['end'] = min(self.elapsed_time, time_window)
            else:
                new_segments.append({
                    'start': last_seg['end'],
                    'end': min(self.elapsed_time, time_window),
                    'status': 'up' if is_connected else 'down'
                })
            
            if self.elapsed_time > time_window:
                offset = self.elapsed_time - time_window
                new_segments = [
                    {
                        'start': max(0, seg['start'] - offset),
                        'end': max(0, seg['end'] - offset),
                        'status': seg['status']
                    }
                    for seg in new_segments if seg['end'] > offset
                ]
        
        self.availability_segments = new_segments
        
        return {
            **prev_data,
            'lastPacketTime': now.strftime('%H:%M:%S'),
            'capturePps': random.randint(1000, 1100) if should_update_kpis else prev_data['capturePps'],
            'parseOkRate': round(random.uniform(96, 99), 1) if should_update_kpis else prev_data['parseOkRate'],
            'filterPass': round(random.uniform(99, 100), 1) if should_update_kpis else prev_data['filterPass'],
            'parseSuccess': round(random.uniform(99, 100), 1) if should_update_kpis else prev_data['parseSuccess'],
            'checksumFail': round(random.uniform(0, 0.5), 1) if should_update_kpis else prev_data['checksumFail'],
            'packetLoss': random.randint(0, 2) if should_update_kpis else prev_data['packetLoss'],
            'jitterP95': round(random.uniform(1.5, 2.5), 1),
            'jitterP99': round(random.uniform(2, 2.8), 1),
            'combinedData': combined_data,
        }

# Global data generator instance
data_gen = DataGenerator()

# ============================================================================
# COMPONENTS
# ============================================================================

def create_status_chip(label, value, variant='default'):
    """Create status chip component"""
    color_map = {
        'success': {'bg': '#d1fae5', 'border': '#a7f3d0', 'text': '#065f46'},
        'warning': {'bg': '#fef3c7', 'border': '#fde68a', 'text': '#92400e'},
        'destructive': {'bg': '#fee2e2', 'border': '#fecaca', 'text': '#991b1b'},
        'default': {'bg': '#f1f5f9', 'border': '#e2e8f0', 'text': '#334155'},
    }
    
    colors = color_map.get(variant, color_map['default'])
    
    return html.Div([
        html.Span(label, style={
            'fontSize': '12px',
            'fontWeight': '500',
            'opacity': '0.7',
            'color': colors['text']
        }),
        html.Span(str(value), style={
            'fontSize': '12px',
            'fontWeight': '600',
            'color': colors['text']
        })
    ], style={
        'display': 'flex',
        'alignItems': 'center',
        'gap': '8px',
        'padding': '6px 12px',
        'borderRadius': '8px',
        'border': f"1px solid {colors['border']}",
        'backgroundColor': colors['bg']
    })


def create_kpi_card(title, value, unit='', show_progress=False, progress_value=0, progress_color='blue'):
    """Create KPI card component"""
    color_map = {
        'blue': '#3b82f6',
        'green': '#10b981',
        'red': '#ef4444'
    }
    
    return dmc.Card([
        html.Div([
            html.Div(title, style={
                'fontSize': '11px',
                'color': '#64748b',
                'fontWeight': '500',
                'marginBottom': '8px'
            }),
            html.Div([
                html.Span(str(value), style={
                    'fontSize': '24px',
                    'fontWeight': '700',
                    'color': '#0f172a'
                }),
                html.Span(f' {unit}' if unit else '', style={
                    'fontSize': '12px',
                    'color': '#64748b',
                    'fontWeight': '500',
                    'marginLeft': '4px'
                })
            ]),
            dmc.Progress(
                value=progress_value,
                color=progress_color,
                size='sm',
                style={'marginTop': '8px'}
            ) if show_progress else None
        ])
    ], withBorder=True, p='md', radius='md', style={'height': '100%'})


def create_device_grid(devices):
    """Create device connection grid"""
    device_items = []
    
    for device in devices:
        if device['connected']:
            bg_color = '#fef3c7' if device.get('warning') else '#d1fae5'
            border_color = '#fde68a' if device.get('warning') else '#a7f3d0'
            text_color = '#92400e' if device.get('warning') else '#065f46'
            icon = '⚠' if device.get('warning') else '✓'
        else:
            bg_color = '#fee2e2'
            border_color = '#fecaca'
            text_color = '#991b1b'
            icon = '✗'
        
        device_items.append(
            html.Div([
                html.Span(icon, style={'fontSize': '14px', 'marginRight': '6px'}),
                html.Span(device['name'], style={'fontSize': '12px', 'fontWeight': '600'})
            ], style={
                'padding': '8px 12px',
                'borderRadius': '8px',
                'backgroundColor': bg_color,
                'border': f'1px solid {border_color}',
                'color': text_color,
                'textAlign': 'center'
            })
        )
    
    return html.Div(device_items, style={
        'display': 'grid',
        'gridTemplateColumns': 'repeat(5, 1fr)',
        'gap': '8px'
    })


def create_communication_chart(data, p95, p99):
    """Create combined PPS + Jitter chart using Plotly"""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('패킷 수신율 (PPS)', '지터 (Jitter, ms)'),
        vertical_spacing=0.12,
        row_heights=[0.5, 0.5]
    )
    
    # PPS Chart
    fig.add_trace(
        go.Scatter(
            x=[d['timestamp'] for d in data],
            y=[d['pps'] for d in data],
            mode='lines',
            name='PPS',
            line=dict(color='#3b82f6', width=2),
            fill='tozeroy',
            fillcolor='rgba(59, 130, 246, 0.1)'
        ),
        row=1, col=1
    )
    
    # Jitter Chart
    fig.add_trace(
        go.Scatter(
            x=[d['timestamp'] for d in data],
            y=[d['jitter'] for d in data],
            mode='lines',
            name='Jitter',
            line=dict(color='#10b981', width=2),
            fill='tozeroy',
            fillcolor='rgba(16, 185, 129, 0.1)'
        ),
        row=2, col=1
    )
    
    # P95/P99 lines
    fig.add_hline(y=p95, line_dash="dash", line_color="#f59e0b", 
                  annotation_text=f"P95: {p95}ms", row=2, col=1)
    fig.add_hline(y=p99, line_dash="dash", line_color="#ef4444", 
                  annotation_text=f"P99: {p99}ms", row=2, col=1)
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#f1f5f9')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f1f5f9')
    
    fig.update_layout(
        height=400,
        margin=dict(l=40, r=40, t=40, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Inter, sans-serif', size=11),
        showlegend=False,
        hovermode='x unified'
    )
    
    return fig


def create_availability_timeline(segments, duration=3600):
    """Create availability timeline visualization"""
    fig = go.Figure()
    
    for seg in segments:
        color = '#10b981' if seg['status'] == 'up' else '#ef4444'
        fig.add_trace(go.Scatter(
            x=[seg['start'], seg['end']],
            y=[1, 1],
            mode='lines',
            line=dict(color=color, width=20),
            hovertemplate=f"Status: {seg['status']}<br>Duration: {seg['end']-seg['start']}s<extra></extra>",
            showlegend=False
        ))
    
    fig.update_layout(
        height=80,
        margin=dict(l=40, r=40, t=20, b=20),
        xaxis=dict(
            title='Time (seconds)',
            range=[0, duration],
            showgrid=True,
            gridcolor='#f1f5f9'
        ),
        yaxis=dict(
            showticklabels=False,
            range=[0, 2],
            showgrid=False
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Inter, sans-serif', size=11)
    )
    
    return fig


# ============================================================================
# LAYOUT
# ============================================================================

def create_layout():
    """Create main dashboard layout"""
    initial_data = data_gen.generate_initial_data()
    
    return dmc.MantineProvider([
        # Store for data
        dcc.Store(id='dashboard-data', data=initial_data),
        dcc.Store(id='is-paused', data=False),
        dcc.Store(id='auto-scroll', data=True),
        
        # Interval for polling (2 seconds)
        dcc.Interval(id='interval-component', interval=2000, n_intervals=0),
        
        html.Div([
            # Header Bar
            html.Div([
                html.Div([
                    html.Div([
                        html.Div(style={
                            'width': '4px',
                            'height': '32px',
                            'backgroundColor': '#3b82f6',
                            'borderRadius': '9999px'
                        }),
                        html.H1('VIC↔OCS 실시간 모니터링', style={
                            'fontSize': '20px',
                            'fontWeight': '700',
                            'color': '#1e293b',
                            'margin': '0'
                        })
                    ], style={'display': 'flex', 'alignItems': 'center', 'gap': '12px'}),
                    
                    html.Div([
                        create_status_chip('연결상태', 
                                         '연결됨' if initial_data['connected'] else '연결끊김',
                                         'success' if initial_data['connected'] else 'destructive'),
                        create_status_chip('인터페이스', initial_data['interface']),
                        create_status_chip('필터', initial_data['filter']),
                        create_status_chip('시간범위', initial_data['timeRange']),
                    ], id='status-chips', style={'display': 'flex', 'gap': '8px'})
                ], style={
                    'display': 'flex',
                    'justifyContent': 'space-between',
                    'alignItems': 'center'
                })
            ], style={
                'backgroundColor': 'white',
                'border': '1px solid #e2e8f0',
                'borderRadius': '12px',
                'padding': '16px 24px',
                'marginBottom': '24px',
                'boxShadow': '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
            }),
            
            # KPI Cards Row
            html.Div([
                create_kpi_card('수신 pps', initial_data['capturePps'], 'pps', True, 70, 'blue'),
                create_kpi_card('필터 통과율', initial_data['filterPass'], '%', True, initial_data['filterPass'], 'green'),
                create_kpi_card('파싱 성공률', initial_data['parseSuccess'], '%', True, initial_data['parseSuccess'], 'green'),
                create_kpi_card('체크섬 오류율', initial_data['checksumFail'], '%'),
                create_kpi_card('추정 패킷 손실', initial_data['packetLoss'], 'pkts'),
                create_kpi_card('가용성 (5분)', initial_data['availability5min'], '%', True, initial_data['availability5min'], 'green'),
                create_kpi_card('가용성 (1시간)', initial_data['availability1hour'], '%', True, initial_data['availability1hour'], 'green'),
                create_kpi_card('지터 (P95/P99)', f"{initial_data['jitterP95']} / {initial_data['jitterP99']}", 'ms'),
            ], id='kpi-cards', style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(8, 1fr)',
                'gap': '16px',
                'marginBottom': '24px'
            }),
            
            # Main Content - 2 Columns
            html.Div([
                # Left Column
                html.Div([
                    # 현재 운용 상태
                    dmc.Card([
                        html.Div([
                            html.Div(style={
                                'width': '4px',
                                'height': '16px',
                                'backgroundColor': '#3b82f6',
                                'borderRadius': '9999px'
                            }),
                            html.Div('현재 운용 상태', style={
                                'fontSize': '14px',
                                'fontWeight': '600',
                                'color': '#334155'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '8px', 'marginBottom': '16px'}),
                        
                        html.Div([
                            html.Div([
                                html.Div('운용모드', style={
                                    'fontSize': '12px',
                                    'fontWeight': '500',
                                    'color': '#059669',
                                    'marginBottom': '8px'
                                }),
                                html.Div(initial_data['operationalMode'], style={
                                    'fontSize': '16px',
                                    'fontWeight': '700',
                                    'color': '#064e3b'
                                })
                            ], style={
                                'background': 'linear-gradient(to bottom right, #d1fae5, #a7f3d0)',
                                'padding': '16px',
                                'borderRadius': '8px',
                                'border': '1px solid #a7f3d0'
                            }),
                            
                            html.Div([
                                html.Div('운용권한', style={
                                    'fontSize': '12px',
                                    'fontWeight': '500',
                                    'color': '#2563eb',
                                    'marginBottom': '8px'
                                }),
                                html.Div(initial_data['operationalAuthority'], style={
                                    'fontSize': '16px',
                                    'fontWeight': '700',
                                    'color': '#1e3a8a'
                                })
                            ], style={
                                'background': 'linear-gradient(to bottom right, #dbeafe, #bfdbfe)',
                                'padding': '16px',
                                'borderRadius': '8px',
                                'border': '1px solid #bfdbfe'
                            }),
                            
                            html.Div([
                                html.Div('주행상태', style={
                                    'fontSize': '12px',
                                    'fontWeight': '500',
                                    'color': '#475569',
                                    'marginBottom': '8px'
                                }),
                                html.Div(initial_data['drivingState'], style={
                                    'fontSize': '16px',
                                    'fontWeight': '700',
                                    'color': '#0f172a'
                                })
                            ], style={
                                'background': 'linear-gradient(to bottom right, #f1f5f9, #e2e8f0)',
                                'padding': '16px',
                                'borderRadius': '8px',
                                'border': '1px solid #e2e8f0'
                            })
                        ], id='operational-status', style={'display': 'flex', 'flexDirection': 'column', 'gap': '16px'})
                    ], withBorder=True, p='lg', radius='md', style={'marginBottom': '24px'}),
                    
                    # 비상정지/이상 원인
                    dmc.Card([
                        html.Div([
                            html.Div(style={
                                'width': '4px',
                                'height': '16px',
                                'backgroundColor': '#f59e0b',
                                'borderRadius': '9999px'
                            }),
                            html.Div('비상정지/이상 원인', style={
                                'fontSize': '14px',
                                'fontWeight': '600',
                                'color': '#334155'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '8px', 'marginBottom': '16px'}),
                        
                        html.Div([
                            html.Div([
                                html.Div(style={
                                    'width': '8px',
                                    'height': '8px',
                                    'borderRadius': '9999px',
                                    'backgroundColor': '#ef4444' if status else '#cbd5e1',
                                    'boxShadow': '0 0 12px rgba(239, 68, 68, 0.5)' if status else 'none',
                                    'animation': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' if status else 'none'
                                }),
                                html.Span(name, style={
                                    'fontSize': '12px',
                                    'fontWeight': '600' if status else '500',
                                    'color': '#dc2626' if status else '#64748b'
                                })
                            ], style={
                                'display': 'flex',
                                'alignItems': 'center',
                                'gap': '12px',
                                'padding': '8px 12px',
                                'borderRadius': '8px',
                                'backgroundColor': '#fee2e2' if status else '#f8fafc',
                                'border': f"1px solid {'#fecaca' if status else 'transparent'}"
                            })
                            for name, status in initial_data['emergencyStatus'].items()
                        ], id='emergency-status', style={'display': 'flex', 'flexDirection': 'column', 'gap': '6px'})
                    ], withBorder=True, p='lg', radius='md')
                ], style={'display': 'flex', 'flexDirection': 'column'}),
                
                # Right Column
                html.Div([
                    # 장치 연결 상태
                    dmc.Card([
                        html.Div([
                            html.Div([
                                html.Div(style={
                                    'width': '4px',
                                    'height': '16px',
                                    'backgroundColor': '#3b82f6',
                                    'borderRadius': '9999px'
                                }),
                                html.Div('장치 연결 상태', style={
                                    'fontSize': '14px',
                                    'fontWeight': '600',
                                    'color': '#334155'
                                })
                            ], style={'display': 'flex', 'alignItems': 'center', 'gap': '8px'}),
                            html.Span('전체: 9/10 개, 정상: 1s', style={
                                'fontSize': '12px',
                                'color': '#64748b'
                            })
                        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '16px'}),
                        
                        html.Div(id='device-grid-container', children=[
                            create_device_grid(initial_data['devices'])
                        ])
                    ], withBorder=True, p='lg', radius='md', style={'marginBottom': '24px'}),
                    
                    # 통신 품질 차트
                    dmc.Card([
                        html.Div([
                            html.Div(style={
                                'width': '4px',
                                'height': '16px',
                                'backgroundColor': '#3b82f6',
                                'borderRadius': '9999px'
                            }),
                            html.Div('통신 품질 차트', style={
                                'fontSize': '14px',
                                'fontWeight': '600',
                                'color': '#334155'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '8px', 'marginBottom': '16px'}),
                        
                        dcc.Graph(
                            id='comm-quality-chart',
                            figure=create_communication_chart(
                                initial_data['combinedData'],
                                initial_data['jitterP95'],
                                initial_data['jitterP99']
                            ),
                            config={'displayModeBar': False}
                        )
                    ], withBorder=True, p='lg', radius='md', style={'marginBottom': '24px'}),
                    
                    # 가용성 타임라인
                    dmc.Card([
                        html.Div([
                            html.Div(style={
                                'width': '4px',
                                'height': '16px',
                                'backgroundColor': '#3b82f6',
                                'borderRadius': '9999px'
                            }),
                            html.Div('가용성 타임라인 (1시간)', style={
                                'fontSize': '14px',
                                'fontWeight': '600',
                                'color': '#334155'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '8px', 'marginBottom': '8px'}),
                        
                        dcc.Graph(
                            id='availability-timeline',
                            figure=create_availability_timeline(data_gen.availability_segments),
                            config={'displayModeBar': False}
                        )
                    ], withBorder=True, p='lg', radius='md')
                ], style={'display': 'flex', 'flexDirection': 'column'})
            ], style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(2, 1fr)',
                'gap': '24px',
                'marginBottom': '24px'
            }),
            
            # Log Table
            dmc.Card([
                html.Div([
                    html.Div([
                        html.Div(style={
                            'width': '4px',
                            'height': '16px',
                            'backgroundColor': '#9333ea',
                            'borderRadius': '9999px'
                        }),
                        html.Div(id='log-table-title', children=f'로그/이벤트 테이블 (최근 {len(data_gen.logs_history)}개)', style={
                            'fontSize': '14px',
                            'fontWeight': '600',
                            'color': '#334155'
                        })
                    ], style={'display': 'flex', 'alignItems': 'center', 'gap': '8px'}),
                    
                    html.Div([
                        dmc.Button(
                            'Auto-scroll',
                            id='auto-scroll-btn',
                            variant='outline',
                            size='xs',
                            leftIcon=html.I(className='fas fa-arrow-down'),
                            color='blue'
                        ),
                        dmc.Button(
                            'Pause',
                            id='pause-btn',
                            variant='outline',
                            size='xs',
                            leftIcon=html.I(className='fas fa-pause')
                        ),
                        dmc.Button(
                            'Clear',
                            id='clear-btn',
                            variant='outline',
                            size='xs',
                            leftIcon=html.I(className='fas fa-trash'),
                            color='red'
                        )
                    ], style={'display': 'flex', 'gap': '8px'})
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '16px'}),
                
                html.Div([
                    dash_table.DataTable(
                        id='log-table',
                        columns=[
                            {'name': 'Time', 'id': 'time'},
                            {'name': 'Seq', 'id': 'seq'},
                            {'name': 'Msg Code', 'id': 'msg_code'},
                            {'name': 'Parse OK', 'id': 'parse_ok'},
                            {'name': 'Checksum OK', 'id': 'checksum_ok'},
                            {'name': 'Mode', 'id': 'mode'},
                            {'name': 'Authority', 'id': 'authority'},
                            {'name': 'Notes', 'id': 'notes'},
                        ],
                        data=[
                            {
                                'time': log['time'],
                                'seq': log['seq'],
                                'msg_code': log['msg_code'],
                                'parse_ok': '✓' if log['parse_ok'] else '✗',
                                'checksum_ok': '✓' if log['checksum_ok'] else '✗',
                                'mode': log['mode'],
                                'authority': log['authority'],
                                'notes': log['notes']
                            }
                            for log in data_gen.logs_history[:50]
                        ],
                        style_table={
                            'maxHeight': '400px',
                            'overflowY': 'auto',
                            'border': '1px solid #e2e8f0',
                            'borderRadius': '8px'
                        },
                        style_header={
                            'backgroundColor': '#f8fafc',
                            'fontWeight': '600',
                            'fontSize': '12px',
                            'color': '#334155',
                            'borderBottom': '1px solid #e2e8f0'
                        },
                        style_cell={
                            'textAlign': 'left',
                            'padding': '12px',
                            'fontSize': '12px',
                            'fontFamily': 'Inter, sans-serif'
                        },
                        style_data={
                            'backgroundColor': 'white',
                            'color': '#1e293b'
                        },
                        style_data_conditional=[
                            {
                                'if': {'row_index': 0},
                                'backgroundColor': '#dbeafe',
                                'borderLeft': '2px solid #3b82f6'
                            }
                        ]
                    )
                ], style={'border': '1px solid #e2e8f0', 'borderRadius': '8px', 'overflow': 'hidden'})
            ], withBorder=True, p='lg', radius='md')
            
        ], style={
            'minHeight': '100vh',
            'background': 'linear-gradient(to bottom right, #f8fafc, #f1f5f9)',
            'padding': '24px',
            'fontFamily': 'Inter, sans-serif'
        })
    ])

app.layout = create_layout()

# ============================================================================
# CALLBACKS
# ============================================================================

@app.callback(
    Output('dashboard-data', 'data'),
    Input('interval-component', 'n_intervals'),
    State('dashboard-data', 'data'),
    State('is-paused', 'data')
)
def update_dashboard_data(n, current_data, is_paused):
    """Update dashboard data on interval"""
    if is_paused:
        return current_data
    
    return data_gen.update_data(current_data)


@app.callback(
    [Output('status-chips', 'children'),
     Output('kpi-cards', 'children'),
     Output('operational-status', 'children'),
     Output('emergency-status', 'children'),
     Output('device-grid-container', 'children'),
     Output('comm-quality-chart', 'figure'),
     Output('availability-timeline', 'figure'),
     Output('log-table', 'data'),
     Output('log-table-title', 'children')],
    Input('dashboard-data', 'data')
)
def update_all_components(data):
    """Update all dashboard components when data changes"""
    
    # Status chips
    status_chips = [
        create_status_chip('연결상태', 
                         '연결됨' if data['connected'] else '연결끊김',
                         'success' if data['connected'] else 'destructive'),
        create_status_chip('인터페이스', data['interface']),
        create_status_chip('필터', data['filter']),
        create_status_chip('시간범위', data['timeRange']),
    ]
    
    # KPI cards
    kpi_cards = [
        create_kpi_card('수신 pps', data['capturePps'], 'pps', True, 70, 'blue'),
        create_kpi_card('필터 통과율', data['filterPass'], '%', True, data['filterPass'], 'green'),
        create_kpi_card('파싱 성공률', data['parseSuccess'], '%', True, data['parseSuccess'], 'green'),
        create_kpi_card('체크섬 오류율', data['checksumFail'], '%'),
        create_kpi_card('추정 패킷 손실', data['packetLoss'], 'pkts'),
        create_kpi_card('가용성 (5분)', data['availability5min'], '%', True, data['availability5min'], 'green'),
        create_kpi_card('가용성 (1시간)', data['availability1hour'], '%', True, data['availability1hour'], 'green'),
        create_kpi_card('지터 (P95/P99)', f"{data['jitterP95']} / {data['jitterP99']}", 'ms'),
    ]
    
    # Operational status
    operational_status = [
        html.Div([
            html.Div('운용모드', style={
                'fontSize': '12px',
                'fontWeight': '500',
                'color': '#059669',
                'marginBottom': '8px'
            }),
            html.Div(data['operationalMode'], style={
                'fontSize': '16px',
                'fontWeight': '700',
                'color': '#064e3b'
            })
        ], style={
            'background': 'linear-gradient(to bottom right, #d1fae5, #a7f3d0)',
            'padding': '16px',
            'borderRadius': '8px',
            'border': '1px solid #a7f3d0'
        }),
        
        html.Div([
            html.Div('운용권한', style={
                'fontSize': '12px',
                'fontWeight': '500',
                'color': '#2563eb',
                'marginBottom': '8px'
            }),
            html.Div(data['operationalAuthority'], style={
                'fontSize': '16px',
                'fontWeight': '700',
                'color': '#1e3a8a'
            })
        ], style={
            'background': 'linear-gradient(to bottom right, #dbeafe, #bfdbfe)',
            'padding': '16px',
            'borderRadius': '8px',
            'border': '1px solid #bfdbfe'
        }),
        
        html.Div([
            html.Div('주행상태', style={
                'fontSize': '12px',
                'fontWeight': '500',
                'color': '#475569',
                'marginBottom': '8px'
            }),
            html.Div(data['drivingState'], style={
                'fontSize': '16px',
                'fontWeight': '700',
                'color': '#0f172a'
            })
        ], style={
            'background': 'linear-gradient(to bottom right, #f1f5f9, #e2e8f0)',
            'padding': '16px',
            'borderRadius': '8px',
            'border': '1px solid #e2e8f0'
        })
    ]
    
    # Emergency status
    emergency_status = [
        html.Div([
            html.Div(style={
                'width': '8px',
                'height': '8px',
                'borderRadius': '9999px',
                'backgroundColor': '#ef4444' if status else '#cbd5e1',
                'boxShadow': '0 0 12px rgba(239, 68, 68, 0.5)' if status else 'none'
            }),
            html.Span(name, style={
                'fontSize': '12px',
                'fontWeight': '600' if status else '500',
                'color': '#dc2626' if status else '#64748b'
            })
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'gap': '12px',
            'padding': '8px 12px',
            'borderRadius': '8px',
            'backgroundColor': '#fee2e2' if status else '#f8fafc',
            'border': f"1px solid {'#fecaca' if status else 'transparent'}"
        })
        for name, status in data['emergencyStatus'].items()
    ]
    
    # Device grid
    device_grid = create_device_grid(data['devices'])
    
    # Charts
    comm_chart = create_communication_chart(
        data['combinedData'],
        data['jitterP95'],
        data['jitterP99']
    )
    
    avail_timeline = create_availability_timeline(data_gen.availability_segments)
    
    # Log table data
    log_data = [
        {
            'time': log['time'],
            'seq': log['seq'],
            'msg_code': log['msg_code'],
            'parse_ok': '✓' if log['parse_ok'] else '✗',
            'checksum_ok': '✓' if log['checksum_ok'] else '✗',
            'mode': log['mode'],
            'authority': log['authority'],
            'notes': log['notes']
        }
        for log in data_gen.logs_history[:50]
    ]
    
    log_title = f'로그/이벤트 테이블 (최근 {len(data_gen.logs_history)}개)'
    
    return status_chips, kpi_cards, operational_status, emergency_status, device_grid, comm_chart, avail_timeline, log_data, log_title


@app.callback(
    Output('is-paused', 'data'),
    Input('pause-btn', 'n_clicks'),
    State('is-paused', 'data'),
    prevent_initial_call=True
)
def toggle_pause(n_clicks, is_paused):
    """Toggle pause state"""
    return not is_paused


@app.callback(
    Output('pause-btn', 'children'),
    Input('is-paused', 'data')
)
def update_pause_button(is_paused):
    """Update pause button text"""
    return 'Resume' if is_paused else 'Pause'


@app.callback(
    Output('auto-scroll', 'data'),
    Input('auto-scroll-btn', 'n_clicks'),
    State('auto-scroll', 'data'),
    prevent_initial_call=True
)
def toggle_auto_scroll(n_clicks, auto_scroll):
    """Toggle auto-scroll"""
    return not auto_scroll


@app.callback(
    Output('dashboard-data', 'data', allow_duplicate=True),
    Input('clear-btn', 'n_clicks'),
    State('dashboard-data', 'data'),
    prevent_initial_call=True
)
def clear_logs(n_clicks, current_data):
    """Clear all logs"""
    data_gen.logs_history = []
    return current_data


# ============================================================================
# RUN APP
# ============================================================================

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
