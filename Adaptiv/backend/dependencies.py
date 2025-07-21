from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from config.database import get_db
from models import User
from routers.auth import get_current_user

# Define typed dependencies for better Pydantic compatibility
SessionDep = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

# Create a database helper that wraps a session dependency
class DBSessionDep:
    """A helper class that wraps a database session dependency."""
    
    def __init__(self, session: Session):
        self.session = session
        
    @classmethod
    def get_dependency(cls):
        """Get a dependency that returns a DBSessionDep instance."""
        async def _get_db_session_dep(session: SessionDep) -> "DBSessionDep":
            return cls(session)
        return _get_db_session_dep

# Create a dependency that returns a DBSessionDep instance
get_db_session_dep = DBSessionDep.get_dependency()
DBSession = Annotated[DBSessionDep, Depends(get_db_session_dep)]
