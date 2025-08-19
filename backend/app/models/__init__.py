"""
Database models initialization.
"""

from sqlalchemy.ext.declarative import declarative_base

# Create a single declarative base for all models
Base = declarative_base()

# Import all models to register them with the base
from .user import *

__all__ = ["Base", "User", "ConversationSession", "ConversationMessage", 
           "ConversationInteraction", "ConversationAnalytics", "UserLearningProgress"]
