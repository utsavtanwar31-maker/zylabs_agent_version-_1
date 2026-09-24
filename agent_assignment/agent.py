import os
import sys
import uuid
import json
import sqlite3
from typing import TypedDict, List, Dict, Any, Optional, Annotated

import requests
from bs4 import BeautifulSoup
import html2text

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from tavily import TavilyClient

DB_FILE = "agent_cache.db"

# Global context for evidence grouping
CURRENT_COMPANY = ""

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # page_cache persists across runs
    c.execute('''CREATE TABLE IF NOT EXISTS page_cache (url TEXT PRIMARY KEY, content TEXT)''')
    # evidence table
    c.execute('''CREATE TABLE IF NOT EXISTS evidence (id TEXT PRIMARY KEY, company TEXT, topic TEXT, claim TEXT, exact_quote TEXT, source_url TEXT, confidence REAL, confidence_reason TEXT)''')
    conn.commit()
    conn.close()

@tool
def search_web(query: str) -> str:
    """Search the web for information using Tavily."""
    print(f"\n🔍 [TOOL: search_web] Searching for: '{query}'")
    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    try:
        res = client.search(query=query, search_depth="basic", max_results=3)
        results = res.get('results', [])
        for i, r in enumerate(results):
            print(f"   Result {i+1}: {r.get('title', 'N/A')} — {r['url']}")
        return json.dumps(results)
    except Exception as e:
        print(f"   ❌ Search failed: {e}")
        return f"Search failed: {e}"

@tool
def fetch_page(url: str) -> str:
    """Fetch the text content of a webpage. The result is cached persistently to avoid re-visits."""
    print(f"\n🌐 [TOOL: fetch_page] Fetching: {url}")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT content FROM page_cache WHERE url=?", (url,))
    row = c.fetchone()
    if row:
        conn.close()
        print(f"   📦 Cache HIT — returning stored content ({len(row[0])} chars)")
        return row[0][:25000]
    
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style", "nav", "footer"]):
            script.extract()
        text_maker = html2text.HTML2Text()
        text_maker.ignore_images = True
        text_maker.ignore_links = False
        text = text_maker.handle(str(soup))
        
        c.execute("INSERT INTO page_cache VALUES (?, ?)", (url, text))
        conn.commit()
        conn.close()
        print(f"   ✅ Fetched & cached ({len(text)} chars)")
        return text[:25000]
    except Exception as e:
        conn.close()
        print(f"   ❌ Fetch FAILED: {e}")
        return f"Failed to fetch {url}: {e}"

@tool
def verify_and_save_evidence(topic: str, claim: str, exact_quote: str, source_url: str, confidence: float, confidence_reason: str) -> str:
    """
    Save evidence about the company (e.g. topic='offering', 'target_audience', 'case_study').
    CRITICAL: You MUST provide an EXACT QUOTE from the page to prove your claim.
    The system verifies the exact_quote exists in the fetched page text for source_url.
    If it doesn't match, it rejects the evidence (anti-hallucination).
    Provide a confidence score (0.0 to 1.0) and reasoning (e.g., 'Weak evidence - third party site', 'Strong - official case study').
    If contradictory info is found later, add new evidence with negative or low confidence.
    """
    print(f"\n📝 [TOOL: verify_and_save_evidence]")
    print(f"   Topic: {topic}")
    print(f"   Claim: {claim}")
    print(f"   Quote: '{exact_quote[:80]}...'" if len(exact_quote) > 80 else f"   Quote: '{exact_quote}'")
    print(f"   Source: {source_url}")
    print(f"   Confidence: {confidence} ({confidence_reason})")
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT content FROM page_cache WHERE url=?", (source_url,))
    row = c.fetchone()
    if not row:
        conn.close()
        print(f"   ❌ REJECTED — page not fetched yet!")
        return f"Error: {source_url} has not been fetched yet. Use fetch_page first."
    
    page_text = row[0]
    quote_clean = " ".join(exact_quote.split()).lower()
    page_clean = " ".join(page_text.split()).lower()
    
    if quote_clean not in page_clean:
        conn.close()
        print(f"   🚫 REJECTED — HALLUCINATION DETECTED! Quote not found in page.")
        return f"Error: exact_quote not found in the page text! Hallucination detected. Do not invent quotes. Copy exactly from the page."
    
    ev_id = str(uuid.uuid4())[:8]
    c.execute("INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (ev_id, CURRENT_COMPANY, topic, claim, exact_quote, source_url, confidence, confidence_reason))
    conn.commit()
    conn.close()
    print(f"   ✅ VERIFIED & SAVED (ID: {ev_id})")
    return f"Success! Evidence saved with ID {ev_id}"

@tool
def get_all_evidence() -> str:
    """Retrieve all saved evidence to review what has been found, detect contradictions, or increase confidence if multiple sources agree."""
    print(f"\n📋 [TOOL: get_all_evidence] Reviewing collected evidence...")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM evidence WHERE company=?", (CURRENT_COMPANY,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        print(f"   (empty — no evidence saved yet)")
        return "No evidence saved yet."
    
    print(f"   Found {len(rows)} evidence item(s)")
    out = []
    for r in rows:
        out.append(f"ID: {r[0]} | Topic: {r[2]} | Claim: {r[3]} | Quote: '{r[4]}' | URL: {r[5]} | Conf: {r[6]} ({r[7]})")
    return "\n".join(out)

@tool
def search_company_website_strict(company_name: str) -> str:
    """Finds the official website of the company. Verifies domain match to avoid partial matches."""
    print(f"\n🏢 [TOOL: search_company_website_strict] Looking for: '{company_name}'")
    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    try:
        res = client.search(query=f"{company_name} official website", search_depth="basic", max_results=5)
        results = res.get('results', [])
        
        clean_name = "".join(e for e in company_name.lower() if e.isalnum())
        for r in results:
            url = r['url']
            domain = url.split("//")[-1].split("/")[0].replace("www.", "")
            if clean_name in domain.replace(".", ""):
                print(f"   ✅ Domain MATCH: {url}")
                return f"Found matching domain: {url}"
        
        print(f"   ⚠️ No exact domain match. Top results: {[r['url'] for r in results]}")
        return f"Could not find a strictly matching domain for {company_name}. Top results: {[r['url'] for r in results]}. You may need to use search_web to investigate further or look for a parent company."
    except Exception as e:
        print(f"   ❌ Search failed: {e}")
        return f"Search failed: {e}"

def build_agent():
    # Note: Requires langchain-community or langgraph prebuilt depending on versions
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    tools = [search_company_website_strict, search_web, fetch_page, verify_and_save_evidence, get_all_evidence]
    
    system_prompt = f"""You are an autonomous company research agent. 
Your goal is to research a company and find:
1. What they sell (Products/Services)
2. Who they sell to (Industries, Company Size, Geography)
3. Customer case studies.

You are a TRUE tool-calling agent. You decide which tools to use and in what order.
Steps:
1. Find the official website using `search_company_website_strict` (or use a provided URL).
2. Fetch pages using `fetch_page`.
3. Read the content, and if you find evidence, save it using `verify_and_save_evidence`.
4. The verify tool REQUIRES an exact quote from the page. Do not hallucinate!
5. Assign a confidence score (0.0 to 1.0) based on source quality. If you find contradictory info later, save it with a low/negative confidence. 
6. If you need more info (like case studies not on the homepage), use `search_web` to Google for it.
7. Use `get_all_evidence` to see what you have. 
8. Stop when you have sufficient evidence for all 3 areas, or if you have searched exhaustively and cannot find more.

If you cannot find something, explicitly note that the information is missing or evidence is weak.
"""
    return create_react_agent(llm, tools), system_prompt

def generate_profile(company_name: str):
    print("--- GENERATING PROFILE ---")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM evidence WHERE company=?", (company_name,))
    rows = c.fetchall()
    conn.close()
    
    evidence_str = "\n".join([f"- [{r[2]}] {r[3]} (Confidence: {r[6]} - {r[7]})\n  Quote: '{r[4]}'\n  Source: {r[5]}" for r in rows])
    
    prompt = f"""You are an expert business analyst. Based on the gathered evidence below, write a comprehensive Company Profile in Markdown format.

Company: {company_name}

Evidence:
{evidence_str}

Please use the following structure:
# Company Profile: {company_name}

## Company Overview
...

## What They Sell
(List products/services with evidence and source URLs)

## Who They Sell To
(List Industries, Company Size, Geography with evidence and source URLs)

## Case Studies
(List discovered case studies with details and source URLs)

## Research Notes
- Pages investigated: ...
- Information that could not be verified: ...
- Conflicting or ambiguous evidence: ... (Highlight any low/negative confidence evidence)

## Sources
(Numbered list of source URLs referenced)

IMPORTANT: Every factual claim MUST include a source URL citation. If information is missing, state it explicitly.
"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    res = llm.invoke([SystemMessage(content=prompt)])
    
    filename = f"{company_name.lower().replace(' ', '_')}_profile.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(res.content)
        
    print(f"Profile saved to {filename}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("Usage: python agent.py 'Company Name' [website]")
        sys.exit(1)
        
    company = sys.argv[1]
    website = sys.argv[2] if len(sys.argv) > 2 else ""
    
    CURRENT_COMPANY = company
    
    init_db()
    
    print(f"Starting research on {company}...")
    agent, sys_prompt = build_agent()
    
    initial_message = f"Research {company}."
    if website:
        initial_message += f" Their official website is {website}."
        
    final_state = agent.invoke({"messages": [SystemMessage(content=sys_prompt), HumanMessage(content=initial_message)]})
    generate_profile(company)
    print("Done!")
