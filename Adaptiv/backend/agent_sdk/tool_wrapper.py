"""
Tool wrapper module that provides a function_tool decorator compatible with Pydantic V2.
This ensures SQLAlchemy Session objects are properly handled during serialization.
"""
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar
from agents import function_tool as openai_function_tool
from .db_helper import DBHelper
from .session_type import SessionType
from sqlalchemy.orm import Session

F = TypeVar('F', bound=Callable)

def function_tool(func: F) -> F:
    """
    A wrapper for the OpenAI function_tool decorator that handles SQLAlchemy Session objects.
    
    This decorator replaces Session objects with DBHelper instances to avoid Pydantic
    serialization issues with SQLAlchemy Session objects.
    
    Args:
        func: The function to wrap
        
    Returns:
        The wrapped function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check if we have a db or db_helper parameter
        if 'db' in kwargs and isinstance(kwargs['db'], Session):
            # Replace the db Session with a DBHelper
            db_helper = DBHelper(kwargs['db'])
            # Remove the db parameter and add the db_helper parameter
            del kwargs['db']
            kwargs['db_helper'] = db_helper
        elif 'db_helper' not in kwargs:
            # Check if the last positional argument is a Session
            if args and isinstance(args[-1], Session):
                # Convert the last positional argument to a DBHelper
                args_list = list(args)
                db_helper = DBHelper(args_list.pop())
                args = tuple(args_list)
                kwargs['db_helper'] = db_helper
        
        # Call the original function with the modified arguments
        return func(*args, **kwargs)
    
    # Apply the OpenAI function_tool decorator with a simple wrapper
    decorated = openai_function_tool(wrapper)
    return decorated
