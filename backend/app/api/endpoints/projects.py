from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from datetime import datetime
from app.models import (
    ProjectCreate, ProjectUpdate, ProjectResponse, 
    Project, System, User
)
from app.core.auth import get_current_user

router = APIRouter()


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new project for the current user.
    System ID is optional - if not provided, it will be determined by LLM during dataset upload.
    """
    try:
        # Verify that the system exists (only if system_id is provided)
        if project_data.system_id:
            system = await System.get(project_data.system_id)
            if not system:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid system ID"
                )
        
        # Check if project with same name already exists for this user
        existing_project = await Project.find_one(
            Project.user_id == str(current_user.id),
            Project.name == project_data.name,
            Project.status != "deleted"  # Don't count deleted projects
        )
        
        if existing_project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project '{project_data.name}' already exists"
            )
        
        project = Project(
            user_id=str(current_user.id),
            name=project_data.name,
            system_id=project_data.system_id,  # Can be None - will be set by LLM later
            status="created"
        )
        
        await project.insert()
        
        return ProjectResponse(
            id=str(project.id),
            user_id=project.user_id,
            name=project.name,
            system_id=project.system_id,  # Can be None - will be set by LLM later
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get("/projects", response_model=List[ProjectResponse])
async def list_user_projects(
    current_user: User = Depends(get_current_user)
):
    """
    List all projects for the current user (excluding soft-deleted projects, sorted by latest first)
    """
    try:
        projects = await Project.find(
            Project.user_id == str(current_user.id),
            Project.status != "deleted"
        ).sort(-Project.created_at).to_list()
        
        return [
            ProjectResponse(
                id=str(project.id),
                user_id=project.user_id,
                name=project.name,
                system_id=project.system_id,
                status=project.status,
                created_at=project.created_at,
                updated_at=project.updated_at
            )
            for project in projects
        ]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects: {str(e)}"
        )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific project by ID (user can only access their own projects)
    """
    try:
        project = await Project.get(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if the project belongs to the current user
        if project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. This project belongs to another user."
            )
        
        return ProjectResponse(
            id=str(project.id),
            user_id=project.user_id,
            name=project.name,
            system_id=project.system_id,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project: {str(e)}"
        )


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update a project (user can only update their own projects)
    """
    try:
        project = await Project.get(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if the project belongs to the current user
        if project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. This project belongs to another user."
            )
        
        # Update fields that are provided
        update_data = project_update.model_dump(exclude_unset=True)
        
        if update_data:
            for field, value in update_data.items():
                setattr(project, field, value)
            
            project.updated_at = datetime.utcnow()
            await project.save()
        
        return ProjectResponse(
            id=str(project.id),
            user_id=project.user_id,
            name=project.name,
            system_id=project.system_id,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete a project (user can only delete their own projects)
    """
    try:
        project = await Project.get(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if the project belongs to the current user
        if project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. This project belongs to another user."
            )
        
        # Soft delete by updating status
        project.status = "deleted"
        project.updated_at = datetime.utcnow()
        await project.save()
        
        return {"message": f"Project '{project.name}' has been deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )


@router.get("/projects/duplicates")
async def find_duplicate_projects(
    current_user: User = Depends(get_current_user)
):
    """
    Find duplicate projects for the current user (for cleanup purposes)
    """
    try:
        # Get all projects for the user (excluding deleted ones)
        projects = await Project.find(
            Project.user_id == str(current_user.id),
            Project.status != "deleted"
        ).to_list()
        
        # Group by name to find duplicates
        name_groups = {}
        for project in projects:
            if project.name not in name_groups:
                name_groups[project.name] = []
            name_groups[project.name].append(project)
        
        # Find duplicates (groups with more than 1 project)
        duplicates = {}
        for name, project_list in name_groups.items():
            if len(project_list) > 1:
                duplicates[name] = [
                    {
                        "id": str(p.id),
                        "name": p.name,
                        "created_at": p.created_at,
                        "status": p.status
                    }
                    for p in sorted(project_list, key=lambda x: x.created_at)
                ]
        
        return {
            "total_duplicate_groups": len(duplicates),
            "duplicates": duplicates
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find duplicates: {str(e)}"
        )


@router.delete("/projects/duplicates/cleanup")
async def cleanup_duplicate_projects(
    current_user: User = Depends(get_current_user)
):
    """
    Remove duplicate projects, keeping only the oldest one for each name
    """
    try:
        # Get all projects for the user (excluding deleted ones)
        projects = await Project.find(
            Project.user_id == str(current_user.id),
            Project.status != "deleted"
        ).to_list()
        
        # Group by name to find duplicates
        name_groups = {}
        for project in projects:
            if project.name not in name_groups:
                name_groups[project.name] = []
            name_groups[project.name].append(project)
        
        deleted_count = 0
        kept_projects = []
        
        # For each group with duplicates, keep the oldest and delete the rest
        for name, project_list in name_groups.items():
            if len(project_list) > 1:
                # Sort by creation date, keep the oldest
                sorted_projects = sorted(project_list, key=lambda x: x.created_at)
                oldest = sorted_projects[0]
                kept_projects.append(str(oldest.id))
                
                # Delete the duplicates (newer ones)
                for project in sorted_projects[1:]:
                    project.status = "deleted"
                    project.updated_at = datetime.utcnow()
                    await project.save()
                    deleted_count += 1
        
        return {
            "message": f"Cleanup completed. Deleted {deleted_count} duplicate projects.",
            "deleted_count": deleted_count,
            "kept_projects": kept_projects
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup duplicates: {str(e)}"
        )