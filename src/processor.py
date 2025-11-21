import os
import json
from typing import List, Dict
import pypdf
import docx
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from src.database import add_candidate, get_candidate_by_filename


# Define Pydantic model for structured output
class WorkExperience(BaseModel):
    company: str = Field(description="Name of the company")
    role: str = Field(description="Job title")
    duration: str = Field(description="Duration of employment")
    description: str = Field(description="Brief description of responsibilities")

class CandidateProfile(BaseModel):
    name: str = Field(description="Full name of the candidate")
    age: int = Field(description="Age of the candidate, if mentioned. If not, estimate or put 0")
    skillset: str = Field(description="Comma-separated list of all skills mentioned")
    high_confidence_skills: str = Field(description="Comma-separated skills that are clearly demonstrated in work experience with concrete examples (e.g., 'Built X using Y', 'Managed Z'). Only include skills with evidence of actual usage.")
    low_confidence_skills: str = Field(description="Comma-separated skills that are only listed without proof or context in work experience. These are claimed but not demonstrated.")
    years_of_experience: int = Field(description="Total years of experience")
    work_experience: List[WorkExperience] = Field(description="List of work experiences")
    tech_stack: str = Field(description="Comma-separated list of technologies used, prioritize those from work experience")
    general_proficiency: str = Field(description="General proficiency level (e.g., Junior, Mid, Senior, Lead)")
    ai_summary: str = Field(description="A brief AI-generated summary of the candidate's profile")

def extract_text_from_pdf(filepath: str) -> str:
    text = ""
    try:
        with open(filepath, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text()
    except Exception as e:
        print(f"Error reading PDF {filepath}: {e}")
    return text

def extract_text_from_docx(filepath: str) -> str:
    text = ""
    try:
        doc = docx.Document(filepath)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"Error reading DOCX {filepath}: {e}")
    return text

def extract_data_with_gemini(text: str) -> Dict:
    if not text:
        return {}
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY not found in environment variables.")
        return {}

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key=api_key)
    
    parser = PydanticOutputParser(pydantic_object=CandidateProfile)
    
    prompt = PromptTemplate(
        template="Extract the following information from the resume text.\n{format_instructions}\n\nResume Text:\n{text}",
        input_variables=["text"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({"text": text})
        return result.dict()
    except Exception as e:
        print(f"Error extracting data with Gemini: {e}")
        return {}

def process_resumes(folder_path: str):
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} does not exist.")
        return

    for filename in os.listdir(folder_path):
        filepath = os.path.join(folder_path, filename)
        if not os.path.isfile(filepath):
            continue
            
        if filename.lower().endswith(('.pdf', '.docx')):
            # Check if already processed
            if get_candidate_by_filename(filename):
                print(f"Skipping {filename}, already processed.")
                continue
            
            print(f"Processing {filename}...")
            text = ""
            if filename.lower().endswith('.pdf'):
                text = extract_text_from_pdf(filepath)
            elif filename.lower().endswith('.docx'):
                text = extract_text_from_docx(filepath)
            
            if text:
                data = extract_data_with_gemini(text)
                if data:
                    data['filename'] = filename
                    add_candidate(data)
                    print(f"Added {filename} to database.")
                else:
                    print(f"Failed to extract structured data for {filename}")
