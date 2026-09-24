# context.md — Autonomous Company Research Agent

> Running log for the internship assignment. Updated after every work session.
> Last updated: 2026-09-24 (Session 5: V2 agent rewrite + Agilocrats test run)

---

## 1. Goal (one line)
Build an agent that takes a company name (+ optional website), decides for itself how to research it, and outputs a cited Markdown **Company Profile**: what they sell, who they sell to (industry / size / geography), and representative case studies.

## 2. What the evaluators actually grade (ranked by weight)
1. **Agent design.** It must be a real agent: plans, picks tools, reacts, changes strategy. A fixed scrape-then-summarize pipeline fails.
2. **Research quality.** Offerings and customers are correctly identified.
3. **Case study discovery.** It finds them even under "Resources", "Stories", "Customers", and similar.
4. **Evidence.** Every claim is traceable (URL + title + snippet). It says "unclear" instead of guessing.
5. **Robustness.** Handles JS sites, redirects, 404s, missing pages, tool failures.
6. **Efficiency.** No full crawl, no duplicate visits, controlled context.
7. **Code quality.** Clean, production-ish.

## 3. Required deliverables (checklist)
- [x] Source code (`agent.py` — V2 ReAct agent)
- [x] README (setup + run) — needs update for V2
- [x] Tool descriptions (5 tools: `search_web`, `fetch_page`, `verify_and_save_evidence`, `get_all_evidence`, `search_company_website_strict`)
- [x] Explanation of how autonomy is implemented (ReAct agent, LLM picks tools freely)
- [ ] ≥3 example runs on differently structured sites (1/3 done: Agilocrats)
- [ ] Generated Markdown profiles for those runs (1/3 done: `agilocrats_profile.md`)
- [x] Logs/traces of agent decisions + tool calls (verbose emoji-tagged print tracing in each tool)
- [ ] Known limitations + improvements (in `evaluation_findings.txt`, needs expansion)

**Bonus targets** (pick the cheap, high-signal ones): checkpoint/resume, ~~page cache~~ ✅, subagents in parallel, Pydantic-validated output, ~~confidence levels~~ ✅, ~~conflict detection~~ ✅ (via negative confidence), stopping criteria, token/cost tracking, retry/fallback between fetchers.

## 4. Platform decision
**Recommended: local Python repo built with Claude Code. Add an optional Colab notebook only as a "try it" demo.**

Reasons:
- The deliverable is a repo (code, README, logs, outputs), not a notebook.
- Playwright (needed for JS-heavy sites) is awkward in Colab because of browser installs and async event-loop clashes.
- Checkpointing, SQLite cache, and trace files persist locally; Colab wipes them when the session ends.
- Claude Code can run the agent against real websites and iterate. The chat sandbox has restricted internet, so real test runs must happen on your machine.

Status: ✅ **Confirmed.** Built with Claude Code. Utsav pastes prompts from `claude_code_prompts.md`; `CLAUDE.md` holds the spec.

## 5. Proposed architecture (draft)
- **Framework:** LangChain **Deep Agents** on LangGraph. It is named in the brief and provides planning (todo list), subagents, and a virtual file system for notes out of the box.
- **Orchestrator agent:** reads the goal, writes a research plan, dispatches subagents, checks coverage gaps, and decides when to stop.
- **Subagents** (isolated context, can run in parallel):
  - `offerings_researcher`: products, services, platforms, product families
  - `customer_researcher`: industries, company size, geography
  - `case_study_hunter`: finds and extracts customer stories
- **Tools:**
  - `web_search(query)`: Tavily / DuckDuckGo. Used for website discovery and `site:` searches.
  - `fetch_page(url)`: httpx + trafilatura first, Playwright fallback for JS pages. Returns a clean summary plus a list of links.
  - `get_sitemap(domain)`: robots.txt → sitemap.xml → filtered URL list.
  - `find_links(url, keywords)`: ranks the links on a page by relevance.
  - `save_evidence(claim, url, title, quote)`: writes to the evidence store and returns an evidence ID.
  - `research_status()`: shows visited URLs, filled vs. missing fields, and budget used.
- **State/infra:** SQLite page cache (dedup), LangGraph SqliteSaver (checkpoint/resume), JSONL trace log, token/cost counter.
- **Output:** Pydantic `CompanyProfile` in which every field references evidence IDs, rendered to Markdown. A validator rejects any claim without evidence.
- **Stopping rule:** stop when all required fields have evidence or are explicitly marked unverifiable, or when the page/token budget is exhausted.

## 6. Build sequence
Deadline: **2026-09-24 EOD IST**. Total estimate is about 9 h of Claude Code time.

| # | Phase (prompt) | Output | Est. | Status |
|---|-------|--------|------|--------|
| 0 | Setup + Deep Agents API check | skeleton repo, API cheat sheet | 20m | ✅ |
| 1 | Tool layer: fetch, search, cache, budgets | all in `agent.py` (consolidated) | 1.5h | ✅ (V2: SQLite cache, strict domain search, fetch_page) |
| 2 | Evidence store (quote verification) + confidence | `verify_and_save_evidence` tool in `agent.py` | 45m | ✅ (programmatic anti-hallucination + confidence scores) |
| 3 | Agent: ReAct tool-calling agent, tracing | `agent.py` (create_react_agent + verbose prints) | 2h | ✅ (single ReAct agent; subagents deferred) |
| 4 | Finalize (evidence-only) + Markdown | `generate_profile()` in `agent.py` | 1.5h | ✅ (builds profile from evidence DB only) |
| 5 | Runs: ≥3 companies | `agilocrats_profile.md` + 2 more needed | 2h | 🔶 (1/3 done) |
| 6 | README, autonomy explanation, limitations, final commit | submission | 1h | ⏳ |

## 6a. Deep Agents API cheat sheet (verified against installed deepagents 0.7.18, langgraph 1.2.12, langchain 1.4.2)
1. `from deepagents import create_deep_agent` → `create_deep_agent(model=None, tools=None, *, system_prompt, middleware=(), subagents=None, skills, memory, permissions, backend, interrupt_on, response_format, state_schema, context_schema, checkpointer, store, debug, name, cache)` → `CompiledStateGraph`.
2. `model` must be a `str` ("provider:model") or a `BaseChatModel`. **A `.with_fallbacks()` Runnable crashes it** (`resolve_model` calls `.partition` on it).
3. Fallback for agents = `langchain.agents.middleware.ModelFallbackMiddleware(fallback_model)` in `middleware=[...]`. Also available: `ModelRetryMiddleware`, `ModelCallLimitMiddleware`, `ToolCallLimitMiddleware`.
4. Custom tools: `tools=[...]` accepts `BaseTool`, plain typed functions with docstrings, or dicts.
5. Subagents: `subagents=[SubAgent]`, a TypedDict: `name`, `description` (required); `system_prompt`, `tools`, `model`, `middleware`, `response_format`, `mode` ("isolated" default | "fork"), `interrupt_on`, `skills`, `permissions` (optional).
6. Subagent `tools` omitted → inherits main tools. `model` omitted → inherits main model. **`middleware` is NOT inherited**, so add `ModelFallbackMiddleware` to each subagent spec.
7. The orchestrator calls subagents via the built-in `task(description, subagent_type=name)` tool; the subagent's last AIMessage (or `structured_response`) comes back as the ToolMessage.
8. A `general-purpose` subagent is auto-added unless you define one with that name or disable it via a `HarnessProfile(general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False))`.
9. Built-ins: `write_todos`, virtual FS (`ls`, `read_file`, `write_file`, `edit_file`, …) backed by state by default (`backend=`).
10. Checkpointer: `from langgraph.checkpoint.sqlite import SqliteSaver` (pkg `langgraph-checkpoint-sqlite`); `with SqliteSaver.from_conn_string("x.sqlite") as cp: create_deep_agent(..., checkpointer=cp)`; invoke with `config={"configurable": {"thread_id": run_id}}`.

## 7. Open questions
- Confirm the Gemini free-tier requests-per-minute limit on Utsav's key. It sets how long each run takes. `LLM_RPM=8` is the default for now.

## 7a. Issues / problems
- `docs/assignment.md` is missing from the repo folder. Needs to be added.
- Phase 0 ran in Claude's cloud workspace, which is **blocked from Gemini/Groq/Cerebras/Tavily** and has no shell on Utsav's PC. So the live tool-call check and `playwright install chromium` haven't run yet. They run via `setup.ps1` on Utsav's machine.
- `init_chat_model` has no `cerebras` provider in langchain 1.4. `llm.build_model` constructs `ChatCerebras` directly for `cerebras:` specs.
- `.with_fallbacks()` is incompatible with `create_deep_agent` (see cheat sheet #2). So `llm.py` exposes both `get_llm()` (a fallback chain for direct calls such as finalize) and `get_models()` + `get_fallback_middleware()` for agents.

## 7b. agent_assignment/ Implementation Status (V2 — current)
The `agent_assignment/` directory has been **completely rewritten** from a fixed-loop scraper to a true **ReAct tool-calling agent** using `langgraph.prebuilt.create_react_agent` with OpenAI `gpt-4o`.

**Architecture (V2):**
- **Agent type:** ReAct (Reasoning + Acting). The LLM autonomously decides which tools to call, in what order, and when to stop.
- **Tools exposed to the agent (5):**
  1. `search_company_website_strict(name)` — Tavily search + domain-match verification to avoid partial matches.
  2. `search_web(query)` — General web search via Tavily. Agent can use this mid-research (e.g., to find case studies).
  3. `fetch_page(url)` — HTTP fetch → BeautifulSoup → Markdown. Results cached in SQLite (`agent_cache.db`).
  4. `verify_and_save_evidence(topic, claim, exact_quote, source_url, confidence, confidence_reason)` — Anti-hallucination gate: verifies that `exact_quote` exists in the cached page text. Rejects if not found. Saves with confidence score.
  5. `get_all_evidence()` — Returns all saved evidence for the company. Agent uses this to check coverage, detect contradictions, and decide when to stop.
- **Anti-hallucination:** Programmatic. The `verify_and_save_evidence` tool cross-checks the exact_quote against the SQLite-cached page content. If the quote is not found, the evidence is rejected.
- **Confidence tracking:** Each evidence item has a `confidence` (0.0–1.0) and `confidence_reason`. Agent is prompted to increase confidence on corroboration and use low/negative confidence for contradictions.
- **Caching:** SQLite `page_cache` table. Duplicate fetches across runs return instantly from DB.
- **Tracing:** Verbose emoji-tagged `print()` statements inside every tool (🔍 search, 🌐 fetch, 📝 evidence, 🚫 hallucination rejection, 📦 cache hit, 🏢 domain match).
- **Profile generation:** `generate_profile()` reads only from the evidence DB and uses GPT-4o to render the final Markdown.

**What is still missing:**
- JS rendering (Playwright/Firecrawl) — still uses `requests` only.
- Parallel subagents — agent is sequential.
- 2 more example company runs needed (have 1: Agilocrats).
- README needs update for V2 architecture.

## 8. Decisions log
- 2026-09-24: Project started. Plan drafted.
- 2026-09-24: Switched to FREE models only. Primary: Gemini 2.5 Flash (Google AI Studio). Fallback: Groq or Cerebras `gpt-oss-120b`. Calls are rate-limited and fall back automatically on 429 errors.
- 2026-09-24: Stack locked: Claude Code; Tavily search; Deep Agents on LangGraph; SQLite for cache, evidence and checkpoints.
- 2026-09-24: Anti-hallucination approach: `save_evidence` only accepts quotes that match cached page text, and the final profile is built from the evidence store only.
- 2026-09-24: Fallback plan: if the Deep Agents API blocks progress, switch to the LangGraph ReAct agent with subagents exposed as tools (rescue prompt).
- 2026-09-24: Agent-level fallback uses `ModelFallbackMiddleware` (on the main agent and each subagent). `.with_fallbacks()` is only used for direct calls. SDK `max_retries=1` so a 429 hands over to the fallback fast. Rate limits are env-configurable (`LLM_RPM`, `LLM_FALLBACK_RPM`).
- 2026-09-24: Packaging: `pyproject.toml` (src layout, `pip install -e .[dev]`); added `rank-bm25` for `read_page_section`; `setup.ps1` for Windows setup and verification.
- 2026-09-24: **V2 rewrite.** Abandoned the fixed-loop StateGraph scraper. Replaced with `create_react_agent` (true tool-calling agent). Consolidated all logic into a single `agent.py` file for simplicity.
- 2026-09-24: **Anti-hallucination implemented.** `verify_and_save_evidence` programmatically checks exact_quote against the SQLite-cached page content. Rejects if not found.
- 2026-09-24: **Confidence tracking implemented.** Each evidence item stores a float confidence + reasoning. Agent prompted to use negative confidence for contradictions.
- 2026-09-24: **Domain verification implemented.** `search_company_website_strict` parses domains and enforces heuristic name-match to prevent partial matches (e.g. Zylabs vs Zycus). Tested on Tavily for "AGILOCRATS" — returned correct domain.
- 2026-09-24: **SQLite page caching implemented.** `agent_cache.db` persists fetched pages across runs. Cache hits return instantly.
- 2026-09-24: **Verbose tool tracing implemented.** Emoji-tagged print statements inside every tool for real-time observability in the terminal.
- 2026-09-24: **Model switched to OpenAI `gpt-4o`** for the agent (extraction + reasoning) and profile generation. `gpt-4o-mini` was insufficient for structured tool calling.

## 9. Session log
- **S1 (2026-09-24):** Read the brief, drafted the plan and architecture, created context.md.
- **S2 (2026-09-24):** Confirmed the stack and deadline. Wrote CLAUDE.md (spec) and claude_code_prompts.md (7 phase prompts + rescue prompts). Next: Utsav runs Prompt 0.
- **S3 (2026-09-24): Phase 0.** Scaffolded the repo (14 stub modules plus real `config.py` and `llm.py`), `pyproject.toml`, `.env.example`, `.gitignore`, git init. Installed the stack in a venv. Read the installed deepagents source and wrote the cheat sheet (§6a). Built `llm.py`. Offline checks: `pytest` shows **3 passed**. A deep agent built with `ModelFallbackMiddleware`, a subagent and a checkpointer compiled OK. `scripts/verify_phase0.py` runs end to end, but all live calls fail with `403 proxy` (sandbox network block, not a code error).
- **S4 (2026-09-24):** Reviewed the `agent_assignment/` folder against the full assignment spec. Created `evaluation_findings.txt` with a detailed gap analysis. Identified 12 critical issues: no true tool calling, no anti-hallucination, no confidence tracking, no domain verification, no caching, no tracing, etc.
- **S5 (2026-09-24): V2 Rewrite.** Completely rewrote `agent.py`. Replaced the fixed-loop StateGraph scraper with a `create_react_agent` (true ReAct tool-calling agent). Implemented 5 tools: `search_company_website_strict`, `search_web`, `fetch_page`, `verify_and_save_evidence`, `get_all_evidence`. Added programmatic anti-hallucination (exact_quote verification against cached page text), confidence tracking (0.0–1.0 + reasoning), SQLite persistent caching (`agent_cache.db`), strict domain verification, and verbose emoji-tagged print tracing. Tested Tavily domain search for "AGILOCRATS" — returned correct URL. Ran the agent on Agilocrats — completed successfully, generated `agilocrats_profile.md`. Updated `evaluation_findings.txt` and this context document. **Next:** Run 2 more company profiles, update README for V2, consider Playwright integration.
