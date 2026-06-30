import uuid
from fastapi import APIRouter, HTTPException
from core.schemas import ProjectState
from core.state_manager import state_manager
from core.orchestrator import orchestrator

from typing import Optional
from pydantic import BaseModel

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""

router = APIRouter(prefix="/project", tags=["project"])

@router.get("")
async def get_project(project_id: str):
    """Mengambil status project saat ini."""
    state = await state_manager.get_project_state(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan.")
    return state

@router.post("")
async def create_project(
    body: Optional[ProjectCreate] = None,
    name: Optional[str] = None,
    description: Optional[str] = ""
):
    """Membuat proyek baru (mendukung JSON body dan backward-compatible dengan query params)."""
    proj_name = ""
    proj_desc = ""
    
    if body:
        proj_name = body.name
        proj_desc = body.description or ""
    elif name:
        proj_name = name
        proj_desc = description or ""
    else:
        raise HTTPException(status_code=400, detail="Parameter 'name' harus disertakan di query params atau request body.")

    project_id = str(uuid.uuid4())
    state = ProjectState(
        project_id=project_id,
        name=proj_name,
        description=proj_desc,
        status="init"
    )
    await state_manager.save_project_state(state)
    await orchestrator.initialize_project(project_id)
    return state
