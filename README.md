# PNUTH Newsletter

부산대학교기술지주 뉴스레터 HTML 자동 생성기입니다.

## 환경 변수 / Streamlit Secrets

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-5"
OPENAI_FALLBACK_MODEL = ""
OPENAI_VISION_MODEL = "gpt-4o-mini"
GITHUB_TOKEN = "github_pat_..."
GITHUB_REPO = "owner/repo"
TRACKING_BASE_URL = "https://배포된-streamlit-앱주소"
CLICK_LOG_BACKEND = "github"
CLICK_LOG_PATH = "logs/click_logs.csv"
```

- `OPENAI_API_KEY`가 없으면 테스트/MOCK 모드로 동작합니다.
- `GITHUB_TOKEN`, `GITHUB_REPO`가 없으면 PDF/이미지 외부 링크 업로드는 비활성화됩니다.
- PDF 링크는 브라우저 내 PDF 보기 가능성을 높이기 위해 jsDelivr CDN 주소로 생성되며, 이미지는 `raw.githubusercontent.com` 원본 파일 주소로 생성됩니다.
- PDF는 PyMuPDF로 텍스트를 추출한 뒤 OpenAI API로 뉴스레터용 제목/요약/분야를 생성합니다.
- 같은 기술번호의 PNG/JPG가 있으면 해당 이미지를 `OPENAI_VISION_MODEL`로 먼저 분석합니다.
- 같은 기술번호 이미지가 없을 때는 PDF 페이지를 이미지로 변환한 뒤 `OPENAI_VISION_MODEL`로 다시 분석합니다.
- AI는 `문제`, `기업 이점`, `활용 분야`, `적용산업 태그` 중심으로 요약합니다.
- 뉴스레터 본문은 기업 담당자가 판단하기 쉽도록 4개 요약 항목, 확대된 기술 이미지, 밀도 높은 직사각형 카드 레이아웃으로 구성됩니다.
- 기술 제목은 단순 기술명 대신 `기술명 + 핵심 효용`이 드러나는 뉴스레터형 제목으로 보강됩니다.
- 생성된 링크에는 `utm_source=newsletter`, `utm_campaign`, `tech_id` 등이 자동으로 붙어 관심 기술 추적에 활용할 수 있습니다.
- HTML은 메일 클라이언트 호환을 위해 table 기반 구조를 유지하면서 680px 폭과 모바일 대응 스타일을 적용했습니다.

## 클릭 추적: GitHub CSV 방식

`TRACKING_BASE_URL`, `GITHUB_TOKEN`, `GITHUB_REPO`를 설정하면 뉴스레터 링크가 Streamlit 앱을 먼저 거치며 GitHub 저장소의 CSV 파일에 클릭 로그를 저장합니다.

기본 저장 위치:

```text
logs/click_logs.csv
```

CSV에는 아래 컬럼이 자동 생성됩니다.

```text
clicked_at, campaign, link_type, tech_id, category, target_url, source_app
```

- `link_type=smk`: 기술요약서 클릭
- `link_type=consult`: 수요기술 상담신청 클릭
- `link_type=pr`: PNUTH 홍보 채널 클릭

GitHub 토큰에는 해당 저장소의 `Contents: Read and write` 권한이 필요합니다. 클릭이 발생할 때마다 CSV 파일 업데이트 커밋이 생성됩니다.
