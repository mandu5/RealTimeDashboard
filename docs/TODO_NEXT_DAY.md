# 내일 작업 계획

## 📋 현재 상태

### 완료된 작업
- ✅ Capture 모듈 구현 (PacketSniffer, PacketQueue, CaptureStats)
- ✅ Parser 모듈 구현 (ICDParser, Enum 타입 추가)
- ✅ Analysis 모듈 통합 (StatsCalculator, AnomalyDetector)
- ✅ 통합 테스트 (`test_capture_packets.py`)
- ✅ 중복 패킷 필터링 추가
- ✅ Enum 타입 도입 (타입 안정성 향상)

### 발견된 문제
- ⚠️ `ICDHeader` 클래스가 `IntEnum`을 상속하고 있음 (버그)
- ⚠️ 페이로드 파싱은 주석처리 필요 (0x01 패킷 아직 미수신)

---

## 🎯 우선순위별 작업 계획

### 🔴 우선순위 1: 버그 수정 (필수, 10분)

#### 작업 1-1: `ICDHeader` 클래스 수정

**파일**: `ugv_mon/parser/models.py` (28줄)

**현재 코드 (잘못됨)**:
```python
@dataclass
class ICDHeader(IntEnum):  # ❌ IntEnum 상속 불가
```

**수정 후**:
```python
@dataclass
class ICDHeader:  # ✅ dataclass만 사용
```

**이유**: `dataclass`와 `IntEnum`은 동시에 상속할 수 없습니다.

**확인 방법**:
```bash
python3 -c "from ugv_mon.parser.models import ICDHeader; print('✅ OK')"
```

**예상 소요 시간**: 5분

---

### 🟡 우선순위 2: Live 모드 통합 테스트 (1-2시간)

#### 작업 2-1: Mock 모드 기본 확인

**목적**: 대시보드 기본 동작 확인

**실행 명령**:
```bash
python3 run.py
```

**확인 사항**:
- [ ] 브라우저에서 `http://localhost:8050` 접속 가능
- [ ] 대시보드 UI가 정상적으로 로드됨
- [ ] Mock 데이터가 정상적으로 표시됨
- [ ] 차트, KPI 카드, 로그 테이블이 정상 작동

**예상 소요 시간**: 10분

---

#### 작업 2-2: Live 모드 기본 테스트 (lo 인터페이스)

**목적**: Live 모드 기본 동작 확인

**실행 명령**:
```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo
sudo -E python3 run.py
```

**확인 사항**:
- [ ] 대시보드가 정상적으로 로드됨
- [ ] 패킷이 캡처되고 파싱됨 (콘솔 로그 확인)
- [ ] 통계가 업데이트됨 (PPS, 지터 등)
- [ ] 차트에 데이터가 표시됨
- [ ] 에러가 발생하지 않음

**문제 발생 시**:
1. 콘솔 로그 확인
2. 브라우저 개발자 도구 콘솔 확인
3. 에러 메시지 기록

**예상 소요 시간**: 30분

---

#### 작업 2-3: 통합 테스트 스크립트 실행

**목적**: 개별 모듈 동작 확인

**실행 명령**:
```bash
sudo python3 test_capture_packets.py
```

**확인 사항**:
- [ ] 패킷 캡처 정상 동작
- [ ] 헤더 파싱 정상 동작
- [ ] 통계 계산 정상 동작
- [ ] 이상 탐지 정상 동작
- [ ] 출력 포맷 확인 (Enum 이름 표시)

**예상 소요 시간**: 15분

---

### 🟢 우선순위 3: 실제 환경 테스트 (2-3시간)

#### 작업 3-1: 실제 네트워크 인터페이스 테스트 (eno2)

**목적**: 실제 VIC↔OCS 통신 패킷 캡처 및 분석

**실행 명령**:
```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=eno2
sudo -E python3 run.py
```

**확인 사항**:
- [ ] 실제 패킷이 캡처됨
- [ ] 패킷 파싱 성공률 확인
- [ ] 통계 정확성 검증
- [ ] UI에 실시간 데이터 표시
- [ ] 장시간 실행 안정성 (최소 10분)

**예상 소요 시간**: 1시간

---

#### 작업 3-2: 실제 네트워크 인터페이스 테스트 (eno3)

**목적**: 다른 인터페이스에서도 정상 동작 확인

**실행 명령**:
```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=eno3
sudo -E python3 run.py
```

**확인 사항**: 작업 3-1과 동일

**예상 소요 시간**: 30분

---

#### 작업 3-3: 통계 검증

**목적**: 계산된 통계가 실제와 일치하는지 확인

**확인 항목**:

| 통계 항목 | 확인 방법 | 예상 범위 |
|----------|----------|----------|
| **PPS** | 대시보드 표시값 확인 | 1000 PPS (1ms 간격) |
| **지터** | 평균, P95, P99 확인 | 평균 < 5ms, P99 < 20ms |
| **패킷 손실** | 시퀀스 번호 기반 계산 | 0개 (정상 통신 시) |
| **가용성** | 수신 패킷 / 기대 패킷 | 95% 이상 |

**비교 방법**:
- Wireshark로 동시 캡처하여 비교
- 실제 통신 상태와 비교

**예상 소요 시간**: 30분

---

### 🔵 우선순위 4: UI/UX 확인 및 개선 (1-2시간)

#### 작업 4-1: 대시보드 기능 확인

**확인 항목**:

- [ ] **헤더 바**
  - 상태 칩이 정상 표시됨
  - 실시간 통계가 업데이트됨

- [ ] **KPI 카드**
  - PPS, 지터, 가용성 등이 정상 표시됨
  - 값이 실시간으로 업데이트됨

- [ ] **차트 패널**
  - 통신 품질 차트가 정상 표시됨
  - 가용성 타임라인이 정상 표시됨
  - 시간 범위 선택이 정상 작동함
  - 범례가 정상 표시됨

- [ ] **장치 그리드**
  - 장치 상태가 정상 표시됨
  - 연결/미연결 상태가 정확함
  - 에러 상태가 정상 표시됨

- [ ] **로그 테이블**
  - 로그가 정상 표시됨
  - 시간 순서가 정확함
  - 필터링이 정상 작동함

**예상 소요 시간**: 30분

---

#### 작업 4-2: 실시간 업데이트 확인

**확인 사항**:
- [ ] 2초마다 자동 갱신됨 (`dcc.Interval`)
- [ ] 데이터가 실시간으로 반영됨
- [ ] 성능 이슈 없음 (렌더링 지연 없음)
- [ ] 메모리 누수 없음 (장시간 실행 시)

**예상 소요 시간**: 20분

---

### 🟣 우선순위 5: 문제 해결 및 개선 (시간 여유 시)

#### 작업 5-1: 발견된 문제 해결

**발생 가능한 문제**:

1. **Enum 변환 에러**
   - 증상: `safe_enum()` 함수가 예상과 다르게 동작
   - 해결: `icd_parser.py`의 `safe_enum()` 로직 확인

2. **페이로드 파싱 에러**
   - 증상: `msg_code = 0x01` 패킷이 들어올 때 에러 발생
   - 해결: `docs/DEBUGGING_GUIDE.md` 참고 (필요 시)

3. **통계 계산 오류**
   - 증상: 실제 데이터와 계산값이 다름
   - 해결: `stats_calculator.py` 로직 확인

4. **UI 렌더링 문제**
   - 증상: 차트나 테이블이 표시되지 않음
   - 해결: 브라우저 콘솔 에러 확인, 데이터 형식 확인

**예상 소요 시간**: 문제 발생 시 대응

---

#### 작업 5-2: 성능 최적화

**확인 사항**:
- [ ] 메모리 사용량: 패킷 큐 크기 적절한가? (현재 1000)
- [ ] CPU 사용률: 과도한 부하가 없는가?
- [ ] 네트워크 부하: 캡처가 통신에 영향을 주지 않는가?

**최적화 방법**:
- 패킷 큐 크기 조정
- 통계 계산 주기 조정
- UI 업데이트 주기 조정

**예상 소요 시간**: 30분

---

## 📝 작업 체크리스트

### 오전 작업 (1-2시간)

- [ ] **버그 수정**: `ICDHeader` 클래스 수정
- [ ] **단위 테스트**: 수정 후 파싱 테스트
  ```bash
  python3 -c "from ugv_mon.parser.models import ICDHeader; print('OK')"
  sudo python3 test_capture_packets.py
  ```
- [ ] **Mock 모드 테스트**: 대시보드 기본 동작 확인
  ```bash
  python3 run.py
  ```
- [ ] **Live 모드 기본 테스트**: `lo` 인터페이스로 실행
  ```bash
  export UGV_MON_USE_LIVE=true
  sudo -E python3 run.py
  ```

### 오후 작업 (2-3시간)

- [ ] **실제 환경 테스트**: `eno2` 인터페이스
  ```bash
  export UGV_MON_USE_LIVE=true
  export UGV_MON_INTERFACE=eno2
  sudo -E python3 run.py
  ```
- [ ] **실제 환경 테스트**: `eno3` 인터페이스
  ```bash
  export UGV_MON_USE_LIVE=true
  export UGV_MON_INTERFACE=eno3
  sudo -E python3 run.py
  ```
- [ ] **UI 확인**: 대시보드 모든 기능 테스트
- [ ] **통계 검증**: 실제 데이터와 비교
- [ ] **문제 해결**: 발견된 이슈 해결

### 추가 작업 (시간 여유 시)

- [ ] **문서화**: 발견한 이슈 및 해결 방법 기록
- [ ] **코드 리뷰**: 개선 가능한 부분 확인
- [ ] **성능 테스트**: 장시간 실행 테스트 (1시간 이상)

---

## 🚨 예상 시나리오별 대응

### 시나리오 1: Live 모드가 정상 동작 ✅

**다음 단계**:
1. 실제 환경에서 장시간 테스트 (1시간 이상)
2. 통계 정확성 검증 (Wireshark와 비교)
3. UI 개선 사항 확인
4. 멘토님에게 데모 준비

---

### 시나리오 2: Live 모드에서 에러 발생 ❌

**대응 순서**:
1. **에러 로그 확인**
   - 콘솔 출력 확인
   - 브라우저 개발자 도구 콘솔 확인
   - 에러 메시지 전체 복사

2. **개별 모듈 테스트**
   ```bash
   sudo python3 test_capture_packets.py
   ```
   - 어느 모듈에서 문제가 발생하는지 확인

3. **문제 모듈 격리**
   - Capture 모듈 문제 → `sniffer.py` 확인
   - Parser 모듈 문제 → `icd_parser.py` 확인
   - Analysis 모듈 문제 → `stats_calculator.py` 확인

4. **수정 및 재테스트**

---

### 시나리오 3: UI가 정상 표시되지 않음 ⚠️

**대응 순서**:
1. **브라우저 콘솔 에러 확인**
   - F12 → Console 탭
   - 에러 메시지 확인

2. **데이터 형식 확인**
   - `live_provider.py`의 `_build_state_dict()` 확인
   - 반환되는 데이터 형식이 올바른지 확인

3. **콜백 함수 확인**
   - `callbacks/update_callbacks.py` 확인
   - 데이터 업데이트 로직 확인

4. **네트워크 탭 확인**
   - F12 → Network 탭
   - API 호출이 정상인지 확인

---

## 📚 참고 명령어 모음

### 기본 명령어

```bash
# 버그 수정 확인
python3 -c "from ugv_mon.parser.models import ICDHeader; print('✅ OK')"

# Mock 모드 실행
python3 run.py

# Live 모드 실행 (lo)
export UGV_MON_USE_LIVE=true
sudo -E python3 run.py

# Live 모드 실행 (eno2)
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=eno2
sudo -E python3 run.py

# Live 모드 실행 (eno3)
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=eno3
sudo -E python3 run.py

# 통합 테스트
sudo python3 test_capture_packets.py
```

### 디버깅 명령어

```bash
# Python 버전 확인
python3 --version

# 모듈 캐시 삭제
find ugv_mon -name "__pycache__" -type d -exec rm -r {} + 2>/dev/null
find ugv_mon -name "*.pyc" -delete

# 패킷 캡처 권한 확인
sudo setcap cap_net_raw+ep $(which python3)

# 환경변수 확인
echo $UGV_MON_USE_LIVE
echo $UGV_MON_INTERFACE
```

---

## 📊 성공 기준

### 최소 성공 기준
- [ ] 버그 수정 완료
- [ ] Mock 모드 정상 동작
- [ ] Live 모드 (lo) 정상 동작
- [ ] 대시보드 기본 기능 확인

### 완전 성공 기준
- [ ] 실제 환경 (eno2/eno3) 정상 동작
- [ ] 통계 정확성 검증 완료
- [ ] UI 모든 기능 정상 작동
- [ ] 장시간 실행 안정성 확인 (1시간 이상)

---

## 💡 핵심 포인트

1. **버그 수정이 최우선**: 다른 작업 전에 반드시 수정
2. **단계별 테스트**: Mock → Live(lo) → Live(실제 인터페이스)
3. **문제 발생 시**: 로그 확인 → 모듈 격리 → 수정 → 재테스트
4. **통계 정확성**: 실제 데이터와 비교하여 검증

---

## 📞 문제 발생 시

1. **에러 메시지 전체 복사**
2. **재현 단계 기록**
3. **관련 파일 확인** (에러가 발생한 모듈)
4. **디버깅 가이드 참고** (필요 시)

---

## ✅ 작업 완료 후

1. **결과 요약 작성**
   - 성공한 작업
   - 발견된 문제
   - 해결한 문제
   - 남은 작업

2. **코드 커밋** (사용자 요청 시)
   - 버그 수정
   - 개선 사항

3. **멘토님 보고**
   - 진행 상황
   - 다음 단계 계획

---

**작성일**: 2025-01-XX  
**작성자**: 개발자  
**상태**: 진행 중
