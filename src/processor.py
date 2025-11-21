import os
import json
from typing import List, Dict, Optional
import pypdf
import docx
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from src.database import add_candidate, get_candidate_by_filename


# Define Pydantic model for structured output
class WorkExperience(BaseModel):
    company: str = Field(description="Company name")
    role: str = Field(description="Job title/role")
    duration: str = Field(description="Duration (e.g., '2020-2022', 'Jan 2020 - Dec 2021')")
    months_of_service: int = Field(description="Total months in this role (calculate from duration)")
    skillset: str = Field(description="Specific skills demonstrated in this role with concrete examples from description")
    tech_stack: str = Field(description="Technologies explicitly mentioned for this role")
    projects: List[str] = Field(default_factory=list, description="Key projects, achievements, or specific work mentioned")
    is_internship: bool = Field(default=False, description="True if clearly marked as internship")
    description: str = Field(description="Detailed responsibilities and achievements")
    start_date: str = Field(default="", description="Start date (extract if available)")
    end_date: str = Field(default="", description="End date (extract if available, 'Present' if current)")

class CandidateProfile(BaseModel):
    name: str = Field(description="Full name of the candidate")
    age: int = Field(description="Age of the candidate, if mentioned. If not, estimate or put 0")
    work_experience: List[WorkExperience] = Field(description="List of all work experiences in chronological order")
    
    # Aggregated summary (calculated from work experience)
    total_months_experience: int = Field(description="Sum of all months_of_service across experiences")
    total_companies: int = Field(description="Count of unique companies")
    roles_served: str = Field(description="Comma-separated list of unique roles held")
    
    # Skills
    skillset: str = Field(description="Comma-separated list of all skills mentioned anywhere")
    high_confidence_skills: str = Field(description="Skills clearly demonstrated in work experience with concrete examples")
    low_confidence_skills: str = Field(description="Skills only listed without proof in work experience")
    tech_stack: str = Field(description="Comma-separated list of all technologies from work experience")
    
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

def extract_structured_data(text: str) -> Optional[Dict]:
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("GOOGLE_API_KEY not found in environment variables.")
            return None
        
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", google_api_key=api_key, temperature=0)
        parser = PydanticOutputParser(pydantic_object=CandidateProfile)
        
        prompt = PromptTemplate(
            template="""You are an expert resume parser. Extract detailed structured information from this resume.

IMPORTANT INSTRUCTIONS FOR WORK EXPERIENCE:
1. For EACH work experience entry, calculate months_of_service by parsing the duration
2. Extract skills that are SPECIFICALLY demonstrated in each role (look for action verbs like "Built", "Developed", "Managed")
3. List technologies that are EXPLICITLY mentioned for that specific role
4. Extract key projects, achievements, or specific deliverables mentioned
5. Determine if it's an internship (look for keywords: "intern", "internship", "trainee")
6. Extract start_date and end_date if mentioned (keep format as-is, or use "Present" for current roles)

SKILL CLASSIFICATION:
- high_confidence_skills: Skills with concrete examples in work experience (e.g., "Built REST API using Python")
- low_confidence_skills: Skills only listed in a skills section without work evidence

AGGREGATED FIELDS TO CALCULATE:
- total_months_experience: Sum all months_of_service from work experiences
- total_companies: Count unique company names
- roles_served: Comma-separated list of unique job titles
- tech_stack: Aggregate all technologies from work experience entries

Resume text:
{text}

{format_instructions}
""",
            input_variables=["text"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        chain = prompt | llm | parser
        result = chain.invoke({"text": text})
        return result.dict()
    
    except Exception as e:
        print(f"Error extracting structured data: {e}")
        return None

def process_resumes(folder_path: str):
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} not found.")
        return
    
    files = os.listdir(folder_path)
    for filename in files:
        if filename.endswith('.pdf') or filename.endswith('.docx'):
            # Check if already processed
            existing = get_candidate_by_filename(filename)
            if existing:
                print(f"Skipping {filename}, already processed.")
                continue
            
            filepath = os.path.join(folder_path, filename)
            print(f"Processing {filename}...")
            
            # Extract text
            if filename.endswith('.pdf'):
                text = extract_text_from_pdf(filepath)
            else:
                text = extract_text_from_docx(filepath)
            
            # Extract structured data
            data = extract_structured_data(text)
            
            if data:
                data['filename'] = filename
                add_candidate(data)
                print(f"Added {data.get('name', 'Unknown')} to database.")
            else:
                print(f"Failed to extract structured data for {filename}")
