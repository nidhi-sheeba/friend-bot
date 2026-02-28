# tools.py
import sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from langchain.tools import tool
from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# ── THE @tool DECORATOR ────────────────────────────────────────────────
# @tool turns a regular Python function into a LangChain tool.
# The function's docstring becomes the tool's description —
# the LLM reads this to decide WHEN to use the tool.
# This is why the docstrings are written clearly — they're instructions for the AI.


@tool
def search_web(query: str) -> str:
    """
    Search the web for current information.
    Use this when the user asks about recent events, facts, news,
    or anything that requires up to date information.
    Input should be a clear search query.
    """
    try:
        results = tavily.search(query=query, max_results=3)
        # Format results into readable text for the LLM
        output = []
        for r in results["results"]:
            output.append(f"Title: {r['title']}\nURL: {r['url']}\nSummary: {r['content']}\n")
        return "\n---\n".join(output)
    except Exception as e:
        return f"Search failed: {str(e)}"


@tool
def save_note(note: str) -> str:
    """
    Save a note or reminder for the user to Apple Notes.
    Use this when the user asks to remember something, save something,
    or set a reminder. Input should be the note content to save.
    """
    import requests
    import os

    webhook_url = os.getenv("MAKE_WEBHOOK_URL")

    if not webhook_url:
        return "Note saving is not configured."

    try:
        response = requests.post(
            webhook_url,
            json={"note": note},
            timeout=10
        )
        if response.status_code == 200:
            return f"Got it — I've saved '{note}' to your Apple Notes 📝"
        else:
            return f"Failed to save note — webhook returned {response.status_code}"
    except Exception as e:
        return f"Failed to save note: {str(e)}"


@tool
def summarise_url(url: str) -> str:
    """
    Fetch and summarise the content of a webpage or article.
    Use this when the user shares a URL or link and wants to know
    what it's about or asks you to read something.
    Input should be a valid URL starting with http or https.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}  # pretend to be a browser
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # crash if status code is 4xx or 5xx

        # BeautifulSoup parses the raw HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style tags — we don't want code, just text
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()

        # Get all visible text and clean it up
        text = soup.get_text(separator=" ", strip=True)

        # Trim to first 3000 characters — enough for a good summary
        # without blowing up the context window
        trimmed = text[:3000]
        return f"Page content (first 3000 chars):\n{trimmed}"
    except Exception as e:
        return f"Could not fetch URL: {str(e)}"


# Export all tools as a list — agent.py will import this
TOOLS = [search_web, save_note, summarise_url]