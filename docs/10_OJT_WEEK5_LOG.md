# OJT 실습 일지 - 5주차 (2026.01.27 ~ 02.05)

> 최종 수정: 2026-02-05  
> 작성자: [이름]  
> 프로젝트: UGV-MON (무인차량 통신 모니터링 대시보드)

---

## 1. 주간 목표

1.1. 중간 발표 피드백 반영 및 개선
1.2. 데이터 분석 기능 확장 (pandas 기반)
1.3. UI/UX 개선 및 신규 패널 추가

---

## 2. 수행 내용

### 2.1. 중간 발표 피드백 분석 및 반영

2.1.1. **기술적 질문 정리**
- dcc.Store의 데이터 저장 방식 (JSON 직렬화)
- Scapy의 Raw 레이어와 packet[Raw].load 의미
- dcc.Interval과 콜백 트리거 메커니즘
- Dash 콜백의 선언적/반응형 특성 (람다와의 유사성)

2.1.2. **문서화 개선**
- `docs/09_MIDTERM_FEEDBACK.md` 신규 작성
- `docs/07_VISUALIZATION_IDEAS.md` 전면 개정
- `docs/03_ICD_SPECIFICATION.md` 시퀀스 번호 비트 수정 (8비트 → 4비트)

2.1.3. **코드 정리**
- 미사용 코드 제거 (`chart-time-range` 콜백)
- 지터 계산 로직 회사 기준으로 단순화

---

### 2.2. 데이터 분석 기능 확장

2.2.1. **Phase 1: pandas 전환**
- `stats_calculator.py` 하이브리드 방식 구현
- 실시간 저장: `List[Dict]` (성능 최적화)
- 분석 시: `pd.DataFrame` 변환 (필요시)
- FutureWarning 해결 및 33개 테스트 통과

2.2.2. **Phase 2: 가용성 요약 통계**
- `get_hourly_availability()` 메서드 추가
- 가용성 패널에 10분/1시간 배지 UI 추가
- `availabilityHourly` 데이터 필드 추가

2.2.3. **Phase 3: msg_code별 통계**
- `get_stats_by_code()` 메서드 구현
- 탭 기반 UI 패널 (`0x01`, `0x10`, `0x25`, `0x40`)
- PPS, 패킷 손실, 평균 크기, 총 패킷 표시

2.2.4. **Phase 4: 연결 이력 로그**
- `_connection_history` 추적 변수 추가
- 연결/끊김 시점 및 지속시간 기록
- `create_connection_history_panel()` UI 구현

2.2.5. **Phase 5: 운용상태 전이 분석**
- `_mode_transitions` 추적 변수 추가
- 운용모드 변경 이력 (from → to) 기록
- `create_mode_transitions_panel()` UI 구현

2.2.6. **Phase 6: 비상정지 원인 통계**
- `_emergency_counts` 집계 변수 추가
- 비상정지 원인별 발생 횟수 카운트
- `create_emergency_stats_panel()` UI 구현

---

### 2.3. 기술적 학습 내용

2.3.1. **pandas 데이터 처리**
- DataFrame의 row-wise append 비효율성 이해
- 하이브리드 방식 (리스트 + 필요시 변환) 설계
- quantile, resample 등 분석 메서드 활용

2.3.2. **Dash 콜백 심화**
- 선언적/반응형 프로그래밍 개념
- Input → Output 자동 매핑 메커니즘
- dcc.Store의 JSON 직렬화 제약

2.3.3. **실시간 시스템 설계**
- 성능과 기능 간 트레이드오프
- 이력 데이터 관리 (deque, maxlen)
- 상태 변경 감지 및 이벤트 기록

---

## 3. 주요 성과

3.1. 데이터 분석 기능 6개 Phase 완료
3.2. UI 패널 5개 신규 추가
3.3. 테스트 33개 전체 통과 유지
3.4. 중간 발표 피드백 100% 반영

---

## 4. 어려웠던 점 및 해결 방안

4.1. **pandas FutureWarning 문제**
- 문제: DataFrame.concat() 시 경고 발생
- 해결: 하이브리드 방식으로 전환 (리스트 저장 + 필요시 변환)

4.2. **테스트 호환성**
- 문제: PacketRecord dataclass 제거로 테스트 실패
- 해결: 테스트 코드에서 import 수정 및 로직 독립화

4.3. **실시간 이력 추적**
- 문제: 언제 이력을 기록할지 시점 결정
- 해결: 상태 변경 감지 패턴 적용 (`_last_*` 변수 비교)

---

## 5. 차주 계획

5.1. 팀장님 발표 준비 (전체 프로젝트 정리)
5.2. 실제 환경 테스트 (UGV 연동)
5.3. 최종 문서화 및 코드 리뷰

---

## 6. 멘토 피드백

*(멘토님 작성란)*

---

## 7. 자기 평가

- 목표 달성도: ★★★★★ (100%)
- 기술적 성장: ★★★★☆ (80%)
- 문서화 품질: ★★★★★ (100%)
