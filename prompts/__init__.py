from pathlib import Path
from prompts.prompt_loader import load_prompt

# Define base path
PROMPTS_DIR = Path(__file__).parent

# Load prompts
RESUME_ANALYSIS_PROMPT = load_prompt(PROMPTS_DIR / "resume_analysis.txt")
JOB_ANALYSIS_PROMPT = load_prompt(PROMPTS_DIR / "job_analysis.txt")
WEB_RESEARCH_PROMPT = load_prompt(PROMPTS_DIR / "web_research.txt")
COMPARISON_PROMPT = load_prompt(PROMPTS_DIR / "comparison.txt")
FINAL_DECISION_PROMPT = load_prompt(PROMPTS_DIR / "final_decision.txt")
GITHUB_ANALYSIS_PROMPT = load_prompt(PROMPTS_DIR / "github_analysis.txt")

# Export all prompts
__all__ = [
    "RESUME_ANALYSIS_PROMPT",
    "JOB_ANALYSIS_PROMPT",
    "WEB_RESEARCH_PROMPT",
    "COMPARISON_PROMPT",
    "FINAL_DECISION_PROMPT",
    "GITHUB_ANALYSIS_PROMPT",
]