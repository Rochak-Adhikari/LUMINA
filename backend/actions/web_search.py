
import re
import time
import webbrowser
from datetime import datetime

try:
    import requests
    _REQUESTS = True
except ImportError:
    _REQUESTS = False


def _clean_response(text: str) -> str:
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'#{1,6}\s(.+)', r'\1', text)
    text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def _search_with_gemini(query: str) -> str:
    try:
        from actions._gemini_helper import get_genai_model
        model  = get_genai_model("gemini-2.5-flash")
        now    = datetime.now().strftime("%Y-%m-%d %H:%M")
        prompt = (
            f"Current date/time: {now}\n\n"
            f"Search query: {query}\n\n"
            f"Provide a comprehensive, accurate, and up-to-date response. "
            f"Include key facts, numbers, and specific details. "
            f"Format for voice output — no markdown, no bullet points, write in flowing prose."
        )
        response = model.generate_content(prompt)
        return _clean_response(response.text)
    except Exception as e:
        return f"Gemini search failed: {e}"


def _search_ddg(query: str) -> str | None:
    if not _REQUESTS:
        return None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        url      = "https://api.duckduckgo.com/"
        params   = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
        response = requests.get(url, headers=headers, params=params, timeout=8)
        data     = response.json()

        # Try instant answer first
        abstract = data.get("AbstractText", "").strip()
        if abstract:
            source = data.get("AbstractSource", "DDG")
            return f"{abstract}\n\nSource: {source}"

        # Try related topics
        topics = data.get("RelatedTopics", [])
        results = []
        for t in topics[:3]:
            if isinstance(t, dict) and t.get("Text"):
                results.append(t["Text"])
        if results:
            return "Results:\n" + "\n\n".join(results)

        return None
    except Exception:
        return None


def _open_in_browser(query: str) -> str:
    url = f"https://www.google.com/search?q={requests.utils.quote(query)}" if _REQUESTS else \
          f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(url)
    return f"Opened search results for: {query}"


def web_search(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Lumina web search action.

    parameters:
        query       : Search query text (required)
        mode        : 'gemini' (default) | 'ddg' | 'browser'
        open_browser: bool — also open in browser (default False)
    """
    params  = parameters or {}
    query   = params.get("query", "").strip()
    mode    = params.get("mode", "gemini").lower()
    also_open_browser = params.get("open_browser", False)

    if not query:
        return "Please provide a search query."

    if player:
        player.write_log(f"[search] {query[:60]}")

    print(f"[WebSearch] 🔍 Query: {query!r} Mode: {mode}")

    result = None

    if mode == "browser":
        return _open_in_browser(query)

    if mode == "ddg":
        result = _search_ddg(query)
        if not result:
            result = _search_with_gemini(query)
    else:
        # Default Gemini-first
        result = _search_with_gemini(query)
        if not result or "failed" in result.lower():
            ddg = _search_ddg(query)
            if ddg:
                result = ddg

    if also_open_browser:
        _open_in_browser(query)

    if not result:
        return f"No results found for: {query}"

    print(f"[WebSearch] ✅ Result length: {len(result)} chars")
    return result
