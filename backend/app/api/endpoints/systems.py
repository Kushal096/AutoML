from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from app.models import SystemCreate, SystemResponse, System, User
from app.core.auth import get_current_user

router = APIRouter()


@router.post("/systems", response_model=SystemResponse)
async def create_system(
    system_data: SystemCreate, 
    current_user: User = Depends(get_current_user)
):
    """
    Create a new system type (admin only for now)
    """
    try:
        # Check if system name already exists
        existing_system = await System.find_one(System.name == system_data.name)
        if existing_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"System '{system_data.name}' already exists"
            )
        
        system = System(
            name=system_data.name,
            description=system_data.description,
            default_pipeline=system_data.default_pipeline
        )
        
        await system.insert()
        
        return SystemResponse(
            id=str(system.id),
            name=system.name,
            description=system.description,
            default_pipeline=system.default_pipeline,
            created_at=system.created_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create system: {str(e)}"
        )


@router.get("/systems", response_model=List[SystemResponse])
async def list_systems():
    """
    List all available system types
    """
    try:
        systems = await System.find_all().to_list()
        
        return [
            SystemResponse(
                id=str(system.id),
                name=system.name,
                description=system.description,
                default_pipeline=system.default_pipeline,
                created_at=system.created_at
            )
            for system in systems
        ]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch systems: {str(e)}"
        )


@router.get("/systems/{system_id}", response_model=SystemResponse)
async def get_system(system_id: str):
    """
    Get a specific system by ID
    """
    try:
        system = await System.get(system_id)
        
        if not system:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System not found"
            )
        
        return SystemResponse(
            id=str(system.id),
            name=system.name,
            description=system.description,
            default_pipeline=system.default_pipeline,
            created_at=system.created_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch system: {str(e)}"
        )