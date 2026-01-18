# UGV-MON 개발 가이드 문서 요약

> **참고**: 각 날짜별 상세 가이드는 `04_DAY01.md`와 `05_DAY02.md`의 구조를 참고하여 작성되었습니다.
> 나머지 날짜별 문서(Day 3-10)는 각 날짜 작업 시 동일한 구조로 확장하시면 됩니다.

---

## 📚 문서 생성 완료 목록

### ✅ 완료된 문서

1. **[00_PROJECT_OVERVIEW.md](./00_PROJECT_OVERVIEW.md)** - 프로젝트 개요
2. **[01_ARCHITECTURE.md](./01_ARCHITECTURE.md)** - 아키텍처 구조  
3. **[02_FILE_STRUCTURE.md](./02_FILE_STRUCTURE.md)** - 파일 구조 및 역할
4. **[03_ICD_SPECIFICATION.md](./03_ICD_SPECIFICATION.md)** - ICD v1.0 파싱 규격
5. **[04_DAY01.md](./04_DAY01.md)** - Day 1 상세 가이드 (완료) ✅
6. **[05_DAY02.md](./05_DAY02.md)** - Day 2 상세 가이드 (완료) ✅
7. **[99_APPENDIX.md](./99_APPENDIX.md)** - 부록
8. **[README.md](./README.md)** - 문서 인덱스

### 🔄 확장 필요한 문서 (Day 3-10)

다음 문서들은 `05_DAY02.md`의 구조를 참고하여 각 날짜 작업 시 확장하시면 됩니다:

- **06_DAY03.md** - ICD 파싱 MVP
- **07_DAY04.md** - 데이터 품질 분석
- **08_DAY05.md** - 가용성 분석
- **09_DAY06.md** - 지터 + 손실 추정
- **10_DAY07.md** - 백엔드 → UI 연동
- **11_DAY08.md** - 차트 구현
- **12_DAY09.md** - 로그 테이블 + 폴리싱
- **13_DAY10.md** - 통합 안정화 + 문서화

---

## 📋 각 날짜별 문서 구조 (템플릿)

각 `DAYXX.md` 파일은 다음 구조를 따릅니다:

```markdown
# Day X (주차 요일) - 작업명

> **상태**: 🔲 예정  
> **목표**: 목표 설명

## 📋 해야 할 일 (체크리스트)
- [ ] 작업 항목 1
- [ ] 작업 항목 2

## 📁 작성할 파일 목록
- 새로 생성되는 파일
- 수정되는 파일

## 💻 코드 구현 내용
### 1. 파일명 - 역할
**역할**: ...
**구현 내용**: ...
**설명 및 근거**: ...

## 🧪 테스트 방법
- 테스트 절차
- 확인 사항

## ✅ 결과물 확인
- 성공 기준
- 확인 체크리스트

## 📝 커밋 메시지
```
feat(...): ...
```
```

---

## 💡 사용 가이드

### 1. 프로젝트 처음 시작
→ **[00_PROJECT_OVERVIEW.md](./00_PROJECT_OVERVIEW.md)** 읽기

### 2. 현재 작업 (Day 1 완료)
→ **[04_DAY01.md](./04_DAY01.md)** 확인

### 3. 다음 작업 (Day 2 예정)
→ **[05_DAY02.md](./05_DAY02.md)** 읽고 구현

### 4. ICD 파싱 규격 확인
→ **[03_ICD_SPECIFICATION.md](./03_ICD_SPECIFICATION.md)** 참고

### 5. 파일 구조 이해
→ **[02_FILE_STRUCTURE.md](./02_FILE_STRUCTURE.md)** 참고

### 6. 아키텍처 이해
→ **[01_ARCHITECTURE.md](./01_ARCHITECTURE.md)** 참고

---

## 📅 각 날짜별 주요 작업 요약

| Day | 주요 작업 | 핵심 파일 |
|-----|----------|----------|
| 1 | UI 스켈레톤 | `ugv_mon/components/`, `layouts/` |
| 2 | Scapy 캡처 | `ugv_mon/capture/sniffer.py` |
| 3 | ICD 파싱 | `ugv_mon/parser/icd_parser.py` |
| 4 | 품질 분석 | `ugv_mon/analysis/quality.py` |
| 5 | 가용성 분석 | `ugv_mon/analysis/availability.py` |
| 6 | 지터/손실 | `ugv_mon/analysis/jitter.py`, `loss.py` |
| 7 | UI 연동 | `ugv_mon/data/live_data.py` |
| 8 | 차트 구현 | `ugv_mon/layouts/charts.py` (수정) |
| 9 | 로그 테이블 | `ugv_mon/components/log_table.py` (수정) |
| 10 | 통합 테스트 | `tests/` 디렉토리 |

---

**문서 생성 완료 일자**: 2026-01-18
