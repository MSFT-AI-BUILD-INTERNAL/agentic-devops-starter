"""Use cases for Fleet and Infinite Session background jobs."""

import asyncio

from fastapi import HTTPException

from src.jobs import create_job, get_job, run_fleet, run_infinite_session
from src.models import FleetRequest, InfiniteSessionRequest, JobStatusResponse


async def start_fleet_job(request: FleetRequest) -> dict[str, str]:
    """Start a Fleet job for a batch of prompts."""
    job_id = create_job()
    items = [(item.prompt, item.system_message) for item in request.items]
    asyncio.create_task(run_fleet(job_id, items))
    return {"job_id": job_id}


async def start_infinite_session_job(request: InfiniteSessionRequest) -> dict[str, str]:
    """Start an Infinite Session job for chained reasoning."""
    job_id = create_job()
    asyncio.create_task(
        run_infinite_session(job_id, request.prompt, request.iterations, request.system_message)
    )
    return {"job_id": job_id}


async def get_job_status(job_id: str) -> JobStatusResponse:
    """Return the current status for a background job."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
