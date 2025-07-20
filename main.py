from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import TypedDict, List, Any
from langgraph.graph import StateGraph
from openai import OpenAI
import requests
import feedparser
from dotenv import load_dotenv
import os

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()
api_key = os.getenv("API_KEY")

if not api_key:
    raise ValueError("❗ API_KEY not found. Please check your .env file.")

client = OpenAI(api_key=api_key)

class ResearchState(TypedDict):
    user_query: str
    arxiv_results: List[Any]
    openalex_results: List[Any]
    merged_results: List[Any]
    summary: str
    critique: str
    verification: str
    final_output: str
    status: str
    rewrite_count: int

# Agents
def search_arxiv(query, max_results=3):
    url = f'http://export.arxiv.org/api/query?search_query={query}&start=0&max_results={max_results}'
    feed = feedparser.parse(requests.get(url).text)
    return [{'title': entry.title, 'summary': entry.summary, 'link': entry.link} for entry in feed.entries]

def search_openalex(query, max_results=3):
    url = f"https://api.openalex.org/works?search={query}&per-page={max_results}"
    response = requests.get(url).json()
    return [{'title': item.get('display_name', 'No Title'), 'summary': item.get('abstract_inverted_index', {}), 'link': item.get('id', 'No Link')} for item in response.get('results', [])]

def merge_results(arxiv_results, openalex_results):
    return arxiv_results + openalex_results

def summarize_papers(papers):
    content = "\n\n".join([f"Title: {p['title']}\nSummary: {p['summary']}" for p in papers])
    prompt = (
        "You are a professional research assistant tasked with analyzing and summarizing academic research papers.\n\n"
        "Carefully review the following research papers and generate a comprehensive general summary that highlights:\n"
        "- The most significant opportunities, advancements, or contributions discussed across the papers.\n"
        "- The key challenges, limitations, or concerns raised collectively in the research.\n"
        "- The most relevant real-world applications, case studies, or practical implications mentioned.\n\n"
        "Write the summary in clear, professional, and concise language suitable for a research-oriented audience.\n"
        "Organize the summary in natural, flowing paragraphs grouped by topic — not by individual papers.\n"
        "Do not list papers separately and do not invent information not found in the content.\n\n"
        "Here are the research papers for your analysis:\n\n"
        f"{content}"
    )
    response = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
    return response.choices[0].message.content

def critique_summary(summary_text):
    prompt = (
        "You are a critical reviewer of academic research summaries.\n\n"
        "Carefully review the following summarized research papers.\n"
        "Provide feedback on completeness, accuracy, clarity, and missing details.\n"
        "If a summary lacks information, suggest improvements.\n\n"
        "Summary:\n\n"
        f"{summary_text}"
    )
    response = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
    critique = response.choices[0].message.content
    if any(k in critique.lower() for k in ["missing", "improve", "bias", "error"]):
        return critique, 'needs_rewrite'
    return critique, 'approved'

def verify_summary(summary_text):
    prompt = f"Fact-check the following summary. Highlight factual inaccuracies:\n\n{summary_text}"
    response = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
    return response.choices[0].message.content

def compose_final_answer(summary, papers):
    paper_list = "\n".join([f"- {p['title']}" for p in papers])
    return f"{summary}\n\nSummarized Research Papers:\n{paper_list}"

# Graph Nodes
def search_arxiv_node(state: ResearchState) -> ResearchState:
    state['arxiv_results'] = search_arxiv(state['user_query'])
    return state

def search_openalex_node(state: ResearchState) -> ResearchState:
    state['openalex_results'] = search_openalex(state['user_query'])
    return state

def merge_results_node(state: ResearchState) -> ResearchState:
    state['merged_results'] = merge_results(state['arxiv_results'], state['openalex_results'])
    return state

def summarizer_node(state: ResearchState) -> ResearchState:
    state['summary'] = summarize_papers(state['merged_results'])
    return state

def critic_node(state: ResearchState) -> ResearchState:
    critique, status = critique_summary(state['summary'])
    state['critique'] = critique
    if state.get('rewrite_count', 0) >= 2:
        state['status'] = 'approved'
    else:
        state['status'] = status
    if status == 'needs_rewrite':
        state['rewrite_count'] = state.get('rewrite_count', 0) + 1
    return state

def verifier_node(state: ResearchState) -> ResearchState:
    state['verification'] = verify_summary(state['summary'])
    return state

def final_composer_node(state: ResearchState) -> ResearchState:
    state['final_output'] = compose_final_answer(state['summary'], state['merged_results'])
    return state

def check_critique_status(state: ResearchState) -> str:
    return state['status']

# Build LangGraph
graph = StateGraph(ResearchState)
graph.add_node('SearchArxiv', search_arxiv_node)
graph.add_node('SearchOpenAlex', search_openalex_node)
graph.add_node('MergeResults', merge_results_node)
graph.add_node('SummarizerAgent', summarizer_node)
graph.add_node('CriticAgent', critic_node)
graph.add_node('VerifierAgent', verifier_node)
graph.add_node('FinalComposer', final_composer_node)

graph.add_edge('__start__', 'SearchArxiv')
graph.add_edge('SearchArxiv', 'SearchOpenAlex')
graph.add_edge('SearchOpenAlex', 'MergeResults')
graph.add_edge('MergeResults', 'SummarizerAgent')
graph.add_edge('SummarizerAgent', 'CriticAgent')
graph.add_conditional_edges('CriticAgent', check_critique_status, {'needs_rewrite': 'SummarizerAgent', 'approved': 'VerifierAgent'})
graph.add_edge('VerifierAgent', 'FinalComposer')

app_graph = graph.compile()

# ----------------- FastAPI Endpoint -----------------
class QueryRequest(BaseModel):
    query: str

@app.post("/summarize")
def summarize_research(request: QueryRequest):
    try:
        initial_state: ResearchState = {
            'user_query': request.query,
            'arxiv_results': [],
            'openalex_results': [],
            'merged_results': [],
            'summary': '',
            'critique': '',
            'verification': '',
            'final_output': '',
            'status': '',
            'rewrite_count': 0
        }
        result = app_graph.invoke(initial_state)
        return {"summary": result['final_output']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
