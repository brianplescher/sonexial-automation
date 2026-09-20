from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import json
import asyncio
import os
import time
from openai import AsyncOpenAI

app = FastAPI(title="Sonexial Agentic GEO Scanner API")

# CORS for your Next.js Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://www.sonexial.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI Client for the Agentic Layer
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

class ScanRequest(BaseModel):
    url: HttpUrl

class AgenticPitchRequest(BaseModel):
    url: str
    score: int
    critical_failures: list
    recommendations: list
    author_name: str = Field(default="Author", description="Name of the author if known")

class GEOReport(BaseModel):
    url: str
    status: str
    score: int
    geo_grade: str
    execution_time: str
    checks: dict
    critical_failures: list
    recommendations: list

async def fetch_urls(client: httpx.AsyncClient, url: str):
    """Fetches HTML, llms.txt, and robots.txt concurrently for maximum speed."""
    parsed = urlparse(str(url))
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    llms_url = urljoin(base_url, "/llms.txt")
    robots_url = urljoin(base_url, "/robots.txt")
    
    headers = {"User-Agent": "Mozilla/5.0 (Sonexial GEO Scanner 1.0)"}
    
    # Run all 3 network requests at the exact same time
    html_task = client.get(str(url), headers=headers, follow_redirects=True)
    llms_task = client.get(llms_url, headers=headers, follow_redirects=True)
    robots_task = client.get(robots_url, headers=headers, follow_redirects=True)
    
    return await asyncio.gather(html_task, llms_task, robots_task, return_exceptions=True)

def analyze_html(html_text: str):
    # lxml is significantly faster than the default html.parser
    soup = BeautifulSoup(html_text, "lxml") 
    checks = {}
    score = 0
    critical_failures = []
    recommendations = []

    # 1. JSON-LD Schema (Sonexial Stack: Book, Person, FAQPage)
    schemas = soup.find_all("script", type="application/ld+json")
    has_book, has_person, has_faq = False, False, False
    
    for script in schemas:
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    t = item.get("@type")
                    if t == "Book": has_book = True
                    if t == "Person": has_person = True
                    if t == "FAQPage": has_faq = True
        except: pass
        
    checks["schema_markup"] = {"book": has_book, "person": has_person, "faq": has_faq}
    
    if has_book and has_person:
        score += 30
    elif has_book or has_person:
        score += 15
        recommendations.append("Missing complete Author/Book entity mapping in Schema.")
    else:
        critical_failures.append("Missing core JSON-LD Schema (Person/Book).")
        recommendations.append("Add 'Person' and 'Book' JSON-LD schema to define your entity.")

    # 2. Semantic HTML Hierarchy
    h1_tags = soup.find_all("h1")
    h2_tags = soup.find_all("h2")
    checks["semantic_html"] = {"h1_count": len(h1_tags), "h2_count": len(h2_tags)}
    
    if len(h1_tags) == 1 and len(h2_tags) > 0:
        score += 15
    else:
        critical_failures.append("Poor Semantic Hierarchy (Needs exactly one H1).")
        recommendations.append("Fix H1/H2 hierarchy so AI can parse your main topics.")

    # 3. Entity Connectivity (Amazon, Goodreads, BookBub)
    links = [a.get("href", "").lower() for a in soup.find_all("a", href=True)]
    has_amazon = any("amazon" in l or "amzn" in l for l in links)
    has_goodreads = any("goodreads" in l for l in links)
    
    checks["entity_links"] = {"amazon": has_amazon, "goodreads": has_goodreads}
    if has_amazon or has_goodreads:
        score += 15
    else:
        recommendations.append("Add outbound entity links to Amazon/Goodreads to connect your knowledge graph.")

    # 4. Open Graph / Meta
    og_tags = soup.find_all("meta", property=lambda x: x and str(x).startswith("og:"))
    checks["open_graph"] = len(og_tags) >= 3
    if len(og_tags) >= 3:
        score += 10
    else:
        recommendations.append("Add Open Graph tags for accurate social and AI previews.")

    return score, checks, critical_failures, recommendations

def analyze_files(llms_res, robots_res):
    score = 0
    checks = {}
    critical_failures = []
    recommendations = []

    # llms.txt Check
    if isinstance(llms_res, httpx.Response) and llms_res.status_code == 200 and len(llms_res.text) > 50:
        checks["llms_txt"] = True
        score += 20
    else:
        checks["llms_txt"] = False
        critical_failures.append("Missing llms.txt AI roadmap file.")
        recommendations.append("Create an llms.txt file to guide AI crawlers to your key data.")

    # robots.txt AI Bot Check (Crucial for GEO)
    checks["ai_bot_access"] = {"blocked": []}
    if isinstance(robots_res, httpx.Response) and robots_res.status_code == 200:
        content = robots_res.text.lower()
        ai_bots = ["gptbot", "claudebot", "perplexitybot", "anthropic-ai"]
        blocked = []
        
        for bot in ai_bots:
            if f"user-agent: {bot}" in content and "disallow: /" in content:
                blocked.append(bot)
                
        checks["ai_bot_access"]["blocked"] = blocked
        if blocked:
            score -= 20 # Massive GEO penalty
            critical_failures.append(f"CRITICAL: Blocking AI crawlers ({', '.join(blocked)}).")
            
    return score, checks, critical_failures, recommendations

@app.post("/scan", response_model=GEOReport)
async def scan_website(request: ScanRequest):
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        html_res, llms_res, robots_res = await fetch_urls(client, request.url)
        
        if isinstance(html_res, Exception) or not isinstance(html_res, httpx.Response):
            raise HTTPException(status_code=400, detail="Failed to fetch the target URL.")
            
        # Analyze HTML
        html_score, html_checks, html_fails, html_recs = analyze_html(html_res.text)
        
        # Analyze Files
        file_score, file_checks, file_fails, file_recs = analyze_files(llms_res, robots_res)
        
        # Aggregate
        total_score = max(0, min(100, html_score + file_score))
        
        # Grading
        if total_score >= 80: grade = "A (AI-Ready)"
        elif total_score >= 60: grade = "B (Needs Tuning)"
        elif total_score >= 40: grade = "C (Invisible to AI)"
        else: grade = "F (Ghost in the Machine)"

        execution_time = f"{time.time() - start_time:.2f}s"

        return GEOReport(
            url=str(request.url),
            status="success",
            score=total_score,
            geo_grade=grade,
            execution_time=execution_time,
            checks={**html_checks, **file_checks},
            critical_failures=html_fails + file_fails,
            recommendations=html_recs + file_recs
        )

@app.post("/generate-pitch")
async def generate_agentic_pitch(request: AgenticPitchRequest):
    """
    Agentic Endpoint: Takes the scan data and uses an LLM to write 
    the personalized 'Brian from Sonexial' outreach email automatically.
    """
    prompt = f"""
    You are Brian Plescher, founder of Sonexial. You are writing a short, punchy, 
    empathetic email to an author ({request.author_name}) who just ran a Free GEO Audit on {request.url}.
    
    Their GEO Score is {request.score}/100.
    Critical Failures: {request.critical_failures}
    Recommendations: {request.recommendations}
    
    Sonexial builds done-for-you author websites structured for AI-era discovery (Generative Engine Optimization).
    Explain briefly why AI (ChatGPT, Perplexity) is ignoring their site based on their specific failures (mention llms.txt, Schema, or Entity Links).
    Pitch the appropriate Sonexial package (e.g., Author Foundation for $1,500 or Author Platform for $3,000) as the exact solution to fix these errors.
    
    Keep it under 200 words. Professional, authoritative, but peer-to-peer (author to author).
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return {"email_draft": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Generation failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    