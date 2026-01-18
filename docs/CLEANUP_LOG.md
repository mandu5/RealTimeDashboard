# 프로젝트 파일 정리 로그

> **정리 일자**: 2026-01-18  
> **정리 기준**: 내부망 Linux 개발 환경에서 Python Dash 프로젝트에 필요한 파일만 유지

---

## ✅ 삭제된 파일 및 디렉토리

### React/TypeScript 관련 파일 (Python Dash와 무관)

| 파일/디렉토리 | 삭제 이유 |
|--------------|----------|
| `ATTRIBUTIONS.md` | React/Figma 라이선스 정보. Python Dash 프로젝트와 무관 |
| `index.html` | React/Vite 빌드용 HTML. Dash는 자체 HTML 생성 |
| `package.json` | React/TypeScript 의존성. Python 프로젝트에는 불필요 |
| `postcss.config.mjs` | Tailwind CSS PostCSS 설정. Dash는 자체 CSS 사용 |
| `vite.config.ts` | Vite 빌드 설정. Dash는 Vite 불필요 |
| `src/` 디렉토리 | React 컴포넌트 전체 (55개 파일). Python Dash로 전환했으므로 불필요 |

### Docker 관련 파일 (내부망 개발 환경)

| 파일/디렉토리 | 삭제 이유 |
|--------------|----------|
| `docker-compose.yml` | Docker 컨테이너 배포 설정. 내부망 PC 개발 환경에서는 불필요 |
| `Dockerfile/` 디렉토리 | 잘못된 구조 (main.tsx 파일 포함). Dockerfile이 아님 |

### 실행 스크립트 (중복/불필요)

| 파일 | 삭제 이유 |
|------|----------|
| `run_dash.bat` | Windows 배치 파일. 내부망 Linux 환경에서는 불필요 |
| `run_dash.sh` | Linux 셸 스크립트. `run.py`가 더 적합한 진입점 |

### 참고용/레거시 파일 (불필요)

| 파일 | 삭제 이유 |
|------|----------|
| `dash_app.py` | 단일 파일 버전 (1029줄). 실제 사용은 `ugv_mon/` 모듈 구조 |
| `README_DASH.md` | `dash_app.py` 사용법 문서. 프로젝트에서 더 이상 사용하지 않음 |
| `config.py` | Flask 스타일 레거시 설정. 실제 사용은 `ugv_mon/config.py` (dataclass 기반) |

### 개발 환경 폴더 (불필요)

| 폴더 | 삭제 이유 |
|------|----------|
| `venv/` | Python 가상 환경. `.gitignore` 포함, 필요시 재생성 가능 |
| `.cursor/` | Cursor IDE 설정 폴더. IDE가 자동 재생성, 프로젝트와 무관 |

---

## ✅ 유지된 파일

### 핵심 파일
- `run.py` - 진입점 (권장)
- `requirements.txt` - Python 의존성
- `README.md` - 프로젝트 메인 문서

### 프로젝트 구조
- `ugv_mon/` - 메인 Python 패키지 (모든 기능)
- `docs/` - 개발 가이드 문서

---

## 📊 정리 결과

### 삭제된 항목
- **파일**: 11개 (React/Docker/스크립트/참고용/레거시)
- **디렉토리**: 4개 (`src/`, `Dockerfile/`, `venv/`, `.cursor/`)
- **총 파일 수**: 약 60개 이상 (src/, venv/ 포함)

### 남은 항목
- **Python 코드**: `ugv_mon/` 모듈 구조 (실제 사용)
- **문서**: `docs/` 가이드 문서
- **설정**: `requirements.txt`
- **진입점**: `run.py`

---

## 📝 후속 작업 완료

1. ✅ **`dash_app.py` 삭제**: 참고용 단일 파일 버전 제거
2. ✅ **`README_DASH.md` 삭제**: 관련 문서 제거
3. ✅ **`config.py` 삭제**: 레거시 Flask 스타일 설정 제거 (실제 사용은 `ugv_mon/config.py`)
4. ✅ **`venv/`, `.cursor/` 삭제**: 개발 환경 폴더 제거 (필요시 재생성 가능)
5. ✅ **`.gitignore` 업데이트**: `.cursor/` 추가
6. ✅ **`02_FILE_STRUCTURE.md` 업데이트**: 삭제된 파일 참조 제거

---

## 🔍 정리 전후 비교

### 정리 전
```
opus1/
├── React 파일들 (index.html, package.json, vite.config.ts, ...)
├── React 컴포넌트 (src/ 디렉토리, 55개 파일)
├── Docker 파일들 (docker-compose.yml, Dockerfile/)
├── 실행 스크립트들 (run_dash.bat, run_dash.sh)
└── Python 프로젝트 (ugv_mon/, run.py, ...)
```

### 정리 후
```
opus1/
├── run.py              # 진입점
├── requirements.txt    # Python 의존성
├── README.md           # 프로젝트 문서
├── ugv_mon/            # 메인 Python 패키지
└── docs/               # 개발 가이드
```

---

**정리 완료**: 2026-01-18
