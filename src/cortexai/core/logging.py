"""Logging utilities for the CortexAi framework."""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str = "cortexai",
    level: int = logging.INFO,
    filename: Optional[str] = None
) -> logging.Logger:
    """Set up and configure a logger.
    
    Args:
        name: Name of the logger
        level: Logging level
        filename: Optional file to log to (if None, logs to stdout)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding handlers if they already exist
    if not logger.handlers:
        if filename:
            handler = logging.FileHandler(filename)
        else:
            handler = logging.StreamHandler(sys.stdout)
            
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


# Default framework-wide logger instance
logger = setup_logger()


def get_logger(name: Optional[str] = None, level: Optional[int] = None) -> logging.Logger:
    """Get a logger with the specified name.
    
    Args:
        name: Name of the logger (will be prefixed with 'cortexai.')
        level: Optional specific logging level for this logger
        
    Returns:
        Logger instance
    """
    if name:
        child_logger = logging.getLogger(f"cortexai.{name}")
        if level is not None:
            child_logger.setLevel(level)
        return child_logger
    
    # If no name provided, return the default logger
    if level is not None:
        logger.setLevel(level)
    return logger
