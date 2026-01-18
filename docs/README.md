# UGV-MON 개발 가이드 문서

이 디렉토리에는 UGV-MON 프로젝트의 완전한 개발 가이드를 포함하고 있습니다.

---

## 📚 문서 구조

### 개요 문서
- **[00_PROJECT_OVERVIEW.md](./00_PROJECT_OVERVIEW.md)** - 프로젝트 개요 및 빠른 시작
- **[01_ARCHITECTURE.md](./01_ARCHITECTURE.md)** - 아키텍처 구조 및 설계 결정
- **[02_FILE_STRUCTURE.md](./02_FILE_STRUCTURE.md)** - 디렉토리 및 파일별 역할
- **[03_ICD_SPECIFICATION.md](./03_ICD_SPECIFICATION.md)** - ICD v1.0 파싱 규격 상세

### 일별 개발 가이드
- **[04_DAY01.md](./04_DAY01.md)** - Day 1: UI 스켈레톤 완성 ✅
- **[05_DAY02.md](./05_DAY02.md)** - Day 2: Scapy 캡처 + 필터링
- **[06_DAY03.md](./06_DAY03.md)** - Day 3: ICD 파싱 MVP
- **[07_DAY04.md](./07_DAY04.md)** - Day 4: 데이터 품질 분석
- **[08_DAY05.md](./08_DAY05.md)** - Day 5: 가용성 분석
- **[09_DAY06.md](./09_DAY06.md)** - Day 6: 지터 + 손실 추정
- **[10_DAY07.md](./10_DAY07.md)** - Day 7: 백엔드 → UI 연동
- **[11_DAY08.md](./11_DAY08.md)** - Day 8: 차트 구현
- **[12_DAY09.md](./12_DAY09.md)** - Day 9: 로그 테이블 + 폴리싱
- **[13_DAY10.md](./13_DAY10.md)** - Day 10: 통합 안정화 + 문서화

### 부록
- **[99_APPENDIX.md](./99_APPENDIX.md)** - 환경변수, 색상 코드, 비트 매핑 등

### 참고 문서
- [analysis_rationale.md](./analysis_rationale.md) - 분석 방법 선택 근거 (Availability/Jitter/Loss)
- [testing_checklist.md](./testing_checklist.md) - 테스트 체크리스트 (날짜별 검증 항목)

---

## 🚀 빠른 시작

### 처음 시작하는 경우

1. **[00_PROJECT_OVERVIEW.md](./00_PROJECT_OVERVIEW.md)** 읽기
2. **[02_FILE_STRUCTURE.md](./02_FILE_STRUCTURE.md)** 읽어서 프로젝트 구조 파악
3. **[04_DAY01.md](./04_DAY01.md)** 읽고 현재 상태 확인

### 특정 작업을 하는 경우

- **캡처 구현**: [05_DAY02.md](./05_DAY02.md)
- **파싱 구현**: [06_DAY03.md](./06_DAY03.md)
- **ICD 규격 확인**: [03_ICD_SPECIFICATION.md](./03_ICD_SPECIFICATION.md)
- **아키텍처 이해**: [01_ARCHITECTURE.md](./01_ARCHITECTURE.md)

---

## 📅 현재 진행 상황

| 일차 | 상태 | 문서 |
|------|------|------|
| Day 1 | ✅ 완료 | [04_DAY01.md](./04_DAY01.md) |
| Day 2 | 🔲 예정 | [05_DAY02.md](./05_DAY02.md) |
| Day 3 | 🔲 예정 | [06_DAY03.md](./06_DAY03.md) |
| Day 4 | 🔲 예정 | [07_DAY04.md](./07_DAY04.md) |
| Day 5 | 🔲 예정 | [08_DAY05.md](./08_DAY05.md) |
| Day 6 | 🔲 예정 | [09_DAY06.md](./09_DAY06.md) |
| Day 7 | 🔲 예정 | [10_DAY07.md](./10_DAY07.md) |
| Day 8 | 🔲 예정 | [11_DAY08.md](./11_DAY08.md) |
| Day 9 | 🔲 예정 | [12_DAY09.md](./12_DAY09.md) |
| Day 10 | 🔲 예정 | [13_DAY10.md](./13_DAY10.md) |

---

## 💡 문서 사용법

### 각 날짜별 문서 구조

각 `DAYXX.md` 파일은 다음 섹션으로 구성됩니다:

1. **해야 할 일 (체크리스트)**: 작업 항목 목록
2. **작성할 파일 목록**: 새로 생성/수정할 파일
3. **코드 구현 내용**: 상세한 코드 및 설명
4. **테스트 방법**: 검증 절차
5. **결과물 확인**: 성공 기준
6. **커밋 메시지**: Git 커밋 메시지 예시

### 코드 구현 내용 읽는 법

각 코드 블록에는:
- **역할**: 해당 코드의 목적
- **구현 내용**: 실제 코드
- **설명 및 근거**: 왜 이렇게 구현했는지

---

## 📞 문의 및 피드백

문서에 대한 질문이나 개선 사항이 있으면 멘토에게 확인하세요.

---

**문서 버전**: 1.0.0  
**최종 수정**: 2026-01-18
