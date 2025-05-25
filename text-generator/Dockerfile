FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 종속성 설치
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 코드 복사
COPY ./app /app

# 포트 노출
EXPOSE 8003

# 서버 실행 명령
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
