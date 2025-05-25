## 🐳 Docker 이미지 빌드
```bash
docker build -t embedder .
```

## 🐳 Docker 컨테이너 실행 (CPU 환경)
```bash
docker run -p 8002:8002 embedder
```

## 🔎 API 테스트 (Swagger UI)
브라우저에서 접속: http://localhost:8002/docs