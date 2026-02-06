# UGV-MON 프로젝트 개요

> **최종 업데이트**: 2026-02-06

## 목표

**UGV-MON**은 무인지상차량(UGV)의 VIC<->OCS 간 UDP 통신을 **수동 감시**하여:

1. ICD v1.0 규격에 따라 메시지를 해석(파싱)
2. 운용 상태/장치 상태/비상정지 원인을 실시간 표시
3. 통신 품질(가용성, 지터 P95, 손실 추정)을 정량적으로 분석

## 핵심 제약사항

| 항목 | 내용 |
|------|------|
| **수동 감시** | 절대로 제어 패킷을 송신하지 않음 |
| **환경** | 내부망 Linux, 인터넷 연결 불가 |
| **Python** | 3.10+ |
| **프레임워크** | Dash + Plotly + DMC + AG-Grid |
| **갱신 방식** | Polling (dcc.Interval, 2초) |
| **데이터 저장** | PacketStore (단일 deque, 최대 1시간 보관) |

## 기술 스택

| 계층 | 기술 | 목적 |
|------|------|------|
| 캡처 | Scapy | 패킷 스니핑 및 BPF 필터링 |
| 처리 | Python 3.10 | ICD 파싱, 통계 계산 |
| 저장 | PacketStore (deque) | 단일 저장소 기반 통계/이력 관리 |
| 상태 | dcc.Store | 브라우저 세션별 UI 상태 관리 |
| UI | Dash + DMC | 대시보드 프레임워크 |
| 차트 | Plotly | 시계열 시각화 (PPS, 지터, 가용성) |
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
sudo python3 run.py --mode live --interface lo
sudo python3 run.py --mode live --interface eno2
```
- 실제 네트워크 패킷 캡처
- root 권한 필요
- 양방향 캡처 지원 (상태/제어 방향 전환)

## 주요 KPI

| KPI | 설명 | 소스 |
|-----|------|------|
| PPS | 초당 패킷 수 | PacketStore.get_pps() |
| 지터 (P95) | 지터 95번째 백분위 | PacketStore.get_jitter_p95() |
| 패킷 손실 | 시퀀스 갭 기반 추정 | PacketStore.get_packet_loss() |
| 가용성 | 5분/1시간 연결 시간 비율 | PacketStore.get_availability() |
| 파싱 성공률 | ICD 파싱 성공 비율 | LiveDataProvider 집계 |
| 체크섬 실패율 | 무결성 검증 실패 비율 | LiveDataProvider 집계 |
