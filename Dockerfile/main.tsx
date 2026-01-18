# UGV-MON Dashboard - Dockerfile
# Python Dash Implementation

FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 파일 복사
COPY dash_app.py .

# 데이터 디렉토리 생성 (선택사항)
RUN mkdir -p /app/data

# 포트 노출
EXPOSE 8050

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8050')"

# 애플리케이션 실행
CMD ["python", "dash_app.py"]
