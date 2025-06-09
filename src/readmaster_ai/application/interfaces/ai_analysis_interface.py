"""
Defines the interface for AI analysis services.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any

class AIAnalysisInterface(ABC):
    """
    Abstract Base Class for AI analysis services.
    This interface ensures that any AI service implementation
    can be used interchangeably by the application layer.
    """
    @abstractmethod
    async def analyze_audio(self, audio_url: str, language: str) -> Dict[str, Any]:
        """
        Analyzes audio content from a given URL.

        Args:
            audio_url: The URL of the audio file to analyze.
            language: The language of the audio content (e.g., 'en-US').

        Returns:
            A dictionary containing the structured analysis data,
            which might include transcription, fluency scores, pronunciation feedback, etc.
        """
        pass
