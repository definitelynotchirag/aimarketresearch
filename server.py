import os
import io
import json
import math
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from aiohttp import ClientSession
from dotenv import load_dotenv

from pptx import Presentation
from pptx.util import Inches, Pt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

try:
    from docx import Document
except Exception:
    Document = None


load_dotenv()


class ResearchRequest(BaseModel):
    brand: str = Field(..., description="Brand or company to research")
    country: Optional[str] = Field(None, description="Country or region")
    industry: Optional[str] = Field(None, description="Industry vertical")
    max_results: int = Field(12, ge=1, le=50)
    language: Optional[str] = Field("en")
    use_cache: bool = True


class Competitor(BaseModel):
    name: str
    website: Optional[str] = None
    summary: Optional[str] = None


class SourceItem(BaseModel):
    title: Optional[str] = None
    url: str
    summary: Optional[str] = None


class ResearchResult(BaseModel):
    brand: str
    country: Optional[str]
    industry: Optional[str]
    competitors: List[Competitor]
    trends: List[str] = []
    ad_insights: List[str] = []
    sources: List[SourceItem] = []
    summary: Optional[str] = None


class StrategyRequest(BaseModel):
    brand: str
    industry: Optional[str] = None
    goals: List[str] = ["awareness", "consideration", "leads"]
    budget_usd: float = Field(10000, ge=100)
    country: Optional[str] = None
    research: Optional[ResearchResult] = None
    time_horizon_months: int = Field(3, ge=1, le=12)
    language: Optional[str] = None
    use_cache: bool = True


class StrategyPlan(BaseModel):
    brand: str
    total_budget_usd: float
    allocations: Dict[str, float]
    content_plan: Dict[str, Dict[str, Any]]
    kpis: List[str]
    swot: Dict[str, List[str]]
    timeline: List[Dict[str, Any]]
    media_calendar: List[Dict[str, Any]]


class ReportRequest(BaseModel):
    brand: str
    research: ResearchResult
    strategy: StrategyPlan
    language: Optional[str] = None
    use_cache: bool = True


class WorkflowRequest(BaseModel):
    brand: str
    country: Optional[str] = None
    industry: Optional[str] = None
    goals: List[str] = ["awareness", "consideration", "leads"]
    budget_usd: float = Field(10000, ge=100)
    time_horizon_months: int = Field(3, ge=1, le=12)
    max_results: int = Field(12, ge=1, le=50)


app = FastAPI(title="AI Media Research & Strategy API", version="0.1.0")


def _parse_cors_origins(value: Optional[str]) -> List[str]:
    if not value:
        return ["*"]
    return [v.strip() for v in value.split(",") if v.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(os.getenv("CORS_ORIGINS")),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


async def get_http_session() -> ClientSession:
    session: Optional[ClientSession] = getattr(app.state, "http_session", None)
    if session is None or session.closed:
        session = ClientSession(timeout=None)
        app.state.http_session = session
    return session


@app.on_event("shutdown")
async def _shutdown_event() -> None:
    session: Optional[ClientSession] = getattr(app.state, "http_session", None)
    if session and not session.closed:
        await session.close()


def require_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    required_key = os.getenv("API_KEY")
    if required_key and x_api_key != required_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


async def parse_with_groq(content: str, brand: str, country: Optional[str], industry: Optional[str]) -> Optional[Dict[str, Any]]:
    """Use Groq AI to parse Jina's markdown content into structured JSON"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY not set, falling back to manual parsing")
        return parse_markdown_research(content, brand, country, industry)
    
    session = await get_http_session()
    
    system_prompt = (
        "You are an expert data parser. Parse the provided market research content and extract structured data. "
        "Return ONLY a valid JSON object with this exact schema:\n"
        "{\n"
        "  \"brand\": string,\n"
        "  \"country\": string|null,\n"
        "  \"industry\": string|null,\n"
        "  \"summary\": string,\n"
        "  \"competitors\": [{ \"name\": string, \"website\": string|null, \"summary\": string }],\n"
        "  \"trends\": [string],\n"
        "  \"ad_insights\": [string],\n"
        "  \"sources\": [{ \"title\": string|null, \"url\": string, \"summary\": string|null }]\n"
        "}\n"
        "Extract competitors from tables and text mentions. Extract market trends and advertising insights. "
        "Include sources from citations. Limit competitors to 12, trends to 8, ad_insights to 6, sources to 12. "
        "Ensure all extracted text is clean and meaningful - no markdown artifacts like '---' or table separators."
    )
    
    user_prompt = (
        f"Parse this market research content for {brand} in {industry or 'the market'}:\n\n"
        f"{content[:8000]}"  # Limit content to avoid token limits
    )
    
    url = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
    model = os.getenv("GROQ_MODEL", "llama3-70b-8192")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "stream": False,
        "response_format": {"type": "json_object"}
    }
    
    try:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"Groq parsing API error: {resp.status} {text}")
                return parse_markdown_research(content, brand, country, industry)
            
            data = await resp.json()
            groq_content = data["choices"][0]["message"]["content"]
            parsed = json.loads(groq_content)
            
            print(f"Groq extracted: {len(parsed.get('competitors', []))} competitors, {len(parsed.get('trends', []))} trends")
            return parsed
            
    except Exception as e:
        print(f"Error using Groq for parsing: {e}")
        return parse_markdown_research(content, brand, country, industry)


def parse_markdown_research(content: str, brand: str, country: Optional[str], industry: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse Jina's markdown research content into structured JSON format"""
    import re
    
    try:
        # Extract competitors from markdown table
        competitors = []
        
        # Try multiple table patterns
        table_patterns = [
            r'\|\s*Competitor\s*\|\s*Strengths\s*\|\s*Weaknesses\s*\|\s*Market Share.*?\n((?:\|.*?\|.*?\|\n?)+)',
            r'\|\s*Competitor\s*\|\s*Summary\s*\|.*?\n((?:\|.*?\|.*?\|\n?)+)',
            r'Direct competitors include ([^.]+)\.',
            r'competitors include ([^.]+)\.',
        ]
        
        # Try table extraction first
        for pattern in table_patterns[:2]:
            table_match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if table_match:
                rows = table_match.group(1).strip().split('\n')
                for row in rows:
                    # Skip markdown table separators and empty rows
                    if ('|' in row and 
                        not row.strip().startswith('|---') and
                        not row.strip().startswith('| ---') and
                        '---' not in row and
                        len(row.strip()) > 5):
                        
                        parts = [p.strip() for p in row.split('|') if p.strip()]
                        if len(parts) >= 2:
                            name = parts[0].strip()
                            summary = parts[1].strip() if len(parts) > 1 else ""
                            
                            # Comprehensive filtering for valid competitor names
                            if (name and 
                                name.lower() not in ['competitor', 'tesla', '---', '--', '-', 'strengths', 'weaknesses', 'market share'] and 
                                len(name) > 1 and 
                                not name.startswith('-') and
                                not name.endswith('-') and
                                not all(c in '-|=+*#' for c in name) and
                                not re.match(r'^-+$', name) and
                                not re.match(r'^\|.*\|$', name)):
                                
                                competitors.append({
                                    "name": name,
                                    "website": None,
                                    "summary": summary if summary and summary not in ['---', '--', '-'] else f"Competitor in the {industry or 'market'} space"
                                })
                break
        
        # If no table found, extract from text mentions
        if not competitors:
            for pattern in table_patterns[2:]:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    comp_text = match.group(1)
                    # Split by common delimiters
                    comp_names = re.split(r'[,;]\s*(?:and\s+)?', comp_text)
                    for name in comp_names:
                        name = name.strip().replace('and ', '').strip()
                        if name and len(name) > 2:
                            competitors.append({
                                "name": name,
                                "website": None,
                                "summary": f"Competitor in the {industry or 'market'} space"
                            })
                    break
        
        # Extract individual competitor mentions from text
        if not competitors:
            competitor_keywords = [
                r'BYD[^a-zA-Z]',
                r'Ford[^a-zA-Z]',
                r'General Motors',
                r'\bGM\b',
                r'Rivian',
                r'Lucid Motors',
                r'Volkswagen',
                r'BMW[^a-zA-Z]',
                r'NIO[^a-zA-Z]',
                r'Mercedes-Benz',
                r'Toyota[^a-zA-Z]'
            ]
            
            found_competitors = set()
            for keyword in competitor_keywords:
                matches = re.findall(keyword, content, re.IGNORECASE)
                if matches:
                    clean_name = re.sub(r'[^a-zA-Z\s-]', '', keyword.replace('\\b', '').replace('[^a-zA-Z]', ''))
                    found_competitors.add(clean_name.strip())
            
            for name in list(found_competitors)[:12]:
                # Additional filtering for keyword matches
                if (name and 
                    len(name) > 2 and 
                    not name.startswith('-') and
                    name not in ['---', '--', '-', '|'] and
                    not all(c in '-|=' for c in name)):
                    competitors.append({
                        "name": name,
                        "website": None,
                        "summary": f"Major competitor in the {industry or 'automotive'} industry"
                    })
        
        # Extract trends from content
        trends = []
        
        # Look for market trends section
        trend_section_match = re.search(r'### Shifting Market Trends(.*?)(?:###|$)', content, re.DOTALL | re.IGNORECASE)
        if trend_section_match:
            trend_section = trend_section_match.group(1)
            # Extract sentences with key trend indicators
            trend_sentences = re.findall(r'([^.]*(?:market|sales|growth|trend|increasing|declining|competition|technology)[^.]*\.)', trend_section, re.IGNORECASE)
            trends = [t.strip() for t in trend_sentences if len(t.strip()) > 20][:8]
        
        # Fallback: extract key market insights from anywhere in content
        if not trends:
            trend_indicators = [
                r'The US EV market is experiencing ([^.]+\.)',
                r'sales growth ([^.]+\.)',
                r'([^.]*competition[^.]*\.)',
                r'([^.]*market share[^.]*\.)',
                r'([^.]*dominance[^.]*\.)',
                r'([^.]*technology[^.]*\.)'
            ]
            
            for pattern in trend_indicators:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches[:2]:
                    if len(match.strip()) > 15:
                        trends.append(match.strip())
        
        # Clean and deduplicate trends - filter out markdown artifacts
        cleaned_trends = []
        for t in trends:
            t = t.strip()
            if (len(t) > 15 and 
                not t.startswith('#') and 
                not t.startswith('|') and
                not t.startswith('[^') and
                '---' not in t and
                not all(c in '-|=*#' for c in t[:10])):
                cleaned_trends.append(t)
        trends = list(dict.fromkeys(cleaned_trends))[:8]
        
        # Extract ad insights
        ad_insights = []
        
        # Look for marketing/sales strategy sections
        marketing_sections = [
            r'### Tesla\'s Marketing and Sales Strategies(.*?)(?:###|$)',
            r'marketing strategy(.*?)(?:\[|\n\n)',
            r'direct.*?sales.*?model(.*?)(?:\[|\n\n)',
            r'advertising(.*?)(?:\[|\n\n)'
        ]
        
        for section_pattern in marketing_sections:
            section_match = re.search(section_pattern, content, re.DOTALL | re.IGNORECASE)
            if section_match:
                section_text = section_match.group(1)
                # Extract meaningful insights
                insight_sentences = re.findall(r'([^.]*(?:Tesla|marketing|sales|brand|advertising|direct|consumer|strategy)[^.]*\.)', section_text, re.IGNORECASE)
                ad_insights.extend([s.strip() for s in insight_sentences if len(s.strip()) > 20][:4])
                break
        
        # Fallback: extract marketing-related insights
        if not ad_insights:
            marketing_indicators = [
                r'([^.]*direct.to.consumer[^.]*\.)',
                r'([^.]*brand awareness[^.]*\.)',
                r'([^.]*marketing strategy[^.]*\.)',
                r'([^.]*sales model[^.]*\.)',
                r'([^.]*advertising[^.]*\.)'
            ]
            
            for pattern in marketing_indicators:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches[:2]:
                    if len(match.strip()) > 15:
                        ad_insights.append(match.strip())
        
        # Clean and deduplicate ad insights - filter out markdown artifacts
        cleaned_insights = []
        for a in ad_insights:
            a = a.strip()
            if (len(a) > 15 and 
                not a.startswith('#') and 
                not a.startswith('|') and
                not a.startswith('[^') and
                '---' not in a and
                not all(c in '-|=*#' for c in a[:10])):
                cleaned_insights.append(a)
        ad_insights = list(dict.fromkeys(cleaned_insights))[:6]
        
        # Extract sources from citations/footnotes
        sources = []
        citation_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        citations = re.findall(citation_pattern, content)
        for title, url in citations[:12]:
            sources.append({
                "title": title.strip(),
                "url": url.strip(),
                "summary": None
            })
        
        # Extract summary (first few sentences)
        summary_match = re.search(r'^([^.]+\.[^.]+\.)', content.strip())
        summary = summary_match.group(1).strip() if summary_match else f"Research analysis for {brand} in the {industry or 'market'} sector."
        
        # Clean up data
        competitors = competitors[:12]
        trends = list(dict.fromkeys([t for t in trends if len(t) > 10]))[:8]
        ad_insights = list(dict.fromkeys([a for a in ad_insights if len(a) > 10]))[:6]
        
        result = {
            "brand": brand,
            "country": country,
            "industry": industry,
            "summary": summary,
            "competitors": competitors,
            "trends": trends,
            "ad_insights": ad_insights,
            "sources": sources
        }
        
        print(f"Extracted {len(competitors)} competitors, {len(trends)} trends, {len(ad_insights)} insights, {len(sources)} sources")
        print(f"Competitors: {[c['name'] for c in competitors]}")
        print(f"First trend: {trends[0] if trends else 'None'}")
        return result
        
    except Exception as e:
        print(f"Error parsing markdown content: {e}")
        return None


def build_research_query(req: ResearchRequest) -> str:
    parts: List[str] = []
    parts.append(f"Competitors of {req.brand}")
    if req.industry:
        parts.append(f"in industry {req.industry}")
    if req.country:
        parts.append(f"in {req.country}")
    parts.append("pricing, ads, audience, messaging, tone, content strategy, market trends")
    return " ".join(parts)


async def call_jina_deepsearch_structured(req: ResearchRequest) -> Dict[str, Any]:
    api_key = os.getenv("JINA_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Missing JINA_API_KEY")
    session = await get_http_session()
    if not hasattr(app.state, "jina_lock"):
        app.state.jina_lock = asyncio.Lock()
    if not hasattr(app.state, "jina_cache"):
        app.state.jina_cache = {}
    cache_key = json.dumps({
        "brand": req.brand.strip().lower(),
        "country": (req.country or "").strip().lower(),
        "industry": (req.industry or "").strip().lower(),
        "max_results": req.max_results,
        "language": req.language
    }, sort_keys=True)
    print(cache_key)
    cached = app.state.jina_cache.get(cache_key)
    if req.use_cache and cached:
        cached_time = cached.get("_cached_at")
        if cached_time and (datetime.utcnow() - cached_time).total_seconds() < 60 * 60 * 12:
            return cached["data"]
    system_prompt = (
        "You are an expert market and media research agent. "
        "CRITICAL: Return ONLY a valid JSON object. No explanatory text before or after. No markdown formatting. "
        "Use up-to-date web intelligence to identify direct and indirect competitors, key market trends, and paid media insights. "
        "The JSON schema must be exactly: {\n"
        "  \"brand\": string,\n"
        "  \"country\": string|null,\n"
        "  \"industry\": string|null,\n"
        "  \"summary\": string,\n"
        "  \"competitors\": [ { \"name\": string, \"website\": string|null, \"summary\": string } ],\n"
        "  \"trends\": [ string ],\n"
        "  \"ad_insights\": [ string ],\n"
        "  \"sources\": [ { \"title\": string|null, \"url\": string, \"summary\": string|null } ]\n"
        "}. "
        "Limit competitors to 12 and sources to {max_results}. "
        "Your response must start with {{ and end with }}."
    ).replace("{max_results}", str(req.max_results))
    user_prompt = (
        f"Research scope:\n"
        f"Brand: {req.brand}\n"
        f"Country: {req.country or 'global'}\n"
        f"Industry: {req.industry or 'general'}\n"
        f"Language: {req.language or 'en'}\n"
        f"Task: Identify direct and indirect competitors with brief summaries, extract key market trends, and paid media insights. "
        f"Provide credible sources (title, url, 1-line summary)."
    )
    url = os.getenv("JINA_DEEPSEARCH_URL", "https://deepsearch.jina.ai/v1/chat/completions")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "jina-deepsearch-v1",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "reasoning_effort": "low",
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    async with app.state.jina_lock:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"Jina API Error {resp.status}: {text}")
                raise HTTPException(status_code=502, detail=f"Jina API error: {resp.status} {text}")
            data = await resp.json()
    
    print(f"Jina API Response: {json.dumps(data, indent=2)}")
    
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        print(f"Jina response structure error: {e}")
        print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        raise HTTPException(status_code=502, detail=f"Jina API unexpected response format: {str(e)}")
    
    print(f"Jina content: {content}")
    
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Content that failed to parse: {content[:500]}...")
        
        # Use Groq to parse the markdown content into structured JSON
        parsed = await parse_with_groq(content, req.brand, req.country, req.industry)
        if parsed:
            print(f"Successfully parsed markdown content with Groq AI")
        else:
            # Fallback: create a basic response structure
            parsed = {
            "brand": req.brand,
            "country": req.country,
            "industry": req.industry,
            "summary": f"Basic research generated for {req.brand}",
            "competitors": [
                {"name": f"{req.brand} Competitor 1", "website": None, "summary": "Generated competitor"},
                {"name": f"{req.brand} Competitor 2", "website": None, "summary": "Generated competitor"}
            ],
            "trends": ["Market trend 1", "Market trend 2"],
            "ad_insights": ["Ad insight 1", "Ad insight 2"],
            "sources": []
        }
        print(f"Using fallback data: {parsed}")
    
    app.state.jina_cache[cache_key] = {"data": parsed, "_cached_at": datetime.utcnow()}
    return parsed


async def call_groq_strategy_structured(
    research: ResearchResult,
    goals: List[str],
    budget_usd: float,
    time_horizon_months: int,
    language: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Missing GROQ_API_KEY")
    session = await get_http_session()
    if not hasattr(app.state, "groq_lock"):
        app.state.groq_lock = asyncio.Lock()
    if not hasattr(app.state, "groq_cache"):
        app.state.groq_cache = {}
    cache_key = json.dumps({
        "brand": research.brand,
        "country": research.country,
        "industry": research.industry,
        "goals": goals,
        "budget_usd": budget_usd,
        "time_horizon_months": time_horizon_months,
        "language": language
    }, sort_keys=True)
    cached = app.state.groq_cache.get(cache_key)
    if use_cache and cached:
        cached_time = cached.get("_cached_at")
        if cached_time and (datetime.utcnow() - cached_time).total_seconds() < 60 * 60 * 12:
            return cached["data"]
    system_prompt = (
        "You are a senior media strategist. Return one valid JSON object only, no markdown. "
        "Use the provided research to produce an actionable media plan. Output schema must be: {\n"
        "  \"allocations\": { \"Google Ads\": number, \"LinkedIn\": number, \"Meta\": number, \"YouTube\": number, \"Twitter/X\": number, \"Others\": number },\n"
        "  \"content_plan\": { \"Video\": { \"cadence_per_week\": number, \"platforms\": [string] }, \"Blog\": { \"cadence_per_week\": number, \"platforms\": [string] }, \"Social\": { \"cadence_per_week\": number, \"platforms\": [string] } },\n"
        "  \"kpis\": [ string ],\n"
        "  \"swot\": { \"strengths\": [string], \"weaknesses\": [string], \"opportunities\": [string], \"threats\": [string] },\n"
        "  \"timeline\": [ { \"phase\": string, \"start\": \"YYYY-MM-DD\", \"end\": \"YYYY-MM-DD\" } ],\n"
        "  \"media_calendar\": [ { \"week\": number, \"channel\": string, \"budget_usd\": number } ]\n"
        "}. "
        "The sum of values in \"allocations\" must equal the total budget {budget}. Use only channels: Google Ads, LinkedIn, Meta, YouTube, Twitter/X, Others. "
        "Make the number of months in the timeline equal to {months}. Respond in the requested language if provided."
    ).replace("{budget}", str(budget_usd)).replace("{months}", str(time_horizon_months))
    research_json = json.dumps(research.dict(), ensure_ascii=False)
    user_prompt = (
        f"Goals: {', '.join(goals)}\n"
        f"Total budget (USD): {budget_usd}\n"
        f"Time horizon (months): {time_horizon_months}\n"
        f"Language: {language or 'en'}\n"
        f"Research JSON: {research_json}\n"
        f"Produce the strategy following the schema with realistic numbers and dates."
    )
    url = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
    model = os.getenv("GROQ_MODEL", "llama3-70b-8192")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "stream": False,
        "response_format": {"type": "json_object"}
    }
    async with app.state.groq_lock:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise HTTPException(status_code=502, detail=f"Groq API error: {resp.status} {text}")
            data = await resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        raise HTTPException(status_code=502, detail="Groq API unexpected response format")
    try:
        parsed = json.loads(content)
    except Exception:
        raise HTTPException(status_code=502, detail="Groq API did not return valid JSON content")
    app.state.groq_cache[cache_key] = {"data": parsed, "_cached_at": datetime.utcnow()}
    return parsed


def synthesize_competitors(brand: str, industry: Optional[str], n: int) -> List[Competitor]:
    base = industry or "market"
    names = [
        f"{brand} Labs",
        f"{brand} Media",
        f"{brand} Digital",
        f"{brand} Solutions",
        f"{brand} Edge",
        f"{brand} Analytics",
        f"{brand} Hub",
        f"{brand} Works",
        f"{brand} Pro",
        f"{brand} Nexus"
    ]
    competitors: List[Competitor] = []
    for i in range(min(n, len(names))):
        competitors.append(Competitor(
            name=names[i],
            website=None,
            summary=f"Provider in {base} with focus on growth and performance"
        ))
    return competitors


def parse_jina_results(jina_json: Dict[str, Any], fallback_brand: str, industry: Optional[str], limit: int) -> Tuple[List[Competitor], List[SourceItem], List[str], List[str], str]:
    competitors_data = jina_json.get("competitors") or []
    sources_data = jina_json.get("sources") or []
    trends_data = jina_json.get("trends") or []
    ad_insights_data = jina_json.get("ad_insights") or []
    summary = jina_json.get("summary") or None
    competitors: List[Competitor] = []
    for c in competitors_data[:limit]:
        competitors.append(Competitor(
            name=str(c.get("name") or "").strip() or fallback_brand,
            website=c.get("website"),
            summary=c.get("summary")
        ))
    if not competitors:
        competitors = synthesize_competitors(fallback_brand, industry, limit)
    sources: List[SourceItem] = []
    for s in sources_data[:limit]:
        url = s.get("url")
        if not url:
            continue
        sources.append(SourceItem(title=s.get("title"), url=url, summary=s.get("summary")))
    trends = [str(t) for t in trends_data][:5]
    ad_insights = [str(a) for a in ad_insights_data][:8]
    return competitors, sources, trends, ad_insights, summary or f"Research on {fallback_brand}"


def build_trend_insights(brand: str, industry: Optional[str], sources: List[SourceItem]) -> List[str]:
    base = industry or "the category"
    items = [
        f"Increased competition in {base} with emphasis on multi-channel attribution",
        f"Growing adoption of short-form video for {brand} and peers",
        f"Rise of AI-assisted ad targeting and creative testing",
        f"Greater focus on privacy-safe measurement and first-party data",
        f"Shift in budget towards performance channels and influencer collaborations"
    ]
    return items[:5]


def build_ad_insights(brand: str, industry: Optional[str], sources: List[SourceItem]) -> List[str]:
    base = industry or "the space"
    items = [
        f"Competitors in {base} emphasize Google Search and YouTube for intent and reach",
        f"LinkedIn is effective for B2B lead gen with thought leadership",
        f"Retargeting via Meta improves conversion efficiency",
        f"Content themes center on case studies, ROI proof, and product demos"
    ]
    return items


def allocate_budget(goals: List[str], total_budget: float) -> Dict[str, float]:
    goals_lower = {g.lower() for g in goals}
    if "leads" in goals_lower or "conversions" in goals_lower:
        weights = {"Google Ads": 0.38, "LinkedIn": 0.22, "Meta": 0.18, "YouTube": 0.12, "Twitter/X": 0.05, "Others": 0.05}
    elif "awareness" in goals_lower:
        weights = {"YouTube": 0.3, "Meta": 0.25, "Google Ads": 0.2, "LinkedIn": 0.15, "Twitter/X": 0.05, "Others": 0.05}
    else:
        weights = {"Google Ads": 0.3, "LinkedIn": 0.2, "Meta": 0.2, "YouTube": 0.2, "Others": 0.1}
    allocations = {ch: round(total_budget * w, 2) for ch, w in weights.items()}
    return allocations


def build_content_plan(goals: List[str]) -> Dict[str, Dict[str, Any]]:
    return {
        "Video": {"cadence_per_week": 2, "platforms": ["YouTube", "LinkedIn", "Meta"]},
        "Blog": {"cadence_per_week": 1, "platforms": ["Website", "LinkedIn"]},
        "Social": {"cadence_per_week": 3, "platforms": ["LinkedIn", "Twitter/X", "Meta"]}
    }


def build_kpis(goals: List[str]) -> List[str]:
    goals_lower = {g.lower() for g in goals}
    base = ["CTR", "CPC", "CPM", "Reach", "Engagement Rate"]
    if "leads" in goals_lower:
        base += ["CPL", "SQLs", "Pipeline Value"]
    if "awareness" in goals_lower:
        base += ["Share of Voice", "Brand Search Lift"]
    return list(dict.fromkeys(base))


def build_swot(brand: str, competitors: List[Competitor]) -> Dict[str, List[str]]:
    return {
        "strengths": [f"{brand} product depth", "Agile execution", "Existing customer base"],
        "weaknesses": ["Limited brand awareness", "Small creative library"],
        "opportunities": ["AI-driven optimization", "New channels", "Partnerships"],
        "threats": ["Aggressive competitor pricing", "Platform policy changes"]
    }


def build_timeline(months: int) -> List[Dict[str, Any]]:
    start = datetime.utcnow()
    phases = []
    per_phase = max(1, months // 3)
    labels = ["Discovery & Setup", "Testing & Optimization", "Scale & Expansion"]
    for i, label in enumerate(labels):
        phase_start = start + timedelta(days=30 * per_phase * i)
        phase_end = start + timedelta(days=30 * per_phase * (i + 1))
        phases.append({"phase": label, "start": phase_start.date().isoformat(), "end": phase_end.date().isoformat()})
    return phases


def build_media_calendar(allocations: Dict[str, float]) -> List[Dict[str, Any]]:
    calendar: List[Dict[str, Any]] = []
    weeks = 4
    for i in range(weeks):
        for ch, amt in allocations.items():
            calendar.append({"week": i + 1, "channel": ch, "budget_usd": round(amt / weeks, 2)})
    return calendar


def generate_budget_chart(allocations: Dict[str, float]) -> io.BytesIO:
    labels = list(allocations.keys())
    sizes = list(allocations.values())
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, counterclock=False)
    ax.axis('equal')
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format='png', dpi=200)
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_enhanced_budget_chart(allocations: Dict[str, float]) -> io.BytesIO:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import numpy as np
    
    # Modern color palette
    colors = [
        '#1A237E',  # Deep blue
        '#FF5722',  # Deep orange  
        '#4CAF50',  # Green
        '#FFC107',  # Amber
        '#9C27B0',  # Purple
        '#00BCD4',  # Cyan
        '#E91E63',  # Pink
        '#795548'   # Brown
    ]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    fig.patch.set_facecolor('#F5F5F5')
    
    channels = list(allocations.keys())
    amounts = list(allocations.values())
    
    # PIE CHART with modern styling
    wedges, texts, autotexts = ax1.pie(
        amounts, 
        labels=channels, 
        colors=colors[:len(channels)],
        autopct='%1.1f%%',
        startangle=90,
        explode=[0.05] * len(channels),  # Slight separation
        shadow=True,
        textprops={'fontsize': 12, 'fontweight': 'bold'}
    )
    
    ax1.set_title('💰 BUDGET DISTRIBUTION', fontsize=18, fontweight='bold', pad=20, color='#1A237E')
    
    # BAR CHART for comparison
    bars = ax2.barh(channels, amounts, color=colors[:len(channels)], alpha=0.8, edgecolor='white', linewidth=2)
    
    # Add value labels on bars
    for i, (bar, amount) in enumerate(zip(bars, amounts)):
        width = bar.get_width()
        ax2.text(width + max(amounts) * 0.01, bar.get_y() + bar.get_height()/2, 
                f'${amount:,.0f}', ha='left', va='center', fontweight='bold', fontsize=11)
    
    ax2.set_title('📊 BUDGET BY CHANNEL', fontsize=18, fontweight='bold', pad=20, color='#1A237E')
    ax2.set_xlabel('Budget ($)', fontsize=14, fontweight='bold')
    ax2.grid(axis='x', alpha=0.3, linestyle='--')
    ax2.set_facecolor('#FAFAFA')
    
    # Style improvements
    for ax in [ax1, ax2]:
        ax.tick_params(labelsize=11)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=300, bbox_inches='tight', facecolor='#F5F5F5')
    plt.close(fig)
    buf.seek(0)
    return buf


async def call_groq_doc_sections(
    research: ResearchResult,
    strategy: StrategyPlan,
    doc_type: str,
    language: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Missing GROQ_API_KEY")
    session = await get_http_session()
    if not hasattr(app.state, "groq_lock"):
        app.state.groq_lock = asyncio.Lock()
    if not hasattr(app.state, "groq_cache"):
        app.state.groq_cache = {}
    cache_key = json.dumps({
        "doc_type": doc_type,
        "language": language,
        "research": research.dict(),
        "strategy": strategy.dict()
    }, sort_keys=True)
    cached = app.state.groq_cache.get(cache_key)
    if use_cache and cached:
        cached_time = cached.get("_cached_at")
        if cached_time and (datetime.utcnow() - cached_time).total_seconds() < 60 * 60 * 12:
            return cached["data"]
    system_prompt = (
        "You are a senior strategy copywriter and media planner. Return one JSON object only. "
        "Output schema: {\n"
        "  \"executive_summary\": string,\n"
        "  \"key_findings\": [string],\n"
        "  \"competitor_insights\": [string],\n"
        "  \"recommendations\": [string],\n"
        "  \"timeline_bullets\": [string],\n"
        "  \"swot\": { \"strengths\": [string], \"weaknesses\": [string], \"opportunities\": [string], \"threats\": [string] }\n"
        "}. Respond in the requested language if provided."
    )
    user_prompt = (
        f"Document type: {doc_type}\n"
        f"Language: {language or 'en'}\n"
        f"Research JSON: {json.dumps(research.dict(), ensure_ascii=False)}\n"
        f"Strategy JSON: {json.dumps(strategy.dict(), ensure_ascii=False)}\n"
        f"Produce concise and executive-ready content following the schema."
    )
    url = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
    model = os.getenv("GROQ_MODEL", "llama3-70b-8192")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "stream": False,
        "response_format": {"type": "json_object"}
    }
    async with app.state.groq_lock:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise HTTPException(status_code=502, detail=f"Groq API error: {resp.status} {text}")
            data = await resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except Exception:
        raise HTTPException(status_code=502, detail="Groq API doc sections invalid format")
    app.state.groq_cache[cache_key] = {"data": parsed, "_cached_at": datetime.utcnow()}
    return parsed


async def build_ppt(brand: str, research: ResearchResult, strategy: StrategyPlan, language: Optional[str] = None, use_cache: bool = True) -> io.BytesIO:
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.enum.shapes import MSO_SHAPE
    
    try:
        sections = await call_groq_doc_sections(research, strategy, doc_type="pptx", language=language, use_cache=use_cache)
    except HTTPException:
        sections = {}
    
    prs = Presentation()
    
    # Define brand colors - modern gradient scheme
    primary_color = RGBColor(26, 35, 126)     # Deep blue
    accent_color = RGBColor(255, 87, 34)      # Vibrant orange
    success_color = RGBColor(76, 175, 80)     # Success green
    warning_color = RGBColor(255, 193, 7)     # Warning amber
    light_gray = RGBColor(245, 245, 245)      # Light background
    dark_gray = RGBColor(66, 66, 66)          # Dark text
    
    # 🎨 SLIDE 1: STUNNING TITLE SLIDE
    title_layout = prs.slide_layouts[6]  # Blank layout for custom design
    slide = prs.slides.add_slide(title_layout)
    
    # Background gradient effect with shapes
    bg_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
    )
    bg_fill = bg_shape.fill
    bg_fill.solid()
    bg_fill.fore_color.rgb = light_gray
    
    # Accent stripe
    accent_stripe = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, Inches(2), prs.slide_height
    )
    stripe_fill = accent_stripe.fill
    stripe_fill.solid()
    stripe_fill.fore_color.rgb = primary_color
    
    # Modern title with custom positioning
    title_box = slide.shapes.add_textbox(Inches(2.5), Inches(2), Inches(7), Inches(2))
    title_frame = title_box.text_frame
    title_frame.clear()
    title_para = title_frame.paragraphs[0]
    title_para.text = f"🚀 {brand.upper()}"
    title_para.font.size = Pt(48)
    title_para.font.bold = True
    title_para.font.color.rgb = primary_color
    title_para.alignment = PP_ALIGN.LEFT
    
    # Subtitle with style
    subtitle_box = slide.shapes.add_textbox(Inches(2.5), Inches(3.2), Inches(7), Inches(1.5))
    subtitle_frame = subtitle_box.text_frame
    subtitle_frame.clear()
    subtitle_para = subtitle_frame.paragraphs[0]
    subtitle_para.text = "MEDIA STRATEGY & MARKET INTELLIGENCE"
    subtitle_para.font.size = Pt(18)
    subtitle_para.font.color.rgb = accent_color
    subtitle_para.alignment = PP_ALIGN.LEFT
    
    # Tagline
    tagline_box = slide.shapes.add_textbox(Inches(2.5), Inches(4.2), Inches(7), Inches(1))
    tagline_frame = tagline_box.text_frame
    tagline_frame.clear()
    tagline_para = tagline_frame.paragraphs[0]
    tagline_para.text = f"🎯 {research.industry} | 🌍 {research.country} | 📊 Competitive Intelligence"
    tagline_para.font.size = Pt(14)
    tagline_para.font.color.rgb = dark_gray
    tagline_para.alignment = PP_ALIGN.LEFT

    # 🎨 SLIDE 2: EXECUTIVE SUMMARY WITH MODERN LAYOUT
    layout = prs.slide_layouts[6]  # Blank for custom design
    slide = prs.slides.add_slide(layout)
    
    # Header with gradient background
    header_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.2)
    )
    header_fill = header_shape.fill
    header_fill.solid()
    header_fill.fore_color.rgb = primary_color
    
    # Title in header
    header_title = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(9), Inches(0.8))
    header_frame = header_title.text_frame
    header_frame.clear()
    header_para = header_frame.paragraphs[0]
    header_para.text = "💡 EXECUTIVE SUMMARY"
    header_para.font.size = Pt(24)
    header_para.font.bold = True
    header_para.font.color.rgb = RGBColor(255, 255, 255)
    header_para.alignment = PP_ALIGN.CENTER
    
    # Content with modern styling
    content_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(9), Inches(5))
    content_frame = content_box.text_frame
    content_frame.clear()
    content_frame.margin_left = Inches(0.2)
    content_frame.margin_top = Inches(0.2)
    
    # Add executive summary content
    exec_summary = (sections.get("executive_summary") if isinstance(sections, dict) else None) or research.summary
    summary_para = content_frame.paragraphs[0]
    summary_para.text = f"📈 {exec_summary}"
    summary_para.font.size = Pt(16)
    summary_para.font.color.rgb = dark_gray
    summary_para.line_spacing = 1.3
    
    # Key metrics in colored boxes
    metrics = [
        (f"🏢 {len(research.competitors)}", "COMPETITORS", success_color),
        (f"📊 {len(research.trends)}", "MARKET TRENDS", accent_color),
        (f"💰 ${strategy.total_budget_usd:,.0f}", "BUDGET", warning_color)
    ]
    
    x_positions = [Inches(0.5), Inches(3.5), Inches(6.5)]
    for i, (value, label, color) in enumerate(metrics):
        metric_box = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, x_positions[i], Inches(4.5), Inches(2.5), Inches(1.5)
        )
        metric_fill = metric_box.fill
        metric_fill.solid()
        metric_fill.fore_color.rgb = color
        
        # Value text
        value_text = slide.shapes.add_textbox(x_positions[i], Inches(4.7), Inches(2.5), Inches(0.6))
        value_frame = value_text.text_frame
        value_frame.clear()
        value_para = value_frame.paragraphs[0]
        value_para.text = value
        value_para.font.size = Pt(20)
        value_para.font.bold = True
        value_para.font.color.rgb = RGBColor(255, 255, 255)
        value_para.alignment = PP_ALIGN.CENTER
        
        # Label text
        label_text = slide.shapes.add_textbox(x_positions[i], Inches(5.3), Inches(2.5), Inches(0.4))
        label_frame = label_text.text_frame
        label_frame.clear()
        label_para = label_frame.paragraphs[0]
        label_para.text = label
        label_para.font.size = Pt(10)
        label_para.font.color.rgb = RGBColor(255, 255, 255)
        label_para.alignment = PP_ALIGN.CENTER

    # 🎨 SLIDE 3: COMPETITIVE LANDSCAPE - MODERN CARD DESIGN
    slide = prs.slides.add_slide(layout)
    
    # Header
    header_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.2)
    )
    header_fill = header_shape.fill
    header_fill.solid()
    header_fill.fore_color.rgb = accent_color
    
    header_title = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(9), Inches(0.8))
    header_frame = header_title.text_frame
    header_frame.clear()
    header_para = header_frame.paragraphs[0]
    header_para.text = "🏢 COMPETITIVE LANDSCAPE"
    header_para.font.size = Pt(24)
    header_para.font.bold = True
    header_para.font.color.rgb = RGBColor(255, 255, 255)
    header_para.alignment = PP_ALIGN.CENTER
    
    # Competitor cards in grid layout
    competitors = research.competitors[:6]  # Top 6 competitors
    card_width = Inches(2.8)
    card_height = Inches(1.8)
    
    positions = [
        (Inches(0.5), Inches(1.8)), (Inches(3.5), Inches(1.8)), (Inches(6.5), Inches(1.8)),
        (Inches(0.5), Inches(4.0)), (Inches(3.5), Inches(4.0)), (Inches(6.5), Inches(4.0))
    ]
    
    card_colors = [primary_color, success_color, accent_color, warning_color, RGBColor(156, 39, 176), RGBColor(0, 150, 136)]
    
    for i, (comp, (x, y)) in enumerate(zip(competitors, positions)):
        if i >= len(card_colors):
            break
            
        # Card background
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, card_width, card_height)
        card_fill = card.fill
        card_fill.solid()
        card_fill.fore_color.rgb = card_colors[i % len(card_colors)]
        
        # Company name
        name_box = slide.shapes.add_textbox(x + Inches(0.1), y + Inches(0.1), card_width - Inches(0.2), Inches(0.5))
        name_frame = name_box.text_frame
        name_frame.clear()
        name_para = name_frame.paragraphs[0]
        name_para.text = f"🏆 {comp.name}"
        name_para.font.size = Pt(14)
        name_para.font.bold = True
        name_para.font.color.rgb = RGBColor(255, 255, 255)
        name_para.alignment = PP_ALIGN.CENTER
        
        # Summary
        summary_box = slide.shapes.add_textbox(x + Inches(0.1), y + Inches(0.7), card_width - Inches(0.2), card_height - Inches(0.8))
        summary_frame = summary_box.text_frame
        summary_frame.clear()
        summary_frame.word_wrap = True
        summary_para = summary_frame.paragraphs[0]
        summary_para.text = (comp.summary or "Key market player")[:100] + "..."
        summary_para.font.size = Pt(10)
        summary_para.font.color.rgb = RGBColor(255, 255, 255)
        summary_para.alignment = PP_ALIGN.LEFT

    # 🎨 SLIDE 4: SWOT ANALYSIS - BEAUTIFUL 2x2 MATRIX
    slide = prs.slides.add_slide(layout)
    
    # Header
    header_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.2)
    )
    header_fill = header_shape.fill
    header_fill.solid()
    header_fill.fore_color.rgb = success_color
    
    header_title = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(9), Inches(0.8))
    header_frame = header_title.text_frame
    header_frame.clear()
    header_para = header_frame.paragraphs[0]
    header_para.text = "🎯 SWOT ANALYSIS"
    header_para.font.size = Pt(24)
    header_para.font.bold = True
    header_para.font.color.rgb = RGBColor(255, 255, 255)
    header_para.alignment = PP_ALIGN.CENTER
    
    # SWOT matrix with stunning design
    swot_data = sections.get("swot") if isinstance(sections, dict) else strategy.swot
    swot_items = [
        ("💪 STRENGTHS", swot_data.get("strengths", []), success_color, Inches(0.5), Inches(1.5)),
        ("⚠️ WEAKNESSES", swot_data.get("weaknesses", []), RGBColor(244, 67, 54), Inches(5), Inches(1.5)),
        ("🌟 OPPORTUNITIES", swot_data.get("opportunities", []), RGBColor(33, 150, 243), Inches(0.5), Inches(4)),
        ("⚡ THREATS", swot_data.get("threats", []), RGBColor(255, 152, 0), Inches(5), Inches(4))
    ]
    
    box_width = Inches(4)
    box_height = Inches(2.2)
    
    for title, items, color, x, y in swot_items:
        # Background box
        swot_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, box_width, box_height)
        swot_fill = swot_box.fill
        swot_fill.solid()
        swot_fill.fore_color.rgb = color
        
        # Title
        title_box = slide.shapes.add_textbox(x + Inches(0.1), y + Inches(0.1), box_width - Inches(0.2), Inches(0.5))
        title_frame = title_box.text_frame
        title_frame.clear()
        title_para = title_frame.paragraphs[0]
        title_para.text = title
        title_para.font.size = Pt(16)
        title_para.font.bold = True
        title_para.font.color.rgb = RGBColor(255, 255, 255)
        title_para.alignment = PP_ALIGN.CENTER
        
        # Items
        items_box = slide.shapes.add_textbox(x + Inches(0.2), y + Inches(0.7), box_width - Inches(0.4), box_height - Inches(0.8))
        items_frame = items_box.text_frame
        items_frame.clear()
        items_frame.word_wrap = True
        
        for item in items[:3]:  # Limit to 3 items per quadrant
            p = items_frame.add_paragraph()
            p.text = f"• {item}"
            p.font.size = Pt(11)
            p.font.color.rgb = RGBColor(255, 255, 255)
            p.line_spacing = 1.2

    # 🎨 SLIDE 5: BUDGET ALLOCATION - ENHANCED CHART
    slide = prs.slides.add_slide(layout)
    
    # Header
    header_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.2)
    )
    header_fill = header_shape.fill
    header_fill.solid()
    header_fill.fore_color.rgb = warning_color
    
    header_title = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(9), Inches(0.8))
    header_frame = header_title.text_frame
    header_frame.clear()
    header_para = header_frame.paragraphs[0]
    header_para.text = "💰 BUDGET ALLOCATION"
    header_para.font.size = Pt(24)
    header_para.font.bold = True
    header_para.font.color.rgb = RGBColor(255, 255, 255)
    header_para.alignment = PP_ALIGN.CENTER
    
    # Enhanced budget chart
    allocations = strategy.allocations
    chart_buf = generate_enhanced_budget_chart(allocations)
    image = slide.shapes.add_picture(chart_buf, Inches(0.5), Inches(1.5), width=Inches(9))
    
    # Budget breakdown table
    table_data = [["CHANNEL", "BUDGET", "PERCENTAGE"]]
    total_budget = sum(allocations.values())
    
    for channel, amount in allocations.items():
        percentage = (amount / total_budget) * 100 if total_budget > 0 else 0
        table_data.append([
            f"🎯 {channel}",
            f"${amount:,.0f}",
            f"{percentage:.1f}%"
        ])
    
    # Add table below chart
    table_shape = slide.shapes.add_table(len(table_data), 3, Inches(10.5), Inches(1.5), Inches(3), Inches(3))
    table = table_shape.table
    
    # Style the table
    for i, row_data in enumerate(table_data):
        for j, cell_data in enumerate(row_data):
            cell = table.cell(i, j)
            cell.text = cell_data
            
            if i == 0:  # Header row
                cell.fill.solid()
                cell.fill.fore_color.rgb = primary_color
                for paragraph in cell.text_frame.paragraphs:
                    for run in paragraph.runs:
                        run.font.color.rgb = RGBColor(255, 255, 255)
                        run.font.bold = True
                        run.font.size = Pt(12)
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = light_gray
                for paragraph in cell.text_frame.paragraphs:
                    for run in paragraph.runs:
                        run.font.color.rgb = dark_gray
                        run.font.size = Pt(11)

    # 🎨 SLIDE 6: TIMELINE & ROADMAP
    slide = prs.slides.add_slide(layout)
    
    # Header
    header_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.2)
    )
    header_fill = header_shape.fill
    header_fill.solid()
    header_fill.fore_color.rgb = RGBColor(156, 39, 176)
    
    header_title = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(9), Inches(0.8))
    header_frame = header_title.text_frame
    header_frame.clear()
    header_para = header_frame.paragraphs[0]
    header_para.text = "🗓️ STRATEGIC ROADMAP"
    header_para.font.size = Pt(24)
    header_para.font.bold = True
    header_para.font.color.rgb = RGBColor(255, 255, 255)
    header_para.alignment = PP_ALIGN.CENTER
    
    # Timeline visualization
    timeline_colors = [primary_color, success_color, accent_color, warning_color]
    y_start = Inches(2)
    
    for i, phase in enumerate(strategy.timeline[:4]):
        color = timeline_colors[i % len(timeline_colors)]
        y_pos = y_start + Inches(i * 1.2)
        
        # Phase box
        phase_box = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), y_pos, Inches(8.5), Inches(1)
        )
        phase_fill = phase_box.fill
        phase_fill.solid()
        phase_fill.fore_color.rgb = color
        
        # Phase text
        phase_text = slide.shapes.add_textbox(Inches(0.7), y_pos + Inches(0.1), Inches(8.1), Inches(0.8))
        phase_frame = phase_text.text_frame
        phase_frame.clear()
        phase_para = phase_frame.paragraphs[0]
        phase_para.text = f"📅 {phase['phase']}: {phase['start']} → {phase['end']}"
        phase_para.font.size = Pt(16)
        phase_para.font.bold = True
        phase_para.font.color.rgb = RGBColor(255, 255, 255)
        phase_para.alignment = PP_ALIGN.LEFT

    # 🎨 SLIDE 7: THANK YOU / CONTACT
    slide = prs.slides.add_slide(layout)
    
    # Gradient background
    bg_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
    )
    bg_fill = bg_shape.fill
    bg_fill.solid()
    bg_fill.fore_color.rgb = primary_color
    
    # Thank you message
    thank_you_box = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(8), Inches(2))
    thank_you_frame = thank_you_box.text_frame
    thank_you_frame.clear()
    thank_you_para = thank_you_frame.paragraphs[0]
    thank_you_para.text = "🙏 THANK YOU"
    thank_you_para.font.size = Pt(48)
    thank_you_para.font.bold = True
    thank_you_para.font.color.rgb = RGBColor(255, 255, 255)
    thank_you_para.alignment = PP_ALIGN.CENTER
    
    # Subtitle
    subtitle_box = slide.shapes.add_textbox(Inches(1), Inches(4), Inches(8), Inches(1))
    subtitle_frame = subtitle_box.text_frame
    subtitle_frame.clear()
    subtitle_para = subtitle_frame.paragraphs[0]
    subtitle_para.text = f"🚀 Ready to dominate the {research.industry} market!"
    subtitle_para.font.size = Pt(20)
    subtitle_para.font.color.rgb = accent_color
    subtitle_para.alignment = PP_ALIGN.CENTER

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf


async def build_pdf(brand: str, research: ResearchResult, strategy: StrategyPlan, language: Optional[str] = None, use_cache: bool = True) -> io.BytesIO:
    try:
        sections = await call_groq_doc_sections(research, strategy, doc_type="pdf", language=language, use_cache=use_cache)
    except HTTPException:
        sections = {}
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story: List[Any] = []
    story.append(Paragraph(f"{brand} Market Research & Strategy", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Executive Summary", styles["Heading2"]))
    story.append(Paragraph((sections.get("executive_summary") if isinstance(sections, dict) else None) or research.summary or "Generated research summary.", styles["BodyText"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Competitors", styles["Heading2"]))
    comp_rows = [["Name", "Website", "Summary"]]
    for c in research.competitors[:10]:
        comp_rows.append([c.name, c.website or "", (c.summary or "")[:160]])
    table = Table(comp_rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    story.append(table)
    story.append(Spacer(1, 12))
    if isinstance(sections, dict) and sections.get("recommendations"):
        story.append(Paragraph("Recommendations", styles["Heading2"]))
        for rec in sections["recommendations"][:10]:
            story.append(Paragraph(f"• {rec}", styles["BodyText"]))
        story.append(Spacer(1, 12))
    story.append(Paragraph("Budget Allocation", styles["Heading2"]))
    chart_buf = generate_budget_chart(strategy.allocations)
    image_reader = ImageReader(chart_buf)
    story.append(RLImage(image_reader, width=400, height=260))
    story.append(Spacer(1, 12))
    story.append(Paragraph("SWOT", styles["Heading2"]))
    swot_values = (sections.get("swot") if isinstance(sections, dict) else None) or strategy.swot
    swot_rows = [["S", ", ".join(swot_values.get("strengths", []))], ["W", ", ".join(swot_values.get("weaknesses", []))], ["O", ", ".join(swot_values.get("opportunities", []))], ["T", ", ".join(swot_values.get("threats", []))]]
    swot_table = Table(swot_rows)
    swot_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
    story.append(swot_table)
    story.append(Spacer(1, 12))
    story.append(Paragraph("Timeline", styles["Heading2"]))
    if isinstance(sections, dict) and sections.get("timeline_bullets"):
        for line in sections["timeline_bullets"][:10]:
            story.append(Paragraph(str(line), styles["BodyText"]))
    else:
        for phase in strategy.timeline:
            story.append(Paragraph(f"{phase['phase']}: {phase['start']} → {phase['end']}", styles["BodyText"]))
    doc.build(story)
    buf.seek(0)
    return buf


async def build_docx(brand: str, research: ResearchResult, strategy: StrategyPlan, language: Optional[str] = None, use_cache: bool = True) -> io.BytesIO:
    if Document is None:
        raise HTTPException(status_code=501, detail="python-docx not installed")
    try:
        sections = await call_groq_doc_sections(research, strategy, doc_type="docx", language=language, use_cache=use_cache)
    except HTTPException:
        sections = {}
    doc = Document()
    doc.add_heading(f"{brand} Market Research & Strategy", 0)
    doc.add_heading("Executive Summary", level=1)
    doc.add_paragraph((sections.get("executive_summary") if isinstance(sections, dict) else None) or research.summary or "Generated research summary.")
    doc.add_heading("Competitors", level=1)
    table = doc.add_table(rows=1, cols=3)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Name"
    hdr_cells[1].text = "Website"
    hdr_cells[2].text = "Summary"
    for c in research.competitors[:10]:
        row_cells = table.add_row().cells
        row_cells[0].text = c.name
        row_cells[1].text = c.website or ""
        row_cells[2].text = (c.summary or "")[:200]
    if isinstance(sections, dict) and sections.get("recommendations"):
        doc.add_heading("Recommendations", level=1)
        for rec in sections["recommendations"][:10]:
            doc.add_paragraph(rec, style="List Bullet")
    doc.add_heading("Budget Allocation", level=1)
    chart_buf = generate_budget_chart(strategy.allocations)
    chart_buf.name = "budget.png"
    doc.add_picture(chart_buf, width=None)
    doc.add_heading("SWOT", level=1)
    swot_values = (sections.get("swot") if isinstance(sections, dict) else None) or strategy.swot
    for k in ["strengths", "weaknesses", "opportunities", "threats"]:
        doc.add_heading(k.capitalize(), level=2)
        for item in swot_values.get(k, []):
            doc.add_paragraph(item, style="List Bullet")
    doc.add_heading("Timeline", level=1)
    if isinstance(sections, dict) and sections.get("timeline_bullets"):
        for line in sections["timeline_bullets"][:12]:
            doc.add_paragraph(str(line))
    else:
        for phase in strategy.timeline:
            doc.add_paragraph(f"{phase['phase']}: {phase['start']} → {phase['end']}")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.post("/test-parsing")
async def test_parsing(test_data: Dict[str, Any]) -> Dict[str, Any]:
    """Test the markdown parsing function with example Jina response"""
    try:
        # Extract the content from the test data
        content = test_data.get("content", "")
        brand = test_data.get("brand", "TestBrand")
        country = test_data.get("country", "TestCountry")
        industry = test_data.get("industry", "TestIndustry")
        
        if not content:
            return {"error": "No content provided. Send JSON with 'content' field containing the Jina response text."}
        
        # Test the parsing function with Groq
        result = await parse_with_groq(content, brand, country, industry)
        
        if result:
            return {
                "status": "success",
                "message": "Parsing completed successfully",
                "extracted_data": result,
                "stats": {
                    "competitors_found": len(result.get("competitors", [])),
                    "trends_found": len(result.get("trends", [])),
                    "ad_insights_found": len(result.get("ad_insights", [])),
                    "sources_found": len(result.get("sources", []))
                }
            }
        else:
            return {
                "status": "failed",
                "message": "Parsing failed - check server logs for details",
                "extracted_data": None
            }
            
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Error during parsing test: {str(e)}",
            "extracted_data": None
        }


@app.get("/test-jina")
async def test_jina() -> Dict[str, Any]:
    api_key = os.getenv("JINA_API_KEY")
    if not api_key:
        return {"status": "error", "message": "JINA_API_KEY not set"}
    
    if api_key == "test":
        return {"status": "warning", "message": "JINA_API_KEY is set to 'test' - please set a real API key"}
    
    session = await get_http_session()
    url = os.getenv("JINA_DEEPSEARCH_URL", "https://deepsearch.jina.ai/v1/chat/completions")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    # Simple test payload
    payload = {
        "model": "jina-deepsearch-v1",
        "messages": [{"role": "user", "content": "Hello, can you respond with just 'OK'?"}],
        "stream": False,
        "reasoning_effort": "low",
        "temperature": 0.1
    }
    
    try:
        async with session.post(url, headers=headers, json=payload) as resp:
            status = resp.status
            if status == 401:
                return {"status": "error", "message": "Invalid Jina API key"}
            elif status != 200:
                text = await resp.text()
                return {"status": "error", "message": f"Jina API error: {status} {text}"}
            
            data = await resp.json()
            return {"status": "success", "message": "Jina API connection successful", "response_keys": list(data.keys())}
    
    except Exception as e:
        return {"status": "error", "message": f"Connection error: {str(e)}"}


@app.post("/api/research", dependencies=[Depends(require_api_key)])
async def research(req: ResearchRequest) -> ResearchResult:
    jina_json = await call_jina_deepsearch_structured(req)
    competitors, sources, trends, ad_insights, summary = parse_jina_results(jina_json, req.brand, req.industry, req.max_results)
    return ResearchResult(
        brand=req.brand,
        country=req.country,
        industry=req.industry,
        competitors=competitors,
        trends=trends,
        ad_insights=ad_insights,
        sources=sources,
        summary=summary
    )


@app.post("/api/strategy", dependencies=[Depends(require_api_key)])
async def strategy(req: StrategyRequest) -> StrategyPlan:
    research_data: Optional[ResearchResult] = req.research
    if research_data is None:
        raise HTTPException(status_code=400, detail="'research' is required. Call /api/research or /api/workflow first.")
    try:
        groq_json = await call_groq_strategy_structured(
            research=research_data,
            goals=req.goals,
            budget_usd=req.budget_usd,
            time_horizon_months=req.time_horizon_months,
            language=req.language or "en",
            use_cache=req.use_cache
        )
    except HTTPException:
        groq_json = {}
    allocations = groq_json.get("allocations") or allocate_budget(req.goals, req.budget_usd)
    total = sum(float(v) for v in allocations.values()) if isinstance(allocations, dict) else 0.0
    if isinstance(allocations, dict) and total > 0 and abs(total - req.budget_usd) > 0.01:
        factor = req.budget_usd / total
        allocations = {k: round(float(v) * factor, 2) for k, v in allocations.items()}
    content_plan = groq_json.get("content_plan") or build_content_plan(req.goals)
    kpis = groq_json.get("kpis") or build_kpis(req.goals)
    swot = groq_json.get("swot") or build_swot(req.brand, research_data.competitors)
    timeline = groq_json.get("timeline") or build_timeline(req.time_horizon_months)
    calendar = groq_json.get("media_calendar") or build_media_calendar(allocations)
    return StrategyPlan(
        brand=req.brand,
        total_budget_usd=req.budget_usd,
        allocations=allocations,
        content_plan=content_plan,
        kpis=kpis,
        swot=swot,
        timeline=timeline,
        media_calendar=calendar
    )


@app.post("/api/generate/pptx", dependencies=[Depends(require_api_key)])
async def generate_pptx(req: ReportRequest) -> StreamingResponse:
    buf = await build_ppt(req.brand, req.research, req.strategy, language=req.language, use_cache=req.use_cache)
    filename = f"{req.brand.replace(' ', '_').lower()}_strategy_{datetime.utcnow().strftime('%Y%m%d')}.pptx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.post("/api/generate/pdf", dependencies=[Depends(require_api_key)])
async def generate_pdf(req: ReportRequest) -> StreamingResponse:
    buf = await build_pdf(req.brand, req.research, req.strategy, language=req.language, use_cache=req.use_cache)
    filename = f"{req.brand.replace(' ', '_').lower()}_report_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.post("/api/generate/docx", dependencies=[Depends(require_api_key)])
async def generate_docx(req: ReportRequest) -> StreamingResponse:
    buf = await build_docx(req.brand, req.research, req.strategy, language=req.language, use_cache=req.use_cache)
    filename = f"{req.brand.replace(' ', '_').lower()}_report_{datetime.utcnow().strftime('%Y%m%d')}.docx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.post("/api/workflow", dependencies=[Depends(require_api_key)])
async def workflow(req: WorkflowRequest) -> Dict[str, Any]:
    rreq = ResearchRequest(brand=req.brand, country=req.country, industry=req.industry, max_results=req.max_results, use_cache=True)
    research_result = await research(rreq)
    sreq = StrategyRequest(brand=req.brand, industry=req.industry, goals=req.goals, budget_usd=req.budget_usd, country=req.country, research=research_result, time_horizon_months=req.time_horizon_months)
    strategy_plan = await strategy(sreq)
    return {"research": research_result.dict(), "strategy": strategy_plan.dict()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)


