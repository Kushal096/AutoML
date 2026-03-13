"""
Model Registry API Endpoints
Enhanced model management with versioning, lineage, and governance
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging

from app.models import User, Project, Model
from app.core.auth import get_current_user
from app.services.model_registry_service import ModelRegistryService

logger = logging.getLogger(__name__)
router = APIRouter()
registry_service = ModelRegistryService()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ModelApprovalRequest(BaseModel):
    deployment_stage: str = "staging"  # "staging" or "production"


class ModelComparisonRequest(BaseModel):
    model_id_1: str
    model_id_2: str


# ============================================================================
# MODEL REGISTRY ENDPOINTS
# ============================================================================

@router.get("/projects/{project_id}/registry/models/{model_id}/metadata", response_model=dict)
async def get_model_metadata(
    project_id: str,
    model_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive metadata for a model including governance info
    """
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        # Get model
        model = await Model.get(model_id)
        if not model or model.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found"
            )
        
        # Get registry metadata
        metadata = await registry_service.get_model_metadata(model_id)
        
        return {
            "model_id": model_id,
            "version": model.version,
            "metrics": model.metrics,
            "created_at": model.created_at,
            "storage_path": model.storage_path,
            "registry_metadata": {
                "training_dataset_ids": metadata.training_dataset_ids if metadata else [],
                "feature_set_id": metadata.feature_set_id if metadata else None,
                "training_duration_seconds": metadata.training_duration_seconds if metadata else None,
                "approval_status": metadata.approval_status if metadata else "unknown",
                "deployment_stage": metadata.deployment_stage if metadata else "unknown",
                "approved_by": metadata.approved_by if metadata else None,
                "approved_at": metadata.approved_at if metadata else None,
                "total_predictions": metadata.total_predictions if metadata else 0,
                "last_prediction_at": metadata.last_prediction_at if metadata else None,
                "tags": metadata.tags if metadata else []
            } if metadata else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model metadata: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model metadata: {str(e)}"
        )


@router.get("/projects/{project_id}/registry/models/{model_id}/lineage", response_model=dict)
async def get_model_lineage(
    project_id: str,
    model_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the full lineage of a model (parent models, children, etc.)
    This shows the evolution and relationships of models
    """
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        lineage = await registry_service.get_model_lineage(model_id)
        
        return lineage
        
    except Exception as e:
        logger.error(f"Failed to get model lineage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model lineage: {str(e)}"
        )


@router.post("/projects/{project_id}/registry/models/{model_id}/approve", response_model=dict)
async def approve_model(
    project_id: str,
    model_id: str,
    request: ModelApprovalRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Approve a model for deployment to staging or production
    """
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        # Validate deployment stage
        if request.deployment_stage not in ["staging", "production"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deployment stage must be 'staging' or 'production'"
            )
        
        metadata = await registry_service.approve_model(
            model_id=model_id,
            approved_by=str(current_user.id),
            deployment_stage=request.deployment_stage
        )
        
        return {
            "message": f"Model approved for {request.deployment_stage}",
            "model_id": model_id,
            "approval_status": metadata.approval_status,
            "deployment_stage": metadata.deployment_stage,
            "approved_by": metadata.approved_by,
            "approved_at": metadata.approved_at
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve model: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve model: {str(e)}"
        )


@router.post("/projects/{project_id}/registry/models/{model_id}/promote", response_model=dict)
async def promote_to_production(
    project_id: str,
    model_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Promote a model to production (must be approved first)
    This will demote the current production model
    """
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        metadata = await registry_service.promote_to_production(
            model_id=model_id,
            user_id=str(current_user.id)
        )
        
        return {
            "message": "Model promoted to production",
            "model_id": model_id,
            "deployment_stage": metadata.deployment_stage,
            "promoted_at": metadata.updated_at
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to promote model: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to promote model: {str(e)}"
        )


@router.get("/projects/{project_id}/registry/production", response_model=dict)
async def get_production_model(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the current production model for a project
    """
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        model = await registry_service.get_production_model(project_id)
        
        if not model:
            return {
                "message": "No production model found",
                "model": None
            }
        
        metadata = await registry_service.get_model_metadata(str(model.id))
        
        return {
            "model": {
                "id": str(model.id),
                "version": model.version,
                "metrics": model.metrics,
                "created_at": model.created_at,
                "total_predictions": metadata.total_predictions if metadata else 0,
                "last_prediction_at": metadata.last_prediction_at if metadata else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get production model: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get production model: {str(e)}"
        )


@router.get("/projects/{project_id}/registry/stage/{deployment_stage}", response_model=dict)
async def get_models_by_stage(
    project_id: str,
    deployment_stage: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all models in a specific deployment stage
    Stages: development, staging, production, archived
    """
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        models = await registry_service.get_models_by_stage(
            project_id=project_id,
            deployment_stage=deployment_stage
        )
        
        return {
            "deployment_stage": deployment_stage,
            "models": models,
            "total": len(models)
        }
        
    except Exception as e:
        logger.error(f"Failed to get models by stage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get models by stage: {str(e)}"
        )


@router.post("/projects/{project_id}/registry/compare", response_model=dict)
async def compare_models(
    project_id: str,
    request: ModelComparisonRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Compare two models side by side
    Shows metric differences and improvements
    """
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        comparison = await registry_service.compare_models(
            model_id_1=request.model_id_1,
            model_id_2=request.model_id_2
        )
        
        return comparison
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to compare models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare models: {str(e)}"
        )


@router.get("/projects/{project_id}/registry/summary", response_model=dict)
async def get_registry_summary(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get a summary of all models in the registry for a project
    Provides overview of deployment stages, approval status, etc.
    """
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        summary = await registry_service.get_registry_summary(project_id)
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get registry summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get registry summary: {str(e)}"
        )

