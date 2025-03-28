"""
Base Transformation Interface

Defines the abstract interface for message format transformations
between different provider APIs.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union


class BaseTransform(ABC):
    """
    Abstract base class for message format transformations.
    
    Different models and providers may require messages in specific formats.
    These transformation classes convert between them.
    """
    
    @abstractmethod
    def transform_messages(
        self, 
        messages: List[Dict[str, Any]],
        system_prompt: str = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Transform messages to the required format.
        
        Args:
            messages: List of message dictionaries to transform
            system_prompt: Optional system prompt to include
            **kwargs: Additional parameters for specific transformations
            
        Returns:
            Transformed message list
        """
        pass


class TransformationRegistry:
    """
    Registry for message transformations.
    
    Maps model IDs to their appropriate transformations.
    """
    
    _registry = {}
    
    @classmethod
    def register(cls, model_pattern: str, transform_class):
        """
        Register a transformation class for models matching the pattern.
        
        Args:
            model_pattern: String pattern to match model IDs
            transform_class: Transformation class to use
        """
        cls._registry[model_pattern] = transform_class
    
    @classmethod
    def get_transform(cls, model_id: str):
        """
        Get the appropriate transformation for a model ID.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Transformation instance or None if no match
        """
        for pattern, transform_class in cls._registry.items():
            if pattern in model_id:
                return transform_class()
        return None
