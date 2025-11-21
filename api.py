from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from agent import ResumeScreeningAgent
from processor import process_resumes
from database import get_all_candidates, init_db
import os

app = FastAPI(title="Resume Screening Agent API")

# Initialize DB on startup
@app.on_event("startup")
def startup_event():
    init_db()

class ScreenRequest(BaseModel):
    role: str
    seniority: str
    tech_stack: str

class CandidateResponse(BaseModel):
    filename: Optional[str] = None
    name: Optional[str] = None
    score: Optional[float] = None
    general_proficiency: Optional[str] = None
    tech_stack: Optional[str] = None
    ai_summary: Optional[str] = None

class ScreenResponse(BaseModel):
    shortlist: List[CandidateResponse]
    longlist: List[CandidateResponse]

@app.post("/screen", response_model=ScreenResponse)
def screen_candidates(request: ScreenRequest):
    agent = ResumeScreeningAgent()
    results = agent.screen_candidates(request.role, request.seniority, request.tech_stack)
    return results

@app.post("/process")
def trigger_processing(background_tasks: BackgroundTasks, directory: str = "resumes"):
    if not os.path.exists(directory):
        raise HTTPException(status_code=404, detail=f"Directory {directory} not found")
    
    background_tasks.add_task(process_resumes, directory)
    return {"message": f"Processing started for directory: {directory}"}

@app.get("/candidates")
def list_candidates():
    return get_all_candidates()

@app.get("/")
def read_root():
    return {"message": "Resume Screening Agent API is running"}
