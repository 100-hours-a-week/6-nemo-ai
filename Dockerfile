FROM python:3.13.3-slim

WORKDIR /app

RUN pip install --upgrade pip==25.1

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
