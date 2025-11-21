import os
from docx import Document

def create_dummy_resume(filename, content):
    doc = Document()
    doc.add_paragraph(content)
    doc.save(filename)

if __name__ == "__main__":
    if not os.path.exists("resumes"):
        os.makedirs("resumes")
    
    resume1 = """
    John Doe
    Senior Backend Engineer
    
    Summary:
    Experienced backend engineer with 8 years of experience in Python, Django, and AWS.
    
    Skills: Python, Django, Flask, AWS, Docker, Kubernetes, PostgreSQL, Redis.
    
    Experience:
    Senior Backend Engineer at Tech Corp (2020-Present)
    - Built scalable microservices using Python and FastAPI.
    - Managed AWS infrastructure.
    
    Backend Developer at Startup Inc (2016-2020)
    - Developed REST APIs using Django.
    """
    
    resume2 = """
    Jane Smith
    Frontend Developer
    
    Summary:
    Creative frontend developer with 3 years of experience in React and TypeScript.
    
    Skills: React, TypeScript, JavaScript, HTML, CSS, Redux, Webpack.
    
    Experience:
    Frontend Developer at Web Solutions (2021-Present)
    - Built responsive web applications using React.
    """
    
    create_dummy_resume("resumes/john_doe.docx", resume1)
    create_dummy_resume("resumes/jane_smith.docx", resume2)
    print("Created dummy resumes.")
