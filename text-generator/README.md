## 🚀 GCP L4 GPU VM에 Text Generator 배포


```bash
✅ 1. GCP L4 GPU VM 인스턴스 만들기

✅ 2. 포트 8003 열기 (도커용)
    - VPC 네트워크 → 방화벽 규칙 → 방화벽 규칙 만들기
    - 이름: allow-8003
    - 대상: 모든 인스턴스
    - 프로토콜: tcp
    - 포트: 8003
    - 소스 IP 범위: 0.0.0.0/0
    
✅ 3. 인스턴스에 접속 & Docker 설치
# SSH 접속
gcloud compute ssh text-generator-vm

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker 권한 부여
sudo usermod -aG docker $USER
newgrp docker

✅ 4. NVIDIA Docker Toolkit 설치 (GPU 사용용)
# 배포판 확인
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)

# GPG 키 및 저장소 추가 
curl -fsSL https://nvidia.github.io/nvidia-docker/gpgkey | sudo tee /usr/share/keyrings/nvidia-docker.gpg > /dev/null
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list \
  | sed 's#https://#signed-by=/usr/share/keyrings/nvidia-docker.gpg https://#' \
  | sudo tee /etc/apt/sources.list.d/nvidia-docker.list > /dev/null

# 설치 및 데몬 재시작
sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker

> Toolkit 설치 후 테스트: docker run --rm --gpus all nvidia/cuda:12.3.0-base-ubuntu22.04 nvidia-smi


✅ 5. 프로젝트 복제
# GitHub에서 프로젝트 클론
git clone https://github.com/your-team/6-nemo-ai.git
cd 6-nemo-ai/text-generator
```

## 🐳 Docker 이미지 빌드

```bash
# 프로젝트 루트에서 실행
docker build -t text-generator .
```

## 🟩 Docker 컨테이너 실행 (GPU VM)

다음 명령어를 통해 GPU 환경에서 컨테이너를 실행할 수 있습니다:

```bash
docker run --gpus all \
  -e HUGGINGFACE_HUB_TOKEN=hf_xxx123456789abcdef \
  -p 8003:8003 \
  text-generator
  
# --gpus all 옵션은 GPU 자원을 컨테이너에 할당합니다.
```
## 🔎 API 테스트
브라우저 접속: http://<VM_EXTERNAL_IP>:8003/docs

