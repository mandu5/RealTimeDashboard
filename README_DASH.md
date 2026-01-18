# UGV-MON Dashboard - Python Dash Version 6.0

## 📋 개요

VIC↔OCS UDP 모니터링을 위한 실시간 대시보드의 Python Dash 구현입니다.
React 버전을 Python Dash + Plotly + Dash Mantine Components로 완전히 마이그레이션했습니다.

## 🚀 설치 및 실행

### 1. Python 환경 준비

Python 3.8 이상이 필요합니다.

```bash
# 가상환경 생성 (권장)
python -m venv venv

# 가상환경 활성화
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 애플리케이션 실행

```bash
python dash_app.py
```

브라우저에서 `http://localhost:8050` 접속

## 📦 주요 의존성

- **dash**: 핵심 대시보드 프레임워크
- **dash-mantine-components**: UI 컴포넌트 라이브러리
- **plotly**: 인터랙티브 차트 시각화
- **pandas**: 데이터 처리

## 🏗️ 아키텍처

### 파일 구조

```
dash_app.py          # 메인 애플리케이션 (단일 파일 구현)
requirements.txt     # Python 패키지 의존성
README_DASH.md      # 문서
```

### 주요 컴포넌트

#### 1. **DataGenerator 클래스**
- 모의 데이터 생성 및 관리
- 실시간 업데이트 시뮬레이션
- 로그 히스토리 관리
- 가용성 타임라인 세그먼트 관리

#### 2. **UI 컴포넌트 함수**
- `create_status_chip()`: 상태 칩 생성
- `create_kpi_card()`: KPI 카드 생성
- `create_device_grid()`: 장치 그리드 생성
- `create_communication_chart()`: PPS/Jitter 차트 생성
- `create_availability_timeline()`: 가용성 타임라인 생성

#### 3. **레이아웃**
- `create_layout()`: 전체 대시보드 레이아웃 구성
- 12컬럼 그리드 기반 반응형 레이아웃
- Dash Mantine Components 활용

#### 4. **콜백 함수**
- `update_dashboard_data()`: 2초마다 데이터 폴링
- `update_all_components()`: 모든 UI 컴포넌트 업데이트
- `toggle_pause()`: 일시정지/재개 토글
- `toggle_auto_scroll()`: 자동 스크롤 토글
- `clear_logs()`: 로그 초기화

## 🎨 UI 구성

### 1. 헤더 바
- 제목 및 브랜딩
- 실시간 상태 칩 (연결상태, 인터페이스, 필터, 시간범위)

### 2. KPI 카드 행 (8개)
- 수신 pps
- 필터 통과율
- 파싱 성공률
- 체크섬 오류율
- 추정 패킷 손실
- 가용성 (5분)
- 가용성 (1시간)
- 지터 (P95/P99)

### 3. 2컬럼 메인 콘텐츠

#### 좌측 컬럼
- **현재 운용 상태**: 운용모드, 운용권한, 주행상태
- **비상정지/이상 원인**: 10가지 상태 실시간 모니터링

#### 우측 컬럼
- **장치 연결 상태**: 10개 장치 연결 상태 그리드
- **통신 품질 차트**: PPS + Jitter 이중 차트 (P95/P99 라인 포함)
- **가용성 타임라인**: 1시간 가용성 시각화

### 4. 로그/이벤트 테이블
- 최근 50개 로그 표시
- Auto-scroll, Pause, Clear 기능
- 실시간 하이라이트 (최신 로그)

## ⚙️ 설정 및 커스터마이징

### 폴링 주기 변경

```python
# dash_app.py의 Interval 컴포넌트 수정
dcc.Interval(
    id='interval-component', 
    interval=2000,  # 2000ms = 2초 (원하는 값으로 변경)
    n_intervals=0
)
```

### 로그 표시 개수 변경

```python
# update_all_components() 콜백에서 슬라이싱 변경
for log in data_gen.logs_history[:50]  # 50 -> 원하는 개수
```

### 포트 변경

```python
# 파일 마지막 부분
app.run_server(debug=True, host='0.0.0.0', port=8050)  # 포트 변경
```

## 🔧 실제 데이터 연동

### UDP 패킷 캡처 연동 예시

```python
import socket
import struct

class UDPDataCollector:
    def __init__(self, host='0.0.0.0', port=61000):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((host, port))
    
    def receive_packet(self):
        data, addr = self.socket.recvfrom(4096)
        # ICD 파싱 로직 구현
        return self.parse_icd(data)
    
    def parse_icd(self, data):
        # ICD 명세에 따른 파싱
        # 예: struct.unpack() 사용
        return parsed_data

# DataGenerator 대신 UDPDataCollector 사용
collector = UDPDataCollector()
```

### 데이터베이스 연동 예시

```python
import sqlite3
# 또는
from sqlalchemy import create_engine

class DatabaseLogger:
    def __init__(self, db_path='ugv_mon.db'):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
    
    def log_packet(self, packet_data):
        # 패킷 데이터 DB 저장
        pass
    
    def get_recent_logs(self, limit=50):
        # 최근 로그 조회
        pass
```

## 📊 Plotly 차트 커스터마이징

### 차트 스타일 변경

```python
def create_communication_chart(data, p95, p99):
    fig = make_subplots(...)
    
    # 색상 변경
    fig.add_trace(go.Scatter(
        line=dict(color='#custom_color', width=3),  # 선 굵기 변경
        # ...
    ))
    
    # 레이아웃 커스터마이징
    fig.update_layout(
        height=500,  # 높이 변경
        template='plotly_dark',  # 다크 테마
        # ...
    )
    
    return fig
```

## 🎯 성능 최적화

### 1. 데이터 캐싱

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_computation(data):
    # 비용이 큰 연산 캐싱
    pass
```

### 2. 콜백 최적화

```python
# prevent_initial_call 사용
@app.callback(
    ...,
    prevent_initial_call=True  # 초기 로드 시 실행 방지
)
```

### 3. 부분 업데이트

```python
# 전체 대신 변경된 부분만 업데이트
from dash import Patch

@app.callback(...)
def update_specific_component():
    patched_data = Patch()
    patched_data['new_field'] = new_value
    return patched_data
```

## 🐛 디버깅

### Debug 모드 활성화

```python
app.run_server(debug=True)  # 이미 활성화됨
```

### 콜백 로깅

```python
@app.callback(...)
def my_callback(input_value):
    print(f"Callback triggered with: {input_value}")  # 로깅
    return output
```

### Dash DevTools

브라우저 개발자 도구에서 "Callbacks" 탭 확인

## 📈 프로덕션 배포

### Gunicorn 사용 (Linux/macOS)

```bash
pip install gunicorn

gunicorn dash_app:server -b 0.0.0.0:8050 -w 4
```

### Waitress 사용 (Windows)

```bash
pip install waitress

waitress-serve --host=0.0.0.0 --port=8050 dash_app:server
```

### Docker 배포

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dash_app.py .

EXPOSE 8050

CMD ["gunicorn", "dash_app:server", "-b", "0.0.0.0:8050", "-w", "4"]
```

## 🔐 보안 고려사항

1. **인증 추가**: dash-auth 패키지 사용
2. **HTTPS**: 리버스 프록시 (nginx, Apache) 사용
3. **환경변수**: 민감한 설정은 환경변수로 관리

```python
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
SECRET_KEY = os.getenv('SECRET_KEY')
```

## 📝 React 버전과의 차이점

| 항목 | React 버전 | Dash 버전 |
|------|-----------|-----------|
| 프레임워크 | React + Tailwind CSS | Dash + Mantine |
| 언어 | JavaScript/TypeScript | Python |
| 상태 관리 | useState, useEffect | dcc.Store, Callbacks |
| 차트 | Recharts | Plotly |
| 폴링 | setInterval | dcc.Interval |
| 스타일링 | Tailwind 클래스 | 인라인 스타일 + Mantine |

## 🤝 기여

버그 리포트 및 기능 제안 환영합니다.

## 📄 라이선스

프로젝트 라이선스에 따릅니다.

## 🙏 감사의 말

- Plotly Dash 팀
- Dash Mantine Components 커뮤니티
- UGV-MON 프로젝트 팀
