from typing import Dict, Optional, Any
import re
import logging

logger = logging.getLogger(__name__)

class GitHubExtractor:
    """Utility class to extract GitHub information from resume data."""
    
    @staticmethod
    def extract_github_info(resume_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Extract GitHub URL and username from resume data.
        
        Args:
            resume_data: Parsed resume data with potential GitHub information
            
        Returns:
            Dictionary with GitHub URL and username if found, None otherwise
        """
        github_info = None
        
        if "online_profiles" in resume_data and resume_data["online_profiles"]:
            online_profiles = resume_data["online_profiles"]
            
            if "github" in online_profiles and online_profiles["github"]:
                github_url = online_profiles["github"].strip()
                
                if not github_url.lower().startswith(('http://', 'https://')):
                    github_url = f"https://{github_url}"
                
                if not github_url.lower().startswith(('http://github.com', 'https://github.com')):
                    username = GitHubExtractor._extract_username_from_text(github_url)
                    if username:
                        github_url = f"https://github.com/{username}"
                
                username = GitHubExtractor._extract_username_from_url(github_url)
                if username:
                    github_info = {
                        "url": github_url,
                        "username": username
                    }
                    logger.info(f"Found GitHub URL in resume: {github_url}, username: {username}")
        
        if not github_info and "raw_text" in resume_data:
            github_info = GitHubExtractor._extract_from_raw_text(resume_data["raw_text"])
        
        return github_info
    
    @staticmethod
    def _extract_username_from_url(url: str) -> Optional[str]:
        """Extract username from a GitHub URL."""
        patterns = [
            r'github\.com/([a-zA-Z0-9_-]+)',  # github.com/username
            r'([a-zA-Z0-9_-]+)\.github\.io'   # username.github.io
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                username = match.group(1)
                if username.lower() in ['www', 'http', 'https', 'com']:
                    continue
                return username
        
        return None
    
    @staticmethod
    def _extract_username_from_text(text: str) -> Optional[str]:
        """Extract GitHub username from text."""
        patterns = [
            r'github:?\s*([a-zA-Z0-9_-]+)',    # github: username
            r'GitHub:?\s*([a-zA-Z0-9_-]+)'     # GitHub: username
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                username = match.group(1)
                # Skip common false positives
                if username.lower() in ['www', 'http', 'https', 'com']:
                    continue
                return username
        
        return None
    
    @staticmethod
    def _extract_from_raw_text(text: str) -> Optional[Dict[str, str]]:
        """Extract GitHub information from raw resume text."""
        # Patterns for GitHub URLs
        url_patterns = [
            r'(https?://(?:www\.)?github\.com/[a-zA-Z0-9_-]+)',  # Full GitHub URL
            r'(github\.com/[a-zA-Z0-9_-]+)'                      # github.com/username without http
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                url = match.group(1)
                if not url.lower().startswith(('http://', 'https://')):
                    url = f"https://{url}"
                
                username = GitHubExtractor._extract_username_from_url(url)
                if username:
                    return {
                        "url": url,
                        "username": username
                    }
        
        username = GitHubExtractor._extract_username_from_text(text)
        if username:
            return {
                "url": f"https://github.com/{username}",
                "username": username
            }
        
        return None