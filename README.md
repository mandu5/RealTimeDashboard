# UGV-MON: VIC↔OCS 실시간 통신 모니터링

VIC(차량연동통제기)와 OCS(운용통제기) 간 UDP 통신을 **수동 감시**하는 대시보드.

> **⚠️ 중요**: 이 시스템은 제어 패킷을 전송하지 않습니다. 오직 모니터링만 수행합니다.

## 핵심 기능

- **실시간 패킷 캡처**: lo (로컬) 또는 eno2/eno3 (실장비) 인터페이스
- **ICD v1.0 파싱**: 헤더, 운용 상태, 장치 연결, 비상정지 원인 해석
- **품질 지표**: 가용성, 지터(P95/P99), 패킷 손실률
- **대시보드**: Dash + Plotly 기반 실시간 UI

## 빠른 시작

### 1. 설치

```bash
pip install -r requirements.txt
```

### 2. 실행

#### Mock 모드 (개발/테스트용)
```bash
python3 run.py
python3 run.py --mode mock
```
- 가짜 데이터로 UI 확인
- 네트워크 권한 불필요

#### Live 모드 (실제 패킷 캡처)
```bash
# CLI 인자 방식 (권장)
sudo python3 run.py --mode live --interface lo
sudo python3 run.py --mode live --interface eno2

# 환경변수 방식
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo
sudo -E python3 run.py
```

### 3. 접속

```
http://localhost:8050
```

## CLI 옵션

```bash
python3 run.py --help

options:
  --mode {mock,live}, -m    실행 모드 (기본: mock)
  --interface, -i           네트워크 인터페이스 (기본: lo)
  --port, -p                서버 포트 (기본: 8050)
  --debug                   디버그 모드 활성화
```

## 환경변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `UGV_MON_USE_LIVE` | `true`면 Live 모드 | Mock 모드 |
| `UGV_MON_INTERFACE` | 캡처 인터페이스 | `lo` |
| `UGV_MON_PORT` | 서버 포트 | `8050` |
| `UGV_MON_DEBUG` | 디버그 모드 | `false` |

## 프로젝트 구조

```
opus1/
├── run.py                 # 통합 진입점 (CLI 지원)
├── requirements.txt       # 의존성 목록
├── test_capture_packets.py  # 통합 테스트
│
├── tests/                 # 단위 테스트
│   ├── test_icd_parser.py
│   └── test_stats_calculator.py
│
├── docs/                  # 문서
│
└── ugv_mon/               # 메인 Python 패키지
    ├── app.py             # Dash 앱 팩토리
    ├── config.py          # 설정 관리
    ├── constants.py       # 상수 정의
    ├── styles.py          # UI 스타일 상수
    ├── capture/           # 패킷 캡처 (Scapy)
    ├── parser/            # ICD v1.0 파싱
    ├── analysis/          # 통계 분석
    ├── data/              # 데이터 모델 및 제공자
    ├── components/        # UI 컴포넌트
    ├── layouts/           # 레이아웃
    └── callbacks/         # Dash 콜백
```

## 테스트

### 단위 테스트
```bash
pip install pytest
python -m pytest tests/ -v
```

### 통합 테스트 (패킷 캡처)
```bash
pip install scapy
sudo python3 test_capture_packets.py
```

### Live 모드 확인 (시뮬레이터 연동)
```bash
# 터미널 1: 시뮬레이터 실행
sudo ./VCS_Simulator -L

# 터미널 2: 대시보드 실행
sudo python3 run.py --mode live --interface lo
```

## 문서

- `docs/00_PROJECT_OVERVIEW.md` - 프로젝트 개요
- `docs/01_ARCHITECTURE.md` - 아키텍처 구조
- `docs/02_FILE_STRUCTURE.md` - 파일별 역할
- `docs/03_ICD_SPECIFICATION.md` - ICD v1.0 파싱 규격
- `docs/04_LIVE_MODE_STABILIZATION.md` - Live 모드 안정화
- `docs/05_REFACTORING_CHANGELOG.md` - 리팩토링 변경 이력
