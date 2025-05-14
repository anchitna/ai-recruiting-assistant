from typing import Dict, Optional
import json
import logging
import traceback

from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults

from workflow.state import RecruitingState, ResumeData, JobRequirements, WebResearchData, ComparisonResult, FinalDecision
from utils.document_parser import DocumentParser
from utils.github_extractor import GitHubExtractor
from utils.github_scraper import GithubScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RecruitingNodes:
    def __init__(self, model: ChatOpenAI):
        """Initialize the recruiting assistant nodes.
        
        Args:
            model: The language model to use for analysis
        """
        self._model = model
        self._search_tool = TavilySearchResults(k=5)
        self._github_scraper = GithubScraper()
        
        from prompts import (
            RESUME_ANALYSIS_PROMPT,
            JOB_ANALYSIS_PROMPT,
            WEB_RESEARCH_PROMPT,
            COMPARISON_PROMPT,
            FINAL_DECISION_PROMPT,
            GITHUB_ANALYSIS_PROMPT
        )
        
        self.resume_analysis_prompt = RESUME_ANALYSIS_PROMPT
        self.job_analysis_prompt = JOB_ANALYSIS_PROMPT
        self.web_research_prompt = WEB_RESEARCH_PROMPT
        self.comparison_prompt = COMPARISON_PROMPT
        self.final_decision_prompt = FINAL_DECISION_PROMPT
        self.github_analysis_prompt = GITHUB_ANALYSIS_PROMPT
    
    def parse_resume(self, state: RecruitingState) -> RecruitingState:
        """Parse the resume file and extract structured information.
        
        Args:
            state: Current state with resume file path
            
        Returns:
            Updated state with parsed resume data
        """
        logger.info(f"Parsing resume for candidate: {state['candidate_name']}")
        
        try:
            resume_text = DocumentParser.extract_text(state["resume_file_path"])
            
            if not resume_text.strip():
                raise ValueError("No text could be extracted from the resume file. The file may be corrupted or empty.")
            
            logger.info(f"Successfully extracted {len(resume_text)} characters from resume")
            
            parser = JsonOutputParser(pydantic_object=ResumeData)
            chain = self.resume_analysis_prompt | self._model | parser
            
            resume_data = chain.invoke({
                "resume_text": resume_text
            })
            
            resume_data["raw_text"] = resume_text
            
            github_info = GitHubExtractor.extract_github_info(resume_data)
            if github_info:
                state["github_info"] = github_info
                logger.info(f"Found GitHub profile: {github_info['url']} for username: {github_info['username']}")
            else:
                logger.info("No GitHub profile found in resume")
            
            state["resume_data"] = resume_data
            if "completed_nodes" not in state:
                state["completed_nodes"] = []
            state["completed_nodes"].append("parse_resume")
            
            logger.info(f"Successfully parsed resume with {len(resume_data.get('skills', []))} skills and {len(resume_data.get('work_experience', []))} work experiences")
            
        except Exception as e:
            error_msg = f"Error parsing resume: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            state["error"] = error_msg
        
        return state
    
    def parse_job_description(self, state: RecruitingState) -> RecruitingState:
        """Parse the job description and extract requirements.
        
        Args:
            state: Current state with job description
            
        Returns:
            Updated state with parsed job requirements
        """
        logger.info("Parsing job description")
        
        try:
            if "job_description_text" in state and state["job_description_text"]:
                job_text = state["job_description_text"]
                logger.info(f"Using provided job description text ({len(job_text)} characters)")
            elif "job_description_path" in state and state["job_description_path"]:
                job_text = DocumentParser.extract_text(state["job_description_path"])
                logger.info(f"Extracted {len(job_text)} characters from job description file")
            else:
                raise ValueError("No job description provided")
            
            if not job_text.strip():
                raise ValueError("No text could be extracted from the job description. The file may be corrupted or empty.")
            
            parser = JsonOutputParser(pydantic_object=JobRequirements)
            chain = self.job_analysis_prompt | self._model | parser
            
            job_requirements = chain.invoke({
                "job_description": job_text
            })
            
            job_requirements["raw_text"] = job_text
            
            state["job_requirements"] = job_requirements
            if "completed_nodes" not in state:
                state["completed_nodes"] = []
            state["completed_nodes"].append("parse_job_description")
            
            logger.info(f"Successfully parsed job description with {len(job_requirements.get('core_skills', []))} core skills")
            
        except Exception as e:
            error_msg = f"Error parsing job description: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            state["error"] = error_msg
        
        return state
    
    def github_research(self, state: RecruitingState) -> RecruitingState:
        """
        Scrape and analyze GitHub repositories for the candidate if GitHub info is available.
        
        Args:
            state: Current state with GitHub info from resume
            
        Returns:
            Updated state with GitHub research data
        """
        logger.info("Starting GitHub repository scraping")
        
        try:
            if "github_info" not in state or not state["github_info"]:
                logger.info("No GitHub information available, skipping GitHub research")
                state["github_research_data"] = None
                if "completed_nodes" not in state:
                    state["completed_nodes"] = []
                state["completed_nodes"].append("github_research")
                return state
            
            github_info = state["github_info"]
            github_url = github_info["url"]
            
            logger.info(f"Scraping GitHub repositories from: {github_url}")
            repository_data = self._github_scraper.get_repositories(github_url)
            
            if "error" in repository_data:
                logger.warning(f"Error scraping GitHub repositories: {repository_data['error']}")
                state["github_research_data"] = {
                    "github_url": github_info.get("url"),
                    "github_username": github_info.get("username"),
                    "repositories": []
                }
                if "completed_nodes" not in state:
                    state["completed_nodes"] = []
                state["completed_nodes"].append("github_research")
                return state
            
            if not repository_data or "repositories" not in repository_data or not repository_data["repositories"]:
                logger.info(f"No repository data found for GitHub user: {github_info.get('username')}")
                state["github_research_data"] = {
                    "github_url": github_info.get("url"),
                    "github_username": github_info.get("username"),
                    "repositories": []
                }
                if "completed_nodes" not in state:
                    state["completed_nodes"] = []
                state["completed_nodes"].append("github_research")
                return state
            
            parser = JsonOutputParser()
            chain = self.github_analysis_prompt | self._model | parser
            
            logger.info(f"Analyzing {len(repository_data['repositories'])} GitHub repositories with LLM")
            github_analysis = chain.invoke({
                "candidate_name": state["candidate_name"],
                "github_username": github_info.get("username", ""),
                "github_url": github_info.get("url", ""),
                "repository_data": json.dumps(repository_data, indent=2)
            })
            
            github_analysis["raw_data"] = repository_data
            
            state["github_research_data"] = github_analysis
            if "completed_nodes" not in state:
                state["completed_nodes"] = []
            state["completed_nodes"].append("github_research")
            
            logger.info(f"Successfully analyzed {len(repository_data.get('repositories', []))} GitHub repositories")
            
        except Exception as e:
            error_msg = f"Error performing GitHub research: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            state["error"] = error_msg
        
        return state
    
    def web_research(self, state: RecruitingState) -> RecruitingState:
        """Gather additional information about the candidate from the web.
        
        Args:
            state: Current state with candidate name
            
        Returns:
            Updated state with web research data
        """
        logger.info(f"Performing web research for candidate: {state['candidate_name']}")
        
        try:
            candidate_name = state["candidate_name"]
            web_research_data: WebResearchData = {
                "github_info": None,
                "blog_posts": [],
                "conference_appearances": [],
                "news_mentions": [],
                "social_profiles": {},
                "raw_data": {}
            }
            
            if "github_info" not in state or not state["github_info"]:
                logger.info("No GitHub information found, attempting to search GitHub directly")
                
                github_info = self._search_github_by_name(candidate_name)
                if github_info:
                    logger.info(f"Found GitHub profile via GitHub search: {github_info['url']}")
                    state["github_info"] = github_info
                    
                    if hasattr(self, "github_research"):
                        logger.info("Running GitHub research with newly found profile")
                        state = self.github_research(state)
            
            if "github_research_data" in state and state["github_research_data"]:
                github_data = state["github_research_data"]
                
                github_profile = github_data.get("github_profile", {})
                key_projects = github_data.get("key_projects", [])
                
                web_research_data["github_info"] = {
                    "username": github_profile.get("username"),
                    "url": github_profile.get("url"),
                    "primary_languages": github_profile.get("primary_languages", []),
                    "key_projects": key_projects
                }
                
                web_research_data["raw_data"]["github"] = github_data.get("raw_data", {})
                
                if github_profile.get("url"):
                    web_research_data["social_profiles"]["github"] = github_profile.get("url")
                
                logger.info("Including GitHub research data in web research") 

            elif "github_info" in state and state["github_info"]:
                github_info = state["github_info"]
                web_research_data["github_info"] = {
                    "username": github_info["username"],
                    "url": github_info["url"]
                }
                web_research_data["social_profiles"]["github"] = github_info["url"]
                logger.info(f"Including GitHub profile in web research: {github_info['url']}")
            else:
                logger.info("No GitHub information available for web research")
            
            search_queries = [
                f'{candidate_name} blog posts',
                f'{candidate_name} conference speaker',
                f'{candidate_name} portfolio',
                f'site:twitter.com "{candidate_name}"',
                f'site:stackoverflow.com "asked by {candidate_name}"',
                f'site:stackoverflow.com "answered by {candidate_name}"',
            ]
            
            all_search_results = []
            for query in search_queries:
                try:
                    logger.info(f"Searching the web for: '{query}'")
                    results = self._search_tool.invoke(query)
                    logger.info(f"Found {len(results)} results for '{query}'")
                    all_search_results.extend(results)
                except Exception as e:
                    logger.warning(f"Error searching for '{query}': {str(e)}")
            
            web_research_data["raw_data"]["search_results"] = all_search_results
            
            parser = JsonOutputParser(pydantic_object=WebResearchData)
            chain = self.web_research_prompt | self._model | parser
            
            logger.info(f"Processing {len(all_search_results)} search results with LLM")
            structured_web_data = chain.invoke({
                "candidate_name": candidate_name,
                "search_results": json.dumps(all_search_results, indent=2),
                "github_data": json.dumps(web_research_data.get("github_info", {}), indent=2) 
                            if web_research_data.get("github_info") else "No GitHub information found"
            })
            
            for key, value in structured_web_data.items():
                if key != "raw_data" and key != "github_info":
                    web_research_data[key] = value
            
            if (not state.get("github_info") and 
                structured_web_data.get("social_profiles", {}).get("github")):
                github_url = structured_web_data["social_profiles"]["github"]
                logger.info(f"Found GitHub profile in web research: {github_url}")
                
                from utils.github_extractor import GitHubExtractor
                github_info = {"url": github_url}
                username = GitHubExtractor._extract_username_from_url(github_url)
                if username:
                    github_info["username"] = username
                    state["github_info"] = github_info
                    logger.info(f"Extracted GitHub username from web research: {username}")
            
            state["web_research_data"] = web_research_data
            if "completed_nodes" not in state:
                state["completed_nodes"] = []
            state["completed_nodes"].append("web_research")
            
            logger.info(f"Successfully completed web research with {len(all_search_results)} search results")
            
        except Exception as e:
            error_msg = f"Error performing web research: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            state["error"] = error_msg
        
        return state

    def create_candidate_profile(self, state: RecruitingState) -> RecruitingState:
        """Create a comprehensive candidate profile combining resume and web research data.
        
        Args:
            state: Current state with resume data and web research data
            
        Returns:
            Updated state with candidate profile
        """
        logger.info("Creating comprehensive candidate profile")
        
        try:
            candidate_profile = {
                "name": state["candidate_name"],
                "resume_data": state["resume_data"],
                "web_research": state["web_research_data"]
            }
            
            if "github_research_data" in state and state["github_research_data"]:
                candidate_profile["github_research"] = state["github_research_data"]
            
            state["candidate_profile"] = candidate_profile
            if "completed_nodes" not in state:
                state["completed_nodes"] = []
            state["completed_nodes"].append("create_candidate_profile")
            
            logger.info("Successfully created candidate profile")
            
        except Exception as e:
            error_msg = f"Error creating candidate profile: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            state["error"] = error_msg
        
        return state
    
    def compare_candidate_to_job(self, state: RecruitingState) -> RecruitingState:
        """Compare candidate qualifications to job requirements.
        
        Args:
            state: Current state with candidate profile and job requirements
            
        Returns:
            Updated state with comparison results
        """
        logger.info("Comparing candidate to job requirements")
        
        try:
            parser = JsonOutputParser(pydantic_object=ComparisonResult)
            chain = self.comparison_prompt | self._model | parser
            
            comparison_result = chain.invoke({
                "candidate_name": state["candidate_name"],
                "candidate_profile": json.dumps(state["candidate_profile"], indent=2),
                "job_requirements": json.dumps(state["job_requirements"], indent=2)
            })
            
            state["comparison_result"] = comparison_result
            if "completed_nodes" not in state:
                state["completed_nodes"] = []
            state["completed_nodes"].append("compare_candidate_to_job")
            
            logger.info("Successfully compared candidate to job requirements")
            
        except Exception as e:
            error_msg = f"Error comparing candidate to job: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            state["error"] = error_msg
        
        return state
    
    def generate_final_decision(self, state: RecruitingState) -> RecruitingState:
        """Generate a final decision on candidate fit.
        
        Args:
            state: Current state with comparison results
            
        Returns:
            Updated state with final decision
        """
        logger.info("Generating final decision")
        
        try:
            parser = JsonOutputParser(pydantic_object=FinalDecision)
            chain = self.final_decision_prompt | self._model | parser
            
            final_decision = chain.invoke({
                "candidate_name": state["candidate_name"],
                "candidate_profile": json.dumps(state["candidate_profile"], indent=2),
                "job_requirements": json.dumps(state["job_requirements"], indent=2),
                "comparison_result": json.dumps(state["comparison_result"], indent=2)
            })
            
            state["final_decision"] = final_decision
            if "completed_nodes" not in state:
                state["completed_nodes"] = []
            state["completed_nodes"].append("generate_final_decision")
            
            logger.info(f"Final decision: {final_decision['fit_score']}")
            
        except Exception as e:
            error_msg = f"Error generating final decision: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            state["error"] = error_msg
        
        return state
    
    def _search_github_by_name(self, candidate_name: str) -> Optional[Dict[str, str]]:
        """
        Search for a GitHub profile using GitHub's user search functionality.
        
        Args:
            candidate_name: Name of the candidate
            
        Returns:
            Dictionary with GitHub URL and username if found, None otherwise
        """
        logger.info(f"Searching GitHub for candidate: {candidate_name}")
        
        try:
            formatted_name = candidate_name.replace(" ", "+")
            
            github_search_url = f"https://github.com/search?q={formatted_name}&type=users"
            logger.info(f"Using GitHub search URL: {github_search_url}")
            
            try:
                import requests
                from bs4 import BeautifulSoup
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0'
                }
                
                response = requests.get(github_search_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    html_content = response.text
                    logger.info("Successfully fetched GitHub search results page")
                else:
                    logger.warning(f"Failed to fetch GitHub search page: Status code {response.status_code}")
                    return self._fallback_github_search(candidate_name)
            except Exception as e:
                logger.warning(f"Error fetching GitHub search page directly: {str(e)}")
                return self._fallback_github_search(candidate_name)
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            results_container = soup.find('div', attrs={'data-testid': 'results-list'})
            
            if not results_container:
                logger.warning("Could not find results list container in GitHub search page")
                return self._fallback_github_search(candidate_name)
            
            github_profiles = []

            user_items = results_container.find_all('div', recursive=False)
        
            logger.info(f"Found {len(user_items)} potential user results in GitHub search")
            
            for item in user_items:
                try:
                    profile = {}
                    
                    avatar_img = item.find('img', attrs={'data-testid': 'github-avatar'})
                    if avatar_img:
                        profile['avatar_url'] = avatar_img.get('src')
                    
                    links = item.find_all('a', class_='prc-Link-Link-85e08')
                    
                    if len(links) >= 2:
                        name_span = links[0].find('span')
                        if name_span:
                            profile['full_name'] = name_span.get_text(strip=True).lower()
                        
                        username_span = links[1].find('span', recursive=True)
                        if username_span:
                            profile['username'] = username_span.get_text(strip=True)
                        
                        if 'username' in profile:
                            profile['url'] = f"https://github.com/{profile['username']}"
                    
                    bio_span = item.find('span', class_='search-match')
                    if not bio_span:
                        bio_div = item.find('div', class_='dcdlju')
                        if bio_div:
                            bio_span = bio_div.find('span')
                    
                    if bio_span:
                        profile['bio'] = bio_span.get_text(strip=True)
                    
                    metadata_list = item.find('ul')
                    if metadata_list:
                        metadata_items = metadata_list.find_all('li')
                        
                        if len(metadata_items) > 0:
                            profile['location'] = metadata_items[0].get_text(strip=True)
                        
                        repo_span = metadata_list.find('span', attrs={'aria-label': lambda x: x and 'repositories' in x if x else False})
                        if repo_span:
                            profile['repositories'] = repo_span.get_text(strip=True)
                        
                        followers_span = metadata_list.find('span', attrs={'aria-label': lambda x: x and 'followers' in x if x else False})
                        if followers_span:
                            profile['followers'] = followers_span.get_text(strip=True)
                    
                    if 'username' in profile and 'full_name' in profile:
                        github_profiles.append(profile)
                        
                except Exception as e:
                    logger.warning(f"Error parsing user item: {str(e)}")
            
            logger.info(f"Successfully extracted {len(github_profiles)} GitHub profiles")
            
            if github_profiles:
                candidate_name_lower = candidate_name.lower()
                
                for profile in github_profiles:
                    if profile['full_name'].lower() == candidate_name_lower:
                        logger.info(f"Found exact name match: {profile['username']}")
                        return {
                            'url': profile['url'],
                            'username': profile['username']
                        }
                
                # Look for name match at the start of full name
                for profile in github_profiles:
                    if profile['full_name'].lower().startswith(candidate_name_lower):
                        logger.info(f"Found name match at start: {profile['username']}")
                        return {
                            'url': profile['url'],
                            'username': profile['username']
                        }
                
                # If no match found, return the first profile
                logger.info(f"No specific name match found, using first result: {github_profiles[0]['username']}")
                return {
                    'url': github_profiles[0]['url'],
                    'username': github_profiles[0]['username']
                }
            
            # If no profiles found, use fallback
            logger.info("No GitHub profiles extracted from search results")
            return self._fallback_github_search(candidate_name)
        
        except Exception as e:
            logger.warning(f"Error in GitHub search: {str(e)}")
            return self._fallback_github_search(candidate_name)

    def _fallback_github_search(self, candidate_name: str) -> Optional[Dict[str, str]]:
        """
        Fallback method to search for GitHub profiles using general web search.
        
        Args:
            candidate_name: Name of the candidate
            
        Returns:
            Dictionary with GitHub URL and username if found, None otherwise
        """
        logger.info(f"Using fallback search for GitHub profile: {candidate_name}")
        
        try:
            search_queries = [
                f'"{candidate_name}" github profile',
                f'"{candidate_name}" site:github.com',
                f'{candidate_name} github'
            ]
            
            for query in search_queries:
                results = self._search_tool.invoke(query)
                
                for result in results:
                    url = result.get('url', '')
                    if 'github.com/' in url and not any(x in url for x in ['/pulls', '/issues', '/commit', '/blob', '/tree']):
                        from utils.github_extractor import GitHubExtractor
                        username = GitHubExtractor._extract_username_from_url(url)
                        if username:
                            logger.info(f"Found GitHub profile via fallback search: {username}")
                            return {
                                'url': f'https://github.com/{username}',
                                'username': username
                            }
            
            logger.info("No GitHub profile found via fallback search")
            return None
        
        except Exception as e:
            logger.warning(f"Error in fallback GitHub search: {str(e)}")
            return None