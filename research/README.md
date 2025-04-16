**이 내용은 플레이스홀더 텍스트이지만, 실제로 이 프로젝트에서 사용될 예정입니다. 
이 README는 추후 변경될 예정입니다.**

# 🔍 로컬 LLM 모델 찾기 및 사용하기

이 문서는 Hugging Face, Unsloth, Ollama, vLLM, GGUF 등을 활용하여 로컬에서 LLM(Local Language Model)을 검색하고 실행하는 방법을 소개합니다.

---

## 🤗 Hugging Face

Hugging Face Hub에서는 다양한 LLM을 라이선스, 파라미터 수, 데이터셋 기준으로 필터링하여 검색할 수 있습니다. `transformers`, `accelerate` 패키지를 활용하면 로컬 환경에서도 쉽게 모델을 실행할 수 있습니다.

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("모델_이름")
tokenizer = AutoTokenizer.from_pretrained("모델_이름")
```

# 🦥 Unsloth

Unsloth는 경량화된 파인튜닝과 추론 속도에 최적화된 프레임워크입니다. QLoRA 어댑터 기반 학습을 지원하며, Hugging Face 모델과의 높은 호환성을 자랑합니다.

* 단일 GPU 환경에서도 안정적으로 작동
* 빠른 파인튜닝 및 추론 성능
* 로컬 환경에 적합한 경량 구조

🔗 [Unsloth GitHub](https://github.com/unslothai/unsloth)

# 🦙 Ollama
Ollama는 Docker 기반의 로컬 LLM 관리 도구로, 명령어 한 줄로 다양한 모델을 설치하고 실행할 수 있습니다.

```bash
ollama run llama2
```
* 프롬프트 캐싱 및 관리 기능 포함
* Mistral, LLaMA, Codellama 등 다양한 모델 지원

🔗 [Ollama 공식 사이트](https://ollama.com/)

# ⚡ vLLM
vLLM은 고성능 추론 서버로, 대규모 배치에서도 낮은 지연 시간과 높은 처리량을 제공합니다. PagedAttention, Continuous Batching 등 최신 기술이 적용되어 있습니다.

* OpenAI API 호환
* Hugging Face 모델과 연동 가능
* 프로덕션용 API 서버로 적합

🔗 [vLLM GitHub](https://github.com/vllm-project/vllm)

# 📦 GGUF
**GGUF (GPTQ Quantized Unified Format)** 는 quantized 모델을 위한 새로운 통합 포맷입니다. 다음과 같은 툴과 호환됩니다:

* llama.cpp
* koboldcpp
* GPT4All
* 기타 경량 LLM 실행기

GGUF 포맷은 CPU 또는 로우스펙 GPU 환경에서도 효율적인 추론을 가능하게 하며, 4bit 또는 5bit로 경량화된 모델을 제공합니다.

⚙️ 이 가이드는 로컬에서 LLM을 직접 실행하거나 개인 서버 환경에 배포하려는 개발자를 위한 참고 자료입니다.

