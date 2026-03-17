"""
Dashboard API - Comprehensive Analytics & Metrics
Provides aggregated insights across all user projects, models, and systems
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from app.models import (
    User, Project, Model, Dataset, System, 
    ModelRegistryMetadata, DriftMetric, FeatureDefinition
)
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dashboard/overview", response_model=dict)
async def get_dashboard_overview(
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive dashboard overview with all key metrics
    
    Returns:
    - Project statistics
    - Model performance metrics
    - System usage breakdown
    - Recent activity
    - Health indicators
    """
    try:
        user_id = str(current_user.id)
        
        # Get all user projects and filter out deleted ones early
        all_projects = await Project.find({"user_id": user_id}).to_list()
        projects = [p for p in all_projects if p.status != "deleted"]
        project_ids = [str(p.id) for p in projects]
        
        # Project Statistics
        project_stats = {
            "total_projects": len(projects),
            "active_projects": len([p for p in projects if p.status == "trained"]),
            "training_projects": len([p for p in projects if p.status == "training"]),
            "new_projects": len([p for p in projects if p.status == "created"]),
        }
        
        # Batch fetch all systems (fetch all since there are typically few systems)
        system_ids = list(set([p.system_id for p in projects if p.system_id]))
        all_systems_list = await System.find_all().to_list()
        all_systems = [s for s in all_systems_list if str(s.id) in system_ids]
        systems_by_id = {str(s.id): s for s in all_systems}
        
        # System Usage Breakdown (using batch-fetched systems)
        system_usage = {}
        for project in projects:
            system = systems_by_id.get(str(project.system_id))
            if system:
                system_name = system.name
                if system_name not in system_usage:
                    system_usage[system_name] = {
                        "count": 0,
                        "trained": 0,
                        "system_id": str(system.id)
                    }
                system_usage[system_name]["count"] += 1
                if project.status == "trained":
                    system_usage[system_name]["trained"] += 1
        
        # Batch fetch all models
        all_models = await Model.find({"project_id": {"$in": project_ids}}).to_list()
        
        model_stats = {
            "total_models": len(all_models),
            "total_versions": len(all_models),
            "avg_models_per_project": len(all_models) / len(projects) if projects else 0
        }
        
        # Batch fetch Model Registry Statistics
        model_ids = [str(m.id) for m in all_models]
        registry_metadata = await ModelRegistryMetadata.find(
            {"model_id": {"$in": model_ids}}
        ).to_list()
        
        deployment_stages = {}
        approval_status = {}
        total_predictions = 0
        
        for metadata in registry_metadata:
            # Deployment stages
            stage = metadata.deployment_stage
            deployment_stages[stage] = deployment_stages.get(stage, 0) + 1
            
            # Approval status
            approval = metadata.approval_status
            approval_status[approval] = approval_status.get(approval, 0) + 1
            
            # Total predictions
            total_predictions += metadata.total_predictions
        
        # Performance Metrics Aggregation
        accuracy_scores = []
        f1_scores = []
        
        for model in all_models:
            if model.metrics:
                if "accuracy" in model.metrics:
                    accuracy_scores.append(model.metrics["accuracy"])
                if "f1_score" in model.metrics:
                    f1_scores.append(model.metrics["f1_score"])
        
        performance_metrics = {
            "avg_accuracy": sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0,
            "max_accuracy": max(accuracy_scores) if accuracy_scores else 0,
            "min_accuracy": min(accuracy_scores) if accuracy_scores else 0,
            "avg_f1_score": sum(f1_scores) / len(f1_scores) if f1_scores else 0,
            "models_with_metrics": len(accuracy_scores)
        }
        
        # Batch fetch Dataset Statistics
        all_datasets = await Dataset.find({"project_id": {"$in": project_ids}}).to_list()
        
        total_rows = sum(d.row_count or 0 for d in all_datasets)
        deleted_datasets = len([d for d in all_datasets if d.status == "processed_and_deleted"])
        
        dataset_stats = {
            "total_datasets": len(all_datasets),
            "total_rows_processed": total_rows,
            "deleted_for_privacy": deleted_datasets,
            "avg_rows_per_dataset": total_rows / len(all_datasets) if all_datasets else 0
        }
        
        # Feature Store Statistics
        feature_definitions = await FeatureDefinition.find({
            "$or": [
                {"project_id": {"$in": project_ids}},
                {"project_id": None}
            ]
        }).to_list()
        
        feature_stats = {
            "total_features": len(feature_definitions),
            "active_features": len([f for f in feature_definitions if f.is_active]),
            "feature_types": {}
        }
        
        for feature in feature_definitions:
            ftype = feature.feature_type
            feature_stats["feature_types"][ftype] = feature_stats["feature_types"].get(ftype, 0) + 1
        
        # Batch fetch Drift Detection Statistics
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        recent_drift = await DriftMetric.find({
            "project_id": {"$in": project_ids},
            "detected_at": {"$gte": cutoff_date}
        }).to_list()
        
        drift_scores = [d.drift_score for d in recent_drift]
        drift_stats = {
            "total_checks_7d": len(recent_drift),
            "avg_drift_score": sum(drift_scores) / len(drift_scores) if drift_scores else 0,
            "drift_alerts": len([d for d in recent_drift if d.drift_score > 0.1]),
            "features_monitored": len(set(d.feature_name for d in recent_drift))
        }
        
        # Recent Activity (last 7 days)
        recent_projects = [p for p in projects if p.created_at >= cutoff_date]
        recent_models = [m for m in all_models if m.created_at >= cutoff_date]
        
        recent_activity = {
            "new_projects_7d": len(recent_projects),
            "new_models_7d": len(recent_models),
            "predictions_7d": sum(
                m.total_predictions for m in registry_metadata 
                if m.last_prediction_at and m.last_prediction_at >= cutoff_date
            )
        }
        
        # Health Indicators
        health_score = 0
        health_factors = []
        
        # Factor 1: Active projects (max 25 points)
        if project_stats["active_projects"] > 0:
            health_score += min(25, project_stats["active_projects"] * 5)
            health_factors.append("Active projects")
        
        # Factor 2: Model performance (max 25 points)
        if performance_metrics["avg_accuracy"] > 0.7:
            health_score += 25
            health_factors.append("Good model performance")
        elif performance_metrics["avg_accuracy"] > 0.5:
            health_score += 15
            health_factors.append("Moderate model performance")
        
        # Factor 3: Recent activity (max 25 points)
        if recent_activity["new_models_7d"] > 0:
            health_score += 25
            health_factors.append("Recent model training")
        
        # Factor 4: Monitoring (max 25 points)
        if drift_stats["total_checks_7d"] > 0:
            health_score += 25
            health_factors.append("Active monitoring")
        
        health_status = {
            "score": health_score,
            "status": "excellent" if health_score >= 80 else "good" if health_score >= 60 else "fair" if health_score >= 40 else "needs_attention",
            "factors": health_factors
        }
        
        # Top Performing Models (using already fetched projects)
        projects_by_id = {str(p.id): p for p in projects}
        top_models = sorted(
            [m for m in all_models if m.metrics and "accuracy" in m.metrics],
            key=lambda x: x.metrics.get("accuracy", 0),
            reverse=True
        )[:5]
        
        top_models_info = []
        for model in top_models:
            project = projects_by_id.get(str(model.project_id))
            top_models_info.append({
                "model_id": str(model.id),
                "project_name": project.name if project else "Unknown",
                "version": model.version,
                "accuracy": model.metrics.get("accuracy", 0),
                "created_at": model.created_at
            })
        
        # Compile Dashboard (visualizations removed for performance)
        dashboard = {
            "user": {
                "id": user_id,
                "name": current_user.name,
                "email": current_user.email,
                "member_since": current_user.created_at
            },
            "summary": {
                "projects": project_stats,
                "models": model_stats,
                "datasets": dataset_stats,
                "features": feature_stats,
                "predictions_served": total_predictions
            },
            "system_usage": system_usage,
            "model_registry": {
                "deployment_stages": deployment_stages,
                "approval_status": approval_status,
                "total_predictions": total_predictions
            },
            "performance": performance_metrics,
            "monitoring": drift_stats,
            "recent_activity": recent_activity,
            "health": health_status,
            "top_models": top_models_info,
            "generated_at": datetime.utcnow()
        }
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Dashboard overview failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate dashboard: {str(e)}"
        )


@router.get("/dashboard/projects", response_model=dict)
async def get_projects_dashboard(
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed project-level dashboard with per-project metrics
    """
    try:
        user_id = str(current_user.id)
        projects = await Project.find({"user_id": user_id}).to_list()
        
        project_details = []
        
        for project in projects:
            # Get system info
            system = await System.get(project.system_id)
            
            # Get models
            models = await Model.find({"project_id": str(project.id)}).to_list()
            
            # Get datasets
            datasets = await Dataset.find({"project_id": str(project.id)}).to_list()
            
            # Get latest model metrics
            latest_model = models[0] if models else None
            latest_metrics = latest_model.metrics if latest_model else {}
            
            # Get registry info
            registry_info = None
            if latest_model:
                registry_metadata = await ModelRegistryMetadata.find_one({
                    "model_id": str(latest_model.id)
                })
                if registry_metadata:
                    registry_info = {
                        "deployment_stage": registry_metadata.deployment_stage,
                        "approval_status": registry_metadata.approval_status,
                        "total_predictions": registry_metadata.total_predictions,
                        "last_prediction_at": registry_metadata.last_prediction_at
                    }
            
            project_details.append({
                "project_id": str(project.id),
                "name": project.name,
                "system": system.name if system else "Unknown",
                "status": project.status,
                "created_at": project.created_at,
                "updated_at": project.updated_at,
                "models": {
                    "total": len(models),
                    "latest_version": latest_model.version if latest_model else 0,
                    "latest_metrics": latest_metrics
                },
                "datasets": {
                    "total": len(datasets),
                    "total_rows": sum(d.row_count or 0 for d in datasets)
                },
                "registry": registry_info
            })
        
        return {
            "total_projects": len(projects),
            "projects": project_details
        }
        
    except Exception as e:
        logger.error(f"Projects dashboard failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate projects dashboard: {str(e)}"
        )


@router.get("/dashboard/analytics", response_model=dict)
async def get_analytics_dashboard(
    days: int = 30,
    current_user: User = Depends(get_current_user)
):
    """
    Get time-series analytics and trends
    Optimized with batch queries to avoid N+1 problem
    """
    try:
        user_id = str(current_user.id)
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all user projects and filter out deleted ones early
        all_projects = await Project.find({"user_id": user_id}).to_list()
        projects = [p for p in all_projects if p.status != "deleted"]
        project_ids = [str(p.id) for p in projects]
        
        # Project creation trend (in-memory processing)
        projects_by_date = {}
        for project in projects:
            if project.created_at and project.created_at >= cutoff_date:
                date_key = project.created_at.strftime("%Y-%m-%d")
                projects_by_date[date_key] = projects_by_date.get(date_key, 0) + 1
        
        # Batch fetch ALL models for all projects at once
        all_models = await Model.find({
            "project_id": {"$in": project_ids},
            "created_at": {"$gte": cutoff_date}
        }).to_list()
        
        # Model training trend (in-memory processing)
        models_by_date = {}
        for model in all_models:
            if model.created_at:
                date_key = model.created_at.strftime("%Y-%m-%d")
                models_by_date[date_key] = models_by_date.get(date_key, 0) + 1
        
        # Batch fetch ALL ModelRegistryMetadata at once
        model_ids = [str(m.id) for m in all_models]
        all_metadata = await ModelRegistryMetadata.find({
            "model_id": {"$in": model_ids}
        }).to_list()
        
        # Create lookup map for metadata by model_id
        metadata_by_model_id = {m.model_id: m for m in all_metadata}
        
        # Prediction volume trend (in-memory processing)
        predictions_by_date = {}
        for model in all_models:
            metadata = metadata_by_model_id.get(str(model.id))
            if metadata and metadata.last_prediction_at and metadata.last_prediction_at >= cutoff_date:
                date_key = metadata.last_prediction_at.strftime("%Y-%m-%d")
                predictions_by_date[date_key] = predictions_by_date.get(date_key, 0) + metadata.total_predictions
        
        # Batch fetch ALL drift metrics at once
        all_drift_metrics = await DriftMetric.find({
            "project_id": {"$in": project_ids},
            "detected_at": {"$gte": cutoff_date}
        }).to_list()
        
        # Drift trend (in-memory processing)
        drift_by_date = {}
        for drift in all_drift_metrics:
            if drift.detected_at:
                date_key = drift.detected_at.strftime("%Y-%m-%d")
                if date_key not in drift_by_date:
                    drift_by_date[date_key] = {"count": 0, "avg_score": 0, "scores": []}
                drift_by_date[date_key]["count"] += 1
                drift_by_date[date_key]["scores"].append(drift.drift_score)
        
        # Calculate averages for drift
        for date_key in drift_by_date:
            scores = drift_by_date[date_key]["scores"]
            drift_by_date[date_key]["avg_score"] = sum(scores) / len(scores) if scores else 0
            del drift_by_date[date_key]["scores"]  # Remove raw scores
        
        return {
            "period_days": days,
            "start_date": cutoff_date.isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "trends": {
                "projects_created": projects_by_date,
                "models_trained": models_by_date,
                "predictions_served": predictions_by_date,
                "drift_monitoring": drift_by_date
            },
            "totals": {
                "projects": sum(projects_by_date.values()),
                "models": sum(models_by_date.values()),
                "predictions": sum(predictions_by_date.values()),
                "drift_checks": sum(d["count"] for d in drift_by_date.values())
            }
        }
        
    except Exception as e:
        logger.error(f"Analytics dashboard failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate analytics: {str(e)}"
        )


@router.get("/dashboard/system/{system_id}", response_model=dict)
async def get_system_dashboard(
    system_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get dashboard for a specific ML system
    """
    try:
        user_id = str(current_user.id)
        
        # Get system
        system = await System.get(system_id)
        if not system:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System not found"
            )
        
        # Get all projects for this system
        projects = await Project.find({
            "user_id": user_id,
            "system_id": system_id
        }).to_list()
        
        project_ids = [str(p.id) for p in projects]
        
        # Aggregate metrics
        all_models = []
        for project_id in project_ids:
            models = await Model.find({"project_id": project_id}).to_list()
            all_models.extend(models)
        
        # Performance metrics
        accuracy_scores = [m.metrics.get("accuracy", 0) for m in all_models if m.metrics and "accuracy" in m.metrics]
        
        return {
            "system": {
                "id": str(system.id),
                "name": system.name,
                "description": system.description
            },
            "usage": {
                "total_projects": len(projects),
                "active_projects": len([p for p in projects if p.status == "trained"]),
                "total_models": len(all_models)
            },
            "performance": {
                "avg_accuracy": sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0,
                "max_accuracy": max(accuracy_scores) if accuracy_scores else 0,
                "models_evaluated": len(accuracy_scores)
            },
            "projects": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "status": p.status,
                    "created_at": p.created_at
                }
                for p in projects
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"System dashboard failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate system dashboard: {str(e)}"
        )

