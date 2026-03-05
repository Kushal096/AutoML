from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Optional, List, Dict, Any
from app.models import (
    User, Project,
    PredictionRequest, BatchPredictionRequest,
    PredictionResponse, BatchPredictionResponse
)
from app.core.auth import get_current_user
from app.services.prediction_service import PredictionService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
prediction_service = PredictionService()


@router.post("/predict_batch_demo")
async def predict_batch_demo(request: Dict[str, Any]):
    """
    Demo endpoint for batch prediction without authentication
    Used for testing and demonstration purposes only
    """
    try:
        project_id = request.get("project_id")
        input_data = request.get("input_data", [])
        
        if not project_id or not input_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing project_id or input_data"
            )
        
        # For demo purposes, we'll use a simple mock prediction
        # In production, this would load and use the actual model
        predictions = []
        
        for data in input_data:
            # Mock churn prediction based on features
            watch_hours = data.get("watch_hours", 0)
            days_inactive = data.get("days_inactive", 0)
            tenure_months = data.get("tenure_months", 1)
            payment_failures = data.get("payment_failures", 0)
            tier = data.get("tier", 0)
            
            # Simple model simulation
            prob = 0.85
            if watch_hours < 5:
                prob -= 0.3
            if days_inactive > 14:
                prob -= 0.25
            if tenure_months < 3:
                prob -= 0.2
            if payment_failures > 0:
                prob -= (payment_failures * 0.15)
            if tier == 2:  # Premium
                prob += 0.1
            
            prob = max(0.05, min(0.95, prob))
            
            predictions.append({
                "user_id": data.get("user_id"),
                "prediction": prob,
                "confidence": 0.85
            })
        
        return {
            "project_id": project_id,
            "model_version": 1,
            "predictions": predictions,
            "metadata": {
                "total_predictions": len(predictions),
                "successful": len(predictions),
                "failed": 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Demo batch prediction failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Demo prediction failed: {str(e)}"
        )


@router.post("/predict", response_model=PredictionResponse)
async def predict_single(
    request: PredictionRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Make a single prediction using the trained model
    
    - For Recommendation systems: provide user_id
    - For Churn Prediction: provide customer_id or user_id with optional input_data
    - For other systems: provide input_data dictionary
    """
    try:
        # Verify project exists and user has access
        project = await Project.get(request.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        if project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        # Check if project has a trained model
        if project.status != "trained":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project does not have a trained model. Please train a model first."
            )
        
        # Detect source (SDK vs Web)
        user_agent = http_request.headers.get("user-agent", "").lower()
        source_header = http_request.headers.get("x-request-source", "").lower()
        
        if "taranga" in user_agent or "sdk" in user_agent or source_header == "sdk":
            source = "sdk"
        else:
            source = "web"
        
        # Determine which ID to use
        identifier = request.user_id or request.customer_id
        
        # Make prediction
        result = await prediction_service.predict_single(
            project_id=request.project_id,
            user_id=identifier,
            input_data=request.input_data,
            customer_id=request.customer_id,
            top_k=request.top_k,
            source=source
        )
        
        # Get model version
        from app.models import Model
        latest_model = await Model.find(
            Model.project_id == request.project_id
        ).sort(-Model.version).first_or_none()
        
        return PredictionResponse(
            project_id=request.project_id,
            model_version=latest_model.version if latest_model else 1,
            predictions=result["predictions"],
            metadata=result.get("metadata")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@router.post("/predict_batch", response_model=BatchPredictionResponse)
async def predict_batch(
    request: BatchPredictionRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Make batch predictions using the trained model
    
    - For Recommendation systems: provide list of user_ids in 'users'
    - For Churn Prediction: provide list of customer_ids in 'customers' with optional input_data
    - For other systems: provide list of input_data dictionaries
    """
    try:
        # Verify project exists and user has access
        project = await Project.get(request.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        if project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        # Check if project has a trained model
        if project.status != "trained":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project does not have a trained model. Please train a model first."
            )
        
        # Make batch predictions
        results = await prediction_service.predict_batch(
            project_id=request.project_id,
            users=request.users,
            customers=request.customers,
            input_data=request.input_data,
            top_k=request.top_k
        )
        
        # Get model version
        from app.models import Model
        latest_model = await Model.find(
            Model.project_id == request.project_id
        ).sort(-Model.version).first_or_none()
        
        return BatchPredictionResponse(
            project_id=request.project_id,
            model_version=latest_model.version if latest_model else 1,
            predictions=results,
            metadata={
                "total_predictions": len(results),
                "successful": sum(1 for r in results if r.get("status") == "success"),
                "failed": sum(1 for r in results if r.get("status") == "error")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch prediction failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )


@router.get("/projects/{project_id}/prediction/status")
async def get_prediction_status(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Check if a project is ready for predictions (has a trained model)
    """
    try:
        # Verify project exists and user has access
        project = await Project.get(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        if project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        # Check for trained model
        from app.models import Model, System
        latest_model = await Model.find(
            Model.project_id == project_id
        ).sort(-Model.version).first_or_none()
        
        if not latest_model:
            return {
                "ready": False,
                "message": "No trained model available. Please train a model first.",
                "project_status": project.status
            }
        
        # Get system info
        system = await System.get(project.system_id)
        
        return {
            "ready": True,
            "message": "Project is ready for predictions",
            "project_status": project.status,
            "model_version": latest_model.version,
            "model_metrics": latest_model.metrics,
            "system_type": system.name if system else "unknown",
            "prediction_endpoint": "/api/v1/predict",
            "batch_prediction_endpoint": "/api/v1/predict_batch"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check prediction status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check prediction status: {str(e)}"
        )

