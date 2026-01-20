# UGV-MON 실행 가이드

> **작성일**: 2026-01-20  
> **목적**: Mock/Live 모드 및 환경별 실행 방법 종합 가이드

---

## 📋 목차

1. Mock 모드로 개발 완료 (일단 mock data로 UI부터 빠르게 끝내야지 2번 캡처한 데이터는 live lo로 연동을 하던 필요한 상태로 파싱을 하던 할거아니냐)
UI 개발: MockDataGenerator로 대시보드 UI 완성
컴포넌트: 모든 UI 컴포넌트 구현 및 테스트 완료
목적: 실제 패킷 없이도 UI 기능 확인

2. Local 실시간 캡처 연동 단계
패킷 캡처 모듈: capture/ 모듈 구현 완료
테스트 성공: sniffer 테스트로 패킷 수, bit length 확인 완료
다음 단계: Live 모드로 전환하여 실제 패킷 캡처 → 파싱 → UI 연동

[완료] Mock 모드 개발
    ↓
[완료] capture/ 모듈 구현 및 테스트
    ↓
[진행 중] Live 모드 연동 (lo 인터페이스)
    ↓
[다음] parser/ 모듈 연동 (ICD 파싱)
    ↓
[다음] analysis/ 모듈 연동 (통계 계산)
    ↓
[최종] 실장비 연동 (eno2/eno3)

# Mock 모드 (가짜 데이터)
python3 run.py
# 또는
export UGV_MON_USE_LIVE=false
python3 run.py


1. [실행 모드 개요](#실행-모드-개요)
2. [환경별 실행 방법](#환경별-실행-방법)
3. [권한 설정](#권한-설정)
4. [환경변수 상세](#환경변수-상세)
5. [문제 해결](#문제-해결)
6. [실행 확인](#실행-확인)

---

## 🎯 실행 모드 개요

UGV-MON은 두 가지 실행 모드를 지원합니다:

### Mock 모드 (시뮬레이션)

- **데이터 소스**: `MockDataGenerator` (랜덤 가짜 데이터)
- **권한**: 불필요
- **용도**: UI 개발, 테스트, 데모
- **특징**: 실제 네트워크 접근 없이 대시보드 기능 확인 가능

### Live 모드 (실시간 캡처)

- **데이터 소스**: 실제 네트워크 패킷 (`PacketSniffer` → `ICDParser`)
- **권한**: root 또는 `cap_net_raw` capability 필요
- **용도**: 실제 VIC↔OCS 통신 모니터링
- **특징**: 실시간 패킷 캡처 및 파싱

---

## 🔄 데이터 흐름 비교

### Mock 모드 데이터 흐름

```
MockDataGenerator
    │
    ├─► 랜덤 PPS 값 생성 (900-1100)
    ├─► 랜덤 지터 값 생성 (0.5-2.5ms)
    ├─► 가짜 장치 연결 상태 생성
    ├─► 가짜 운용 상태 생성
    └─► UI 표시
```

**특징**:
- 네트워크 인터페이스 사용 안 함
- 즉시 실행 가능 (권한 불필요)
- 일관된 데이터 패턴 (테스트 용이)

### Live 모드 데이터 흐름

```
실제 네트워크 (lo/eno2/eno3)
    │
    ▼
PacketSniffer (Scapy)
    │ BPF 필터: udp and src port 50000 and dst port 61000
    ▼
PacketQueue (스레드 안전 버퍼)
    │
    ▼
ICDParser
    │ 체크섬 검증 + 헤더/페이로드 파싱
    ▼
LiveDataProvider
    │
    ├─► StatsCalculator (지터, PPS, 가용성 계산)
    ├─► AnomalyDetector (이상 탐지)
    └─► UI 표시
```

**특징**:
- 실제 VIC↔OCS 패킷 캡처
- 실시간 통계 계산
- 이상 탐지 및 알림

---

## 🌍 환경별 실행 방법

### 1. Mock 모드 (가짜 데이터)

**용도**: UI 개발, 테스트, 데모

#### 방법 A: 간편 스크립트 (권장)

```bash
./start.sh mock
```

#### 방법 B: 직접 실행

```bash
python3 run.py
```

**설명**:
- 환경변수 설정 불필요
- 기본값으로 Mock 모드 실행
- root 권한 불필요
- 즉시 실행 가능

**확인 방법**:
터미널 출력에서 다음 메시지 확인:
```
Mode: MOCK (시뮬레이션)
```

---

### 2. Live 모드 - Local (lo 인터페이스)

**용도**: VIC↔OCS 시뮬레이터 테스트, 개발 PC에서 테스트

**인터페이스**: `lo` (루프백, localhost)

#### 방법 A: 간편 스크립트 (권장)

```bash
./start.sh live
```

스크립트가 자동으로 `sudo` 권한 확인 후 실행합니다.

#### 방법 B: 직접 실행

```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo
sudo -E python3 run.py
```

**설명**:
- `-E` 옵션: 환경변수 전달 (중요!)
- `lo` 인터페이스: localhost 통신 캡처
- 시뮬레이터와 같은 PC에서 실행 시 사용

**사용 시나리오**:
```bash
# 터미널 1: VIC↔OCS 시뮬레이터 실행
sudo ./VCS_Simulator -L

# 터미널 2: 대시보드 실행
./start.sh live
```

---

### 3. Live 모드 - 실장비 (eno2 인터페이스)

**용도**: 실제 VIC↔OCS 장비 모니터링

**인터페이스**: `eno2` (물리 네트워크 인터페이스)

#### 방법 A: 간편 스크립트 (권장)

```bash
./start.sh eno2
```

#### 방법 B: 직접 실행

```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=eno2
sudo -E python3 run.py
```

**설명**:
- 실제 장비와 연결된 네트워크 인터페이스
- VIC↔OCS 실제 통신 패킷 캡처
- 프로덕션 환경

**인터페이스 확인 방법**:
```bash
# 사용 가능한 인터페이스 확인
ip link show

# 또는
ifconfig -a

# 예시 출력:
# 1: lo: <LOOPBACK,UP,LOWER_UP> ...
# 2: eno2: <BROADCAST,MULTICAST,UP,LOWER_UP> ...
# 3: eno3: <BROADCAST,MULTICAST,UP,LOWER_UP> ...
```

---

### 4. Live 모드 - 실장비 (eno3 인터페이스)

**용도**: 실제 VIC↔OCS 장비 모니터링 (eno2 대신)

**인터페이스**: `eno3` (물리 네트워크 인터페이스)

#### 방법 A: 간편 스크립트 (권장)

```bash
./start.sh eno3
```

#### 방법 B: 직접 실행

```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=eno3
sudo -E python3 run.py
```

**설명**:
- eno2와 동일한 용도
- 장비 연결 상태에 따라 선택

---

## 🔐 권한 설정

### Live 모드 권한 요구사항

Live 모드는 raw socket 접근이 필요하므로 **root 권한** 또는 **`cap_net_raw` capability**가 필요합니다.

### 방법 1: sudo 사용 (간단, 매번 필요)

```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo
sudo -E python3 run.py
```

**주의사항**:
- `-E` 옵션 필수: 환경변수 전달
- 매번 sudo 비밀번호 입력 필요

### 방법 2: setcap 사용 (한 번만 설정)

```bash
# 한 번만 실행 (root 권한 필요)
sudo setcap cap_net_raw+ep $(which python3)

# 이후 sudo 없이 실행 가능
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo
python3 run.py
```

**설명**:
- `cap_net_raw+ep`: 네트워크 raw socket 접근 권한 부여
- `+ep`: effective + permitted 플래그
- 한 번 설정하면 계속 유지됨

**권한 확인**:
```bash
getcap $(which python3)
# 출력: /usr/bin/python3 = cap_net_raw+ep
```

**권한 제거** (필요 시):
```bash
sudo setcap -r $(which python3)
```

---

## ⚙️ 환경변수 상세

### 필수 환경변수

| 변수명 | 설명 | 기본값 | 필수 여부 |
|--------|------|--------|----------|
| `UGV_MON_USE_LIVE` | `true`면 Live 모드, 그 외 Mock 모드 | (없음) | Live 모드 시 필수 |

### 선택 환경변수

| 변수명 | 설명 | 기본값 | 사용 예시 |
|--------|------|--------|----------|
| `UGV_MON_INTERFACE` | 캡처 인터페이스 | `lo` | `export UGV_MON_INTERFACE=eno2` |
| `UGV_MON_PORT` | 서버 포트 | `8050` | `export UGV_MON_PORT=8080` |
| `UGV_MON_POLL_INTERVAL` | 폴링 간격 (ms) | `2000` | `export UGV_MON_POLL_INTERVAL=1000` |
| `UGV_MON_DEBUG` | 디버그 모드 | `true` | `export UGV_MON_DEBUG=false` |

### 환경변수 설정 예시

#### 한 줄로 설정

```bash
# Live 모드 + eno2 인터페이스
UGV_MON_USE_LIVE=true UGV_MON_INTERFACE=eno2 sudo -E python3 run.py

# Live 모드 + 커스텀 포트
UGV_MON_USE_LIVE=true UGV_MON_PORT=8080 sudo -E python3 run.py
```

#### 세션별로 설정 (현재 터미널에만 유효)

```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=eno2
export UGV_MON_PORT=8080
sudo -E python3 run.py
```

#### 영구 설정 (선택사항)

`~/.bashrc` 또는 `~/.zshrc`에 추가:

```bash
# UGV-MON 환경변수
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=eno2
```

---

## 🔍 실행 확인

### 1. 터미널 출력 확인

실행 시 다음 배너가 표시됩니다:

```
╔══════════════════════════════════════════════════════════════════╗
║                    UGV-MON Dashboard v1.0.0                      ║
║              VIC↔OCS Real-time Communication Monitor             ║
╠══════════════════════════════════════════════════════════════════╣
║  Mode: MOCK (시뮬레이션)  ← 모드 확인                            ║
║  Mode: LIVE (실시간 캡처) ← Live 모드                            ║
║  Interface: lo              ← 인터페이스 확인                     ║
║  Server: http://0.0.0.0:8050                                     ║
║  Filter: UDP 50000→61000                                         ║
║  Poll Interval: 2000ms                                           ║
╚══════════════════════════════════════════════════════════════════╝
```

### 2. 브라우저 접속 확인

```
http://localhost:8050
```

### 3. Live 모드 캡처 확인

#### 로그 확인

터미널에서 다음 메시지 확인:
```
[INFO] ugv_mon.data.live_provider: Using LiveDataProvider (real-time capture)
[INFO] ugv_mon.capture.sniffer: Sniffer started on interface 'lo'
```

#### 대시보드에서 확인

- **헤더 바**: "연결상태"가 "연결됨" (녹색)
- **KPI 카드**: "수신 pps"가 0보다 큰 값
- **로그 테이블**: 실제 패킷 로그가 표시됨

### 4. Mock 모드 확인

터미널에서 다음 메시지 확인:
```
[INFO] ugv_mon.data.live_provider: Using MockDataGenerator (simulated data)
```

대시보드에서:
- **KPI 카드**: 랜덤 값 (900-1100 pps)
- **로그 테이블**: 가짜 로그 엔트리

---

## 🐛 문제 해결

### 문제 1: Permission denied

**증상**:
```
PermissionError: [Errno 1] Operation not permitted
```

**원인**: Live 모드 실행 시 root 권한 없음

**해결**:
```bash
# 방법 1: sudo 사용
sudo -E python3 run.py

# 방법 2: setcap 설정 (한 번만)
sudo setcap cap_net_raw+ep $(which python3)
python3 run.py
```

---

### 문제 2: Interface not found

**증상**:
```
OSError: [Errno 19] No such device
```

**원인**: 존재하지 않는 인터페이스 지정

**해결**:
```bash
# 사용 가능한 인터페이스 확인
ip link show

# 올바른 인터페이스로 재설정
export UGV_MON_INTERFACE=lo  # 또는 eno2, eno3
```

---

### 문제 3: 패킷이 캡처되지 않음

**증상**: Live 모드에서 "수신 pps"가 0

**확인 사항**:

1. **인터페이스 확인**
   ```bash
   # 패킷이 실제로 오는지 확인
   sudo tcpdump -i lo "udp and src port 50000 and dst port 61000"
   ```

2. **BPF 필터 확인**
   - 소스 포트: 50000
   - 목적지 포트: 61000
   - 프로토콜: UDP

3. **VIC↔OCS 통신 확인**
   - 시뮬레이터/장비가 실행 중인지 확인
   - 네트워크 연결 상태 확인

---

### 문제 4: Scapy ImportError

**증상**:
```
ImportError: Scapy is not installed
```

**원인**: scapy 패키지 미설치

**해결**:
```bash
pip install scapy
```

**주의**: Linux에서는 추가 라이브러리 필요:
```bash
# Ubuntu/Debian
sudo apt-get install libpcap-dev

# CentOS/RHEL
sudo yum install libpcap-devel
```

---

### 문제 5: 환경변수가 적용되지 않음

**증상**: 환경변수 설정했는데 Mock 모드로 실행됨

**원인**: 
- `sudo` 사용 시 `-E` 옵션 누락
- 환경변수 이름 오타

**해결**:
```bash
# 올바른 방법
export UGV_MON_USE_LIVE=true
sudo -E python3 run.py

# 잘못된 방법 (환경변수 전달 안 됨)
export UGV_MON_USE_LIVE=true
sudo python3 run.py  # -E 옵션 없음!
```

**확인**:
```bash
# 환경변수 확인
echo $UGV_MON_USE_LIVE
# 출력: true
```

---

## 📊 환경별 비교표

| 항목 | Mock 모드 | Live 모드 (lo) | Live 모드 (eno2/eno3) |
|------|-----------|----------------|----------------------|
| **데이터 소스** | MockDataGenerator | 실제 패킷 (localhost) | 실제 패킷 (물리 인터페이스) |
| **권한** | 불필요 | root 필요 | root 필요 |
| **인터페이스** | 사용 안 함 | `lo` | `eno2` 또는 `eno3` |
| **용도** | UI 테스트 | 시뮬레이터 테스트 | 실제 장비 모니터링 |
| **실행 속도** | 즉시 | 즉시 | 즉시 |
| **패킷 캡처** | 없음 | 있음 | 있음 |
| **실시간 통계** | 가짜 | 실제 | 실제 |

---

## 🎯 빠른 참조

### Mock 모드 실행

```bash
python3 run.py
# 또는
./start.sh mock
```

### Live 모드 실행 (lo)

```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=lo
sudo -E python3 run.py
# 또는
./start.sh live
```

### Live 모드 실행 (eno2)

```bash
export UGV_MON_USE_LIVE=true
export UGV_MON_INTERFACE=eno2
sudo -E python3 run.py
# 또는
./start.sh eno2
```

### 권한 설정 (한 번만)

```bash
sudo setcap cap_net_raw+ep $(which python3)
```

### 인터페이스 확인

```bash
ip link show
```

### 패킷 확인 (tcpdump)

```bash
sudo tcpdump -i lo "udp and src port 50000 and dst port 61000"
```

---

## 📝 추가 참고사항

### Python 버전

Linux에서는 `python` 대신 `python3` 사용:
```bash
# 올바름
python3 run.py

# 잘못됨 (일부 Linux에서는 python 명령 없음)
python run.py
```

### 가상환경 사용

```bash
# 가상환경 활성화
source venv/bin/activate

# 실행
python3 run.py
```

### 백그라운드 실행

```bash
# 백그라운드 실행
nohup python3 run.py > dashboard.log 2>&1 &

# 프로세스 확인
ps aux | grep "python3.*run.py"

# 종료
kill <PID>
```

---

## ✅ 체크리스트

### Mock 모드 실행 전

- [ ] Python 3.10+ 설치 확인
- [ ] 의존성 설치 (`pip install -r requirements.txt`)
- [ ] 가상환경 활성화 (선택사항)

### Live 모드 실행 전

- [ ] `UGV_MON_USE_LIVE=true` 환경변수 설정
- [ ] `UGV_MON_INTERFACE` 설정 (lo/eno2/eno3)
- [ ] root 권한 또는 `cap_net_raw` 설정
- [ ] 인터페이스 존재 확인 (`ip link show`)
- [ ] VIC↔OCS 통신 확인 (시뮬레이터/장비 실행)

### 실행 후 확인

- [ ] 터미널 배너에서 모드 확인
- [ ] 브라우저 접속 확인 (`http://localhost:8050`)
- [ ] 대시보드 로드 확인
- [ ] Live 모드: 패킷 수신 확인 (수신 pps > 0)

---

## 📚 관련 문서

- [`02_FILE_STRUCTURE.md`](02_FILE_STRUCTURE.md): 프로젝트 구조 상세
- [`03_ICD_SPECIFICATION.md`](03_ICD_SPECIFICATION.md): ICD v1.0 파싱 규격
- [`05_DAY02.md`](05_DAY02.md): 패킷 캡처 구현 상세
- [`06_DAY03.md`](06_DAY03.md): ICD 파싱 구현 상세
- [`README.md`](../README.md): 프로젝트 개요

---

**마지막 업데이트**: 2026-01-20
