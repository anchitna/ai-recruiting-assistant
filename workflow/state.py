from typing import TypedDict, Dict, List, Optional, Union, Any, Literal

class ResumeData(TypedDict, total=False):
    education: List[Dict[str, str]]
    work_experience: List[Dict[str, str]]
    skills: List[str]
    certifications: List[str]
    publications: List[str]
    projects: List[str]
    raw_text: str

class JobRequirements(TypedDict, total=False):
    core_skills: List[str]
    preferred_skills: List[str]
    experience_level: str
    education_requirements: List[str]
    industry_domain: str
    raw_text: str

class WebResearchData(TypedDict, total=False):
    github_info: Optional[Dict[str, Any]]
    blog_posts: List[Dict[str, str]]
    conference_appearances: List[Dict[str, str]]
    news_mentions: List[Dict[str, str]]
    social_profiles: Dict[str, str]
    raw_data: Dict[str, Any]

class SkillMatch(TypedDict):
    skill: str
    match_level: Literal["High", "Medium", "Low", "None"]
    details: str

class ExperienceMatch(TypedDict):
    area: str
    match_level: Literal["High", "Medium", "Low", "None"]
    details: str

class EducationMatch(TypedDict):
    requirement: str
    match_level: Literal["High", "Medium", "Low", "None"]
    details: str

class ComparisonResult(TypedDict, total=False):
    skill_matches: List[SkillMatch]
    experience_matches: List[ExperienceMatch]
    education_matches: List[EducationMatch]
    overall_skill_match: Literal["Strong", "Moderate", "Weak"]
    overall_experience_match: Literal["Strong", "Moderate", "Weak"]
    overall_education_match: Literal["Strong", "Moderate", "Weak"]

class FinalDecision(TypedDict):
    fit_score: Literal["Strong Fit", "Moderate Fit", "Not a Fit"]
    reasoning: str
    recommendations: List[str]

class CandidateProfile(TypedDict):
    name: str
    resume_data: ResumeData
    web_research: WebResearchData
    
class RecruitingState(TypedDict, total=False):
    # Input data
    candidate_name: str
    resume_file_path: str
    job_description_path: Optional[str]
    job_description_text: Optional[str]
    
    # Github profile
    github_info: Optional[Dict[str, str]]
    github_research_data: Optional[Dict[str, Any]]
    
    # Processed data
    resume_data: ResumeData
    job_requirements: JobRequirements
    web_research_data: WebResearchData
    
    # Analysis results
    candidate_profile: CandidateProfile
    comparison_result: ComparisonResult
    final_decision: FinalDecision
    
    # Error handling
    error: Optional[str]
    
    # Workflow control
    completed_nodes: List[str]