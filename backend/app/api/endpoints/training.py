from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import logging
from app.models import (
    User, Project, Model, TrainingLogs, Dataset,
    TrainModelResponse, ModelResponse, ModelListResponse
)
from app.core.auth import get_current_user
from app.services.training_service import MLTrainingService
from app.services.monitoring_service import MonitoringService

logger = logging.getLogger(__name__)
router = APIRouter()
training_service = MLTrainingService()
monitoring_service = MonitoringService()


@router.post("/projects/{project_id}/train", response_model=TrainModelResponse)
async def train_model(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Train a machine learning model for the specified project
    Checks drift on new datasets and only trains if drift exceeds threshold
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
        
        # Check if project is already in training
        active_training = await TrainingLogs.find_one(
            {"project_id": project_id, "status": {"$in": ["started", "training"]}}
        )
        
        if active_training:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Training is already in progress for this project"
            )
        
        # Check if there's an existing model - if so, check drift on new datasets
        latest_model = await training_service.get_latest_model(project_id)
        
        if latest_model:
            # Check for new datasets uploaded after the latest model
            latest_model_time = latest_model.created_at
            all_datasets = await Dataset.find(Dataset.project_id == project_id).to_list()
            new_datasets = [d for d in all_datasets if d.uploaded_at and d.uploaded_at > latest_model_time]
            
            if new_datasets:
                # Check drift on new datasets
                logger.info(f"Found {len(new_datasets)} new dataset(s) for project {project_id}, checking drift before training...")
                datasets_to_train = []
                skipped_datasets = []
                
                for dataset in new_datasets:
                    if not dataset.storage_path:
                        logger.warning(f"Dataset {dataset.id} has no storage_path, skipping drift check")
                        datasets_to_train.append(dataset)
                        continue
                    
                    try:
                        drift_result = await monitoring_service.detect_drift_on_dataset(
                            project_id=project_id,
                            new_dataset_path=dataset.storage_path,
                            user_id=str(current_user.id)
                        )
                        
                        drift_score = drift_result.get('overall_drift_score', 0)
                        threshold = drift_result.get('threshold', 0.1)
                        drift_detected = drift_result.get('drift_detected', False)
                        
                        if drift_detected and drift_score > threshold:
                            logger.info(f"Dataset {dataset.id} has high drift (score: {drift_score:.4f} > threshold: {threshold}) - will be included in training")
                            datasets_to_train.append(dataset)
                        elif drift_result.get("error"):
                            logger.warning(f"Drift detection error for dataset {dataset.id}: {drift_result.get('error')}. Including in training as fallback.")
                            datasets_to_train.append(dataset)
                        else:
                            logger.info(f"Dataset {dataset.id} has low drift (score: {drift_score:.4f} <= threshold: {threshold}) - skipping from training")
                            skipped_datasets.append((dataset, drift_score))
                            
                    except Exception as e:
                        logger.error(f"Drift detection failed for dataset {dataset.id}: {str(e)}. Including in training as fallback.")
                        datasets_to_train.append(dataset)
                
                # If all new datasets have low drift, don't train
                if not datasets_to_train:
                    skipped_info = ", ".join([f"{d.name} (drift: {score:.4f})" for d, score in skipped_datasets])
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot train: All new datasets have low drift (below threshold 0.1). Skipped datasets: {skipped_info}. No new data to train on. Use retrain endpoint if you want to retrain on existing data."
                    )
                
                # Log which datasets will be used
                if skipped_datasets:
                    skipped_names = ", ".join([d.name for d, _ in skipped_datasets])
                    logger.info(f"Skipping {len(skipped_datasets)} dataset(s) with low drift: {skipped_names}")
        
        # Start training
        model_id, version, metrics, logs = await training_service.train_model(
            project_id, str(current_user.id)
        )
        
        # Add info about skipped datasets to logs if any
        if latest_model and 'skipped_datasets' in locals() and skipped_datasets:
            skipped_info = ", ".join([f"{d.name} (drift: {score:.4f})" for d, score in skipped_datasets])
            logs += f"\nNote: {len(skipped_datasets)} dataset(s) skipped due to low drift: {skipped_info}"
        
        return TrainModelResponse(
            message="Model training completed successfully",
            model_id=model_id,
            version=version,
            metrics=metrics,
            training_logs=logs
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Training endpoint error: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Training failed: {str(e)}"
        )


@router.post("/projects/{project_id}/retrain", response_model=TrainModelResponse)
async def retrain_model(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Retrain the model with updated data (one-click retrain)
    Checks drift on new datasets and only trains if drift exceeds threshold
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
        
        # Check if there's a previous model to compare against
        latest_model = await training_service.get_latest_model(project_id)
        
        if not latest_model:
            # No existing model, proceed with training
            logger.info(f"No existing model for project {project_id}, proceeding with initial training")
            model_id, version, metrics, logs = await training_service.train_model(
                project_id, str(current_user.id)
            )
            return TrainModelResponse(
                message="Model training completed successfully",
                model_id=model_id,
                version=version,
                metrics=metrics,
                training_logs=logs
            )
        
        # Check for new datasets uploaded after the latest model
        latest_model_time = latest_model.created_at
        all_datasets = await Dataset.find(Dataset.project_id == project_id).to_list()
        new_datasets = [d for d in all_datasets if d.uploaded_at and d.uploaded_at > latest_model_time]
        
        if not new_datasets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No new datasets found to retrain on. Upload a new dataset first."
            )
        
        # Check drift on new datasets
        logger.info(f"Found {len(new_datasets)} new dataset(s) for project {project_id}, checking drift...")
        datasets_to_train = []
        skipped_datasets = []
        
        for dataset in new_datasets:
            if not dataset.storage_path:
                logger.warning(f"Dataset {dataset.id} has no storage_path, skipping drift check")
                datasets_to_train.append(dataset)
                continue
            
            try:
                drift_result = await monitoring_service.detect_drift_on_dataset(
                    project_id=project_id,
                    new_dataset_path=dataset.storage_path,
                    user_id=str(current_user.id)
                )
                
                drift_score = drift_result.get('overall_drift_score', 0)
                threshold = drift_result.get('threshold', 0.1)
                drift_detected = drift_result.get('drift_detected', False)
                
                if drift_detected and drift_score > threshold:
                    logger.info(f"Dataset {dataset.id} has high drift (score: {drift_score:.4f} > threshold: {threshold}) - will be included in training")
                    datasets_to_train.append(dataset)
                elif drift_result.get("error"):
                    logger.warning(f"Drift detection error for dataset {dataset.id}: {drift_result.get('error')}. Including in training as fallback.")
                    datasets_to_train.append(dataset)
                else:
                    logger.info(f"Dataset {dataset.id} has low drift (score: {drift_score:.4f} <= threshold: {threshold}) - skipping from training")
                    skipped_datasets.append((dataset, drift_score))
                    
            except Exception as e:
                logger.error(f"Drift detection failed for dataset {dataset.id}: {str(e)}. Including in training as fallback.")
                datasets_to_train.append(dataset)
        
        # If all new datasets have low drift, don't retrain
        if not datasets_to_train:
            skipped_info = ", ".join([f"{d.name} (drift: {score:.4f})" for d, score in skipped_datasets])
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot retrain: All new datasets have low drift (below threshold 0.1). Skipped datasets: {skipped_info}. No new data to train on."
            )
        
        # Log which datasets will be used
        if skipped_datasets:
            skipped_names = ", ".join([d.name for d, _ in skipped_datasets])
            logger.info(f"Skipping {len(skipped_datasets)} dataset(s) with low drift: {skipped_names}")
        
        # Retrain the model (will use all datasets, but we've validated that new ones have high drift)
        # Note: The training service loads all datasets, but we've checked drift on new ones
        model_id, version, metrics, logs = await training_service.train_model(
            project_id, str(current_user.id)
        )
        
        # Add info about skipped datasets to logs
        if skipped_datasets:
            skipped_info = ", ".join([f"{d.name} (drift: {score:.4f})" for d, score in skipped_datasets])
            logs += f"\nNote: {len(skipped_datasets)} dataset(s) skipped due to low drift: {skipped_info}"
        
        # Check if new model should be promoted
        if latest_model:
            should_promote = await training_service.should_promote_model(project_id, metrics)
            promotion_msg = "Model promoted as performance improved" if should_promote else "Model trained but performance did not improve"
            logs += f"\n{promotion_msg}"
        
        return TrainModelResponse(
            message="Model retraining completed successfully",
            model_id=model_id,
            version=version,
            metrics=metrics,
            training_logs=logs
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Retraining failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retraining failed: {str(e)}"
        )


@router.get("/projects/{project_id}/models", response_model=ModelResponse)
async def get_latest_model(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the latest model for the specified project
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
        
        # Get latest model
        latest_model = await training_service.get_latest_model(project_id)
        
        if not latest_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No models found for this project"
            )
        
        return ModelResponse(
            id=str(latest_model.id),
            project_id=latest_model.project_id,
            version=latest_model.version,
            storage_path=latest_model.storage_path,
            metrics=latest_model.metrics,
            created_at=latest_model.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch model: {str(e)}"
        )


@router.get("/projects/{project_id}/models/all", response_model=ModelListResponse)
async def get_all_models(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all model versions for the specified project
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
        
        # Get all models
        models = await training_service.get_all_models(project_id)
        
        if not models:
            return ModelListResponse(
                models=[],
                latest_version=0,
                total_models=0
            )
        
        model_responses = [
            ModelResponse(
                id=str(model.id),
                project_id=model.project_id,
                version=model.version,
                storage_path=model.storage_path,
                metrics=model.metrics,
                created_at=model.created_at
            )
            for model in models
        ]
        
        return ModelListResponse(
            models=model_responses,
            latest_version=models[0].version if models else 0,
            total_models=len(models)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch models: {str(e)}"
        )


@router.get("/projects/{project_id}/training/status", response_model=dict)
async def get_training_status(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the current training status for the specified project
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
        
        # Get latest training log
        latest_log = await TrainingLogs.find(
            {"project_id": project_id}
        ).sort("-created_at").first_or_none()
        
        if not latest_log:
            return {
                "status": "no_training",
                "message": "No training has been started for this project",
                "logs": ""
            }
        
        return {
            "status": latest_log.status,
            "model_id": latest_log.model_id,
            "logs": latest_log.logs,
            "created_at": latest_log.created_at,
            "last_updated": latest_log.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch training status: {str(e)}"
        )


@router.get("/projects/{project_id}/models/{model_id}/details", response_model=dict)
async def get_model_details(
    project_id: str,
    model_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed statistics for a specific model
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
        
        # Get model
        model = await Model.get(model_id)
        if not model or model.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found"
            )
        
        # Return detailed model information with all metrics
        return {
            "model_id": str(model.id),
            "project_id": model.project_id,
            "version": model.version,
            "created_at": model.created_at,
            "metrics": model.metrics,
            "storage_path": model.storage_path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model details: {str(e)}"
        )