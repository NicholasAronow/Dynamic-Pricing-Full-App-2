from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

import models
from database import get_db
from auth import get_current_user
from jobs import get_job_status

# Create router
job_status_router = APIRouter(
    prefix="/jobs",
    tags=["job-status"],
    responses={404: {"description": "Not found"}},
)


@job_status_router.get("/{job_id}")
async def check_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Check the status of a background job
    """
    try:
        status = get_job_status(job_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking job status: {str(e)}")
