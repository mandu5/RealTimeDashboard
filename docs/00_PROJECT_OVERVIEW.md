# UGV-MON 프로젝트 개요

> **한화에어로스페이스 자율SW개발팀 인턴 과제**  
> VIC↔OCS 실시간 통신 모니터링 시스템  
> 작성일: 2026-01-18

---

## 📋 프로젝트 목표

**UGV-MON**은 무인지상차량(UGV)의 VIC(차량연동통제기)와 OCS(운용통제기) 간 UDP 통신을 **수동 감시(Passive Monitoring)**하여:

1. ICD v1.0 규격에 따라 메시지를 해석(파싱)
2. 운용 상태/장치 상태/비상정지 원인을 실시간 표시
3. 통신 품질(가용성, 지터, 손실 추정)을 정량적으로 분석

### 핵심 가치

> **"패킷을 잡는다"가 아니라, 패킷을 '의미 있는 운용 상태'로 바꾸고 신뢰 가능한 지표로 보여준다.**

---

## 🎯 핵심 제약사항

| 항목 | 내용 |
|------|------|
| **수동 감시** | ⚠️ 절대로 제어 패킷을 송신하지 않음 |
| **환경** | 내부망 Linux, 인터넷 연결 불가 |
| **Python** | 3.10.12 |
| **프레임워크** | Dash + Plotly + DMC + AG-Grid |
| **갱신 방식** | Polling (dcc.Interval, 2초) |

---

## 🛠️ 기술 스택

```
┌─────────────────────────────────────────────────────────────┐
│                     기술 스택                                │
├─────────────────────────────────────────────────────────────┤
│ 캡처      │ Scapy (Day 2에서 구현)                          │
│ 파싱      │ Python struct, bitwise operations               │
│ 상태관리  │ dcc.Store (in-memory)                           │
│ 갱신      │ dcc.Interval (2초 polling)                      │
│ UI        │ Dash + Dash Mantine Components                  │
│ 차트      │ Plotly                                          │
│ 테이블    │ dash-ag-grid                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📅 개발 일정 개요

| 주차 | 일차 | 날짜 | 주요 작업 | 상태 |
|------|------|------|----------|------|
| 3주차 | Day 1 | 월 | UI 스켈레톤 + DMC 레이아웃 | ✅ 완료 |
| 3주차 | Day 2 | 화 | Scapy 캡처 + 필터링 | 🔲 예정 |
| 3주차 | Day 3 | 수 | ICD 파싱 MVP + 체크섬 | 🔲 예정 |
| 3주차 | Day 4 | 목 | 데이터 품질 분석 | 🔲 예정 |
| 3주차 | Day 5 | 금 | 가용성 분석 | 🔲 예정 |
| 4주차 | Day 6 | 월 | 지터 + 손실 추정 | 🔲 예정 |
| 4주차 | Day 7 | 화 | 백엔드 → UI 연동 | 🔲 예정 |
| 4주차 | Day 8 | 수 | 차트 구현 | 🔲 예정 |
| 4주차 | Day 9 | 목 | 로그 테이블 + 폴리싱 | 🔲 예정 |
| 4주차 | Day 10 | 금 | 통합 안정화 + 문서화 | 🔲 예정 |

---

## 🚀 빠른 시작

### 환경 설정

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 대시보드 실행

```bash
# 기본 실행
sudo python run.py

# 환경변수 설정
UGV_MON_PORT=8080 sudo python run.py
UGV_MON_INTERFACE=eno2 sudo python run.py
```

### 시뮬레이터 실행

```bash
# 터미널 1
sudo ./VCS_Simulator -L

# 터미널 2
sudo ./VCS_Application
```

---

## 📚 문서 구조

- `00_PROJECT_OVERVIEW.md` - 이 문서 (프로젝트 개요)
- `01_ARCHITECTURE.md` - 아키텍처 구조 설명
- `02_FILE_STRUCTURE.md` - 디렉토리 및 파일별 역할
- `03_ICD_SPECIFICATION.md` - ICD v1.0 파싱 규격 상세
- `04_DAY01.md` ~ `13_DAY10.md` - 날짜별 상세 개발 가이드
- `99_APPENDIX.md` - 부록 (환경변수, 색상 코드, 비트 매핑 등)

---

## 🔍 관련 문서

- [아키텍처 문서](./01_ARCHITECTURE.md)
- [분석 근거](./analysis_rationale.md) - 분석 방법 선택 근거
- [테스트 체크리스트](./testing_checklist.md) - 날짜별 검증 항목
