# AI Assignment: Autonomous Company Research Agent

## Objective

Build an **agentic company research system** that accepts a company name
and/or company website and autonomously researches the company to
produce a structured **Company Profile**.

The system must behave as an **agent**, not as a fixed scraping
pipeline.

The agent should decide:

-   which pages to visit,
-   what information is still missing,
-   whether it needs to search for additional pages,
-   which tools to use,
-   when to revisit or follow links,
-   how to verify findings,
-   and when it has enough evidence to produce the final profile.

You may use **LangChain Deep Agents, LangGraph, or another agent
framework**.

------------------------------------------------------------------------

## Input

The agent should accept at minimum:

``` text
Company Name: <company name>
Website: <company website, optional if the agent can discover it>
```

Example:

``` text
Company Name: ExampleCorp
Website: https://www.example.com
```

If only the company name is provided, the agent should be capable of
finding and validating the appropriate company website.

------------------------------------------------------------------------

## Core Research Task

The agent must investigate the company's public web presence and answer
the following questions.

### 1. What Does the Company Sell?

Identify the company's products, services, solutions, or major
offerings.

Do not simply copy navigation labels.

The agent should understand and summarize the actual commercial
offerings.

Example output:

``` text
Offering: Digital Banking Platform

Description:
Provides software for retail and commercial banks covering account
management, payments, lending, and digital customer experiences.

Category:
Banking Software
```

Where possible, distinguish between:

-   Products
-   Services
-   Platforms
-   Solutions
-   Major product families

------------------------------------------------------------------------

### 2. Who Does the Company Sell To?

Determine the company's target customers.

The agent should infer this from evidence such as product pages,
solution pages, customer stories, case studies, industries pages, and
other relevant sources.

Research the following dimensions.

#### Industry / Vertical

Examples:

-   Banking
-   Insurance
-   Retail
-   Manufacturing
-   Healthcare
-   Telecommunications

#### Company Size

Where evidence exists, identify whether the company primarily targets:

-   SMB
-   Mid-market
-   Enterprise
-   Large enterprise
-   Public sector

Avoid guessing when there is insufficient evidence.

#### Geography

Identify important markets or customer geographies where possible.

Examples:

-   North America
-   Europe
-   India
-   APAC
-   Global

The agent should distinguish between **where the company operates** and
**where its customers are located** whenever possible.

------------------------------------------------------------------------

### 3. Discover Case Studies / Customer Stories

Find publicly available case studies, customer stories, success stories,
or equivalent evidence of customer relationships.

For each case study, extract where available:

``` text
Customer
Industry
Geography
Products / Services Used
Problem / Use Case
Outcome
Source URL
```

The agent should follow relevant links rather than relying only on a
site's top-level navigation.

If a company has many case studies, the agent does not necessarily need
to extract every one. It should discover enough representative evidence
to understand the company's customer base and offerings, while
explaining its coverage.

------------------------------------------------------------------------

## Agentic Requirement

This is the most important part of the assignment.

**Do not implement the task as a predetermined sequence of scraping
steps.**

A solution such as:

``` text
1. Scrape homepage
2. Scrape /products
3. Scrape /customers
4. Send everything to an LLM
5. Generate profile
```

is **not sufficient**.

The system should instead expose useful tools to an agent and allow the
agent to decide how to accomplish the research objective.

For example, depending on the website, the agent may decide to:

-   inspect the homepage,
-   discover relevant navigation,
-   search the site,
-   follow a Products link,
-   inspect an Industries page,
-   search specifically for case studies,
-   follow several customer-story links,
-   notice missing geographic information,
-   search for additional evidence,
-   compare information from multiple pages,
-   and stop once the requested profile is sufficiently supported.

Different websites should naturally result in different research paths.

The quality of the **agent's decision-making** is part of the
evaluation.

------------------------------------------------------------------------

## Browsing / Research Tools

You may use any tools you consider appropriate.

Examples include:

-   Playwright / Playwright MCP
-   Firecrawl
-   HTTP requests
-   Search APIs
-   Sitemap discovery
-   Browser automation
-   Custom scraping tools
-   Other open-source or commercial research tools

The choice of tools is intentionally left open.

Your agent should decide **when and why to use each available tool**.

JavaScript-heavy websites, pagination, dynamically loaded content,
redirects, missing pages, and different site structures should be
handled reasonably.

------------------------------------------------------------------------

## Evidence and Citations

Every important factual claim in the final Company Profile must be
traceable to evidence.

At minimum, preserve:

``` text
Source URL
Page title
Relevant evidence / extracted text
```

The final output should contain citations or source references
supporting conclusions about:

-   offerings,
-   target industries,
-   customer size,
-   customer geography,
-   and case studies.

Do not allow the model to invent unsupported company information.

If evidence is weak or ambiguous, say so.

------------------------------------------------------------------------

## Expected Output

The agent should generate a Markdown file similar to:

``` markdown
# Company Profile: ExampleCorp

## Company Overview
Short description of the company.

## What They Sell

### Offering 1
- Name:
- Category:
- Description:
- Evidence:
- Source:

### Offering 2
...

## Who They Sell To

### Industries
- Banking
- Insurance
- Retail

### Company Size
- Enterprise
- Large Enterprise

Evidence:
...

### Geography
- North America
- Europe
- APAC

Evidence:
...

## Case Studies

### Customer: Example Bank
- Industry:
- Geography:
- Products / Services Used:
- Use Case:
- Outcome:
- Source:

### Customer: Example Retailer
...

## Research Notes

- Pages investigated:
- Important paths discovered:
- Information that could not be verified:
- Conflicting or ambiguous evidence:

## Sources

1. ...
2. ...
3. ...
```

You may improve this structure if you believe another representation
communicates the research more effectively.

------------------------------------------------------------------------

## Robustness Expectations

Your agent should work across websites with substantially different
structures.

Test against multiple real companies rather than optimizing for one
website.

Your implementation should reasonably handle situations such as:

-   no obvious `/products` page,
-   products spread across multiple sections,
-   case studies under names such as "Customers", "Success Stories",
    "Resources", or "Stories",
-   dynamically rendered websites,
-   broken links,
-   duplicate pages,
-   redirects,
-   large numbers of links,
-   missing information,
-   contradictory information,
-   tool failures,
-   and pages irrelevant to the research objective.

The agent should recover from failures where practical rather than
immediately terminating.

------------------------------------------------------------------------

## Efficiency

The goal is not to crawl the entire website.

A strong agent should identify the pages most likely to contain useful
evidence and adapt its research strategy as it learns.

Consider:

-   avoiding duplicate page visits,
-   limiting irrelevant exploration,
-   keeping large page contents out of the main context where possible,
-   summarizing intermediate research,
-   parallelizing independent research when appropriate,
-   and maintaining a record of what has already been investigated.

------------------------------------------------------------------------

## Deliverables

Submit:

1.  Source code.
2.  README with setup and execution instructions.
3.  Description of the tools available to the agent.
4.  Explanation of how agent autonomy is implemented.
5.  At least **3 example company runs** using companies with different
    website structures.
6.  Generated Markdown Company Profiles for those runs.
7.  Logs or traces showing the agent's decisions and tool calls.
8.  Known limitations and possible improvements.

------------------------------------------------------------------------

## Evaluation Criteria

### Agent Design

Does the system genuinely allow the agent to plan, explore, choose
tools, react to observations, and change its research strategy?

### Research Quality

Does it correctly identify what the company sells and who it sells to?

### Case Study Discovery

Can it discover customer stories even when they are not located at an
obvious URL?

### Evidence Quality

Are conclusions supported by appropriate sources?

### Robustness

Does the system work across different website structures and recover
reasonably from failures?

### Efficiency

Does the agent gather enough evidence without blindly crawling the
entire site?

### Code Quality

Is the implementation understandable, maintainable, and reasonably
production-oriented?

------------------------------------------------------------------------

## Bonus

Additional credit may be given for useful capabilities such as:

-   checkpointing and resume,
-   persistent research state,
-   parallel research or subagents,
-   structured extraction with validation,
-   confidence levels for inferred information,
-   detecting conflicting evidence,
-   intelligent stopping criteria,
-   token/context management,
-   caching previously visited pages,
-   retry and fallback strategies between browsing tools,
-   observability of LLM and tool calls,
-   cost/token tracking,
-   and reusable tools that work across research tasks.

------------------------------------------------------------------------

## Important Constraint

The assignment is intentionally **not** asking for a fixed reference
architecture.

Choose your own architecture, tools, prompts, models, and storage
approach.

The central requirement is:

> **Build an autonomous research agent that can investigate an
> unfamiliar company website, decide how to navigate and research it,
> gather evidence, and produce a cited company profile covering what the
> company sells, who it sells to, and representative customer case
> studies.**
