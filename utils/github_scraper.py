import requests
import logging
import re
import traceback
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)

class GithubScraper:
    """Utility class to scrape GitHub repositories without using the GitHub API."""
    
    def __init__(self):
        """Initialize the GitHub scraper with common headers for requests."""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
    
    def get_repositories(self, github_url: str) -> Dict[str, Any]:
        """
        Scrape repository information from a GitHub profile.
        
        Args:
            github_url: GitHub profile URL
            
        Returns:
            Dictionary containing user info and repositories
        """
        logger.info(f"Scraping repositories from: {github_url}")
        
        try:
            # Extract username from URL
            username = self._extract_username(github_url)
            if not username:
                logger.warning(f"Could not extract username from URL: {github_url}")
                return {"error": "Invalid GitHub URL"}
            
            # Build and normalize the GitHub URL
            github_url = f"https://github.com/{username}"
            repositories_url = f"{github_url}?tab=repositories"
            
            # Get profile page
            profile_page = self._fetch_url(github_url)
            if not profile_page:
                logger.warning(f"Could not fetch profile page: {github_url}")
                return {"error": "Could not access GitHub profile"}
            
            # Parse profile information
            user_info = self._parse_profile_info(profile_page, username)
            
            # Get repositories page
            repos_page = self._fetch_url(repositories_url)
            if not repos_page:
                logger.warning(f"Could not fetch repositories page: {repositories_url}")
                return {"user_info": user_info, "repositories": []}
            
            # Parse repositories
            repositories = self._parse_repositories(repos_page, username)
            
            # Get README content for top repositories
            for repo in repositories[:5]:  # Limit to top 5 repos to avoid rate limiting
                try:
                    readme_content = self._get_readme_content(username, repo["name"])
                    if readme_content:
                        repo["readme"] = readme_content
                        logger.info(f"Found README for repository: {repo['name']}")
                    else:
                        logger.info(f"No README found for repository: {repo['name']}")
                    
                    # Add a small delay to avoid rate limiting
                    time.sleep(1)
                except Exception as e:
                    logger.warning(f"Error getting README for {username}/{repo['name']}: {str(e)}")
            
            return {
                "user_info": user_info,
                "repositories": repositories
            }
        
        except Exception as e:
            logger.error(f"Error scraping GitHub profile: {str(e)}\n{traceback.format_exc()}")
            return {"error": f"Error scraping GitHub profile: {str(e)}"}
    
    def _extract_username(self, url: str) -> Optional[str]:
        """
        Extract GitHub username from a GitHub URL.
        
        Args:
            url: GitHub URL
            
        Returns:
            Username if found, None otherwise
        """
        patterns = [
            r'github\.com/([^/]+)',      # github.com/username
            r'([^/]+)\.github\.io'        # username.github.io
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                username = match.group(1)
                # Skip common false positives
                if username.lower() in ['www', 'http', 'https', 'com']:
                    continue
                return username
        
        return None
    
    def _fetch_url(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from a URL with error handling.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content if successful, None otherwise
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"Failed to fetch URL {url}: Status code {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Error fetching URL {url}: {str(e)}")
            return None
    
    def _parse_profile_info(self, html_content: str, username: str) -> Dict[str, Any]:
        """
        Parse GitHub profile information from HTML.
        
        Args:
            html_content: HTML content of the profile page
            username: GitHub username
            
        Returns:
            Dictionary with profile information
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Initialize profile info
            profile_info = {
                "username": username,
                "name": username,  # Default to username if name not found
                "bio": None,
                "location": None,
                "company": None,
                "website": None,
                "twitter": None
            }
            
            # Try to get display name
            name_element = soup.select_one('span.p-name.vcard-fullname')
            if name_element and name_element.text.strip():
                profile_info["name"] = name_element.text.strip()
            
            # Try to get bio
            bio_element = soup.select_one('div.p-note.user-profile-bio')
            if bio_element:
                bio_text = bio_element.get_text(strip=True)
                if bio_text:
                    profile_info["bio"] = bio_text
            
            # Try to get location
            location_element = soup.select_one('span.p-label')
            if location_element and location_element.text.strip():
                profile_info["location"] = location_element.text.strip()
            
            # Try to get website
            website_element = soup.select_one('a[href^="http"].Link--primary')
            if website_element and website_element.text.strip():
                profile_info["website"] = website_element.get('href')
            
            # Additional information like followers, following count could be added here
            
            return profile_info
        
        except Exception as e:
            logger.warning(f"Error parsing profile info: {str(e)}")
            return {"username": username}
    
    def _parse_repositories(self, html_content: str, username: str) -> List[Dict[str, Any]]:
        """
        Parse repository information from HTML.
        
        Args:
            html_content: HTML content of the repositories page
            username: GitHub username
            
        Returns:
            List of repository dictionaries
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            repositories = []
            
            # Find repository list items
            repo_items = soup.select('li.public', limit=10)  # Limit to top 10 repos
            
            for item in repo_items:
                try:
                    # Repository name and URL
                    name_element = item.select_one('a[itemprop="name codeRepository"]')
                    if not name_element:
                        continue
                    
                    repo_name = name_element.text.strip()
                    repo_url = f"https://github.com/{username}/{repo_name}"
                    
                    # Repository description
                    description_element = item.select_one('p[itemprop="description"]')
                    description = description_element.text.strip() if description_element else None
                    
                    # Primary language
                    language_element = item.select_one('span[itemprop="programmingLanguage"]')
                    language = language_element.text.strip() if language_element else None
                    
                    # Stars count
                    stars_element = item.select_one('a[href$="/stargazers"]')
                    stars = stars_element.text.strip() if stars_element else "0"
                    
                    # Forks count
                    forks_element = item.select_one('a[href$="/network/members"]')
                    forks = forks_element.text.strip() if forks_element else "0"
                    
                    # Updated time
                    updated_element = item.select_one('relative-time')
                    updated_at = updated_element.get('datetime') if updated_element else None
                    
                    repositories.append({
                        "name": repo_name,
                        "description": description,
                        "language": language,
                        "stars": stars,
                        "forks": forks,
                        "updated_at": updated_at,
                        "html_url": repo_url
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing repository item: {str(e)}")
                    continue
            
            return repositories
        
        except Exception as e:
            logger.warning(f"Error parsing repositories: {str(e)}")
            return []
    
    def _get_readme_content(self, username: str, repo_name: str) -> Optional[str]:
        """
        Extract README content from a repository.
        
        Args:
            username: GitHub username
            repo_name: Repository name
            
        Returns:
            README content if found, None otherwise
        """
        try:
            # Try common README filenames
            readme_urls = [
                f"https://github.com/{username}/{repo_name}/blob/master/README.md",
                f"https://github.com/{username}/{repo_name}/blob/main/README.md",
                f"https://github.com/{username}/{repo_name}/blob/master/readme.md",
                f"https://github.com/{username}/{repo_name}/blob/main/readme.md",
                f"https://github.com/{username}/{repo_name}/blob/master/README",
                f"https://github.com/{username}/{repo_name}/blob/main/README"
            ]
            
            for url in readme_urls:
                html_content = self._fetch_url(url)
                if html_content:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Find README content - GitHub displays it in an article element
                    readme_element = soup.select_one('article.markdown-body')
                    if readme_element:
                        # Extract text and preserve some formatting
                        readme_text = readme_element.get_text(separator='\n', strip=True)
                        
                        # If README is too long, truncate it
                        if len(readme_text) > 5000:
                            readme_text = readme_text[:5000] + "...[truncated]"
                        
                        return readme_text
            
            # If no README found in common locations, check repository main page for README
            main_repo_url = f"https://github.com/{username}/{repo_name}"
            html_content = self._fetch_url(main_repo_url)
            
            if html_content:
                soup = BeautifulSoup(html_content, 'html.parser')
                readme_element = soup.select_one('article.markdown-body')
                if readme_element:
                    readme_text = readme_element.get_text(separator='\n', strip=True)
                    if len(readme_text) > 5000:
                        readme_text = readme_text[:5000] + "...[truncated]"
                    return readme_text
            
            return None
        
        except Exception as e:
            logger.warning(f"Error getting README for {username}/{repo_name}: {str(e)}")
            return None