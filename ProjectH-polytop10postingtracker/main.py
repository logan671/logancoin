from __future__ import annotations

import json
import os
import re
from urllib.parse import urlparse
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape

KST = timezone(timedelta(hours=9))
BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
PREVIOUS_POSTS_PATH = BASE_DIR / "previous_posts.json"
STATUS_PATH = BASE_DIR / "status.json"
ARCHIVE_PATH = BASE_DIR / "archive.json"
TEMPLATE_PATH = BASE_DIR / "template.html"


@dataclass
class TweetItem:
    tweet_id: str
    author: str
    url: str
    text_en: str
    text_ko: str
    images: list[str]
    rank_meta: dict[str, Any]
    fetched_at: str


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_previous_posts() -> dict[str, Any]:
    data = load_json(PREVIOUS_POSTS_PATH, {"history": []})
    if "history" not in data or not isinstance(data["history"], list):
        return {"history": []}
    return data


def recent_tweet_ids(previous_posts: dict[str, Any], days: int = 3) -> set[str]:
    now = datetime.now(KST).date()
    result: set[str] = set()
    for row in previous_posts.get("history", []):
        row_date_raw = row.get("date")
        ids = row.get("tweet_ids", [])
        if not row_date_raw or not isinstance(ids, list):
            continue
        try:
            row_date = datetime.strptime(row_date_raw, "%Y-%m-%d").date()
        except ValueError:
            continue
        if (now - row_date).days < days:
            result.update(str(x) for x in ids)
    return result


def update_previous_posts(previous_posts: dict[str, Any], selected_ids: list[str], days: int = 3) -> None:
    today = datetime.now(KST).date()
    history = []
    for row in previous_posts.get("history", []):
        row_date_raw = row.get("date")
        ids = row.get("tweet_ids", [])
        if not row_date_raw or not isinstance(ids, list):
            continue
        try:
            row_date = datetime.strptime(row_date_raw, "%Y-%m-%d").date()
        except ValueError:
            continue
        if (today - row_date).days < days:
            history.append({"date": row_date_raw, "tweet_ids": [str(x) for x in ids]})

    today_raw = today.strftime("%Y-%m-%d")
    history = [row for row in history if row["date"] != today_raw]
    history.append({"date": today_raw, "tweet_ids": selected_ids})
    save_json(PREVIOUS_POSTS_PATH, {"history": history})


def extract_json_object(text: str) -> dict[str, Any]:
    if not text:
        return {}
    text = text.strip()
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(0))
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}


def grok_chat_completion(api_key: str, messages: list[dict[str, str]], timeout_sec: int = 30) -> str:
    base_url = os.getenv("GROK_API_BASE_URL", "https://api.x.ai/v1").rstrip("/")
    model = os.getenv("GROK_MODEL", "grok-2-latest")
    url = f"{base_url}/chat/completions"

    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        },
        timeout=timeout_sec,
    )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for row in content:
            if isinstance(row, dict) and isinstance(row.get("text"), str):
                parts.append(row["text"])
        return "\n".join(parts)
    return str(content)


def get_available_models(api_key: str, timeout_sec: int = 15) -> list[str]:
    base_url = os.getenv("GROK_API_BASE_URL", "https://api.x.ai/v1").rstrip("/")
    url = f"{base_url}/models"
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=timeout_sec,
    )
    response.raise_for_status()
    data = response.json()
    rows = data.get("data", [])
    model_ids = []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("id"), str):
                model_ids.append(row["id"])
    return model_ids


def resolve_grok_model(api_key: str) -> str:
    preferred = [x.strip() for x in os.getenv("GROK_MODEL_CANDIDATES", "grok-2-latest,grok-2,grok-beta").split(",") if x.strip()]
    explicit = os.getenv("GROK_MODEL", "").strip()
    if explicit:
        preferred.insert(0, explicit)

    try:
        available_list = get_available_models(api_key=api_key, timeout_sec=int(os.getenv("GROK_TIMEOUT", "30")))
        available = set(available_list)
        for model in preferred:
            if model in available and "image" not in model.lower():
                return model
        for model in available_list:
            lower = model.lower()
            if "grok" in lower and "image" not in lower:
                return model
        if available_list:
            return available_list[0]
    except Exception:
        pass

    return preferred[0] if preferred else "grok-2-latest"


def normalize_post(row: dict[str, Any]) -> dict[str, Any] | None:
    tweet_id = str(
        row.get("tweet_id")
        or row.get("tweetId")
        or row.get("id")
        or row.get("post_id")
        or ""
    ).strip()
    text_en = str(
        row.get("text_en")
        or row.get("text")
        or row.get("content")
        or row.get("body")
        or ""
    ).strip()
    if not tweet_id or not text_en:
        return None

    def to_number(value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace(",", "").strip()
            if cleaned.isdigit():
                return float(cleaned)
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    rank_value = to_number(row.get("rank"))
    rank = int(rank_value) if rank_value is not None else None

    images_raw = row.get("images")
    if not isinstance(images_raw, list):
        images_raw = row.get("image_urls") or row.get("media") or []

    author_raw = row.get("author")
    if isinstance(author_raw, dict):
        author = str(author_raw.get("username") or author_raw.get("name") or "unknown").strip() or "unknown"
    else:
        author = str(author_raw or row.get("username") or row.get("user") or "unknown").strip() or "unknown"

    url = str(row.get("url") or row.get("link") or row.get("tweet_url") or "").strip()
    if not url:
        url = f"https://x.com/i/status/{tweet_id}"
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host not in {"x.com", "twitter.com"}:
        return None
    if "/status/" not in parsed.path:
        return None

    images = [str(x).strip() for x in images_raw] if isinstance(images_raw, list) else []

    return {
        "tweet_id": tweet_id,
        "author": author,
        "url": url,
        "text_en": text_en,
        "images": [x for x in images if x],
        "rank": rank,
        "view_count": to_number(row.get("view_count") or row.get("views") or row.get("impressions")),
        "like_count": to_number(row.get("like_count") or row.get("likes") or row.get("favorite_count")) or 0,
        "repost_count": to_number(row.get("repost_count") or row.get("retweet_count") or row.get("reposts")) or 0,
        "reply_count": to_number(row.get("reply_count") or row.get("replies")) or 0,
    }


def normalize_posts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = normalize_post(row)
        if not item:
            continue
        tweet_id = item["tweet_id"]
        if tweet_id in seen:
            continue
        seen.add(tweet_id)
        normalized.append(item)
    return normalized


def fetch_posts_from_grok(
    api_key: str,
    model: str,
    candidate_count: int = 20,
    range_label: str = "top 1-10",
) -> list[dict[str, Any]]:
    system_prompt = (
        "You are a data extractor for social posts. "
        "Return valid JSON only."
    )
    user_prompt = (
        f"Find {range_label} X posts from the last 24 hours about Polymarket alpha/strategy/whale/copy-trade. "
        "Return a JSON object with key 'posts'. "
        "Each post item must include only these required keys: tweet_id, text_en. "
        "Optional keys: author, url, images, rank, view_count, like_count, repost_count, reply_count. "
        "IMPORTANT: url must be real x.com or twitter.com status links only (no example.com, no placeholders). "
        "If you are unsure about factual links, return an empty posts array. "
        "If optional fields are unavailable, set them to null or empty list. "
        f"Return up to {candidate_count} items. "
        "Do not include markdown fences."
    )
    os.environ["GROK_MODEL"] = model
    content = grok_chat_completion(
        api_key=api_key,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        timeout_sec=int(os.getenv("GROK_TIMEOUT", "30")),
    )
    payload = extract_json_object(content)
    posts = payload.get("posts", [])
    return normalize_posts(posts if isinstance(posts, list) else [])


def fetch_posts_from_x_api(bearer_token: str, candidate_count: int = 20) -> list[dict[str, Any]]:
    url = "https://api.x.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {bearer_token}"}
    query = os.getenv(
        "X_SEARCH_QUERY",
        '(polymarket (alpha OR whale OR strategy OR "copy trade")) -is:retweet -is:reply lang:en',
    )
    max_results = min(max(candidate_count, 10), 100)
    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "created_at,public_metrics,author_id,attachments,referenced_tweets",
        "expansions": "author_id,attachments.media_keys",
        "user.fields": "username,name",
        "media.fields": "url,preview_image_url,type",
    }
    sort_order = os.getenv("X_SORT_ORDER", "relevancy").strip().lower()
    if sort_order in {"relevancy", "recency"}:
        params["sort_order"] = sort_order

    min_likes = int(os.getenv("X_MIN_LIKES", "5"))
    min_score = int(os.getenv("X_MIN_SCORE", "12"))

    response = requests.get(url, headers=headers, params=params, timeout=int(os.getenv("X_TIMEOUT", "30")))
    response.raise_for_status()
    payload = response.json()

    data_rows = payload.get("data", [])
    includes = payload.get("includes", {})
    users = includes.get("users", [])
    media = includes.get("media", [])

    user_by_id: dict[str, dict[str, Any]] = {}
    for row in users:
        if isinstance(row, dict) and isinstance(row.get("id"), str):
            user_by_id[row["id"]] = row

    media_by_key: dict[str, dict[str, Any]] = {}
    for row in media:
        if isinstance(row, dict) and isinstance(row.get("media_key"), str):
            media_by_key[row["media_key"]] = row

    posts: list[dict[str, Any]] = []
    for row in data_rows:
        if not isinstance(row, dict):
            continue
        tweet_id = str(row.get("id", "")).strip()
        text_en = str(row.get("text", "")).strip()
        if not tweet_id or not text_en:
            continue

        referenced = row.get("referenced_tweets", [])
        if isinstance(referenced, list):
            has_reply_ref = any(
                isinstance(ref, dict) and str(ref.get("type", "")).lower() == "replied_to"
                for ref in referenced
            )
            if has_reply_ref:
                continue

        if text_en.lstrip().startswith("@"):
            continue

        author_id = str(row.get("author_id", "")).strip()
        user = user_by_id.get(author_id, {})
        username = str(user.get("username", "")).strip() if isinstance(user, dict) else ""
        author = username or "unknown"
        post_url = f"https://x.com/{author}/status/{tweet_id}" if username else f"https://x.com/i/status/{tweet_id}"

        metrics = row.get("public_metrics", {})
        like_count = metrics.get("like_count", 0) if isinstance(metrics, dict) else 0
        repost_count = metrics.get("retweet_count", 0) if isinstance(metrics, dict) else 0
        reply_count = metrics.get("reply_count", 0) if isinstance(metrics, dict) else 0
        quote_count = metrics.get("quote_count", 0) if isinstance(metrics, dict) else 0
        score = int(like_count) + (2 * int(repost_count)) + int(reply_count) + int(quote_count)
        if int(like_count) < min_likes or score < min_score:
            continue

        images: list[str] = []
        attachments = row.get("attachments", {})
        if isinstance(attachments, dict):
            media_keys = attachments.get("media_keys", [])
            if isinstance(media_keys, list):
                for key in media_keys:
                    media_row = media_by_key.get(str(key))
                    if not media_row:
                        continue
                    media_url = str(media_row.get("url") or media_row.get("preview_image_url") or "").strip()
                    if media_url:
                        images.append(media_url)

        posts.append(
            {
                "tweet_id": tweet_id,
                "author": author,
                "url": post_url,
                "text_en": text_en,
                "images": images,
                "rank": None,
                "view_count": None,
                "like_count": like_count,
                "repost_count": repost_count + quote_count,
                "reply_count": reply_count,
            }
        )

    posts.sort(
        key=lambda x: (
            -(float(x.get("like_count") or 0) + 2 * float(x.get("repost_count") or 0) + float(x.get("reply_count") or 0))
        )
    )
    return normalize_posts(posts)


def translate_to_korean(api_key: str, model: str, posts: list[dict[str, Any]]) -> dict[str, str]:
    inputs = []
    for row in posts:
        tweet_id = str(row.get("tweet_id", "")).strip()
        text_en = str(row.get("text_en", "")).strip()
        if tweet_id and text_en:
            inputs.append({"tweet_id": tweet_id, "text_en": text_en})
    if not inputs:
        return {}

    system_prompt = (
        "You are a professional Korean translator for crypto trading audience. "
        "Keep meaning accurate and concise. Return valid JSON only."
    )
    user_prompt = (
        "Translate the following English post texts to Korean.\n"
        "Return a JSON object with key 'translations'.\n"
        "Each item must contain: tweet_id, text_ko.\n"
        f"Input: {json.dumps(inputs, ensure_ascii=False)}"
    )
    os.environ["GROK_MODEL"] = model
    content = grok_chat_completion(
        api_key=api_key,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        timeout_sec=int(os.getenv("GROK_TIMEOUT", "30")),
    )
    payload = extract_json_object(content)
    rows = payload.get("translations", [])
    result: dict[str, str] = {}
    if not isinstance(rows, list):
        return result
    for row in rows:
        if not isinstance(row, dict):
            continue
        tweet_id = str(row.get("tweet_id", "")).strip()
        text_ko = str(row.get("text_ko", "")).strip()
        if tweet_id and text_ko:
            result[tweet_id] = text_ko
    return result


def fallback_korean_text(text_en: str) -> str:
    text = text_en.strip()
    if not text:
        return ""

    mock_match = re.match(
        r"Polymarket alpha signal #(\d+): whale flow and momentum setup\.",
        text,
        flags=re.IGNORECASE,
    )
    if mock_match:
        n = mock_match.group(1)
        return f"Polymarket 알파 시그널 #{n}: 고래 자금 흐름과 모멘텀 세팅입니다."

    replacements = {
        "Polymarket": "폴리마켓",
        "alpha": "알파",
        "signal": "시그널",
        "strategy": "전략",
        "momentum": "모멘텀",
        "whale": "고래",
        "copy-trade": "카피트레이드",
    }
    converted = text
    for src, dst in replacements.items():
        converted = re.sub(src, dst, converted, flags=re.IGNORECASE)
    return f"[자동 번역] {converted}"


def ranking_key(row: dict[str, Any]) -> tuple[int, float]:
    rank = row.get("rank")
    if isinstance(rank, int):
        return (0, float(rank))

    view_count = row.get("view_count")
    if isinstance(view_count, (int, float)):
        return (1, -float(view_count))

    like_count = row.get("like_count") if isinstance(row.get("like_count"), (int, float)) else 0
    repost_count = row.get("repost_count") if isinstance(row.get("repost_count"), (int, float)) else 0
    reply_count = row.get("reply_count") if isinstance(row.get("reply_count"), (int, float)) else 0
    score = float(like_count) + float(repost_count) + float(reply_count)
    return (2, -score)


def build_tweet_item(row: dict[str, Any], text_ko_map: dict[str, str]) -> TweetItem | None:
    tweet_id = str(row.get("tweet_id", "")).strip()
    if not tweet_id:
        return None
    text_en = str(row.get("text_en", "")).strip()
    if not text_en:
        return None
    images_raw = row.get("images", [])
    images = [str(x).strip() for x in images_raw] if isinstance(images_raw, list) else []

    return TweetItem(
        tweet_id=tweet_id,
        author=str(row.get("author", "unknown")).strip() or "unknown",
        url=str(row.get("url", "")).strip() or f"https://x.com/i/status/{tweet_id}",
        text_en=text_en,
        text_ko=(
            text_ko_map.get(tweet_id)
            or str(row.get("text_ko", "")).strip()
            or fallback_korean_text(text_en)
        ),
        images=[x for x in images if x],
        rank_meta={
            "rank": row.get("rank"),
            "view_count": row.get("view_count"),
            "like_count": row.get("like_count"),
            "repost_count": row.get("repost_count"),
            "reply_count": row.get("reply_count"),
        },
        fetched_at=datetime.now(KST).isoformat(),
    )


def get_mock_posts(count: int = 20) -> list[dict[str, Any]]:
    rows = []
    for i in range(1, count + 1):
        rows.append(
            {
                "tweet_id": f"mock-{1000 + i}",
                "author": f"trader_{i}",
                "url": f"https://x.com/trader_{i}/status/{1000 + i}",
                "text_en": f"Polymarket alpha signal #{i}: whale flow and momentum setup.",
                "text_ko": f"Polymarket 알파 시그널 #{i}: 고래 자금 흐름과 모멘텀 세팅입니다.",
                "images": [],
                "rank": i,
                "view_count": 10000 - i * 100,
                "like_count": 1000 - i * 10,
                "repost_count": 250 - i,
                "reply_count": 120 - i,
            }
        )
    return normalize_posts(rows)


def load_status() -> dict[str, Any]:
    return load_json(
        STATUS_PATH,
        {"needs_credit_topup": False, "is_mock_data": False, "last_error": "", "updated_at": ""},
    )


def save_status(status: dict[str, Any]) -> None:
    status["updated_at"] = datetime.now(KST).isoformat()
    save_json(STATUS_PATH, status)


def load_archive() -> dict[str, list[dict[str, Any]]]:
    data = load_json(ARCHIVE_PATH, {})
    if not isinstance(data, dict):
        return {}
    cleaned: dict[str, list[dict[str, Any]]] = {}
    for date_key, rows in data.items():
        if not isinstance(date_key, str) or not isinstance(rows, list):
            continue
        cleaned_rows = [row for row in rows if isinstance(row, dict)]
        cleaned[date_key] = cleaned_rows
    return cleaned


def save_archive(archive: dict[str, list[dict[str, Any]]]) -> None:
    save_json(ARCHIVE_PATH, archive)


def render_html(
    posts: list[TweetItem],
    banner_message: str,
    archive_data: dict[str, list[dict[str, Any]]],
    selected_date: str,
) -> str:
    env = Environment(
        loader=FileSystemLoader(str(BASE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(TEMPLATE_PATH.name)
    return template.render(
        generated_at=datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
        posts=[asdict(x) for x in posts],
        banner_message=banner_message,
        selected_date=selected_date,
        archive_data=archive_data,
    )


def main() -> None:
    load_dotenv(BASE_DIR / ".env")
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("GROK_API_KEY", "").strip()
    x_bearer_token = os.getenv("X_BEARER_TOKEN", "").strip()
    candidate_count = int(os.getenv("TOP_N_CANDIDATES", "20"))
    target_posts = int(os.getenv("TARGET_POSTS", "10"))
    use_mock_on_failure = os.getenv("USE_MOCK_ON_FAILURE", "true").lower() == "true"
    enable_translation = os.getenv("ENABLE_GROK_TRANSLATION", "false").lower() == "true"

    status = load_status()
    status.setdefault("is_mock_data", False)
    banner_message = ""
    model = os.getenv("GROK_MODEL", "grok-2-latest")
    if api_key:
        model = resolve_grok_model(api_key)

    try:
        if x_bearer_token:
            raw_posts = fetch_posts_from_x_api(bearer_token=x_bearer_token, candidate_count=candidate_count)
        elif api_key:
            raw_posts = fetch_posts_from_grok(
                api_key=api_key,
                model=model,
                candidate_count=candidate_count,
                range_label="top 1-10",
            )
        else:
            raw_posts = []
        if not raw_posts and use_mock_on_failure:
            raw_posts = get_mock_posts(candidate_count)
            status["is_mock_data"] = True
            status["last_error"] = "no_posts_from_grok_response"
        else:
            status["is_mock_data"] = False
            status["needs_credit_topup"] = False
            status["last_error"] = ""
    except requests.HTTPError as exc:
        error_text = str(exc)
        if exc.response is not None:
            error_text = f"{error_text} | body: {exc.response.text[:300]}"
        source = "x_fetch_error" if x_bearer_token else "fetch_error"
        status["last_error"] = f"{source}: {error_text}"
        if "quota" in error_text.lower() or "credit" in error_text.lower() or "billing" in error_text.lower():
            status["needs_credit_topup"] = True
        raw_posts = get_mock_posts(candidate_count) if use_mock_on_failure else []
        status["is_mock_data"] = bool(raw_posts)
    except Exception as exc:  # noqa: BLE001
        status["last_error"] = str(exc)
        raw_posts = get_mock_posts(candidate_count) if use_mock_on_failure else []
        status["is_mock_data"] = bool(raw_posts)

    raw_posts.sort(key=ranking_key)

    previous_posts = load_previous_posts()
    blocked_ids = recent_tweet_ids(previous_posts, days=3)

    filtered = [row for row in raw_posts if row["tweet_id"] not in blocked_ids]
    selected_raw = filtered[:target_posts]

    if len(selected_raw) < target_posts:
        if x_bearer_token:
            # X recent search already returns broad candidates; avoid duplicate fetch.
            pass
        elif api_key:
            try:
                extra_rows = fetch_posts_from_grok(
                    api_key=api_key,
                    model=model,
                    candidate_count=max(target_posts, 10),
                    range_label="rank 11-20",
                )
                extra_rows = [x for x in extra_rows if x["tweet_id"] not in blocked_ids and x not in selected_raw]
                raw_posts.extend(extra_rows)
            except Exception as exc:  # noqa: BLE001
                status["last_error"] = f"extra_fetch_error: {exc}"

        raw_posts.sort(key=ranking_key)
        needed = target_posts - len(selected_raw)
        fallback_pool = [row for row in raw_posts if row not in selected_raw and row["tweet_id"] not in blocked_ids]
        selected_raw.extend(fallback_pool[:needed])

    text_ko_map: dict[str, str] = {}
    if api_key and selected_raw and not status.get("is_mock_data") and enable_translation:
        try:
            text_ko_map = translate_to_korean(api_key=api_key, model=model, posts=selected_raw)
        except requests.HTTPError as exc:
            error_text = str(exc)
            if exc.response is not None:
                error_text = f"{error_text} | body: {exc.response.text[:300]}"
            status["last_error"] = f"translation_error: {error_text}"
        except Exception as exc:  # noqa: BLE001
            status["last_error"] = f"translation_error: {exc}"

    selected_items = []
    for row in selected_raw:
        item = build_tweet_item(row=row, text_ko_map=text_ko_map)
        if item:
            selected_items.append(item)

    if status.get("needs_credit_topup"):
        banner_message = "잔액 충전하세요"
    elif status.get("is_mock_data"):
        banner_message = "실데이터 수집 실패로 샘플 데이터가 표시 중입니다."

    index_path = PUBLIC_DIR / "index.html"
    wrote_new_page = False
    today_raw = datetime.now(KST).strftime("%Y-%m-%d")
    archive_data = load_archive()
    if selected_items:
        archive_data[today_raw] = [asdict(x) for x in selected_items]
        save_archive(archive_data)
        html = render_html(
            posts=selected_items,
            banner_message=banner_message,
            archive_data=archive_data,
            selected_date=today_raw,
        )
        index_path.write_text(html, encoding="utf-8")
        update_previous_posts(previous_posts, [x.tweet_id for x in selected_items], days=3)
        wrote_new_page = True
    else:
        status["last_error"] = (
            f"{status.get('last_error', '')} | no_posts_selected_keep_previous".strip(" |")
        )
        if not index_path.exists():
            html = render_html(
                posts=[],
                banner_message=banner_message,
                archive_data=archive_data,
                selected_date=today_raw,
            )
            index_path.write_text(html, encoding="utf-8")

    save_status(status)

    if wrote_new_page:
        print(f"Generated {PUBLIC_DIR / 'index.html'} with {len(selected_items)} posts.")
    else:
        print(f"Kept previous {PUBLIC_DIR / 'index.html'} (selected posts: {len(selected_items)}).")


if __name__ == "__main__":
    main()
