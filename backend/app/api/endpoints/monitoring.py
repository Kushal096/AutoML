from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.models import User, Project, Model, Dataset
from app.core.auth import get_current_user
from app.services.monitoring_service import MonitoringService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
monitoring_service = MonitoringService()


@router.post("/monitoring/drift/detect")
async def detect_drift(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Detect drift by comparing new data with baseline training data
    
    Request body:
        {
            "project_id": "...",
            "data": {"feature1": value1, ...}
        }
    """
    try:
        project_id = request.get("project_id")
        data = request.get("data")
        
        if not project_id or not data:
            raise ValueError("Both 'project_id' and 'data' are required")
        
        result = await monitoring_service.detect_drift(
            project_id, data, str(current_user.id)
        )
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Drift detection failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Drift detection failed: {str(e)}"
        )


@router.get("/monitoring/drift/history/{project_id}")
async def get_drift_history(
    project_id: str,
    days: Optional[int] = 7,
    current_user: User = Depends(get_current_user)
):
    """
    Get drift detection history for the last N days
    """
    try:
        result = await monitoring_service.get_drift_history(
            project_id, str(current_user.id), days
        )
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get drift history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get drift history: {str(e)}"
        )


@router.get("/monitoring/metrics/{project_id}")
async def get_model_metrics_history(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get metrics history for all model versions
    """
    try:
        result = await monitoring_service.get_model_metrics_history(
            project_id, str(current_user.id)
        )
        return {
            "project_id": project_id,
            **result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get metrics history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics history: {str(e)}"
        )


@router.get("/monitoring/dashboard/{project_id}")
async def get_monitoring_dashboard(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive monitoring dashboard with drift status and model metrics
    """
    try:
        result = await monitoring_service.get_monitoring_dashboard(
            project_id, str(current_user.id)
        )
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get monitoring dashboard: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get monitoring dashboard: {str(e)}"
        )


@router.get("/monitoring/alerts/{project_id}")
async def get_drift_alerts(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get active drift alerts for a project
    """
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get recent drift history
        drift_history = await monitoring_service.get_drift_history(
            project_id, str(current_user.id), days=1
        )
        
        # Extract alerts
        alerts = []
        for feature, history in drift_history.get("feature_drift", {}).items():
            for entry in history:
                if entry["drift_score"] > monitoring_service.drift_threshold:
                    alerts.append({
                        "feature": feature,
                        "drift_score": entry["drift_score"],
                        "detected_at": entry["detected_at"],
                        "severity": "critical" if entry["drift_score"] > 0.2 else "warning"
                    })
        
        return {
            "project_id": project_id,
            "total_alerts": len(alerts),
            "alerts": sorted(alerts, key=lambda x: x["drift_score"], reverse=True)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get drift alerts: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get drift alerts: {str(e)}"
        )


@router.get("/monitoring/overview")
async def get_monitoring_overview(
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive monitoring overview for all user's projects
    """
    try:
        # Get all user's projects and filter out deleted ones early
        all_projects = await Project.find(Project.user_id == str(current_user.id)).to_list()
        projects = [p for p in all_projects if p.status != "deleted"]
        
        # Batch fetch all models and datasets upfront
        project_ids = [str(p.id) for p in projects]
        
        # Fetch all models in parallel
        all_models = await Model.find({"project_id": {"$in": project_ids}}).to_list()
        # Group models by project_id and get latest version for each
        models_by_project = {}
        for model in all_models:
            project_id = str(model.project_id)
            if project_id not in models_by_project:
                models_by_project[project_id] = model
            elif model.version > models_by_project[project_id].version:
                models_by_project[project_id] = model
        
        # Fetch all datasets in parallel
        all_datasets = await Dataset.find({"project_id": {"$in": project_ids}}).to_list()
        datasets_by_project = {}
        for dataset in all_datasets:
            project_id = str(dataset.project_id)
            if project_id not in datasets_by_project:
                datasets_by_project[project_id] = []
            datasets_by_project[project_id].append(dataset)
        
        # Batch fetch drift metrics for all projects (simpler check, no visualization)
        from app.models import DriftMetric
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        all_drift_metrics = await DriftMetric.find({
            "project_id": {"$in": project_ids},
            "detected_at": {"$gte": cutoff_date}
        }).to_list()
        
        # Group drift metrics by project
        drift_by_project = {}
        for metric in all_drift_metrics:
            project_id = str(metric.project_id)
            if project_id not in drift_by_project:
                drift_by_project[project_id] = []
            drift_by_project[project_id].append(metric)
        
        # Batch fetch model registry metadata for all models
        from app.models import ModelRegistryMetadata
        model_ids = [str(m.id) for m in models_by_project.values() if m]
        all_metadata = await ModelRegistryMetadata.find(
            {"model_id": {"$in": model_ids}}
        ).to_list()
        metadata_by_model = {m.model_id: m for m in all_metadata}
        
        overview_data = []
        
        for project in projects:
            project_id = str(project.id)
            latest_model = models_by_project.get(project_id)
            datasets = datasets_by_project.get(project_id, [])
            
            # Simple drift check without expensive visualization
            drift_detected = False
            if project_id in drift_by_project:
                drift_metrics = drift_by_project[project_id]
                drift_detected = any(
                    m.drift_score > monitoring_service.drift_threshold
                    for m in drift_metrics
                )
            
            # Calculate metrics
            accuracy = None
            algorithm = None
            if latest_model and latest_model.metrics:
                accuracy = latest_model.metrics.get("accuracy")
                algorithm = latest_model.metrics.get("algorithm")
            
            # Get prediction count from model registry (from batch fetch)
            total_predictions = 0
            sdk_predictions = 0
            web_predictions = 0
            
            if latest_model:
                metadata = metadata_by_model.get(str(latest_model.id))
                if metadata:
                    total_predictions = metadata.total_predictions
                    if metadata.usage_stats:
                        sdk_predictions = metadata.usage_stats.get("sdk_predictions", 0)
                        web_predictions = metadata.usage_stats.get("web_predictions", 0)
            
            # Determine status
            if project.status == "trained" and latest_model:
                status = "active"
            elif project.status == "training":
                status = "training"
            elif project.status == "created":
                status = "idle"
            else:
                status = "error"
            
            # Get last trained date
            last_trained = None
            if latest_model:
                last_trained = latest_model.created_at.isoformat() if latest_model.created_at else None
            
            overview_data.append({
                "project_id": str(project.id),
                "project_name": project.name,
                "status": status,
                "last_trained": last_trained,
                "accuracy": accuracy,
                "algorithm": algorithm,
                "drift_detected": drift_detected,
                "total_predictions": total_predictions,
                "sdk_predictions": sdk_predictions,
                "web_predictions": web_predictions,
                "model_version": latest_model.version if latest_model else None,
                "dataset_count": len(datasets),
            })
        
        # Calculate overall stats
        total_projects = len(overview_data)
        active_projects = len([p for p in overview_data if p["status"] == "active"])
        drift_count = len([p for p in overview_data if p["drift_detected"]])
        
        accuracies = [p["accuracy"] for p in overview_data if p["accuracy"] is not None]
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0
        
        return {
            "overview": overview_data,
            "stats": {
                "total_projects": total_projects,
                "active_projects": active_projects,
                "drift_detected": drift_count,
                "avg_accuracy": avg_accuracy,
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get monitoring overview: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get monitoring overview: {str(e)}"
        )


@router.get("/monitoring/project/{project_id}/details")
async def get_project_monitoring_details(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive monitoring details for a specific project
    Includes SDK prediction usage, drift history, metrics, and more
    """
    try:
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != str(current_user.id):
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get all models for this project
        models = await Model.find(Model.project_id == project_id).sort(-Model.version).to_list()
        latest_model = models[0] if models else None
        
        # Get datasets
        datasets = await Dataset.find(Dataset.project_id == project_id).to_list()
        
        # Get comprehensive metrics history
        metrics_history = {}
        if latest_model:
            try:
                metrics_history = await monitoring_service.get_model_metrics_history(
                    project_id, str(current_user.id)
                )
            except:
                pass
        
        # Get drift history
        drift_history = await monitoring_service.get_drift_history(
            project_id, str(current_user.id), days=30
        )
        
        # Get drift alerts
        alerts = []
        try:
            alerts_response = await get_drift_alerts(project_id, current_user)
            alerts = alerts_response.get("alerts", [])
        except:
            pass
        
        # Get prediction statistics
        prediction_stats = {
            "total_predictions": 0,
            "sdk_predictions": 0,
            "web_predictions": 0,
            "recent_predictions": [],
            "prediction_timeline": []
        }
        
        if latest_model:
            try:
                from app.services.model_registry_service import ModelRegistryService
                registry = ModelRegistryService()
                metadata = await registry.get_model_metadata(str(latest_model.id))
                if metadata:
                    prediction_stats["total_predictions"] = metadata.total_predictions
                    if metadata.usage_stats:
                        prediction_stats["sdk_predictions"] = metadata.usage_stats.get("sdk_predictions", 0)
                        prediction_stats["web_predictions"] = metadata.usage_stats.get("web_predictions", 0)
                        prediction_stats["recent_predictions"] = metadata.usage_stats.get("recent_predictions", [])
                        prediction_stats["prediction_timeline"] = metadata.usage_stats.get("prediction_timeline", [])
            except Exception as e:
                logger.warning(f"Failed to get prediction stats: {str(e)}")
        
        # Get model versions info
        model_versions = []
        for model in models:
            model_versions.append({
                "version": model.version,
                "model_id": str(model.id),
                "created_at": model.created_at.isoformat() if model.created_at else None,
                "metrics": model.metrics,
                "status": "latest" if model == latest_model else "previous"
            })
        
        # Calculate response time (mock for now, can be enhanced)
        avg_response_time = 50 + (prediction_stats["total_predictions"] % 100)
        
        return {
            "project_id": project_id,
            "project_name": project.name,
            "project_status": project.status,
            "latest_model": {
                "version": latest_model.version if latest_model else None,
                "model_id": str(latest_model.id) if latest_model else None,
                "metrics": latest_model.metrics if latest_model else {},
                "created_at": latest_model.created_at.isoformat() if latest_model and latest_model.created_at else None,
            } if latest_model else None,
            "model_versions": model_versions,
            "datasets": {
                "count": len(datasets),
                "total_rows": sum(d.row_count or 0 for d in datasets),
            },
            "prediction_stats": prediction_stats,
            "drift_history": drift_history,
            "drift_alerts": alerts,
            "metrics_history": metrics_history,
            "performance": {
                "avg_response_time_ms": avg_response_time,
                "algorithm": latest_model.metrics.get("algorithm") if latest_model and latest_model.metrics else None,
                "accuracy": latest_model.metrics.get("accuracy") if latest_model and latest_model.metrics else None,
                "precision": latest_model.metrics.get("precision") if latest_model and latest_model.metrics else None,
                "recall": latest_model.metrics.get("recall") if latest_model and latest_model.metrics else None,
                "f1_score": latest_model.metrics.get("f1_score") if latest_model and latest_model.metrics else None,
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project monitoring details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get project monitoring details: {str(e)}"
        )

