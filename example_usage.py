import os
import json
import logging

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Simple example of using the recruiting assistant."""
    from workflow.graph import RecruitingWorkflow
    
    if "OPENAI_API_KEY" not in os.environ:
        logger.error("OPENAI_API_KEY environment variable not set")
        return
    
    resume_path = "examples/Anchit_Narayan_Resume_Github.pdf" 
    job_description_path = "examples/DoubleO_Job_Description.docx"
    
    workflow = RecruitingWorkflow()
    
    result = workflow.run(
        candidate_name="Anchit Narayan",
        resume_file_path=resume_path,
        job_description_path=job_description_path
    )
    
    if "error" in result and result["error"]:
        logger.error(f"Evaluation failed: {result['error']}")
        return
    
    logger.info(f"Evaluation completed for: Anchit Narayan")
    logger.info(f"Fit score: {result['final_decision']['fit_score']}")
    logger.info(f"Reasoning: {result['final_decision']['reasoning']}")
    logger.info(f"Recommendations: {', '.join(result['final_decision']['recommendations'])}")
    
    with open("evaluation_result_without_github.json", "w") as f:
        json.dump(result, f, indent=2)
    
    logger.info("Detailed results saved to evaluation_result.json")

if __name__ == "__main__":
    main()