import logging
from .config import get_settings

settings = get_settings()

def setup_logger(name: str) -> logging.Logger:
    """Setup and return a logger instance with the specified name"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(settings.LOG_LEVEL)
        
        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(settings.LOG_LEVEL)
        
        # Create formatter
        formatter = logging.Formatter(settings.LOG_FORMAT)
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
    
    return logger 