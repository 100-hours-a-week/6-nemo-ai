# 6-ne:mo-ai
# 🙋🏻‍♀️ 팀원 가이드 (네모 프로젝트)

안녕하세요! 프로젝트를 원활하게 협업하기 위해 꼭 숙지해야 할 내용들을 정리해 드립니다. 처음이라 어려울 수 있지만, 아래 내용을 보고 하나씩만 따라와 주세요. 😊

---

## ✅ 기본 규칙

### 1. **이슈 생성 시 꼭 작성해야 할 항목**
아래 이미지처럼 **상위 이슈(parent issue)** 를 생성할 때는 **다음 항목들을 모두 입력**해 주세요:

> **시작일, 마감일, 챕터, 유형, 난이도, 볼륨, 스프린트**

<img width="243" alt="image" src="https://github.com/user-attachments/assets/6b03d2c1-c531-4afa-8cbe-4ca1a0a3914a" />


📌 **서브 이슈(sub issue)** 는 **마일스톤만 설정**하시면 됩니다.  
❌ 그 외 항목은 **절대 작성하지 마세요.**

<img width="254" alt="image" src="https://github.com/user-attachments/assets/a6c34705-d0f0-41ba-bac4-0fa59af63d27" />


---

## 🌱 [브랜치 전략](https://www.notion.so/1e487f969ba08025ade0ed04474ecafe?pvs=4)

- 꼭 이슈 생성 후 브랜치 생성하기
- `git-flow` 전략 기반  
- **release 브랜치 사용하지 않음**
- **브랜치 이름은 kebab-case 사용** (`-`으로 구분)

| 브랜치 종류 | 형식 | 설명 |
|--|--|--|
| main | main | 운영 배포용 |
| develop | develop | 개발 통합용 |
| 기능 개발 | feature/이슈번호-기능명 | 예: `feature/3-user-login` |
| 버그 수정 | fix/이슈번호-버그명 |
| 운영 긴급 수정 | hotfix/이슈번호-긴급수정명 |
| 리팩토링 | refactor/이슈번호-기능명 |

⚠️ 그 외 브랜치는 **팀과 상의 후 생성**해 주세요.

---

# 🔥 **📌 꼭 지켜주세요!**

1. **기능 단위로 브랜치를 따로 만들어주세요.**  
   👉 여러 기능을 **한 브랜치에서 작업하지 마세요.**  
   → **기능별로 분리해야 코드 리뷰나 머지가 훨씬 쉬워집니다.**

2. **요청한 기능만 작업해서 PR 올려주세요.**  
   👉 **요청 외의 작업(불필요한 수정, 설정 변경 등)은 절대 포함하지 마세요.**  
   → 여러 요소가 섞이면 추적이 어렵고, 리뷰도 지연됩니다.

---

## 📝 커밋 메시지 컨벤션

\`\`\`
타입: 설명 (#이슈번호)
\`\`\`

예:
\`\`\`
Feat: 모임 생성 API 추가 (#5)
\`\`\`

| 타입 | 설명 |
|------|------|
| Feat | 새로운 기능 추가 |
| Design | UI/CSS 수정 |
| Refactor | 코드 리팩토링 |
| Fix | 버그 수정 |
| Comment | 주석만 변경 |
| Remove | 파일/폴더 삭제 |
| Rename | 이름 변경 |
| Setting | 프로젝트 설정 |
| Docs | 문서 수정 |
| Chore | 기타 잡일 |


---

# 🔀 PR 템플릿

`.github/ISSUE_TEMPLATE/pull_request_template.md` 파일을 사용해 아래 형식으로 작성해 주세요:

\`\`\`markdown
## What
→

## Why
→

## Changes
→

## Related Issue
→
\`\`\`

- 꼭 본인 브랜치는 본인이 PR하기

---

# 🧪 **코드 테스트는 무조건 필수입니다!**

최근 코드 중 **테스트 없이 업로드된 코드**에서 문제가 있었습니다.  
❗ **꼭 기억해 주세요**:

> "**올리기 전에 실행해보고, 최소한 한 번은 테스트를 해주세요.**"

그리고 가능하면 **아래 구조처럼 테스트 코드를 작성**해 주세요:

\`\`\`python
if __name__ == "__main__":
    # 테스트용 코드 작성
    print("기능 확인용 테스트입니다.")
\`\`\`

이 구조는 다른 파일에서 import될 때 **불필요하게 실행되지 않도록 방지**합니다.  
**협업은 신뢰와 검증이 중요합니다.** 본인의 기능이 **정상 작동하는지 꼭 확인**해 주세요.

---

궁금하신 점은 언제든지 편하게 말씀해 주세요!  
정말 감사합니다 😊

---

(본문과 상관 없음)For later use 

``` 
# Web Framework and ASGI Server
fastapi==0.115.9
uvicorn==0.34.2
starlette==0.45.3

# HTTP Client
httpx==0.28.1

# Data Validation and Settings
pydantic==2.11.4
python-dotenv==1.1.0

# Async Support
nest-asyncio==1.6.0

# Development Tools
pyngrok==7.2.5

# Vector Operations and ML
numpy==2.2.5
scikit-learn==1.6.1
scipy==1.15.2

# Text Processing
jinja2==3.1.6

# Vector Database
chromadb==1.0.7

# API Integration
google-genai==1.13.0

# Utility Packages
PyYAML==6.0.2
typing-extensions==4.13.2
```
