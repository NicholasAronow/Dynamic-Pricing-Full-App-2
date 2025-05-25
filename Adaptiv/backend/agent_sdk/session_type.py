"""
Session type handler for Pydantic compatibility with SQLAlchemy.
This module provides a SessionType class that enables SQLAlchemy Session objects to be used
with Pydantic V2 without serialization issues.
"""
from typing import Annotated, Any, ClassVar, Type
from sqlalchemy.orm import Session
import pydantic_core
from pydantic import GetCoreSchemaHandler, PlainSerializer


def session_serializer(session: Session) -> None:
    """
    Serialize a Session object to None to avoid serialization issues.
    
    Args:
        session: The SQLAlchemy Session object to serialize
        
    Returns:
        None
    """
    return None


def get_session_schema(_cls, _handler):
    """Generate a CoreSchema for SQLAlchemy Session objects.
    
    This allows Pydantic to work with Session objects without serialization issues.
    
    Args:
        _cls: The source type
        _handler: The core schema handler
        
    Returns:
        A CoreSchema for SQLAlchemy Session objects
    """
    # Use any_schema to allow Session to be used without serialization issues
    schema = pydantic_core.core_schema.any_schema()
    schema["metadata"] = {
        "title": "SQLAlchemySession",
        "description": "SQLAlchemy Session object (non-serializable)"
    }
    return schema


# Create an Annotated type for use with Pydantic
SessionType = Annotated[
    Session, 
    PlainSerializer(session_serializer),
    get_session_schema
]


class DBSessionMeta(type):
    """
    Metaclass for DB Session class to ensure proper handling of SQLAlchemy Session objects.
    """
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, handler: GetCoreSchemaHandler
    ) -> pydantic_core.CoreSchema:
        """
        Generate a CoreSchema for DBSession class.
        
        Args:
            _source_type: The source type
            handler: The core schema handler
            
        Returns:
            A CoreSchema for DBSession class
        """
        return get_session_schema(cls, handler)


class DBSession(Session, metaclass=DBSessionMeta):
    """
    A wrapper around SQLAlchemy Session with Pydantic V2 compatibility.
    """
    __pydantic_serializer__: ClassVar = session_serializer
    
    def model_dump(self, *args, **kwargs):
        """
        Override model_dump to prevent serialization issues.
        
        Returns:
            None
        """
        return None
    
    def model_dump_json(self, *args, **kwargs):
        """
        Override model_dump_json to prevent serialization issues.
        
        Returns:
            'null'
        """
        return "null"
