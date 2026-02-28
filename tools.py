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
    Save a note or reminder for the user to Notion.
    Use this when the user asks to remember something, save something,
    or set a reminder. Input should be the note content to save.
    """
    import os
    from notion_client import Client
    from datetime import datetime

    notion_key = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_DATABASE_ID")

    if not notion_key or not database_id:
        return "Notion is not configured. Please add NOTION_API_KEY and NOTION_DATABASE_ID."

    try:
        notion = Client(auth=notion_key)

        # Create a title from the first line of the note
        title = note.split("\n")[0][:100]  # first line, max 100 chars
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        notion.pages.create(
            parent={"database_id": database_id},
            properties={
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": f"[{timestamp}] {title}"
                            }
                        }
                    ]
                }
            },
            # The full note goes in the page body
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": note
                                }
                            }
                        ]
                    }
                }
            ]
        )

        return f"Got it — I've saved your note to Notion 📝"

    except Exception as e:
        return f"Failed to save to Notion: {str(e)}"


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