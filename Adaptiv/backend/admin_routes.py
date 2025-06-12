"""
Admin routes for database maintenance and management tasks.
"""
import os
import importlib.util
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db

admin_router = APIRouter()

class MigrationRequest(BaseModel):
    admin_key: str

@admin_router.post("/run-migrations")
async def run_migrations(
    request: MigrationRequest,
    db: Session = Depends(get_db)
):
    """Run all database migrations with secure admin key"""
    # Get admin key from environment
    admin_key = os.getenv("ADMIN_KEY", "")
    
    # Verify admin key for security
    if not admin_key or request.admin_key != admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key"
        )
    
    # Get migrations directory
    migrations_dir = Path(__file__).parent / "migrations"
    results = {}
    
    if not migrations_dir.exists():
        return {"message": "No migrations directory found", "results": {}}
    
    # Run each migration script
    for migration_file in migrations_dir.glob("*.py"):
        if migration_file.name == "__init__.py":
            continue
            
        try:
            # Import the migration file
            spec = importlib.util.spec_from_file_location(
                migration_file.stem, migration_file)
            migration_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration_module)
            
            # Run the upgrade function if it exists
            if hasattr(migration_module, "upgrade"):
                success = migration_module.upgrade()
                results[migration_file.name] = "Success" if success else "Failed"
            else:
                results[migration_file.name] = "No upgrade function found"
        except Exception as e:
            results[migration_file.name] = f"Error: {str(e)}"
    
    return {
        "message": "Migrations completed",
        "results": results
    }

class CheckDBRequest(BaseModel):
    admin_key: str

@admin_router.post("/check-schema")
async def check_db_schema(
    request: CheckDBRequest,
    db: Session = Depends(get_db)
):
    """Check database schema for debugging"""
    # Get admin key from environment
    admin_key = os.getenv("ADMIN_KEY", "")
    
    # Verify admin key for security
    if not admin_key or request.admin_key != admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key"
        )
    
    try:
        from sqlalchemy import inspect
        
        # Get inspector to check database structure
        inspector = inspect(db.bind)
        
        # Get all tables
        tables = inspector.get_table_names()
        result = {}
        
        # For each table, get columns
        for table in tables:
            columns = inspector.get_columns(table)
            result[table] = [{"name": col["name"], "type": str(col["type"])} for col in columns]
        
        return {"schema": result}
    except Exception as e:
        return {"error": str(e)}
