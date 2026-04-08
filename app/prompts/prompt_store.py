"""Prompt loading and management."""

import os
from typing import Optional

from config import settings


class PromptStore:
    """Load and manage prompt templates."""

    _prompts: dict = {}

    @classmethod
    def load_prompt(cls, prompt_name: str) -> Optional[str]:
        """
        Load a prompt template by name.
        
        Args:
            prompt_name: Name of prompt (e.g., 'routing', 'planning')
            
        Returns:
            Prompt template string
        """
        if prompt_name in cls._prompts:
            return cls._prompts[prompt_name]

        prompt_path = os.path.join(settings.PROMPTS_DIR, f'{prompt_name}.txt')
        
        if not os.path.exists(prompt_path):
            return None

        with open(prompt_path, 'r') as f:
            prompt = f.read()
            cls._prompts[prompt_name] = prompt
            return prompt

    @classmethod
    def format_prompt(cls, prompt_name: str, **kwargs) -> str:
        """
        Load and format a prompt template.
        
        Args:
            prompt_name: Name of prompt
            **kwargs: Template variables
            
        Returns:
            Formatted prompt
        """
        template = cls.load_prompt(prompt_name)
        if template is None:
            raise ValueError(f'Prompt not found: {prompt_name}')
        
        return template.format(**kwargs)

    @classmethod
    def reload(cls) -> None:
        """Reload all prompts from disk."""
        cls._prompts = {}
