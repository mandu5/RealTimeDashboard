# UGV-MON Callbacks/Polling Debugging Guide

**작성일**: 2026-02-09
**상태**: Live 모드 대응 가이드

---

## 🛑 상황: Live 모드에서 데이터가 업데이트되지 않음

Live 모드(`run.py --mode live`)로 실행 시, 웹 대시보드 UI는 로드되지만 그래프와 수치가 0에서 멈춰있고 업데이트되지 않는 현상이 발생할 경우, 다음 절차를 따릅니다.

---

## 🔍 진단 절차 (Step-by-Step)

### 1단계: 객체 초기화 확인 (가장 중요 ⭐️)

Live 모드에서는 `app.py` → `LiveDataProvider` → `ServiceProvider` 순서로 객체가 생성됩니다. 가장 흔한 실수는 `PacketSniffer`가 데이터를 넣는 `Queue`와 `PacketProcessor`가 데이터를 꺼내는 `Queue`가 서로 다른 인스턴스일 때 발생합니다.

**확인 방법**:
`ugv_mon/services/service_provider.py` 파일의 `_init_modules` 메서드를 확인합니다.

```python
# ✅ 올바른 코드: 의존성 주입 (Dependency Injection)
self._packet_queue = PacketQueue()
self._sniffer = PacketSniffer(..., callback=self._packet_queue.put)  # 같은 큐 사용
self._processor = PacketProcessor(self._packet_queue, ...)         # 같은 큐 사용
```

```python
# ❌ 잘못된 코드: 각각 생성 (Object Mismatch)
self._sniffer = PacketSniffer(..., callback=PacketQueue().put)     # 새로운 큐 A
self._processor = PacketProcessor(PacketQueue(), ...)             # 새로운 큐 B (비어있음)
```

**조치**: 모든 모듈이 `single instance`의 큐와 저장소(`PacketStore`)를 공유하는지 확인하십시오.

### 2단계: 패킷 유입 확인

`PacketSniffer`가 실제로 패킷을 받고 있는지 확인합니다.

1. 터미널 로그 레벨을 `DEBUG`로 변경 (`config.py` 또는 환경변수 `UGV_MON_DEBUG=true`).
2. `ugv_mon/pipeline/sniffer.py`의 `_capture_loop` 내부에 `print` 문 추가:
   ```python
   print(f"Packet received: {len(raw_data)} bytes")
   ```
3. 로그가 안 찍히면?
   - 네트워크 인터페이스 이름(`lo`, `eno2` 등)이 올바른지 확인.
   - 포트 번호가 맞는지 확인 (`tcpdump -i eno2 udp port 5000` 등으로 교차 검증).

### 3단계: 파싱 성공 여부 확인

패킷은 들어오는데 차트가 안 나온다면, 파싱 실패일 확률이 높습니다.

1. `ugv_mon/pipeline/processor.py` 확인.
2. `ICDParser.parse()` 리턴값이 `None`인지 확인.
3. 가장 흔한 원인:
   - 엔디안(Endianness) 불일치 (`<` vs `>`).
   - 헤더 크기(12바이트) 불일치.
   - 메시지 코드(`0x01`, `0x40` 등)가 정의되지 않은 값임.

### 4단계: Dash Callbacks 확인

데이터는 `PacketStore`에 잘 쌓이는데 UI만 멈춰있다면, Dash의 Polling 메커니즘 문제입니다.

1. 브라우저 개발자 도구 (F12) -> Network 탭.
2. `_dash-update-component` 요청이 2초마다 발생하는지 확인.
3. 요청이 붉은색(500 Error)이거나 멈춰있다면, `callbacks/update_callbacks.py` 내부 로직 에러입니다.
   - `service_provider.get_data()` 호출 부분에 예외 처리가 되어 있는지 확인.

---

## 🛠 긴급 조치 (Workaround)

만약 원인을 바로 찾을 수 없다면, 다음 순서로 격리 테스트를 수행하십시오.

1. **Mock 모드 실행**: `python3 run.py` (Live 모드 인자 없이)
   - Mock 모드는 잘 된다면 -> UI와 콜백 로직은 정상 -> **Sniffer/Network 문제**.
   - Mock 모드도 안 된다면 -> **UI/Callback 로직 문제**.

2. **단위 테스트 실행**: `pytest tests/test_packet_store.py`
   - Store 로직 검증.

---

## ⚡️ 요약 (Checklist)

- [ ] `PacketQueue` 객체가 Sniffer와 Processor 사이에서 공유되고 있는가? (Object Identity)
- [ ] 네트워크 인터페이스(`interface`) 설정이 올바른가?
- [ ] 방화벽(Firewall)이 UDP 패킷을 차단하고 있지 않은가?
- [ ] `constants.py`의 메시지 포맷이 실제 장비와 일치하는가?
