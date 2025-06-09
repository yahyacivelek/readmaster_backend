"""
Application-level abstract interfaces for external services.

This package defines interfaces for services that the application layer
depends on, but whose concrete implementations reside in the infrastructure
layer. This promotes dependency inversion and keeps the application
layer decoupled from specific infrastructure concerns (e.g., specific
AI service providers, payment gateways, file storage solutions).
"""

from .ai_analysis_interface import AIAnalysisInterface

__all__ = [
    "AIAnalysisInterface",
]
