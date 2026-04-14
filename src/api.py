from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from src.processor import process_resumes
from src.database import get_all_candidates
import os

load_dotenv()

app = FastAPI(title="Resume Screening Agent API")


class CandidateResponse(BaseModel):
    filename: Optional[str] = None
    name: Optional[str] = None
    general_proficiency: Optional[str] = None
    tech_stack: Optional[str] = None
    ai_summary: Optional[str] = None


@app.post("/process")
def trigger_processing(background_tasks: BackgroundTasks, directory: str = "resumes"):
    if not os.path.exists(directory):
        raise HTTPException(status_code=404, detail=f"Directory {directory} not found")

    background_tasks.add_task(process_resumes, directory)
    return {"message": f"Processing started for directory: {directory}"}


@app.get("/candidates", response_model=List[CandidateResponse])
def list_candidates():
    return get_all_candidates()


@app.get("/")
def read_root():
    return {"message": "Resume Screening Agent API is running"}
