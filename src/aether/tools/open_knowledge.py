"""
Global Open Knowledge Hub
Direct connectors to open databases and public research archives worldwide.
Features live DuckDuckGo web search, deep multi-page article scraping, Wikipedia, and arXiv.
Zero paid API keys; 100% open access.
"""

from typing import Any, Dict, List

import httpx
from bs4 import BeautifulSoup

DEFAULT_TIMEOUT = 12.0
HEADERS = {
    "User-Agent": "AetherPersonalAssistant/1.0 (https://github.com/aether-assistant; user@example.com)"
}


def search_wikipedia(query: str, max_chars: int = 6000) -> str:
    """
    Query the Wikipedia Open Encyclopedia for definitions, historical context, science, and bios.
    """
    try:
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            "action": "opensearch",
            "search": query,
            "limit": "1",
            "namespace": "0",
            "format": "json",
        }
        with httpx.Client(timeout=DEFAULT_TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
            resp = client.get(search_url, params=search_params)
            data = resp.json()
            if not data or len(data) < 2 or not data[1]:
                return f"No Wikipedia article found for '{query}'."

            title = data[1][0]
            extract_params = {
                "action": "query",
                "format": "json",
                "prop": "extracts",
                "exintro": "true",
                "explaintext": "true",
                "titles": title,
            }
            extract_resp = client.get(search_url, params=extract_params)
            pages = extract_resp.json().get("query", {}).get("pages", {})
            for _, page_info in pages.items():
                extract = page_info.get("extract", "")
                if extract:
                    truncated = extract[:max_chars]
                    if len(extract) > max_chars:
                        truncated += "...\n[Content truncated for memory conservation]"
                    return f"### Wikipedia: {title}\n{truncated}"
            return f"Wikipedia article '{title}' had no summary."
    except Exception as e:
        return f"Wikipedia lookup error: {str(e)}"


def search_arxiv(query: str, max_results: int = 6) -> str:
    """
    Query arXiv for cutting-edge open-access research papers, preprints, and academic breakthroughs.
    """
    try:
        import xml.etree.ElementTree as ET

        url = "https://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": "0",
            "max_results": str(max_results),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        with httpx.Client(timeout=DEFAULT_TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
            resp = client.get(url, params=params)
            root = ET.fromstring(resp.text)
            
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns)
            if not entries:
                return f"No arXiv scientific papers found matching '{query}'."

            results = [f"### arXiv Research Papers on '{query}':"]
            for idx, entry in enumerate(entries, 1):
                title_elem = entry.find("atom:title", ns)
                summary_elem = entry.find("atom:summary", ns)
                published_elem = entry.find("atom:published", ns)
                id_elem = entry.find("atom:id", ns)

                title = title_elem.text.strip().replace("\n", " ") if title_elem is not None and title_elem.text else "Untitled"
                summary = summary_elem.text.strip().replace("\n", " ")[:1200] if summary_elem is not None and summary_elem.text else ""
                published = published_elem.text[:10] if published_elem is not None and published_elem.text else "N/A"
                link = id_elem.text.strip() if id_elem is not None and id_elem.text else ""

                results.append(
                    f"{idx}. **{title}** ({published})\n   *Abstract*: {summary}\n   *URL*: {link}"
                )
            return "\n\n".join(results)
    except Exception as e:
        return f"arXiv query error: {str(e)}"


def search_web(query: str, max_results: int = 8) -> str:
    """
    Execute a live web search via DuckDuckGo to obtain fresh facts, news, and current data.
    """
    try:
        url = "https://html.duckduckgo.com/html/"
        data = {"q": query}
        with httpx.Client(timeout=DEFAULT_TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
            resp = client.post(url, data=data)
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for item in soup.select(".result"):
                title_elem = item.select_one(".result__title a")
                snippet_elem = item.select_one(".result__snippet")
                if title_elem and snippet_elem:
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get("href", "")
                    if "uddg=" in link:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                        link = parsed.get("uddg", [link])[0]
                    snippet = snippet_elem.get_text(strip=True)
                    results.append(f"- **{title}**\n  {snippet}\n  *Source*: {link}")
                    if len(results) >= max_results:
                        break

            if not results:
                return f"No direct web results found for '{query}'."
            return f"### Live Web Search Results for '{query}':\n" + "\n\n".join(results)
    except Exception as e:
        return f"Web search error: {str(e)}"


def browse_web_page(url: str, max_chars: int = 10000) -> str:
    """
    Visit and extract the main readable article/text from any public website URL.
    Strips away scripts, ads, and navigation to present clean, readable text.
    """
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return f"Failed to retrieve page (HTTP {resp.status_code}): {url}"

            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "header", "footer", "aside", "svg", "form", "noscript"]):
                tag.decompose()

            # Strategy A: paragraphs, headings, lists
            paragraphs = [p.get_text(strip=True) for p in soup.find_all(["p", "h1", "h2", "h3", "li"])]
            text = "\n".join(p for p in paragraphs if len(p) > 20)

            # Strategy B fallback: general text blocks
            if not text or len(text) < 100:
                raw_lines = [line.strip() for line in soup.get_text(separator="\n").splitlines() if len(line.strip()) > 25]
                text = "\n".join(raw_lines[:80])

            if not text:
                return f"No readable text extracted from {url}."

            snippet = text[:max_chars]
            if len(text) > max_chars:
                snippet += f"\n\n... [Showing first {max_chars} characters]"
            return f"### Content from: {url}\n\n{snippet}"
    except Exception as e:
        return f"Error browsing webpage {url}: {str(e)}"


def deep_web_research(query: str, max_pages: int = 4) -> str:
    """
    Perform deep multi-source research: searches the web and automatically visits and reads
    the top source pages to provide rich, comprehensive facts and verified information.
    """
    try:
        # Step 1: Search DuckDuckGo and capture snippets
        url = "https://html.duckduckgo.com/html/"
        data = {"q": query}
        target_links: List[str] = []
        snippets_list: List[str] = []

        with httpx.Client(timeout=DEFAULT_TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
            resp = client.post(url, data=data)
            soup = BeautifulSoup(resp.text, "html.parser")
            for item in soup.select(".result"):
                title_elem = item.select_one(".result__title a")
                snippet_elem = item.select_one(".result__snippet")
                if title_elem and snippet_elem:
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get("href", "")
                    if "uddg=" in link:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                        link = parsed.get("uddg", [link])[0]
                    snip = snippet_elem.get_text(strip=True)
                    snippets_list.append(f"- **{title}**: {snip}\n  Source: {link}")
                    if link.startswith("http") and not any(bad in link for bad in ["duckduckgo.com", "yandex", "bing"]):
                        if len(target_links) < max_pages:
                            target_links.append(link)

        if not snippets_list:
            return f"No web intelligence found for query: '{query}'."

        results = [f"### Live Web Intelligence on '{query}':"]
        results.append("#### Verified Search Summaries:\n" + "\n\n".join(snippets_list[:6]))

        # Step 2: Browse top pages for deeper context
        if target_links:
            results.append("#### Deep Article Extracts:")
            for link in target_links:
                page_content = browse_web_page(link, max_chars=4000)
                results.append(page_content)

        return "\n\n---\n\n".join(results)
    except Exception as e:
        return f"Deep web research error: {str(e)}"
