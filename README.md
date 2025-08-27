<p align="center">
   <img width="250" height="250" alt="image" src="https://github.com/user-attachments/assets/55666373-cffe-406b-947b-5a0d391cce5d" align="center" width="30%">
</p>
<p align="center"><h1 align="center">6-NEMO-AI</h1></p>
<p align="center">
	<em>모임 정보 생성과 AI 기반 그룹 추천 챗봇 레포지토리 <br> 2025.04.07 ~ 2025.08.01  </em>
</p>
<p align="center">
	<img src="https://img.shields.io/github/last-commit/100-hours-a-week/6-nemo-ai?style=flat&logo=git&logoColor=white&color=0080ff" alt="last-commit">
	<img src="https://img.shields.io/github/languages/top/100-hours-a-week/6-nemo-ai?style=flat&color=0080ff" alt="repo-top-language">
	<img src="https://img.shields.io/badge/Version-v3%20Complete-success?style=flat&logo=checkmarx&logoColor=white" alt="version">
</p>
<p align="center">사용된 기술 스택:</p>
<p align="center">
	<img src="https://img.shields.io/badge/FastAPI-009688.svg?style=flat&logo=FastAPI&logoColor=white" alt="FastAPI">
    <img src="https://img.shields.io/badge/ChromaDB-FF5E2B.svg?style=flat&logo=databricks&logoColor=white" alt="ChromaDB">
    <img src="https://img.shields.io/badge/Vertex%20AI-4285F4.svg?style=flat&logo=google-cloud&logoColor=white" alt="Vertex AI">
	<img src="https://img.shields.io/badge/vLLM-FF6B35.svg?style=flat&logo=v&logoColor=white" alt="vLLM">
	<br>
	<img src="https://img.shields.io/badge/Docker-2496ED.svg?style=flat&logo=Docker&logoColor=white" alt="Docker">
	<img src="https://img.shields.io/badge/Python-3776AB.svg?style=flat&logo=Python&logoColor=white" alt="Python">
	<img src="https://img.shields.io/badge/Apache%20Kafka-231F20.svg?style=flat&logo=Apache-Kafka&logoColor=white" alt="Kafka">
	<img src="https://img.shields.io/badge/WebSocket-010101.svg?style=flat&logo=socketdotio&logoColor=white" alt="WebSocket">
	<img src="https://img.shields.io/badge/Prometheus-E6522C.svg?style=flat&logo=Prometheus&logoColor=white" alt="Prometheus">
	<img src="https://img.shields.io/badge/Grafana-F46800.svg?style=flat&logo=Grafana&logoColor=white" alt="Grafana">
</p>
<br>

## 🔗 Table of Contents

- [📍 Overview](#-overview)
- [✨ Key Features](#-key-features)
- [🏗️ Architecture](#️-architecture)
- [📁 Project Structure](#-project-structure)
- [🚀 Getting Started](#-getting-started)
  - [☑️ Prerequisites](#-prerequisites)
  - [⚙️ Installation](#-installation)
  - [🤖 Usage](#-usage)
- [📊 API Versions](#-api-versions)
- [🔧 Development](#-development)
- [📌 Project Status](#-project-status)
- [🔰 Contributing](#-contributing)
- [🎗 License](#-license)
- [🙌 Acknowledgments](#-acknowledgments)

---
> **🌐 For International Viewers:** This repository is primarily documented in Korean as per team requirements. For the best reading experience, please use your browser's page translation feature (Chrome: right-click → "Translate to English" | Firefox/Safari: similar options available). All code comments, commit messages, and wiki documentation are also in Korean.

## 📍 Overview

**6-NEMO-AI**는 모임 정보 자동 생성과 AI 기반 그룹 추천을 위한 지능형 챗봇 플랫폼입니다. 사용자로부터 최소한의 정보만을 받아 완전한 모임 정보를 자동 생성하고, 대화형 챗봇을 통해 개인화된 그룹 추천을 제공합니다. Vertex AI의 Gemini부터 로컬 Gemma 모델, 그리고 실시간 WebSocket 스트리밍까지 단계적으로 발전한 완전한 AI 플랫폼입니다.
### Core Purpose
- **자동 모임 정보 생성**: 그룹명, 카테고리, 목적만으로 완전한 모임 정보 자동 생성
- **AI 기반 그룹 추천**: 대화형 챗봇을 통한 개인화된 그룹 추천 서비스
- **실시간 스트리밍**: WebSocket을 통한 실시간 응답 스트리밍
- **확장 가능한 아키텍처**: Kafka 이벤트 스트리밍과 벡터 검색을 통한 고성능 시스템

> 📚 **프로젝트 설계부터 개발, 다양한 트러블 슈팅, 그리고 개발 회고까지 더 자세한 내용은 [프로젝트 위키](https://github.com/100-hours-a-week/6-nemo-ai/wiki)를 참조하세요.**

---

## ✨ Key Features

### Automatic Group Information Generation
- **최소 입력으로 최대 결과**: 그룹명, 카테고리, 목적만 입력하면 완전한 모임 정보 생성
- **AI 생성 콘텐츠**:
  - **한줄 소개**: 모임을 한문장으로 요약한 매력적인 소개
  - **상세 소개**: 모임의 목적과 특징을 상세히 설명하는 소개글
  - **태그 생성**: 모임 특성에 맞는 검색 태그 자동 생성
  - **단계별 계획**: 모임 진행을 위한 체계적인 단계별 활동 계획

### Interactive Chatbot Recommendation
- **3단계 MCQ 시스템**: 사용자와 번갈아가며 진행하는 3개의 객관식 질문
- **개인화된 추천**: 사용자 응답을 바탕으로 한 맞춤형 그룹 추천
- **상세한 설명**: 추천 이유와 그룹 특징에 대한 AI 생성 설명

### Real-time Streaming & Event Processing
- **WebSocket 스트리밍**: 실시간 응답 스트리밍으로 향상된 사용자 경험
- **Kafka 이벤트 처리**: 확장 가능한 이벤트 기반 아키텍처
- **벡터 검색**: ChromaDB를 활용한 의미론적 유사도 검색
- **하이브리드 검색**: 다중 검색 방식을 결합한 정교한 추천 시스템

### Multi-Model AI Integration
- **Vertex AI Gemini**: 클라우드 기반 고성능 AI 모델
- **로컬 Gemma 4B**: 최적화된 로컬 모델을 통한 빠른 응답
- **vLLM 통합**: 효율적인 로컬 모델 서빙
- **Circuit Breaker 패턴**: 안정적인 AI 모델 운영

---

## 🏗️ Architecture
 - to be added
---

## 📁 Project Structure

```sh
6-nemo-ai/
├── 🏗️ app/                          # 메인 애플리케이션
│   ├── 🔧 core/                      # 핵심 유틸리티
│   │   ├── vertex_client.py         # Vertex AI Gemini 클라이언트
│   │   ├── vllm_manager.py         # 로컬 Gemma 모델 매니저
│   │   ├── websocket_manager.py    # WebSocket 연결 관리
│   │   └── buffer_parser.py        # 스트리밍 응답 파싱
│   │
│   ├── 🌐 router/                    # API 엔드포인트
│   │   ├── v1/                     # 모임 정보 생성 API
│   │   │   ├── group_information.py # 모임 정보 생성
│   │   │   ├── group_writer.py     # 소개/계획 생성
│   │   │   └── tag_extraction.py   # 태그 추출
│   │   │
│   │   ├── v2/                     # 챗봇 추천 API
│   │   │   ├── chatbot.py          # MCQ 챗봇
│   │   │   ├── group_information.py # 최적화된 모임 생성
│   │   │   └── vector_db.py        # 벡터 검색
│   │   │
│   │   └── v3/                     # 실시간 스트리밍
│   │       └── ws_chatbot.py       # WebSocket 챗봇
│   │
│   ├── ⚙️ services/                  # 비즈니스 로직
│   │   ├── v1/                     # Vertex AI 기반 서비스
│   │   │   ├── group_information.py # 모임 정보 생성 로직
│   │   │   ├── description_writer.py # 소개 생성
│   │   │   ├── plan_writer.py      # 계획 생성
│   │   │   └── tag_extraction.py   # 태그 추출
│   │   │
│   │   ├── v2/                     # 로컬 모델 기반 서비스
│   │   │   ├── chatbot.py          # MCQ 챗봇 로직
│   │   │   └── group_information.py # 최적화된 생성
│   │   │
│   │   └── v3/                     # 스트리밍 서비스
│   │       └── ws_chatbot.py       # WebSocket 챗봇 로직
│   │
│   ├── 🗄️ database/                  # 데이터 & 검색
│   │   ├── chroma_client.py        # ChromaDB 연결
│   │   ├── hybrid_search.py        # 하이브리드 검색
│   │   ├── vector_searcher.py      # 벡터 유사도 검색
│   │   └── synthetic_document_builder.py # 합성 문서 생성
│   │
│   └── 🔌 integrations/              # 외부 통합
│       ├── kafka/                  # 이벤트 스트리밍
│       └── monitoring/             # 모니터링 스택
```

---

## 🚀 Getting Started

### ☑️ Prerequisites

- **Python 3.11+** 및 pip 패키지 매니저
- **Docker & Docker Compose** 컨테이너화용
- **Google Cloud SDK** Vertex AI Gemini 사용시
- **ChromaDB** 벡터 검색용
- **Apache Kafka** 이벤트 스트리밍용 (v3)

### ⚙️ Installation

#### Quick Start

```powershell
# 저장소 클론
git clone https://github.com/100-hours-a-week/6-nemo-ai.git
cd 6-nemo-ai

# 가상환경 설정
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env에 API 키 및 설정 입력
```

#### Docker Setup

```powershell
# 전체 스택 실행
docker-compose up -d

# 모니터링 포함 실행
docker-compose -f docker-compose.monitoring.yml up -d
```

### 🤖 Usage

#### Starting the Server

```powershell
#  개발 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
---

## 📊 API Versions

### v1 - Foundation (Vertex AI Gemini)
**모임 정보 생성을 위한 클라우드 AI 서비스**

#### Core Features
- **입력**: 그룹명, 카테고리, 목적 (최소 정보)
- **AI 모델**: Google Vertex AI Gemini API
- **자동 생성 콘텐츠**:
  - 📝 **한줄 소개**: 모임의 핵심을 한 문장으로 요약
  - 📖 **상세 소개**: 모임의 목적, 활동, 분위기를 상세히 설명
  - 🏷️ **태그 생성**: 검색과 분류를 위한 관련 태그들
  - 📋 **단계별 계획**: 모임 진행을 위한 체계적인 활동 계획

#### Use Cases
- 새로운 모임 생성시 완전한 정보 자동 생성
- 모임 기획자를 위한 콘텐츠 생성 도구
- 모임 플랫폼의 자동 콘텐츠 생성 기능

### v2 - Enhanced (Local Gemma 4B + Chatbot)
**최적화된 로컬 모델과 대화형 추천 시스템**

#### Core Features
- **AI 모델**: Google Gemma 4B (vLLM을 통한 로컬 실행)
- **3단계 MCQ 시스템**: 
  - 🤖 챗봇이 객관식 질문 생성
  - 🔄 사용자와 번갈아가며 3라운드 진행
  - 📊 각 질문마다 4개의 선택지 제공
- **개인화된 추천**: 사용자 응답 기반 그룹 매칭
- **설명 생성**: AI가 추천 이유를 상세히 설명
- **성능 최적화**: vLLM을 통한 로컬 모델 서빙으로 빠른 응답 속도

#### MCQ Flow Example
1. **1라운드**: "어떤 활동을 선호하시나요?"
   - A) 실내 활동  B) 야외 활동  C) 온라인 활동  D) 혼합 활동
2. **2라운드**: "모임 규모는 어떻게 선호하시나요?"
   - A) 소규모(5명 이하)  B) 중규모(10명 내외)  C) 대규모(20명 이상)  D) 상관없음
3. **3라운드**: "모임 빈도는 어떻게 하고 싶으신가요?"
   - A) 주 1회  B) 월 2-3회  C) 월 1회  D) 비정기적

### v3 - Advanced (WebSocket + Kafka + Fine-tuning)
**실시간 스트리밍, 이벤트 기반 아키텍처, 그리고 커스텀 파인튜닝**

#### Core Features
- **WebSocket 스트리밍**: 실시간 응답 스트리밍
- **Kafka 이벤트 처리**: 확장 가능한 이벤트 기반 시스템
- **모델 파인튜닝**: 도메인 특화 데이터로 Gemma 4B 파인튜닝
- **프로덕션 배포**: 파인튜닝된 모델의 실제 서비스 배포
- **세션 관리**: 지속적인 대화 세션 유지
- **컨텍스트 인식**: 이전 대화 맥락을 고려한 응답
- **실시간 알림**: 새로운 추천이나 업데이트 실시간 전달

---

## 🔧 Development

### Development Setup
```powershell
# 개발 의존성 설치
pip install -r requirements.txt

# ChromaDB 초기화
python scripts/init_chroma.py
```
---

## 📌 Project Status

### ✅ Completed & Production Ready
이 프로젝트는 **최종 완성 버전**으로, 추가적인 주요 업데이트나 기능 개발 계획이 없습니다.

#### Fully Implemented Features
- [x] **v1**: Vertex AI Gemini를 통한 완전한 모임 정보 생성
- [x] **v2**: 로컬 Gemma 4B 모델과 3단계 MCQ 챗봇 시스템
- [x] **v3**: WebSocket 실시간 스트리밍, Kafka 이벤트 처리, 그리고 파인튜닝된 모델 배포
- [x] **벡터 검색**: ChromaDB를 활용한 하이브리드 검색 시스템
- [x] **모니터링**: Prometheus + Grafana 완전한 관찰가능성 스택
- [x] **배포**: AWS/GCP 자동 배포 파이프라인
- [x] **테스트**: 단위/통합/E2E 테스트 스위트

#### Architecture Highlights
- **3단계 진화**: 클라우드 AI → 로컬 최적화 → 실시간 스트리밍
- **멀티모델 지원**: Vertex AI Gemini + 로컬 Gemma 4B 하이브리드 운영
- **확장 가능한 설계**: 마이크로서비스 아키텍처와 이벤트 기반 처리
- **프로덕션 그레이드**: Circuit breaker, 모니터링, 자동 배포 완비

### Final Implementation Notes
- **성능 최적화 완료**: v2의 로컬 Gemma 4B 모델과 vLLM으로 응답 속도 대폭 향상
- **파인튜닝 & 배포 완료**: v3에서 도메인 특화 데이터로 파인튜닝한 커스텀 모델을 실제 프로덕션 환경에 성공적으로 배포
- **운영 안정성 확보**: 완전한 모니터링과 오류 처리 시스템 구축
- **확장성 보장**: Kafka와 벡터 검색을 통한 대규모 서비스 대응

---

## 🔰 Contributing

### 🚀 Team: 네모를 찾아서

이 프로젝트는 [**네모를 찾아서 팀**](https://github.com/orgs/100-hours-a-week/teams/6)의 인공지능 레포지토리입니다. 팀은 프론트엔드, 백엔드, 클라우드, 인공지능 등 각 분야별 전문 레포지토리를 운영하며, 이 레포지토리는 네모 서비스의 인공지능을 담당합니다.

### 🤖 Contributors in this Repository 
#### <img src="https://github.com/chaerheeon.png" width="50" style="border-radius: 50%;" alt="chaerheeon"> &nbsp;&nbsp; 인공지능 팀: [@chaerheeon](https://github.com/chaerheeon)
- **모델 개발**: AI 모델 파인튜닝 및 최적화
- **AI/ML 시스템**: Vertex AI Gemini 연동, 로컬 Gemma 4B 배포, vLLM 최적화  
- **벡터 검색 & 데이터베이스**: ChromaDB 통합, 하이브리드 검색 알고리즘, 벡터 인덱싱
- **실시간 시스템**: WebSocket 스트리밍, 버퍼 파싱, 컨텍스트 처리
- **Kafka**: 이벤트 기반 아키텍처, 메시지 큐 구현
- **테스트 프레임워크**: pytest, E2E 테스트 스위트 (47+ 테스트)
- **모니터링 스택**: Prometheus & Grafana 통합, 관찰가능성 시스템
- **코드 아키텍처**: src/에서 app/ 모듈형 구조로 완전한 리팩토링

#### <img src="https://github.com/R0MMMY.png" width="50" style="border-radius: 50%;" alt="R0MMMY"> &nbsp;&nbsp; 인공지능 팀: [@R0MMMY](https://github.com/R0MMMY)  
- **모델 개발**: AI 모델 파인튜닝 및 최적화
- **프롬프트 엔지니어링**: 프롬프트 설계 및 버전 관리 시스템
- **AI 응답 품질**: 모델 출력 검증 및 개선
- **성능 최적화**: AI 추론 속도 및 정확도 향상

#### <img src="https://github.com/halfmoon01.png" width="50" style="border-radius: 50%;" alt="halfmoon01"> <img src="https://github.com/g1ennk.png" width="50" style="border-radius: 50%;" alt="g1ennk"> &nbsp;&nbsp; 클라우드 팀: **[@halfmoon01](https://github.com/halfmoon01) & [@g1ennk](https://github.com/g1ennk)**
- **CI/CD 파이프라인**: GCP에서 AWS로 인프라 마이그레이션
- **컨테이너 오케스트레이션**: Docker 및 배포 자동화
- **클라우드 운영**: AWS/GCP 서비스 통합 및 관리
- **한국어 로컬라이제이션**: CI/CD 시스템에서 UTF-8 한국어 로케일 지원
- **Infrastructure as Code**: 자동화된 배포 및 확장 시스템

### Welcome Contributions
이 프로젝트는 완성된 상태이지만, 다음과 같은 기여를 환영합니다:

- **🐛 Bug Fixes**: AI 모델 연동 이슈나 시스템 버그 수정
- **📚 Documentation**: AI 모델 사용법이나 API 문서 개선  
- **🔧 Performance**: AI 모델 최적화나 응답 속도 개선
- **🌐 Localization**: 다국어 지원 확장
- **🧪 Testing**: AI 모델 출력 품질 테스트 개선

### Technical Expertise Areas
- **Large Language Models**: Vertex AI Gemini, Gemma 4B, vLLM 최적화
- **Vector Search**: ChromaDB, 하이브리드 검색, 의미론적 유사도
- **Real-time AI**: WebSocket 스트리밍, 실시간 AI 응답
- **Model Fine-tuning**: 도메인 특화 모델 파인튜닝 및 배포
- **AI Infrastructure**: AI 모델 서빙, 모니터링, 확장성
- **Event-driven Architecture**: Kafka 이벤트 스트리밍

## 🎗 License

이 프로젝트는 [MIT 라이선스](LICENSE) 하에 보호됩니다.

---

## 🙌 Acknowledgments

### AI Models & Services
- **Google Vertex AI**: Gemini API를 통한 고품질 모임 정보 생성
- **Google Gemma 4B**: vLLM을 통한 최적화된 로컬 실행을 위한 경량 모델
- **ChromaDB**: 벡터 검색과 의미론적 유사도 계산
- **Apache Kafka**: 확장 가능한 실시간 이벤트 처리

### Development Stack
- **FastAPI**: 고성능 비동기 웹 프레임워크
- **WebSocket**: 실시간 양방향 통신
- **Prometheus + Grafana**: 포괄적인 모니터링 솔루션
- **Docker**: 컨테이너화된 배포 환경

---

<p align="center">
<strong>네모 (NE:MO)</strong><br>
<em>인공지능 팀 레포지토리</em>
</p>
