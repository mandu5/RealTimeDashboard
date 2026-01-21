# UGV-MON 프로젝트 개요

## 목표

**UGV-MON**은 무인지상차량(UGV)의 VIC↔OCS 간 UDP 통신을 **수동 감시**하여:

1. ICD v1.0 규격에 따라 메시지를 해석(파싱)
2. 운용 상태/장치 상태/비상정지 원인을 실시간 표시
3. 통신 품질(가용성, 지터, 손실 추정)을 정량적으로 분석

## 핵심 제약사항

| 항목 | 내용 |
|------|------|
| **수동 감시** | 절대로 제어 패킷을 송신하지 않음 |
| **환경** | 내부망 Linux, 인터넷 연결 불가 |
| **Python** | 3.10+ |
| **프레임워크** | Dash + Plotly + DMC + AG-Grid |
| **갱신 방식** | Polling (dcc.Interval, 2초) |

## 기술 스택

| 계층 | 기술 | 목적 |
|------|------|------|
| 캡처 | Scapy | 패킷 스니핑 및 필터링 |
| 처리 | Python 3.10 | ICD 파싱, 분석 |
| 상태 | dcc.Store | 메모리 내 상태 관리 |
| UI | Dash + DMC | 대시보드 프레임워크 |
| 차트 | Plotly | 시계열 시각화 |
| 테이블 | AG-Grid | 고성능 로그 테이블 |

## 실행 모드

### Mock 모드 (개발/테스트)
```bash
python3 run.py
```
- 가짜 랜덤 데이터 사용
- 네트워크 권한 불필요
- UI 개발/테스트용

### Live 모드 (실제 캡처)
```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo  # 또는 eno2, eno3
sudo -E python3 run.py
```
- 실제 네트워크 패킷 캡처
- root 권한 필요
- 시뮬레이터 또는 실장비 테스트용
