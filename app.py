import streamlit as st
import os
import time
import datetime
import json
import base64
import re
import requests
import math
import csv
import io
from jinja2 import Template
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl, quote_plus, unquote_plus
 
# ==========================================
# 1. 시스템 설정
# ==========================================

def get_secret(name, default=""):
    value = os.environ.get(name)
    if value:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


OPENAI_API_KEY = get_secret("OPENAI_API_KEY")
GH_TOKEN = get_secret("GITHUB_TOKEN")
GH_REPO = get_secret("GITHUB_REPO")
MODEL_ID = get_secret("OPENAI_MODEL", "gpt-5")
FALLBACK_MODEL_ID = get_secret("OPENAI_FALLBACK_MODEL", "")
TRACKING_BASE_URL = get_secret("TRACKING_BASE_URL", "")
CLICK_LOG_BACKEND = get_secret("CLICK_LOG_BACKEND", "github")
CLICK_LOG_PATH = get_secret("CLICK_LOG_PATH", "logs/click_logs.csv")
MOCK_MODE = not OPENAI_API_KEY
 
# 고정 리소스 및 배너 URL
LOGO_URL = "https://lh3.googleusercontent.com/d/1WjzjlOOetztrcgq6rioAZxTzi_K-JwLl"
BLDG_URL = "https://lh3.googleusercontent.com/d/1f7XwQ2Z-43sECHQ53Of0J8NzqOeRh9Ll"
CONSULT_URL = "https://clever-designers-959477.framer.app/pium-%EA%B8%B0%EC%88%A0%EC%82%AC%EC%97%85%ED%99%94-%EC%84%BC%ED%84%B0-%EC%88%98%EC%9A%94%EA%B8%B0%EC%88%A0-%EC%A0%91%EC%88%98-%ED%8E%98%EC%9D%B4%EC%A7%80"
PR_URL = "https://link.inpock.co.kr/pnutlo?utm_source=ig&utm_medium=social&utm_content=link_in_bio"
DEFAULT_CAMPAIGN_PREFIX = "pnuth_newsletter"
 
# ==========================================
# 2. 핵심 유틸리티 함수
# ==========================================
 
def get_week_of_month(dt):
    first_day = dt.replace(day=1)
    adjusted_dom = dt.day + first_day.weekday()
    return int(math.ceil(adjusted_dom / 7.0))


def with_tracking(url, **params):
    if not url or url == "#":
        return url
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({k: v for k, v in params.items() if v not in (None, "")})
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def build_click_tracking_url(target_url, campaign_id, link_type, tech_id="", category=""):
    tagged_target = with_tracking(
        target_url,
        utm_source="newsletter",
        utm_medium="email",
        utm_campaign=campaign_id,
        tech_id=tech_id,
        category=category,
        link_type=link_type,
    )
    if not TRACKING_BASE_URL:
        return tagged_target
    params = {
        "track": "1",
        "campaign": campaign_id,
        "link_type": link_type,
        "tech_id": tech_id,
        "category": category,
        "target": quote_plus(tagged_target),
    }
    return f"{TRACKING_BASE_URL.rstrip('/')}?{urlencode(params)}"


def get_query_param(name, default=""):
    try:
        value = st.query_params.get(name, default)
    except Exception:
        params = st.experimental_get_query_params()
        value = params.get(name, [default])
    if isinstance(value, list):
        return value[0] if value else default
    return value or default


def github_api_headers():
    return {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def get_github_file(path):
    if not GH_TOKEN or not GH_REPO:
        return "", None
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    res = requests.get(url, headers=github_api_headers(), timeout=15)
    if res.status_code == 404:
        return "", None
    res.raise_for_status()
    payload = res.json()
    content = base64.b64decode(payload.get("content", "")).decode("utf-8-sig")
    return content, payload.get("sha")


def put_github_file(path, content, sha=None, message="Update file"):
    if not GH_TOKEN or not GH_REPO:
        return False
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8-sig")).decode("utf-8"),
    }
    if sha:
        payload["sha"] = sha
    res = requests.put(url, headers=github_api_headers(), json=payload, timeout=20)
    return res.status_code in [200, 201]


def append_click_log_to_github(campaign, link_type, tech_id, category, target_url):
    content, sha = get_github_file(CLICK_LOG_PATH)
    rows = []
    if content.strip():
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

    header = ["clicked_at", "campaign", "link_type", "tech_id", "category", "target_url", "source_app"]
    if not rows:
        rows.append(header)
    elif rows[0] != header:
        rows.insert(0, header)

    rows.append([
        datetime.datetime.now().isoformat(timespec="seconds"),
        campaign,
        link_type,
        tech_id,
        category,
        target_url,
        "pnuth-newsletter",
    ])

    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerows(rows)
    return put_github_file(
        CLICK_LOG_PATH,
        out.getvalue(),
        sha=sha,
        message=f"Log newsletter click: {campaign} {link_type} {tech_id}".strip(),
    )


def log_click(campaign, link_type, tech_id, category, target_url):
    if CLICK_LOG_BACKEND != "github":
        return False
    return append_click_log_to_github(campaign, link_type, tech_id, category, target_url)


def handle_tracking_request():
    if get_query_param("track") != "1":
        return False
    target_url = unquote_plus(get_query_param("target", "#"))
    campaign = get_query_param("campaign")
    link_type = get_query_param("link_type")
    tech_id = get_query_param("tech_id")
    category = get_query_param("category")
    try:
        log_click(campaign, link_type, tech_id, category, target_url)
    except Exception as e:
        st.warning(f"클릭 로그 저장 중 오류가 발생했습니다: {e}")

    st.markdown("클릭을 기록했습니다. 잠시 후 원래 페이지로 이동합니다.")
    st.markdown(f"[바로 이동하기]({target_url})")
    st.components.v1.html(
        f"""
        <script>
          window.location.replace({json.dumps(target_url)});
        </script>
        <meta http-equiv="refresh" content="0; url={target_url}">
        """,
        height=0,
    )
    return True
 
def upload_file_to_github(file_obj, patent_id, folder_name):
    if not GH_TOKEN or not GH_REPO:
        st.warning("GitHub 업로드 설정이 없어 외부 링크를 생성하지 못했습니다. `GITHUB_TOKEN`, `GITHUB_REPO`를 설정하세요.")
        return "https://via.placeholder.com/220?text=GitHub+Not+Configured"

    file_content = file_obj.getvalue()
    ext = file_obj.name.split('.')[-1].lower() if hasattr(file_obj, 'name') else 'png'
    file_name = f"{folder_name}/{patent_id}.{ext}"
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{file_name}"
 
    headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None
 
    payload = {"message": f"Update {folder_name}: {patent_id}", "content": base64.b64encode(file_content).decode("utf-8")}
    if sha:
        payload["sha"] = sha
 
    put_res = requests.put(url, headers=headers, json=payload)
 
    if put_res.status_code in [200, 201]:
        user_id, repo_name = GH_REPO.split('/')
        if folder_name == "pdfs":
            return f"https://{user_id}.github.io/{repo_name}/{file_name}"
        else:
            return f"https://raw.githubusercontent.com/{user_id}/{repo_name}/main/{file_name}"

    st.warning(f"⚠️ 업로드 실패: {file_name} (status: {put_res.status_code})")
    return "https://via.placeholder.com/220?text=Upload+Error"


def normalize_summary_field(summary):
    """
    AI 응답의 summary 필드가 list가 아닌 string 등으로 반환되는 경우를 방어.
    - list인 경우: 각 항목을 문자열로 강제 변환 후 그대로 사용
    - string인 경우: 문장 단위(마침표/느낌표/물음표 뒤 공백)로 분리 시도
    - 그 외(None 등): 안전한 기본값으로 대체
    """
    if isinstance(summary, list):
        cleaned = [str(item).strip() for item in summary if str(item).strip()]
        return cleaned if cleaned else ["요약 정보 없음"]

    if isinstance(summary, str):
        text = summary.strip()
        if not text:
            return ["요약 정보 없음"]
        # 문장 단위 분리 (마침표/느낌표/물음표 + 공백 기준)
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        return sentences if sentences else [text]

    if summary:
        return [str(summary)]

    return ["요약 정보 없음"]


def normalize_list_field(value, fallback):
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned if cleaned else fallback
    if isinstance(value, str) and value.strip():
        parts = [p.strip() for p in re.split(r"[,/·\n]", value) if p.strip()]
        return parts if parts else [value.strip()]
    return fallback


def extract_pdf_text(file_obj, max_chars=12000):
    try:
        import fitz
        doc = fitz.open(stream=file_obj.getvalue(), filetype="pdf")
        chunks = []
        for page_idx in range(min(doc.page_count, 6)):
            text = doc.load_page(page_idx).get_text("text").strip()
            if text:
                chunks.append(text)
        doc.close()
        return "\n\n".join(chunks)[:max_chars] or "PDF에서 텍스트를 추출하지 못했습니다."
    except Exception as e:
        return f"PDF 텍스트 추출 실패: {e}"


def extract_json(raw_text):
    raw = raw_text.strip()
    if not raw:
        raise ValueError("OpenAI 응답 텍스트가 비어 있습니다.")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        return json.loads(match.group(0))
    raise ValueError(f"JSON 객체를 찾지 못했습니다: {raw[:300]}")


def response_text(response):
    text = getattr(response, "output_text", "") or ""
    if text.strip():
        return text

    chunks = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            value = getattr(content, "text", None)
            if value:
                chunks.append(value)
    return "\n".join(chunks)


def call_openai_json(prompt, max_output_tokens=2500):
    from openai import (
        APIConnectionError,
        APIError,
        APITimeoutError,
        BadRequestError,
        OpenAI,
        RateLimitError,
    )

    retryable_errors = (APIConnectionError, APIError, APITimeoutError, RateLimitError)
    model = MODEL_ID
    client = OpenAI(api_key=OPENAI_API_KEY)

    for attempt in range(4):
        try:
            response = client.responses.create(
                model=model,
                instructions=(
                    "너는 부산대학교 기술사업화 뉴스레터용 특허 기술요약 전문가다. "
                    "반드시 유효한 JSON 객체만 출력한다."
                ),
                input=[{"role": "user", "content": prompt}],
                text={"format": {"type": "json_object"}},
                max_output_tokens=max_output_tokens,
            )
            raw_text = response_text(response)
            return extract_json(raw_text)
        except BadRequestError as e:
            if FALLBACK_MODEL_ID and is_capacity_error(e) and model != FALLBACK_MODEL_ID:
                model = FALLBACK_MODEL_ID
                continue
            raise
        except (ValueError, json.JSONDecodeError) as e:
            if attempt == 3:
                raise
            wait = min(20, (2 ** attempt) * 2)
            st.warning(f"AI 응답 형식 오류({str(e)[:60]}), {wait}초 후 재시도... ({attempt+1}/4)")
            time.sleep(wait)
        except retryable_errors as e:
            if FALLBACK_MODEL_ID and is_capacity_error(e) and model != FALLBACK_MODEL_ID:
                model = FALLBACK_MODEL_ID
                continue
            if attempt == 3:
                raise
            wait = min(45, (2 ** attempt) * 4)
            st.warning(f"일시적 API 오류({str(e)[:60]}), {wait}초 후 재시도... ({attempt+1}/4)")
            time.sleep(wait)

    raise RuntimeError("OpenAI API 호출에 실패했습니다.")


def is_capacity_error(error):
    message = str(error).lower()
    return "capacity" in message or "overloaded" in message or "temporarily unavailable" in message


def fallback_summary_from_pdf_text(file_obj, pdf_text):
    name = os.path.splitext(getattr(file_obj, "name", "기술요약서"))[0]
    clean_lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in (pdf_text or "").splitlines()
        if len(line.strip()) >= 8
    ]
    title = name
    for line in clean_lines[:20]:
        if any(token in line for token in ["기술명", "발명의 명칭", "명칭"]):
            title = line.split(":")[-1].split("：")[-1].strip()[:40] or name
            break

    joined = " ".join(clean_lines[:12])
    if not joined:
        joined = "PDF 텍스트를 충분히 추출하지 못했습니다."

    return {
        "title": title[:40],
        "problem": "업로드된 SMK 내용을 바탕으로 기업 적용 가능성을 검토할 수 있습니다.",
        "business_value": "세부 기술효과와 사업화 포인트는 SMK 확인 후 상담에서 구체화할 수 있습니다.",
        "applications": joined[:90],
        "summary": [
            "문제: 관련 기업의 기술 개선 수요 검토에 활용할 수 있습니다.",
            "이점: SMK를 통해 차별성과 적용 가능성을 빠르게 확인할 수 있습니다.",
            f"활용: {joined[:55]}",
        ],
        "target_industries": ["적용산업 확인필요"],
        "category": "기타",
    }

 
def analyze_pdf_document(file_obj, test_mode=False):
    if test_mode or MOCK_MODE:
        return {
            "title": "[테스트] 초고강도 하이브리드 금속-플라스틱 결합 신소재 기술",
            "problem": "복합소재 결합부의 내구성과 생산성을 동시에 높이고자 하는 기업에 적합합니다.",
            "business_value": "기존 공정 변경 부담을 낮추면서 제품 경량화와 품질 안정화를 기대할 수 있습니다.",
            "applications": "자동차 부품, 전자기기 하우징, 산업용 구조재에 적용 가능합니다.",
            "summary": [
                "문제: 소재 결합부의 강도와 생산 안정성을 개선합니다.",
                "이점: 경량화와 공정 효율 향상에 기여할 수 있습니다.",
                "활용: 자동차·전자부품·산업용 구조재에 적용 가능합니다."
            ],
            "target_industries": ["자동차부품", "전자부품", "소재·부품"],
            "category": "테스트분야"
        }
 
    pdf_text = extract_pdf_text(file_obj)
    prompt = f"""
    아래 특허 기술요약서(SMK) PDF 추출 텍스트를 분석하여 JSON 형식으로만 응답하세요. 다른 설명 없이 JSON 객체 하나만 출력하세요.

    반드시 아래 JSON 스키마와 자료형을 정확히 지키세요:
    {{
      "title": "문자열 (기술 명칭, 15자 내외)",
      "problem": "기업 관점에서 이 기술이 해결하는 문제 1문장",
      "business_value": "도입 기업이 얻을 수 있는 사업적 이점 1문장",
      "applications": "적용 가능한 제품/공정/서비스 분야 1문장",
      "summary": ["문제: ...", "이점: ...", "활용: ..."],
      "target_industries": ["산업태그1", "산업태그2", "산업태그3"],
      "category": "문자열"
    }}

    - title: 기술 명칭 (간결하게, 15자 내외 권장)
    - problem/business_value/applications: 기술 설명이 아니라 기업 담당자가 읽고 판단하기 쉬운 비즈니스 언어로 작성하세요.
    - summary: 반드시 JSON 배열(list) 형태로, 정확히 3개의 개별 문자열 요소로 구성하세요.
      절대로 3개 문장을 하나의 문자열로 이어 붙이지 마세요. 배열의 각 요소가 아래 각 항목에 대응해야 합니다.
        1) "문제: "로 시작. 기업 현장에서 어떤 문제를 줄이는지
        2) "이점: "로 시작. 비용, 품질, 생산성, 안정성, 성능 중 어떤 이점이 있는지
        3) "활용: "로 시작. 적용 가능한 산업/제품/공정
      각 문장은 35자 내외로 간결하게 작성하고, 세부 구성요소를 나열하는 명세서식 표현(예: 다중관 구조, 파라미터명 등)은 배제한 채
      비전문가도 이해할 수 있는 쉬운 비즈니스 언어로 작성하세요. 한 문장에 여러 절을 쉼표로 길게 이어붙이지 말고 짧고 명확하게 끊어 쓰세요.
      예시: "summary": ["문제: 강판 표면 결함 검사를 자동화합니다.", "이점: 육안 검사 대비 속도와 정확도를 높입니다.", "활용: 자동차·조선 금속 가공에 적용 가능합니다."]
    - target_industries: 기업이 빠르게 판단할 수 있는 적용 산업 태그를 2~4개 작성하세요. 예: 자동차부품, 의료기기, 반도체장비, 스마트팩토리, 이차전지, 조선해양, 식품바이오
    - category: 아래 15개 고정 목록 중에서, 기술의 명칭·요약·적용분야 내용을 근거로 가장 근접한 분야 하나만 추론하여 선택하세요.
      [바이오, 농림수산식품, 보건의료, 기계, 재료, 화공, 전기전자, 정보통신, 에너지자원, 원자력, 환경, 건설교통, 기계조선, 재료전자, 공정재료]
      반드시 위 목록에 있는 단어 중 하나를 그대로(공백/변형 없이) 사용하세요. 목록에 없는 새로운 분야명을 만들어내지 마세요.
      문서 상단의 학과명, 소속, 담당 교수명, 발급 기관 로고명(예: 정보컴퓨터공학부, 기술사업화센터 등)은 절대 참고하지 마세요.
      정확한 분류가 애매하더라도, 기술 내용상 가장 가까운 분야 하나를 반드시 선택하세요.

    <PDF_TEXT>
    {pdf_text}
    </PDF_TEXT>
    """

    try:
        parsed = call_openai_json(prompt, max_output_tokens=2500)
        if isinstance(parsed, list):
            parsed = parsed[0] if parsed and isinstance(parsed[0], dict) else {}
        if not isinstance(parsed, dict):
            raise ValueError(f"예상치 못한 응답 형식(type={type(parsed).__name__})")
        parsed["summary"] = normalize_summary_field(parsed.get("summary"))[:3]
        while len(parsed["summary"]) < 3:
            parsed["summary"].append("세부 활용 분야는 상담을 통해 구체화할 수 있습니다.")
        parsed["problem"] = str(parsed.get("problem") or parsed["summary"][0]).strip()
        parsed["business_value"] = str(parsed.get("business_value") or parsed["summary"][1]).strip()
        parsed["applications"] = str(parsed.get("applications") or parsed["summary"][2]).strip()
        parsed["target_industries"] = normalize_list_field(parsed.get("target_industries"), ["적용산업 확인필요"])[:4]
        if parsed.get("category") not in [
            "바이오", "농림수산식품", "보건의료", "기계", "재료", "화공", "전기전자", "정보통신",
            "에너지자원", "원자력", "환경", "건설교통", "기계조선", "재료전자", "공정재료"
        ]:
            parsed["category"] = "기타"
        return parsed
    except Exception as e:
        fallback = fallback_summary_from_pdf_text(file_obj, pdf_text)
        fallback["summary"][0] = f"문제: AI 상세요약 실패({str(e)[:24]})"
        return fallback
 
def group_patents_by_category(patent_list):
    grouped = {}
    for patent in patent_list:
        raw_cat = patent.get("category", "기타")
        cat = raw_cat.replace(" ", "").replace("\n", "") if raw_cat else "기타"
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(patent)
    return grouped
 
# ==========================================
# 3. 뉴스레터 HTML 템플릿 (Table 구조 - 전 메일 클라이언트 호환)
# ==========================================
html_template_str = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  @media only screen and (max-width: 720px) {
    .container { width: 100% !important; max-width: 100% !important; padding: 14px !important; }
    .brand-cell, .title-cell { display: block !important; width: 100% !important; text-align: left !important; }
    .newsletter-title { font-size: 20px !important; padding-top: 8px !important; }
    .hero-title { font-size: 22px !important; line-height: 1.35 !important; }
    .patent-image-cell, .patent-text-cell { display: block !important; width: 100% !important; border-right: 0 !important; box-sizing: border-box !important; }
    .patent-image { width: 100% !important; max-width: 260px !important; height: auto !important; }
    .cta-button { width: 100% !important; max-width: 420px !important; box-sizing: border-box !important; }
  }
</style>
</head>
<body style="margin:0; padding:0; background-color:#f5f7fa;">
 
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#e8f0fa;">
  <tr>
    <td align="center" style="padding:10px 20px; font-size:12px; color:#444; font-family:'Malgun Gothic', sans-serif;">
      본 메일은 부산대학교 산학협력단의 <strong>기술이전 또는 가족기업 대상</strong>으로 송부드리는 메일입니다. &nbsp;|&nbsp;
      수신을 원치 않으시면 <a href="mailto:cjs7024@pusan.ac.kr" style="color:#005BAC;">수신거부</a>를 클릭해 주세요.
    </td>
  </tr>
</table>
 
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f7fa;">
<tr><td align="center">
<table class="container" width="680" cellpadding="0" cellspacing="0" style="width:680px; max-width:680px; background-color:#ffffff; padding:20px; font-family:'Malgun Gothic', sans-serif;">
 
  <tr>
    <td style="border-bottom:2px solid #005BAC; padding-bottom:10px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td class="brand-cell" style="vertical-align:middle;">
            <img src="{{ logo_url }}" style="height:45px; vertical-align:middle;">
            <span style="font-size:16px; color:#333; font-weight:bold; margin-left:10px;">부산대학교기술지주주식회사</span>
          </td>
          <td class="title-cell newsletter-title" align="right" style="font-size:24px; color:#005BAC; font-weight:bold; vertical-align:middle;">PNUTH Newsletter</td>
        </tr>
      </table>
    </td>
  </tr>
 
  <tr><td style="padding:20px 0;">
    <img src="{{ bldg_url }}" width="100%" style="border-radius:10px; display:block;">
  </td></tr>
 
  <tr>
    <td style="padding-bottom:20px;">
      <h2 class="hero-title" style="color:#005BAC; margin:0 0 5px 0; font-size:25px; line-height:1.3;">부산대학교 산학협력단 우수 특허/기술 리스트</h2>
      <p style="margin:0; font-size:15px; color:#333; font-weight:bold;">{{ week_date }} 기준 우수 특허</p>
    </td>
  </tr>
 
  {% for category, patents in grouped_patents.items() %}
  <tr><td style="padding:10px 0 5px 0;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="background-color:#005BAC; padding:10px 18px; border-radius:6px; color:#ffffff; font-size:17px; font-weight:bold;">
          &#9616; {{ category|e }} 분야
        </td>
      </tr>
    </table>
  </td></tr>
 
  <tr><td style="padding-top:10px;">
    {% for patent in patents %}
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #ddd; border-radius:10px; margin-bottom:12px; background-color:#ffffff;">
      <tr>
        <td class="patent-image-cell" width="190" valign="middle" style="width:190px; padding:8px; border-right:1px solid #eee; background-color:#fafafa; text-align:center; vertical-align:middle;">
          <img class="patent-image" src="{{ patent.image_url }}" width="170" height="150" style="width:170px; height:150px; object-fit:contain; border-radius:6px; border:1px solid #eee; background-color:#fff; display:block; margin:0 auto;">
        </td>
        <td class="patent-text-cell" valign="top" style="padding:14px 16px; vertical-align:top;">
          <p style="margin:0 0 3px 0; font-weight:bold; color:#005BAC; font-size:15px; line-height:1.4; word-break:keep-all;">
            {{ patent.title|e }}
          </p>
          <p style="margin:0 0 10px 0; font-weight:bold; color:#555; font-size:13px; line-height:1.3;">
            ({{ patent.patent_id|e }})
          </p>
          {% if patent.target_industries %}
          <table cellpadding="0" cellspacing="0" style="margin:0 0 10px 0;">
            <tr>
              {% for tag in patent.target_industries %}
              <td style="background-color:#eef5ff; color:#005BAC; border:1px solid #c9ddf5; border-radius:4px; padding:4px 8px; font-size:12px; font-weight:bold;">
                {{ tag|e }}
              </td>
              <td style="width:5px;">&nbsp;</td>
              {% endfor %}
            </tr>
          </table>
          {% endif %}
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:10px;">
            <tr><td style="border-top:1px solid #eee; font-size:0; line-height:0; padding:0;">&nbsp;</td></tr>
          </table>
          {% for s in patent.summary %}
          <p style="margin:0 0 5px 0; font-size:14px; line-height:1.55; color:#333; word-break:keep-all;">&#8226; {{ s|e }}</p>
          {% endfor %}
          <table cellpadding="0" cellspacing="0" style="margin-top:12px;">
            <tr>
              <td style="background-color:#f0f4f8; border:1px solid #005BAC; border-radius:5px; padding:6px 14px;">
                <a href="{{ patent.smk_url }}" target="_blank" style="color:#005BAC; text-decoration:none; font-weight:bold; font-size:13px;">&#128196; 기술요약서(SMK) 보기</a>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    {% endfor %}
  </td></tr>
  {% endfor %}
 
  <tr>
    <td align="center" style="padding:15px 10px 10px 10px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="padding-bottom:12px;">
            <a class="cta-button" href="{{ consult_url }}" style="display:inline-block; width:400px; background-color:#ffffff; color:#005BAC; text-decoration:none; padding:15px 0; border-radius:8px; font-weight:bold; border:2px solid #005BAC; font-size:16px; text-align:center;">&#128161; 수요기술 상담신청</a>
          </td>
        </tr>
        <tr>
          <td align="center">
            <a class="cta-button" href="{{ pr_url }}" style="display:inline-block; width:400px; background-color:#555555; color:#ffffff; text-decoration:none; padding:15px 0; border-radius:8px; font-weight:bold; font-size:16px; text-align:center;">&#128250; PNUTH 홍보 채널 바로가기</a>
          </td>
        </tr>
      </table>
    </td>
  </tr>
 
  <tr>
    <td align="center" style="padding-top:20px; font-size:12px; color:gray; line-height:1.5;">
      부산대학교기술지주주식회사 | 부산광역시 금정구 부산대학로63번길 2<br>
      문의: 기술이전팀 최정식 과장(051-510-7024, jschoi7516@pusan.ac.kr)
    </td>
  </tr>
 
</table>
</td></tr></table>
 
</body>
</html>"""
 
# ==========================================
# 4. Streamlit 메인 실행
# ==========================================
def main():
    st.set_page_config(page_title="PNUTH 뉴스레터 생성기", page_icon="🚀")
    if handle_tracking_request():
        return

    st.title("🚀 PNUTH 뉴스레터 자동 생성기")
    st.info("PDF와 이미지 파일을 함께 업로드하세요. (파일명 번호 일치 필수)")
    if MOCK_MODE:
        st.warning("OPENAI_API_KEY가 없어 MOCK 모드로 동작합니다. 실제 PDF 분석 대신 테스트 요약이 사용됩니다.")
 
    is_test_mode = st.checkbox("🧪 테스트 모드 켜기 (체크 시 API 요금이 나가지 않으며 초고속으로 레이아웃만 확인합니다.)")
    effective_test_mode = is_test_mode or MOCK_MODE
 
    col1, col2 = st.columns(2)
    with col1:
        pdf_files = st.file_uploader("1. SMK PDF들", type="pdf", accept_multiple_files=True)
    with col2:
        img_files = st.file_uploader("2. 특허 이미지들", type=["png", "jpg"], accept_multiple_files=True)
 
    if pdf_files:
        if st.button("뉴스레터 생성 시작"):
            image_map = {os.path.splitext(img.name)[0]: img for img in (img_files or [])}
            patent_list = []
            status_text = st.empty()
            progress_bar = st.progress(0)
 
            for idx, uploaded_file in enumerate(pdf_files):
                base_name = uploaded_file.name.split('_')[0]
                patent_id = os.path.splitext(base_name)[0]
                status_text.text(f"⏳ {patent_id} 처리 중... ({idx+1}/{len(pdf_files)})")
 
                if not effective_test_mode:
                    time.sleep(5)
 
                data = analyze_pdf_document(uploaded_file, test_mode=effective_test_mode)
                data['patent_id'] = patent_id
 
                if effective_test_mode:
                    data['image_url'] = "https://via.placeholder.com/200x180?text=Test+Image"
                    data['smk_url'] = "#"
                else:
                    if patent_id in image_map:
                        data['image_url'] = upload_file_to_github(image_map[patent_id], patent_id, "images")
                    else:
                        data['image_url'] = "https://via.placeholder.com/200x180?text=No+Image"
                    data['smk_url'] = upload_file_to_github(uploaded_file, patent_id, "pdfs")
 
                patent_list.append(data)
                progress_bar.progress((idx + 1) / len(pdf_files))
 
            status_text.success("🎉 생성 완료!")
 
            grouped_patents = group_patents_by_category(patent_list)
            now = datetime.datetime.now()
            week_str = f"{now.year}년 {now.month}월 {get_week_of_month(now)}주차"
            campaign_id = f"{DEFAULT_CAMPAIGN_PREFIX}_{now.strftime('%Y%m%d')}"
            for patent in patent_list:
                patent["smk_url"] = build_click_tracking_url(
                    patent.get("smk_url", "#"),
                    campaign_id=campaign_id,
                    link_type="smk",
                    tech_id=patent.get("patent_id"),
                    category=patent.get("category"),
                )
 
            template = Template(html_template_str)
            result_html = template.render(
                week_date=week_str,
                grouped_patents=grouped_patents,
                logo_url=LOGO_URL,
                bldg_url=BLDG_URL,
                consult_url=build_click_tracking_url(
                    CONSULT_URL,
                    campaign_id=campaign_id,
                    link_type="consult",
                ),
                pr_url=build_click_tracking_url(
                    PR_URL,
                    campaign_id=campaign_id,
                    link_type="pr",
                )
            )
 
            st.divider()
            st.download_button(
                "📂 뉴스레터 HTML 다운로드",
                data=result_html,
                file_name=f"newsletter_{now.strftime('%Y%m%d')}.html",
                mime="text/html"
            )
            st.components.v1.html(result_html, height=800, scrolling=True)
 
if __name__ == "__main__":
    main()
