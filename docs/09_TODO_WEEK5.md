# 5주차 남은 작업 체크리스트

> **작성일**: 2026-02-02 (월요일)

---

## 🔥 필수 작업

### 1. VCS Simulator 연동 테스트
- [ ] 시뮬레이터 연결 후 Live 모드 동작 확인
- [ ] 지터 오염 해결 확인 (포트 전환 시 비정상 값 안 뜨는지)
- [ ] 페이로드 파싱 확인 (0x01 메시지에서 장치/운용/비상 추출)
- [ ] 로그 테이블 sequence, mode, authority 표시 확인
- [ ] KPI 지터(현재) 실시간 표시 확인

### 2. msg_code 검증
- [ ] 0x01이 운용 상태 메시지가 맞는지 확인
- [ ] 아니면 0x10 등 다른 코드로 변경 필요
- [ ] data_length=87 검증

---

## 🟡 권장 작업

### 3. dcc.Store 개선 (멘토 피드백)
- [ ] `is-paused` 같은 UI 상태 → Python 변수로 이동
- [ ] 분석 결과 (지터 히스토리, 이상 탐지) 저장으로 변경

### 4. 문서화
- [ ] README 업데이트
- [ ] FINAL_CODE_REVIEW 최종 작성

---

## ✅ 완료된 작업 (오늘)

| # | 작업 | 상태 |
|---|------|------|
| 1 | 지터 오염 해결 (전역 스킵 카운터) | ✅ |
| 2 | KPI 지터(현재) 추가 | ✅ |
| 3 | 페이로드 파싱 통합 (0x01, 87B) | ✅ |
| 4 | UI 연동 (운용/장치/비상/로그) | ✅ |
| 5 | MsgCode 주석 정리 | ✅ |

---

## 테스트 명령어

```bash
# 테스트 실행
python -m pytest tests/ -v

# Mock 모드 실행
python -m ugv_mon.app

# Live 모드 실행 (시뮬레이터 연결 필요)
UGV_MON_USE_LIVE=true UGV_MON_INTERFACE=lo python -m ugv_mon.app
```
