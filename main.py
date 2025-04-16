import json
import logging
import os

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.DEBUG)

load_dotenv()

mcp = FastMCP("mcp-server")

USER_AGENT = "docs-app/1.0"
SERPER_URL = "https://google.serper.dev/search"

docs_urls = {
    "langchain": "python.langchain.com/docs",
    "llama-index": "docs.llamaindex.ai/en/stable",
    "openai": "platform.openai.com/docs",
}


async def search_web(query: str) -> dict | None:
    logging.debug(f"Starting web search for query: {query}")
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ValueError("Error: SERPER_API_KEY is not set in the environment variables.")

    payload = json.dumps({"q": query, "num": 2})

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                SERPER_URL, headers=headers, data=payload, timeout=60.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            return {"organic": []}


async def fetch_url(url: str):
    logging.debug(f"Fetching URL: {url}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            logging.debug(f"Fetched URL successfully: {url}")
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text()
            return text
        except httpx.TimeoutException:
            logging.error(f"Timeout fetching URL: {url}")
            return "Timeout error"


@mcp.tool()
async def dummy_tool():
    return "MCP Server is ready!"


@mcp.tool()
async def get_docs(query: str, library: str):
    """
    Search the latest docs for a given query and library.
    Supports langchain, openai, and llama-index.

    Args:
      query: The query to search for (e.g. "Chroma DB")
      library: The library to search in (e.g. "langchain")

    Returns:
      Text from the docs
    """
    if library not in docs_urls:
        raise ValueError(f"Library {library} not supported by this tool")

    query = f"site:{docs_urls[library]} {query}"
    results = await search_web(query)
    if len(results["organic"]) == 0:
        return "No results found"

    text = ""
    for result in results["organic"]:
        text += await fetch_url(result["link"])
    return text


if __name__ == "__main__":
    mcp.run(transport="stdio")
