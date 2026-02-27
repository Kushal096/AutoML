from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form, BackgroundTasks
from typing import List, Dict, Any, Optional
from app.models import (
    User, Dataset, DataColumn, Project, System, Model,
    DatasetResponse, DataColumnResponse, DatasetUploadResponse,
    ColumnMappingRequest
)
from app.core.auth import get_current_user
from app.services.dataset_service import DatasetService
from app.services.system_schemas import SystemSchemaResolver
from app.services.training_service import MLTrainingService
from app.services.monitoring_service import MonitoringService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
monitoring_service = MonitoringService()


@router.post("/datasets/upload", response_model=DatasetUploadResponse)
async def upload_dataset_web(
    background_tasks: BackgroundTasks,
    project_id: str = Form(...),
    file: UploadFile = File(...),
    context: Optional[str] = Form(None),  # User's description of what they want to do
    column_mapping: Optional[str] = Form(None),  # JSON string of column mappings
    auto_train: bool = Form(True),  # Automatically train after upload
    current_user: User = Depends(get_current_user)
):
    """
    Upload CSV/Excel file from web form-data
    Now with intelligent LLM-based system detection and auto-training!
    
    Parameters:
    - context: Describe what you want to do (e.g., "I want a movie recommendation system")
    - column_mapping: Optional manual column mappings (LLM will suggest if not provided)
    - auto_train: Automatically start training after upload (default: True)
    """
    try:
        # Validate file type
        if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="Only CSV and Excel files are supported"
            )
        
        # Parse column mapping if provided
        mapping = None
        if column_mapping:
            try:
                import json
                mapping = json.loads(column_mapping)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid column_mapping JSON format"
                )
        
        # Process upload with LLM analysis
        dataset, columns = await DatasetService.process_web_upload(
            file, project_id, str(current_user.id), mapping, context
        )
        
        # Convert to response format
        column_responses = [
            DataColumnResponse(
                id=str(col.id),
                dataset_id=col.dataset_id,
                project_id=col.project_id,
                column_name=col.column_name,
                original_type=col.original_type,
                mapped_type=col.mapped_type,
                is_required=col.is_required,
                sample_values=col.sample_values,
                null_count=col.null_count,
                unique_count=col.unique_count
            ) for col in columns
        ]
        
        # Check if a model already exists - if so, detect drift on the new dataset
        drift_result = None
        should_train = True
        existing_model = await Model.find(
            {"project_id": project_id}
        ).sort("-version").first_or_none()
        
        if existing_model and dataset.storage_path:
            logger.info(f"Model exists (version {existing_model.version}) for project {project_id}, running drift detection on new dataset: {dataset.storage_path}")
            try:
                drift_result = await monitoring_service.detect_drift_on_dataset(
                    project_id=project_id,
                    new_dataset_path=dataset.storage_path,
                    user_id=str(current_user.id)
                )
                if drift_result.get("drift_detected"):
                    logger.warning(f"⚠️ DRIFT DETECTED in new dataset for project {project_id}: overall_score={drift_result.get('overall_drift_score', 0):.4f}, threshold={drift_result.get('threshold', 0.1)}")
                    logger.info(f"Drift exceeds threshold - training will proceed")
                    should_train = True
                elif drift_result.get("error"):
                    logger.error(f"Drift detection error for project {project_id}: {drift_result.get('error')}")
                    # On error, allow training to proceed (fallback behavior)
                    should_train = True
                else:
                    drift_score = drift_result.get('overall_drift_score', 0)
                    threshold = drift_result.get('threshold', 0.1)
                    logger.info(f"No significant drift detected in new dataset for project {project_id}: overall_score={drift_score:.4f}, threshold={threshold}")
                    logger.info(f"Drift score ({drift_score:.4f}) is below threshold ({threshold}) - skipping training")
                    should_train = False
            except Exception as e:
                logger.error(f"Drift detection failed during dataset upload for project {project_id}: {str(e)}", exc_info=True)
                # On exception, allow training to proceed (fallback behavior)
                should_train = True
        else:
            if not existing_model:
                logger.info(f"No model exists yet for project {project_id}, skipping drift detection - training will proceed")
                should_train = True
            elif not dataset.storage_path:
                logger.warning(f"Dataset has no storage_path for project {project_id}, skipping drift detection - training will proceed")
                should_train = True
        
        # Auto-train only if drift exceeds threshold (or if no model exists yet)
        if auto_train and dataset.suggested_system_type and should_train:
            logger.info(f"Auto-training enabled for project {project_id}")
            # Start training in background
            background_tasks.add_task(
                _auto_train_model,
                project_id,
                str(current_user.id)
            )
            message = f"Dataset '{dataset.name}' uploaded successfully. Training started automatically with {dataset.suggested_system_type}!"
        elif auto_train and dataset.suggested_system_type and not should_train:
            drift_score = drift_result.get('overall_drift_score', 0) if drift_result else 0
            threshold = drift_result.get('threshold', 0.1) if drift_result else 0.1
            message = f"Dataset '{dataset.name}' uploaded successfully. Drift detected (score: {drift_score:.4f}) but below threshold ({threshold}) - training skipped. Retrain manually if needed."
            logger.info(f"Training skipped due to low drift score for project {project_id}")
        else:
            message = f"Dataset '{dataset.name}' uploaded successfully. LLM suggests: {dataset.suggested_system_type or 'N/A'}"
        
        # Add drift detection info to response
        response_data = {
            "dataset_id": str(dataset.id),
            "message": message,
            "columns": column_responses,
            "llm_analysis": dataset.llm_analysis,
            "suggested_system_type": dataset.suggested_system_type,
            "column_mappings": dataset.column_mappings,
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "file_size": dataset.file_size,
            "file_type": dataset.file_type,
            "dataset_name": dataset.name
        }
        
        if drift_result:
            response_data["drift_detection"] = {
                "drift_detected": drift_result.get("drift_detected", False),
                "overall_drift_score": drift_result.get("overall_drift_score", 0),
                "features_checked": drift_result.get("features_checked", 0),
                "features_with_drift": [
                    f["feature"] for f in drift_result.get("features", [])
                    if f.get("status") == "drift_detected"
                ]
            }
        
        return DatasetUploadResponse(**response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload dataset: {str(e)}"
        )


@router.post("/datasets/{project_id}/upload_sdk", response_model=DatasetUploadResponse)
async def upload_dataset_sdk(
    background_tasks: BackgroundTasks,
    project_id: str,
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Upload JSON/pandas DataFrame from SDK
    Now with intelligent LLM-based system detection and auto-training!
    
    Expected data format:
    {
        "data": {...},  # The actual dataset
        "context": "I want a movie recommendation system",  # Optional user context
        "auto_train": true  # Optional: automatically train after upload (default: true)
    }
    """
    try:
        # Validate data format
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=400,
                detail="Data must be a dictionary/JSON object"
            )
        
        # Extract context and auto_train flag if provided
        context = data.get("context", None)
        auto_train = data.get("auto_train", True)  # Default to True
        dataset_data = data.get("data", data)  # Support both formats
        
        # Process upload with LLM analysis
        dataset, columns = await DatasetService.process_sdk_upload(
            dataset_data, project_id, str(current_user.id), context
        )
        
        # Convert to response format
        column_responses = [
            DataColumnResponse(
                id=str(col.id),
                dataset_id=col.dataset_id,
                project_id=col.project_id,
                column_name=col.column_name,
                original_type=col.original_type,
                mapped_type=col.mapped_type,
                is_required=col.is_required,
                sample_values=col.sample_values,
                null_count=col.null_count,
                unique_count=col.unique_count
            ) for col in columns
        ]
        
        # Check if a model already exists - if so, detect drift on the new dataset
        drift_result = None
        should_train = True
        existing_model = await Model.find(
            {"project_id": project_id}
        ).sort("-version").first_or_none()
        
        if existing_model and dataset.storage_path:
            logger.info(f"Model exists (version {existing_model.version}) for project {project_id}, running drift detection on new dataset: {dataset.storage_path}")
            try:
                drift_result = await monitoring_service.detect_drift_on_dataset(
                    project_id=project_id,
                    new_dataset_path=dataset.storage_path,
                    user_id=str(current_user.id)
                )
                if drift_result.get("drift_detected"):
                    logger.warning(f"⚠️ DRIFT DETECTED in new dataset for project {project_id}: overall_score={drift_result.get('overall_drift_score', 0):.4f}, threshold={drift_result.get('threshold', 0.1)}")
                    logger.info(f"Drift exceeds threshold - training will proceed")
                    should_train = True
                elif drift_result.get("error"):
                    logger.error(f"Drift detection error for project {project_id}: {drift_result.get('error')}")
                    # On error, allow training to proceed (fallback behavior)
                    should_train = True
                else:
                    drift_score = drift_result.get('overall_drift_score', 0)
                    threshold = drift_result.get('threshold', 0.1)
                    logger.info(f"No significant drift detected in new dataset for project {project_id}: overall_score={drift_score:.4f}, threshold={threshold}")
                    logger.info(f"Drift score ({drift_score:.4f}) is below threshold ({threshold}) - skipping training")
                    should_train = False
            except Exception as e:
                logger.error(f"Drift detection failed during dataset upload for project {project_id}: {str(e)}", exc_info=True)
                # On exception, allow training to proceed (fallback behavior)
                should_train = True
        else:
            if not existing_model:
                logger.info(f"No model exists yet for project {project_id}, skipping drift detection - training will proceed")
                should_train = True
            elif not dataset.storage_path:
                logger.warning(f"Dataset has no storage_path for project {project_id}, skipping drift detection - training will proceed")
                should_train = True
        
        # Auto-train only if drift exceeds threshold (or if no model exists yet)
        if auto_train and dataset.suggested_system_type and should_train:
            logger.info(f"Auto-training enabled for project {project_id} (SDK upload)")
            # Start training in background
            background_tasks.add_task(
                _auto_train_model,
                project_id,
                str(current_user.id)
            )
            message = f"Dataset uploaded successfully via SDK. Training started automatically with {dataset.suggested_system_type}!"
        elif auto_train and dataset.suggested_system_type and not should_train:
            drift_score = drift_result.get('overall_drift_score', 0) if drift_result else 0
            threshold = drift_result.get('threshold', 0.1) if drift_result else 0.1
            message = f"Dataset uploaded successfully via SDK. Drift detected (score: {drift_score:.4f}) but below threshold ({threshold}) - training skipped. Retrain manually if needed."
            logger.info(f"Training skipped due to low drift score for project {project_id}")
        else:
            message = f"Dataset uploaded successfully via SDK. LLM suggests: {dataset.suggested_system_type or 'N/A'}"
        
        # Add drift detection info to response
        response_data = {
            "dataset_id": str(dataset.id),
            "message": message,
            "columns": column_responses,
            "llm_analysis": dataset.llm_analysis,
            "suggested_system_type": dataset.suggested_system_type,
            "column_mappings": dataset.column_mappings,
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "file_size": dataset.file_size,
            "file_type": dataset.file_type,
            "dataset_name": dataset.name
        }
        
        if drift_result:
            response_data["drift_detection"] = {
                "drift_detected": drift_result.get("drift_detected", False),
                "overall_drift_score": drift_result.get("overall_drift_score", 0),
                "features_checked": drift_result.get("features_checked", 0),
                "features_with_drift": [
                    f["feature"] for f in drift_result.get("features", [])
                    if f.get("status") == "drift_detected"
                ]
            }
        
        return DatasetUploadResponse(**response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SDK upload failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload dataset via SDK: {str(e)}"
        )


@router.get("/datasets/project/{project_id}", response_model=List[DatasetResponse])
async def list_datasets(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    List all datasets for a project
    """
    try:
        datasets = await DatasetService.get_project_datasets(
            project_id, str(current_user.id)
        )
        
        return [
            DatasetResponse(
                id=str(dataset.id),
                project_id=dataset.project_id,
                name=dataset.name,
                storage_path=dataset.storage_path,
                file_size=dataset.file_size,
                file_type=dataset.file_type,
                row_count=dataset.row_count,
                column_count=dataset.column_count,
                metadata=dataset.metadata,
                uploaded_at=dataset.uploaded_at,
                status=dataset.status
            ) for dataset in datasets
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list datasets: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list datasets: {str(e)}"
        )


@router.get("/datasets/{dataset_id}/columns", response_model=List[DataColumnResponse])
async def get_dataset_columns(
    dataset_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all columns for a dataset with their types and metadata
    """
    try:
        columns = await DatasetService.get_dataset_columns(
            dataset_id, str(current_user.id)
        )
        
        return [
            DataColumnResponse(
                id=str(col.id),
                dataset_id=col.dataset_id,
                project_id=col.project_id,
                column_name=col.column_name,
                original_type=col.original_type,
                mapped_type=col.mapped_type,
                is_required=col.is_required,
                sample_values=col.sample_values,
                null_count=col.null_count,
                unique_count=col.unique_count
            ) for col in columns
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get columns: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dataset columns: {str(e)}"
        )


@router.put("/datasets/{dataset_id}/columns/mapping")
async def update_column_mappings(
    dataset_id: str,
    mapping_request: ColumnMappingRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update column mappings for a dataset
    Allows users to specify which columns map to user_id, item_id, interaction, etc.
    """
    try:
        # Get dataset columns
        columns = await DatasetService.get_dataset_columns(
            dataset_id, str(current_user.id)
        )
        
        # Update mappings
        updated_columns = []
        for column in columns:
            if column.column_name in mapping_request.column_mappings:
                new_mapping = mapping_request.column_mappings[column.column_name]
                column.mapped_type = new_mapping
                column.is_required = new_mapping in ['user_id', 'item_id', 'interaction']
                await column.save()
                updated_columns.append(column)
        
        return {
            "message": f"Updated mappings for {len(updated_columns)} columns",
            "updated_columns": [col.column_name for col in updated_columns]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update mappings: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update column mappings: {str(e)}"
        )


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a dataset and its associated files
    """
    try:
        await DatasetService.delete_dataset(dataset_id, str(current_user.id))
        
        return {"message": "Dataset deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete dataset: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete dataset: {str(e)}"
        )


@router.get("/datasets/{dataset_id}/info", response_model=DatasetResponse)
async def get_dataset_info(
    dataset_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific dataset
    """
    try:
        # Verify access first through the service
        columns = await DatasetService.get_dataset_columns(
            dataset_id, str(current_user.id)
        )
        
        # Get the dataset
        dataset = await Dataset.get(dataset_id)
        
        return DatasetResponse(
            id=str(dataset.id),
            project_id=dataset.project_id,
            name=dataset.name,
            storage_path=dataset.storage_path,
            file_size=dataset.file_size,
            file_type=dataset.file_type,
            row_count=dataset.row_count,
            column_count=dataset.column_count,
            metadata=dataset.metadata,
            uploaded_at=dataset.uploaded_at,
            status=dataset.status
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dataset info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dataset info: {str(e)}"
        )


@router.get("/datasets/systems")
async def get_supported_systems():
    """
    Get list of supported ML systems and their requirements
    """
    try:
        systems = {}
        for system_name in SystemSchemaResolver.get_supported_systems():
            schema = SystemSchemaResolver.get_schema(system_name)
            systems[system_name] = {
                "name": schema.name,
                "required_columns": schema.required_columns,
                "optional_columns": schema.optional_columns,
                "algorithms": schema.algorithms,
                "metrics": schema.metrics
            }
        
        return {
            "supported_systems": systems
        }
    
    except Exception as e:
        logger.error(f"Failed to get systems: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get systems: {str(e)}"
        )


@router.get("/datasets/project/{project_id}/schema")
async def get_project_dataset_schema(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get dataset schema requirements for a specific project
    """
    try:
        # Get project and verify access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(
                status_code=404,
                detail="Project not found or access denied"
            )
        
        # Get system information (may be None if not set yet)
        if not project.system_id:
            return {
                "project_id": project_id,
                "message": "System type not set yet. Upload a dataset with context and the LLM will determine the appropriate system type.",
                "system_name": None,
                "required_columns": [],
                "optional_columns": [],
                "algorithms": [],
                "metrics": []
            }
        
        system = await System.get(project.system_id)
        if not system:
            raise HTTPException(
                status_code=400,
                detail="Project system not found"
            )
        
        # Get schema requirements
        schema = SystemSchemaResolver.get_schema(system.name)
        
        return {
            "project_id": project_id,
            "system_name": schema.name,
            "required_columns": schema.required_columns,
            "optional_columns": schema.optional_columns,
            "algorithms": schema.algorithms,
            "metrics": schema.metrics,
            "example_column_mapping": {
                "your_user_col": "user_id",
                "your_item_col": "item_id"
            } if schema.name == "recommendation" else {
                "your_customer_col": "customer_id", 
                "your_target_col": "churn"
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project schema: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get project schema: {str(e)}"
        )


# Background task for auto-training
async def _auto_train_model(project_id: str, user_id: str):
    """
    Background task to automatically train model after dataset upload
    """
    try:
        logger.info(f"Starting auto-training for project {project_id}")
        training_service = MLTrainingService()
        model_id, version, metrics, logs = await training_service.train_model(project_id, user_id)
        logger.info(f"Auto-training completed successfully for project {project_id}. Model: {model_id}, Version: {version}")
    except Exception as e:
        logger.error(f"Auto-training failed for project {project_id}: {str(e)}")
        # Don't raise - this is a background task