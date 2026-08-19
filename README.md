# PNUTH Newsletter

부산대학교기술지주 뉴스레터 HTML 자동 생성기입니다.

## 환경 변수 / Streamlit Secrets

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-5"
OPENAI_FALLBACK_MODEL = ""
GITHUB_TOKEN = "github_pat_..."
GITHUB_REPO = "owner/repo"
TRACKING_BASE_URL = "https://배포된-streamlit-앱주소"
GOOGLE_SHEET_ID = "구글시트_ID"
GOOGLE_SHEET_NAME = "click_logs"
GOOGLE_SERVICE_ACCOUNT_JSON = """{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
  "client_email": "...@....iam.gserviceaccount.com",
  "client_id": "..."
}"""
```

- `OPENAI_API_KEY`가 없으면 테스트/MOCK 모드로 동작합니다.
- `GITHUB_TOKEN`, `GITHUB_REPO`가 없으면 PDF/이미지 외부 링크 업로드는 비활성화됩니다.
- PDF는 PyMuPDF로 텍스트를 추출한 뒤 OpenAI API로 뉴스레터용 제목/요약/분야를 생성합니다.
- AI는 `문제`, `기업 이점`, `활용 분야`, `적용산업 태그` 중심으로 요약합니다.
- 생성된 링크에는 `utm_source=newsletter`, `utm_campaign`, `tech_id` 등이 자동으로 붙어 관심 기술 추적에 활용할 수 있습니다.
- HTML은 메일 클라이언트 호환을 위해 table 기반 구조를 유지하면서 680px 폭과 모바일 대응 스타일을 적용했습니다.

## 클릭 추적

`TRACKING_BASE_URL`, `GOOGLE_SHEET_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON`을 설정하면 뉴스레터 링크가 Streamlit 앱을 먼저 거치며 Google Sheets에 클릭 로그를 저장합니다.

Google Sheet에는 아래 컬럼이 자동 생성됩니다.

```text
clicked_at, campaign, link_type, tech_id, category, target_url, user_agent, source_app
```

- `link_type=smk`: 기술요약서 클릭
- `link_type=consult`: 수요기술 상담신청 클릭
- `link_type=pr`: PNUTH 홍보 채널 클릭

구글 서비스 계정의 `client_email`을 클릭 로그를 저장할 Google Sheet에 편집자로 공유해야 기록됩니다.
