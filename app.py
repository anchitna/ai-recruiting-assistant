import os
import tempfile
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from workflow.graph import RecruitingWorkflow

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Recruiting Assistant",
    description="An AI-powered recruiting assistant that evaluates candidates against job descriptions",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create the workflow instance
workflow = RecruitingWorkflow()

class EvaluationRequest(BaseModel):
    candidate_name: str
    job_description: Optional[str] = None

class EvaluationResponse(BaseModel):
    candidate_name: str
    fit_score: str
    reasoning: str
    recommendations: List[str]
    detailed_analysis: Dict[str, Any]

@app.post("/api/evaluate_resume", response_model=EvaluationResponse)
async def evaluate_resume(
    candidate_name: str = Form(...),
    resume_file: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
    job_description_file: Optional[UploadFile] = File(None)
):
    """
    Evaluate a candidate's resume against a job description.
    
    Parameters:
    - candidate_name: Name of the candidate
    - resume_file: PDF or DOCX resume file
    - job_description: Optional job description text
    - job_description_file: Optional PDF or DOCX job description file
    
    Returns:
    - Evaluation result including fit score and detailed analysis
    """
    logger.info(f"Received evaluation request for candidate: {candidate_name}")
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(resume_file.filename)[1]) as temp_resume:
            resume_content = await resume_file.read()
            temp_resume.write(resume_content)
            resume_path = temp_resume.name
        
        job_desc_text = job_description
        job_desc_path = None
        
        if job_description_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(job_description_file.filename)[1]) as temp_job:
                job_desc_content = await job_description_file.read()
                temp_job.write(job_desc_content)
                job_desc_path = temp_job.name
        
        result = workflow.run(
            candidate_name=candidate_name,
            resume_file_path=resume_path,
            job_description_path=job_desc_path,
            job_description_text=job_desc_text
        )
        
        if os.path.exists(resume_path):
            os.unlink(resume_path)
        if job_desc_path and os.path.exists(job_desc_path):
            os.unlink(job_desc_path)
        
        if "error" in result and result["error"]:
            raise Exception(result["error"])
        
        if "final_decision" not in result:
            raise Exception("Evaluation failed to produce a final decision")
        
        final_decision = result["final_decision"]
        
        response = {
            "candidate_name": candidate_name,
            "fit_score": final_decision["fit_score"],
            "reasoning": final_decision["reasoning"],
            "recommendations": final_decision["recommendations"],
            "detailed_analysis": {
                "candidate_profile": result.get("candidate_profile", {}),
                "job_requirements": result.get("job_requirements", {}),
                "comparison_result": result.get("comparison_result", {}),
                "web_research_data": result.get("web_research_data", {})
            }
        }
        
        logger.info(f"Successfully evaluated candidate: {candidate_name} - Fit score: {final_decision['fit_score']}")
        
        return response
    
    except Exception as e:
        logger.error(f"Error evaluating resume: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error evaluating resume: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)