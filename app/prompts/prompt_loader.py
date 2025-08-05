import os
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class PromptLoader:
    """Secure prompt loader that reads prompts from external files with version support"""

    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Initialize the prompt loader.

        Args:
            prompts_dir: Path to prompts directory. Defaults to app/prompts/
        """
        if prompts_dir:
            self.prompts_dir = Path(prompts_dir)
        else:
            # Default to app/prompts/ directory
            # Current file is app/prompts/prompt_loader.py
            self.prompts_dir = Path(__file__).parent

        self._prompts_cache: Dict[str, str] = {}

        # Ensure prompts directory exists
        self.prompts_dir.mkdir(exist_ok=True)

        logger.info(f"PromptLoader initialized with directory: {self.prompts_dir}")

    def load_prompt(self, prompt_name: str, version: Optional[str] = None, use_cache: bool = True) -> str:
        """
        Load a prompt from file.

        Args:
            prompt_name: Name of the prompt file (without .txt extension)
            version: Version folder (v1, v2, v3, shared). If None, loads from root
            use_cache: Whether to use cached version if available

        Returns:
            The prompt content as string

        Raises:
            FileNotFoundError: If prompt file doesn't exist
            IOError: If file cannot be read
        """
        cache_key = f"{version}_{prompt_name}" if version else prompt_name
        
        if use_cache and cache_key in self._prompts_cache:
            return self._prompts_cache[cache_key]

        if version:
            prompt_file = self.prompts_dir / version / f"{prompt_name}.txt"
        else:
            prompt_file = self.prompts_dir / f"{prompt_name}.txt"

        if not prompt_file.exists():
            logger.error(f"Prompt file not found: {prompt_file}")
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if use_cache:
                self._prompts_cache[cache_key] = content

            logger.debug(f"Loaded prompt: {cache_key} ({len(content)} chars)")
            return content

        except IOError as e:
            logger.error(f"Failed to read prompt file {prompt_file}: {e}")
            raise

    def load_prompt_template(self, prompt_name: str, version: Optional[str] = None, **kwargs) -> str:
        """
        Load a prompt template and format it with provided variables.

        Args:
            prompt_name: Name of the prompt template file
            version: Version folder (v1, v2, v3, shared). If None, loads from root
            **kwargs: Variables to substitute in the template

        Returns:
            Formatted prompt string
        """
        template = self.load_prompt(prompt_name, version)

        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing template variable in prompt {prompt_name}: {e}")
            raise ValueError(f"Missing template variable: {e}")
        except ValueError as e:
            logger.error(f"Template formatting error in prompt {prompt_name}: {e}")
            raise

    def list_available_prompts(self, version: Optional[str] = None) -> list[str]:
        """
        List all available prompt files.

        Args:
            version: Version folder to list prompts from. If None, lists from root

        Returns:
            List of prompt names (without .txt extension)
        """
        if version:
            prompt_dir = self.prompts_dir / version
        else:
            prompt_dir = self.prompts_dir
            
        if not prompt_dir.exists():
            return []

        prompts = []
        for file in prompt_dir.glob("*.txt"):
            prompts.append(file.stem)

        return sorted(prompts)

    def clear_cache(self):
        """Clear the prompts cache"""
        self._prompts_cache.clear()
        logger.debug("Prompts cache cleared")

    def reload_prompt(self, prompt_name: str, version: Optional[str] = None) -> str:
        """
        Force reload a prompt from file, bypassing cache.

        Args:
            prompt_name: Name of the prompt to reload
            version: Version folder (v1, v2, v3, shared). If None, loads from root

        Returns:
            The reloaded prompt content
        """
        return self.load_prompt(prompt_name, version, use_cache=False)


# Global prompt loader instance
_prompt_loader = None

def get_prompt_loader() -> PromptLoader:
    """Get the global prompt loader instance"""
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader

def load_prompt(prompt_name: str, version: Optional[str] = None) -> str:
    """Convenience function to load a prompt using the global loader"""
    return get_prompt_loader().load_prompt(prompt_name, version)

def load_prompt_template(prompt_name: str, version: Optional[str] = None, **kwargs) -> str:
    """Convenience function to load and format a prompt template"""
    return get_prompt_loader().load_prompt_template(prompt_name, version, **kwargs)
