"""
Feature Store API Endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging

from app.models import User, Project, FeatureDefinition, FeatureSet
from app.core.auth import get_current_user
from app.services.feature_store_service import FeatureStoreService

logger = logging.getLogger(__name__)
router = APIRouter()
feature_service = FeatureStoreService()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class FeatureDefinitionCreate(BaseModel):
    name: str
    feature_type: str  # "numerical", "categorical", "embedding", "derived"
    data_type: str  # "float", "int", "string", "array"
    source_columns: List[str]
    transformation_logic: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    project_id: Optional[str] = None


class FeatureDefinitionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    feature_type: str
    data_type: str
    source_columns: List[str]
    transformation_logic: Optional[Dict[str, Any]]
    version: int
    is_active: bool
    project_id: Optional[str]


class FeatureSetCreate(BaseModel):
    name: str
    feature_names: List[str]
    description: Optional[str] = None


class FeatureSetResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    project_id: str
    feature_names: List[str]
    version: int
    is_active: bool


class AutoGenerateFeaturesRequest(BaseModel):
    dataset_id: str


class GetFeaturesRequest(BaseModel):
    entity_id: str
    feature_names: List[str]


# ============================================================================
# FEATURE DEFINITION ENDPOINTS
# ============================================================================

@router.post("/projects/{project_id}/features/definitions", response_model=FeatureDefinitionResponse)
async def create_feature_definition(
    project_id: str,
    request: FeatureDefinitionCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new feature definition
    
    Example:
    ```json
    {
        "name": "total_purchases_log",
        "feature_type": "numerical",
        "data_type": "float",
        "source_columns": ["total_purchases"],
        "transformation_logic": {
            "type": "math",
            "operation": "log",
            "column": "total_purchases"
        },
        "description": "Log transformation of total purchases"
    }
    ```
    """
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        feature_def = await feature_service.create_feature_definition(
            name=request.name,
            feature_type=request.feature_type,
            data_type=request.data_type,
            source_columns=request.source_columns,
            transformation_logic=request.transformation_logic,
            description=request.description,
            project_id=project_id,
            user_id=str(current_user.id)
        )
        
        return FeatureDefinitionResponse(
            id=str(feature_def.id),
            name=feature_def.name,
            description=feature_def.description,
            feature_type=feature_def.feature_type,
            data_type=feature_def.data_type,
            source_columns=feature_def.source_columns,
            transformation_logic=feature_def.transformation_logic,
            version=feature_def.version,
            is_active=feature_def.is_active,
            project_id=feature_def.project_id
        )
        
    except Exception as e:
        logger.error(f"Failed to create feature definition: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create feature definition: {str(e)}"
        )


@router.get("/projects/{project_id}/features/definitions", response_model=List[FeatureDefinitionResponse])
async def get_feature_definitions(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all feature definitions for a project"""
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        feature_defs = await feature_service.get_feature_definitions(
            project_id=project_id,
            active_only=True
        )
        
        return [
            FeatureDefinitionResponse(
                id=str(fd.id),
                name=fd.name,
                description=fd.description,
                feature_type=fd.feature_type,
                data_type=fd.data_type,
                source_columns=fd.source_columns,
                transformation_logic=fd.transformation_logic,
                version=fd.version,
                is_active=fd.is_active,
                project_id=fd.project_id
            )
            for fd in feature_defs
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get feature definitions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feature definitions: {str(e)}"
        )


@router.post("/projects/{project_id}/features/auto-generate", response_model=dict)
async def auto_generate_features(
    project_id: str,
    request: AutoGenerateFeaturesRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Automatically generate common features based on dataset columns
    
    This is a smart feature engineering helper that creates:
    - Log/sqrt transformations for numerical columns
    - Normalized features
    - Label encoding for categorical columns
    """
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        generated_features = await feature_service.auto_generate_features(
            project_id=project_id,
            dataset_id=request.dataset_id,
            user_id=str(current_user.id)
        )
        
        return {
            "message": f"Successfully generated {len(generated_features)} features",
            "features": [
                {
                    "name": f.name,
                    "type": f.feature_type,
                    "description": f.description
                }
                for f in generated_features
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to auto-generate features: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to auto-generate features: {str(e)}"
        )


# ============================================================================
# FEATURE SET ENDPOINTS
# ============================================================================

@router.post("/projects/{project_id}/features/sets", response_model=FeatureSetResponse)
async def create_feature_set(
    project_id: str,
    request: FeatureSetCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a feature set (collection of features used together)
    """
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        feature_set = await feature_service.create_feature_set(
            name=request.name,
            project_id=project_id,
            feature_names=request.feature_names,
            description=request.description
        )
        
        return FeatureSetResponse(
            id=str(feature_set.id),
            name=feature_set.name,
            description=feature_set.description,
            project_id=feature_set.project_id,
            feature_names=feature_set.feature_names,
            version=feature_set.version,
            is_active=feature_set.is_active
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create feature set: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create feature set: {str(e)}"
        )


@router.get("/projects/{project_id}/features/sets", response_model=List[FeatureSetResponse])
async def get_feature_sets(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all feature sets for a project"""
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        feature_sets = await FeatureSet.find({
            "project_id": project_id,
            "is_active": True
        }).to_list()
        
        return [
            FeatureSetResponse(
                id=str(fs.id),
                name=fs.name,
                description=fs.description,
                project_id=fs.project_id,
                feature_names=fs.feature_names,
                version=fs.version,
                is_active=fs.is_active
            )
            for fs in feature_sets
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get feature sets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feature sets: {str(e)}"
        )


# ============================================================================
# FEATURE SERVING ENDPOINTS
# ============================================================================

@router.post("/projects/{project_id}/features/get", response_model=dict)
async def get_features(
    project_id: str,
    request: GetFeaturesRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Get feature values for a specific entity (for real-time serving)
    """
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        features = await feature_service.get_features_for_entity(
            entity_id=request.entity_id,
            feature_names=request.feature_names,
            project_id=project_id
        )
        
        return {
            "entity_id": request.entity_id,
            "features": features
        }
        
    except Exception as e:
        logger.error(f"Failed to get features: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get features: {str(e)}"
        )


@router.get("/projects/{project_id}/features/{feature_name}/statistics", response_model=dict)
async def get_feature_statistics(
    project_id: str,
    feature_name: str,
    days: int = 7,
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics about a feature (for monitoring)
    """
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        stats = await feature_service.get_feature_statistics(
            feature_name=feature_name,
            project_id=project_id,
            days=days
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get feature statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feature statistics: {str(e)}"
        )

