"""
Provides a wrapper for SQLAlchemy Session objects to avoid Pydantic schema generation issues.
"""
from typing import Annotated, Any
from fastapi import Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db
import json

class SessionWrapper(BaseModel):
    """A wrapper for a SQLAlchemy Session that avoids Pydantic schema generation issues."""
    
    # Use a dummy field for schema generation - renamed to avoid underscore prefix
    session_id: str = Field(default="", exclude=True)
    
    # Store the actual session - renamed to avoid underscore prefix
    session_obj: Any = Field(default=None, exclude=True)
    
    # Pydantic V2 model_config instead of Config class
    model_config = {
        "arbitrary_types_allowed": True
    }
    
    def __init__(self, **data: Any):
        # Map old field names to new ones for backward compatibility
        if "_session" in data:
            data["session_obj"] = data.pop("_session")
        if "_session_id" in data:
            data["session_id"] = data.pop("_session_id")
            
        super().__init__(**data)
    
    @property
    def session(self) -> Session:
        """Get the SQLAlchemy session."""
        return self.session_obj
    
    def json(self) -> str:
        """Create a JSON representation of the session wrapper."""
        return json.dumps({"session_id": self.session_id})
    
    @classmethod
    def get_session_wrapper(cls):
        """Get a dependency that returns a SessionWrapper."""
        def _get_session_wrapper(db: Session = Depends(get_db)) -> "SessionWrapper":
            return cls(session_obj=db, session_id=str(id(db)))
        return _get_session_wrapper

# Define a dependency for getting a SessionWrapper
get_session_wrapper = SessionWrapper.get_session_wrapper()
SessionDep = Annotated[SessionWrapper, Depends(get_session_wrapper)]
