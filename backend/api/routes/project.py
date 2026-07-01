import uuid
import os
import shutil
from fastapi import APIRouter, HTTPException
from core.schemas import ProjectState
from core.state_manager import state_manager
from core.orchestrator import orchestrator
from config import settings

from typing import Optional, List
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    external_path: Optional[str] = None


class FileItem(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int = 0


router = APIRouter(prefix="/project", tags=["project"])


@router.get("")
async def get_project(project_id: str):
    """Mengambil status project saat ini."""
    state = await state_manager.get_project_state(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan.")
    return state


@router.get("/list", response_model=List[ProjectState])
async def list_projects():
    """Mengambil riwayat semua proyek yang pernah dibuat."""
    return await state_manager.get_all_projects()


@router.post("")
async def create_project(
    body: Optional[ProjectCreate] = None,
    name: Optional[str] = None,
    description: Optional[str] = "",
    external_path: Optional[str] = None
):
    """Membuat proyek baru (mendukung JSON body dan backward-compatible dengan query params)."""
    proj_name = ""
    proj_desc = ""
    proj_ext_path = None

    if body:
        proj_name = body.name
        proj_desc = body.description or ""
        proj_ext_path = body.external_path
    elif name:
        proj_name = name
        proj_desc = description or ""
        proj_ext_path = external_path
    else:
        raise HTTPException(status_code=400, detail="Parameter 'name' harus disertakan di query params atau request body.")

    project_id = str(uuid.uuid4())
    state = ProjectState(
        project_id=project_id,
        name=proj_name,
        description=proj_desc,
        external_path=proj_ext_path,
        status="init"
    )
    await state_manager.save_project_state(state)
    await orchestrator.initialize_project(project_id)
    return state


@router.put("")
async def update_project(
    project_id: str,
    body: ProjectCreate
):
    """Memperbarui informasi proyek (nama dan deskripsi)."""
    state = await state_manager.get_project_state(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan.")
        
    state.name = body.name
    state.description = body.description or ""
    # External path tidak boleh diubah untuk mencegah path traversal issue post-creation
    
    await state_manager.save_project_state(state)
    return state


@router.delete("")
async def delete_project(project_id: str):
    """Menghapus proyek beserta file sandbox-nya secara permanen."""
    state = await state_manager.get_project_state(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan.")
        
    # Hapus file fisik
    root_path = _resolve_workspace_path(state)
    if os.path.exists(root_path) and not state.external_path: 
        # Hanya hapus isi folder jika itu adalah default sandbox (bukan external map)
        try:
            shutil.rmtree(root_path, ignore_errors=True)
            # Jika folder masih membandel, coba paksa dengan OS
            if os.path.exists(root_path):
                import subprocess
                subprocess.run(["rm", "-rf", root_path], check=False)
        except Exception as e:
            print(f"ERROR: Gagal menghapus folder {root_path}: {e}")
            pass
            
    # Hapus dari db/redis
    success = await state_manager.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=500, detail="Gagal menghapus proyek dari database.")
        
    return {"status": "success", "message": "Proyek berhasil dihapus"}


def _resolve_workspace_path(state: ProjectState) -> str:
    """Menentukan path workspace proyek berdasarkan external_path atau project_id."""
    if state.external_path:
        return os.path.abspath(state.external_path)
    return os.path.abspath(os.path.join(settings.WORKSPACE_ROOT, state.project_id))


@router.get("/workspace-path")
async def get_workspace_path(project_id: str):
    """Mengembalikan path folder workspace proyek di dalam container."""
    state = await state_manager.get_project_state(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan.")

    root_path = _resolve_workspace_path(state)
    try:
        os.makedirs(root_path, exist_ok=True)
    except OSError:
        pass

    return {
        "project_id": project_id,
        "project_name": state.name,
        "workspace_path": root_path,
        "external_path": state.external_path,
        "exists": os.path.exists(root_path),
        "file_count": sum(len(files) for _, _, files in os.walk(root_path)),
    }


@router.get("/files", response_model=List[FileItem])
async def get_project_files(project_id: str):
    """Membaca daftar file & folder di dalam workspace sandbox proyek secara dinamis."""
    state = await state_manager.get_project_state(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan.")

    root_path = _resolve_workspace_path(state)

    # Buat folder otomatis jika belum ada (backward compat proyek lama)
    try:
        os.makedirs(root_path, exist_ok=True)
    except OSError:
        pass

    files_list = []
    # Daftar folder yang diabaikan demi performa & kerapian
    ignored_dirs = {".git", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}

    for root, dirs, files in os.walk(root_path):
        # Filter directory yang diabaikan
        dirs[:] = [d for d in dirs if d not in ignored_dirs]

        for d in dirs:
            full_path = os.path.join(root, d)
            rel_path = os.path.relpath(full_path, root_path)
            files_list.append(FileItem(
                name=d,
                path=rel_path,
                is_dir=True,
                size=0
            ))

        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, root_path)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0
            files_list.append(FileItem(
                name=f,
                path=rel_path,
                is_dir=False,
                size=size
            ))

    # Urutkan folder dahulu kemudian file alfabetis
    files_list.sort(key=lambda x: (not x.is_dir, x.path.lower()))
    return files_list
