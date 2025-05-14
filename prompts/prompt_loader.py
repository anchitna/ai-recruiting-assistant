from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate

def load_prompt(prompt_file: str) -> ChatPromptTemplate:
    """
    Load a prompt from a .txt file and return a ChatPromptTemplate.
    
    The .txt file should have a format with "system: " and "user: " sections.
    
    Args:
        prompt_file: Path to the prompt file
        
    Returns:
        ChatPromptTemplate configured with the system and user messages
    """
    prompt_path = Path(prompt_file)
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    
    with open(prompt_path, 'r') as f:
        content = f.read()
    
    # Split the content into system and user parts
    sections = content.split("---")
    
    if len(sections) != 2:
        raise ValueError(f"Prompt file must contain exactly one '---' separator: {prompt_file}")
    
    system = sections[0].strip()
    user = sections[1].strip()

    return ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("user", user)
        ], 
        template_format="mustache"
    )

__all__ = ["load_prompt"]