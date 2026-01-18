@echo off
REM UGV-MON Dashboard - Dash 실행 스크립트 (Windows)
REM Version 6.0

echo 🚀 UGV-MON Dashboard (Dash) 시작...

REM 가상환경 확인
if not exist "venv\" (
    echo 📦 가상환경 생성 중...
    python -m venv venv
)

REM 가상환경 활성화
echo 🔧 가상환경 활성화...
call venv\Scripts\activate.bat

REM 의존성 설치
echo 📥 패키지 설치 중...
pip install -r requirements.txt --quiet

REM 애플리케이션 실행
echo ✅ 대시보드 실행...
echo 🌐 브라우저에서 http://localhost:8050 접속하세요
echo.
python dash_app.py

pause
