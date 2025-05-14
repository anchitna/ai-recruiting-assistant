import logging
from typing import Dict, Any, Optional

from langgraph.graph import END, StateGraph
from langchain_openai import ChatOpenAI

from workflow.state import RecruitingState
from workflow.nodes import RecruitingNodes

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RecruitingWorkflow:
    def __init__(self, model_name: str = "gpt-4o"):
        """Initialize the recruiting workflow.
        
        Args:
            model_name: Name of the language model to use
        """
        self.model = ChatOpenAI(model_name=model_name, temperature=0)
        self.nodes = RecruitingNodes(self.model)
        
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the workflow graph.
        
        Returns:
            StateGraph: The workflow graph
        """
        workflow = StateGraph(RecruitingState)
        
        workflow.add_node("parse_resume", self.nodes.parse_resume)
        workflow.add_node("parse_job_description", self.nodes.parse_job_description)
        workflow.add_node("github_research", self.nodes.github_research)
        workflow.add_node("web_research", self.nodes.web_research)
        workflow.add_node("create_candidate_profile", self.nodes.create_candidate_profile)
        workflow.add_node("compare_candidate_to_job", self.nodes.compare_candidate_to_job)
        workflow.add_node("generate_final_decision", self.nodes.generate_final_decision)
        
        workflow.add_edge("parse_resume", "parse_job_description")
        workflow.add_edge("github_research", "web_research")
        workflow.add_edge("web_research", "create_candidate_profile")
        workflow.add_edge("create_candidate_profile", "compare_candidate_to_job")
        workflow.add_edge("compare_candidate_to_job", "generate_final_decision")
        workflow.add_edge("generate_final_decision", END)
        
        workflow.set_entry_point("parse_resume")
        
        workflow.add_conditional_edges(
            "parse_resume",
            self._check_error,
            {
                "continue": "parse_job_description",
                "error": END
            }
        )
        
        workflow.add_conditional_edges(
            "parse_job_description",
            self._check_github_info,
            {
                "has_github_info": "github_research",
                "no_github_info": "web_research",
                "error": END
            }
        )
        
        workflow.add_conditional_edges(
            "github_research",
            self._check_error,
            {
                "continue": "web_research",
                "error": END
            }
        )
        
        workflow.add_conditional_edges(
            "web_research",
            self._check_error,
            {
                "continue": "create_candidate_profile",
                "error": END
            }
        )
        
        workflow.add_conditional_edges(
            "create_candidate_profile",
            self._check_error,
            {
                "continue": "compare_candidate_to_job",
                "error": END
            }
        )
        
        workflow.add_conditional_edges(
            "compare_candidate_to_job",
            self._check_error,
            {
                "continue": "generate_final_decision",
                "error": END
            }
        )
        
        return workflow.compile()
    
    def _check_error(self, state: RecruitingState) -> str:
        """Check if there was an error in the previous node.
        
        Args:
            state: Current state
            
        Returns:
            "error" if there was an error, "continue" otherwise
        """
        if "error" in state and state["error"]:
            return "error"
        return "continue"
    
    def _check_github_info(self, state: RecruitingState) -> str:
        """Check if GitHub info is available in the state.
        
        Args:
            state: Current state
            
        Returns:
            "has_github_info" if GitHub info exists, "no_github_info" otherwise, "error" if there was an error
        """
        if "error" in state and state["error"]:
            return "error"
        
        if "github_info" in state and state["github_info"]:
            logger.info("GitHub information found, routing to github_research node")
            return "has_github_info"
        else:
            logger.info("No GitHub information found, skipping github_research node")
            return "no_github_info"
    
    def run(self, 
            candidate_name: str, 
            resume_file_path: str, 
            job_description_path: Optional[str] = None,
            job_description_text: Optional[str] = None) -> RecruitingState:
        """Run the recruiting workflow.
        
        Args:
            candidate_name: Name of the candidate
            resume_file_path: Path to the resume file
            job_description_path: Path to the job description file
            job_description_text: Job description text
            
        Returns:
            Final state with evaluation results
        """
        logger.info(f"Starting recruiting workflow for candidate: {candidate_name}")
        
        state: RecruitingState = {
            "candidate_name": candidate_name,
            "resume_file_path": resume_file_path,
            "completed_nodes": []
        }
        
        if job_description_path:
            state["job_description_path"] = job_description_path
        if job_description_text:
            state["job_description_text"] = job_description_text
        
        try:
            final_state = self.workflow.invoke(state)
            
            logger.info(f"Completed recruiting workflow for candidate: {candidate_name}")
            
            return final_state
        except Exception as e:
            logger.error(f"Error running recruiting workflow: {str(e)}")
            state["error"] = f"Workflow execution error: {str(e)}"
            return state