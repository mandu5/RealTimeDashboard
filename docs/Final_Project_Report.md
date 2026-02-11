# UGV-MON 최종 프로젝트 보고서

> **프로젝트명**: 무인차량 데이터 실시간 모니터링 시스템  
> **개발 기간**: 2026년 1월 ~ 2월 (8주)  
> **작성일**: 2026-02-08  
> **소속**: LS 사업부 / 자율SW팀

---

## Executive Summary

**UGV-MON**은 무인지상차량(UGV)과 운용통제기(OCS) 간 UDP 통신을 **수동 감시**하여 통신 품질을 실시간으로 분석하는 대시보드 시스템입니다.

### 핵심 성과

| 항목      | 수치                 |
| --------- | -------------------- |
| 테스트    | **52개** (100% 통과) |
| 코드 라인 | ~4,000줄             |
| UI 패널   | 12개                 |
| KPI 지표  | 8개                  |
| 문서      | 9개 파일             |

### 주요 기능

- ICD v1.0 규격 패킷 파싱 및 체크섬 검증
- 실시간 KPI 대시보드 (PPS, 지터, 가용성, 패킷 손실)
- **ML 이상 탐지** (Isolation Forest + Rule-based 앙상블)
- 운용 상태/장치 상태/비상정지 모니터링

---

## 1. 프로젝트 배경

### 1.1 문제 정의

무인차량 운용 현장에서 VIC(차량연동통제기)와 OCS 간 통신 품질 모니터링 도구가 부재하여:

- 통신 장애 발생 시 원인 파악의 어려움
- 품질 저하 사전 감지 불가
- 운용 데이터 정량화 부재

### 1.2 프로젝트 목표

1. UDP 패킷 실시간 캡처 및 ICD 규격 파싱
2. 통신 품질 KPI (PPS, 지터, 가용성) 정량 분석
3. 운용 상태, 장치 상태, 비상정지 원인 실시간 표시
4. ML 기반 이상 패턴 자동 탐지

### 1.3 제약사항

| 항목      | 내용                                |
| --------- | ----------------------------------- |
| 수동 감시 | 제어 패킷 송신 불가 (모니터링 전용) |
| 환경      | 내부망 Linux, 인터넷 연결 불가      |
| Python    | 3.10+                               |
| 갱신 방식 | Polling (2초 간격)                  |

---

## 2. 시스템 아키텍처

### 2.1 전체 구조

```text
┌─────────────────────────────────────────────────────────────┐
│                        UGV-MON                               │
├─────────────────────────────────────────────────────────────┤
│   [Pipeline Layer]                                           │
│   └── PacketSniffer → PacketQueue → PacketProcessor          │
├─────────────────────────────────────────────────────────────┤
│   [Service Layer] ← NEW (SRP 패턴)                           │
│   ├── CaptureService    (캡처 제어)                          │
│   ├── StatsService      (통계 관리)                          │
│   ├── MLService         (이상 탐지)                          │
│   └── DashboardBuilder  (Dict 빌드)                          │
├─────────────────────────────────────────────────────────────┤
│   [Data Layer]                                               │
│   └── PacketStore (deque) ← 통합 저장소                      │
├─────────────────────────────────────────────────────────────┤
│   [Presentation Layer]                                       │
│   └── Dash App → Callbacks → UI (12개 패널)                  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 데이터 흐름 (단방향)

```text
Network → Sniffer → Queue → Processor → Store
                                          │
    ┌─────────────────────────────────────┘
    ▼
StatsService ← 통계 집계
    │
    ▼
DashboardBuilder → Dict(25키)
    │
    ▼
ServiceProvider → Callbacks → UI
```

### 2.3 Service Layer 역할 분리

| 서비스               | 역할                        |
| -------------------- | --------------------------- |
| **CaptureService**   | 캡처 시작/중지/방향전환     |
| **StatsService**     | 통계 카운터/연결 타임아웃   |
| **MLService**        | Rule+ML 앙상블 탐지         |
| **DashboardBuilder** | Dict(25키) 빌드 (순수 함수) |

### 2.4 기술 스택

| 영역          | 기술          | 선택 이유                      |
| ------------- | ------------- | ------------------------------ |
| 패킷 캡처     | Scapy         | Python 네이티브, BPF 필터링    |
| 웹 프레임워크 | Dash          | 리액티브 UI, Python only       |
| UI 컴포넌트   | Mantine (DMC) | 모던 디자인, 커스터마이징 용이 |
| 차트          | Plotly        | 인터랙티브 시각화              |
| ML            | scikit-learn  | Isolation Forest, PCA          |
| 테스트        | pytest        | 단위/통합 테스트               |
| 린터          | ruff          | 빠른 Python 린터               |

---

## 3. 핵심 기능 상세

### 3.1 패킷 캡처 및 파싱

#### ICD v1.0 헤더 구조 (12바이트)

| 필드      | 오프셋 | 크기 | 설명             |
| --------- | ------ | ---- | ---------------- |
| timestamp | 0      | 4    | 송신 시각/카운터 |
| msg_code  | 4      | 1    | 메시지 코드      |
| length    | 5-6    | 2    | 페이로드 길이    |
| checksum  | 7-10   | 4    | CRC32 체크섬     |
| reserved  | 11     | 1    | 예약             |

#### msg_code 종류

| 코드 | 명칭      | 설명                      |
| ---- | --------- | ------------------------- |
| 0x01 | 상태 보고 | 운용 모드, 권한, 주행상태 |
| 0x10 | 연결 체크 | 하트비트                  |
| 0x25 | 확장 상태 | 추가 상태 정보            |
| 0x40 | 장치 상태 | 10개 장치 연결 상태       |

### 3.2 실시간 KPI 대시보드 (7개 지표)

| KPI           | 정의               | 계산 방식               |
| ------------- | ------------------ | ----------------------- |
| PPS           | 초당 패킷 수       | 최근 1초 내 수신 패킷   |
| 파싱 성공률   | ICD 파싱 성공 비율 | 성공 / 전체 × 100       |
| 체크섬 오류율 | 무결성 검증 실패   | 실패 / 전체 × 100       |
| 패킷 손실     | 시퀀스 갭 합계     | 누락된 시퀀스 번호      |
| 가용성        | 연결 시간 비율     | 연결 / 측정구간 × 100   |
| 지터 (현재)   | 패킷 간격 변동     | \|현재간격 - 이전간격\| |
| 지터 (P95)    | 95번째 백분위      | 상위 5% 제외            |

### 3.3 ML 이상 탐지 시스템

#### 모델 구성

- **Isolation Forest**: 비지도 학습 기반 이상 탐지
- **Rule Detector**: 규칙 기반 탐지 (PPS 급락, 가용성 저하 등)
- **앙상블**: 두 탐지기 결과 결합

#### 특성 벡터 (8차원)

| 특성          | 설명         |
| ------------- | ------------ |
| pps           | 초당 패킷 수 |
| jitter_p95    | 지터 P95     |
| packet_loss   | 패킷 손실    |
| availability  | 가용성       |
| parse_success | 파싱 성공률  |
| msg_01_ratio  | 0x01 비율    |
| msg_25_ratio  | 0x25 비율    |
| msg_40_ratio  | 0x40 비율    |

#### 시각화 패널

- **3D 산점도**: PCA 차원 축소, 정상(파랑)/이상(빨강)
- **이상 타임라인**: 시간별 이상 점수
- **신뢰도 게이지**: 0-100% 탐지 신뢰도
- **기여 특성 차트**: 이상에 기여한 특성 분석

### 3.4 운용 상태 모니터링

#### 운용 모드

| 모드     | 설명           |
| -------- | -------------- |
| 자율주행 | 자율 경로 추종 |
| 원격조종 | 조이스틱 제어  |
| 방호     | 비상 대기      |

#### 장치 연결 상태 (10개)

5x2 그리드 형태로 실시간 표시:

- LIDAR, Camera, GPS, IMU, Motor
- 조향, 브레이크, 통신, 배터리, 센서

#### 비상정지 인디케이터

LED 스타일로 원인별 표시:

- 조이스틱, 원격, 범퍼, 스위치, 시스템

---

## 4. 개발 과정 (8주)

### 4.1 1주차: 프로젝트 기획

- 자율SW팀 현업 업무 이해
- 기술 스택 선정 (Python, Dash, Scapy)
- 프로젝트 일정 수립

### 4.2 2주차: 요구사항 분석 및 설계

- 체계공학 프로세스 학습
- SW 구조 설계 (UML Class Diagram)
- 디렉토리 구조 확정

### 4.3 3주차: ICD 분석 및 파서 구현

- ICD 프로토콜 분석 및 문서화
- Scapy 기반 패킷 캡처 구현
- Mock 데이터 생성기 구현

### 4.4 4주차: 핵심 기능 구현

- PacketStore 통합 저장소
- KPI 계산 로직 (PPS, 지터, 가용성)
- 기본 UI 대시보드

### 4.5 5주차: 데이터 분석 확장

6개 Phase 완료:

1. pandas 하이브리드 전환
2. 가용성 요약 (10분/1시간)
3. msg_code별 통계
4. 연결 이력 로그
5. 운용상태 전이 분석
6. 비상정지 원인 통계

### 4.6 6-7주차: ML 이상 탐지

- Isolation Forest 모델 구현
- 3D 시각화 (PCA)
- 앙상블 탐지 시스템
- 52개 테스트 작성

### 4.7 8주차: 최종 정리

- 코드 품질 점검
- 문서 최신화 (docs/ 정리)
- 최종 보고서 작성

---

## 5. 프로젝트 구조

```text
opus1/
├── run.py                    # 통합 진입점
├── requirements.txt          # 의존성
├── pyproject.toml            # 프로젝트 설정
├── ruff.toml                 # 린터 설정
│
├── tests/                    # 테스트 (52개)
│   ├── test_icd_parser.py
│   ├── test_packet_store.py
│   └── test_ml_anomaly_detector.py
│
├── docs/                     # 문서 (9개)
│   ├── 00_PROJECT_OVERVIEW.md
│   ├── 01_ARCHITECTURE.md
│   ├── 02_FILE_STRUCTURE.md
│   ├── 03_ICD_SPECIFICATION.md
│   ├── 04_KPI_METRICS.md
│   ├── 05_ML_ANOMALY_DETECTION.md
│   ├── 06_DATA_FLOW_GUIDE.md
│   ├── 07_OJT_WEEKLY_LOGS.md
│   └── Final_Project_Report.md
│
└── ugv_mon/                  # 메인 패키지
    ├── config.py             # 앱 설정 (패키지 루트)
    ├── constants.py          # 상수 (패키지 루트)
    ├── models.py             # 모델 (패키지 루트)
    ├── pipeline/             # 데이터 수집 파이프라인
    ├── store/                # 데이터 저장소
    ├── services/             # 서비스 레이어
    ├── analysis/             # ML 이상 탐지
    ├── ui/                   # UI 모듈 (components, layouts, charts)
    ├── callbacks/            # Dash 콜백
    └── mock/                 # ⚠️ DEV ONLY
```

---

## 6. 기술적 성과

### 6.1 코드 품질

| 항목      | 수치                |
| --------- | ------------------- |
| 테스트    | 52개 (100% 통과)    |
| 린트 에러 | 0개 (ruff clean)    |
| 타입 힌트 | 전체 적용           |
| 문서화    | 모든 모듈 docstring |

### 6.2 주요 기술적 도전 및 해결

#### Challenge 1: 실시간 데이터 처리

- **문제**: 스레드 안전한 패킷 처리
- **해결**: `deque` + `threading.Lock` 조합

#### Challenge 2: 지터 계산 정확도

- **문제**: 간격 자체를 지터로 오인
- **해결**: `|현재간격 - 이전간격|` 변동 기반 계산

#### Challenge 3: pandas 최적화

- **문제**: DataFrame row-wise append 비효율
- **해결**: 하이브리드 방식 (List 저장 + 필요시 변환)

#### Challenge 4: ML 실시간 적용

- **문제**: 스트리밍 데이터 이상 탐지
- **해결**: 적응형 임계값 (5σ) + Isolation Forest

---

## 7. 학습 및 성장

### 7.1 기술 역량

| 영역        | 학습 내용                               |
| ----------- | --------------------------------------- |
| 네트워크    | Scapy 패킷 캡처, BPF 필터, UDP 프로토콜 |
| 리액티브 UI | Dash 콜백, dcc.Store, 폴링 패턴         |
| 데이터 분석 | pandas, numpy, 시계열 처리              |
| ML          | Isolation Forest, PCA, 앙상블 기법      |
| 테스트      | pytest, 단위/통합 테스트, 코드 커버리지 |
| 코드 품질   | ruff, mypy, 타입 힌트                   |

### 7.2 소프트웨어 엔지니어링

- 체계공학 프로세스 이해
- ICD 기반 SW 개발 경험
- 클린 아키텍처 설계
- Git 버전 관리

---

## 8. 실행 방법

### Mock 모드 (개발/테스트)

```bash
python3 run.py
python3 run.py --mode mock
```

### Live 모드 (실제 캡처)

```bash
sudo python3 run.py --mode live --interface lo
sudo python3 run.py --mode live --interface eno2
```

### 테스트 실행

```bash
python3 -m pytest tests/ -v
```

### 브라우저 접속

```text
http://localhost:8050
```

---

## 9. 향후 계획

### 단기 (1-2주)

- 실제 UGV 연동 테스트
- 성능 최적화

### 중기 (1개월)

- 알람/알림 기능 (이메일, Slack)
- 데이터 내보내기 (CSV, Excel)
- 리포트 자동 생성

### 장기 (3개월+)

- 다중 UGV 모니터링
- DB 연동 (PostgreSQL, InfluxDB)
- Docker 배포

---

## 10. 결론

UGV-MON 프로젝트를 통해 실제 현장에서 활용 가능한 무인차량 통신 모니터링 시스템을 개발했습니다.

### 프로젝트 가치

- **실용성**: 현장 적용 가능한 완성도
- **확장성**: ML 탐지 시스템 추가
- **코드 품질**: 52개 테스트, 린트 클린

### 개인 성장

- 네트워크 프로그래밍 역량 향상
- ML 실무 적용 경험
- 체계공학 프로세스 이해
- 독립적인 프로젝트 수행 능력

---

## 부록 A: 문서 목록

| 번호 | 문서명               | 설명             |
| ---- | -------------------- | ---------------- |
| 00   | PROJECT_OVERVIEW     | 프로젝트 개요    |
| 01   | ARCHITECTURE         | 시스템 아키텍처  |
| 02   | FILE_STRUCTURE       | 파일 구조        |
| 03   | ICD_SPECIFICATION    | ICD v1.0 규격    |
| 04   | KPI_METRICS          | KPI 정의 및 계산 |
| 05   | ML_ANOMALY_DETECTION | ML 이상 탐지     |
| 06   | DATA_FLOW_GUIDE      | 데이터 흐름      |
| 07   | OJT_WEEKLY_LOGS      | OJT 일지 (8주)   |

---

## 부록 B: 의존성

```
dash>=2.14.0
dash-mantine-components>=0.12.1
dash-ag-grid>=2.3.0
plotly>=5.18.0
pandas>=2.0.0
numpy>=1.24.0
scapy>=2.5.0
scikit-learn>=1.3.0
pytest>=7.4.0
```

---

## 부록 C: 테스트 목록 (52개)

### ICD 파서 (15개)

- `test_parse_header_success`
- `test_parse_header_too_short`
- `test_parse_operational_status`
- `test_parse_device_status`
- `test_checksum_verification`
- ... 외 10개

### PacketStore (22개)

- `test_add_single_packet`
- `test_get_pps`
- `test_get_jitter_p95`
- `test_get_availability`
- `test_get_packet_loss`
- `test_connection_history`
- `test_mode_transitions`
- ... 외 15개

### ML 탐지기 (15개)

- `test_detector_initialization`
- `test_fit_with_sufficient_data`
- `test_predict_normal`
- `test_predict_anomaly`
- `test_contributing_features`
- `test_pipeline_train_success`
- ... 외 9개

---

_본 보고서는 인턴십 OJT 결과 보고 및 포트폴리오 용도로 작성되었습니다._
