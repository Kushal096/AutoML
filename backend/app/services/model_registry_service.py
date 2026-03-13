"""
Enhanced Model Registry Service
Provides model versioning, lineage tracking, and governance
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np

from app.models import (
    Model, ModelRegistryMetadata, Project, User
)

logger = logging.getLogger(__name__)


class ModelRegistryService:
    """
    Enhanced Model Registry with:
    - Model versioning and lineage
    - Deployment stage management
    - Approval workflows
    - Production metrics tracking
    - Model governance
    """
    
    async def register_model(
        self,
        model_id: str,
        project_id: str,
        training_dataset_ids: List[str],
        feature_set_id: Optional[str] = None,
        training_duration_seconds: Optional[float] = None,
        training_parameters: Optional[Dict[str, Any]] = None,
        parent_model_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> ModelRegistryMetadata:
        """
        Register a model with comprehensive metadata
        """
        
        metadata = ModelRegistryMetadata(
            model_id=model_id,
            project_id=project_id,
            training_dataset_ids=training_dataset_ids,
            feature_set_id=feature_set_id,
            training_duration_seconds=training_duration_seconds,
            training_parameters=training_parameters,
            parent_model_id=parent_model_id,
            tags=tags or [],
            approval_status="pending",
            deployment_stage="development"
        )
        
        await metadata.insert()
        logger.info(f"Registered model {model_id} in registry")
        
        return metadata
    
    async def get_model_metadata(
        self,
        model_id: str
    ) -> Optional[ModelRegistryMetadata]:
        """Get metadata for a specific model"""
        
        return await ModelRegistryMetadata.find_one({"model_id": model_id})
    
    async def get_model_lineage(
        self,
        model_id: str
    ) -> Dict[str, Any]:
        """
        Get the full lineage of a model (parent models, children, etc.)
        """
        
        metadata = await self.get_model_metadata(model_id)
        if not metadata:
            return {"model_id": model_id, "lineage": []}
        
        # Get parent lineage
        parent_lineage = []
        current_parent_id = metadata.parent_model_id
        
        while current_parent_id:
            parent_metadata = await self.get_model_metadata(current_parent_id)
            if not parent_metadata:
                break
            
            parent_model = await Model.get(current_parent_id)
            parent_lineage.append({
                "model_id": current_parent_id,
                "version": parent_model.version if parent_model else None,
                "created_at": parent_model.created_at if parent_model else None,
                "metrics": parent_model.metrics if parent_model else None
            })
            
            current_parent_id = parent_metadata.parent_model_id
        
        # Get children models
        children_metadata = await ModelRegistryMetadata.find({
            "parent_model_id": model_id
        }).to_list()
        
        children = []
        for child_meta in children_metadata:
            child_model = await Model.get(child_meta.model_id)
            children.append({
                "model_id": child_meta.model_id,
                "version": child_model.version if child_model else None,
                "created_at": child_model.created_at if child_model else None,
                "deployment_stage": child_meta.deployment_stage
            })
        
        return {
            "model_id": model_id,
            "parent_lineage": parent_lineage,
            "children": children,
            "total_ancestors": len(parent_lineage),
            "total_descendants": len(children)
        }
    
    async def approve_model(
        self,
        model_id: str,
        approved_by: str,
        deployment_stage: str = "staging"
    ) -> ModelRegistryMetadata:
        """
        Approve a model for deployment
        """
        
        metadata = await self.get_model_metadata(model_id)
        if not metadata:
            raise ValueError(f"Model {model_id} not found in registry")
        
        metadata.approval_status = "approved"
        metadata.approved_by = approved_by
        metadata.approved_at = datetime.utcnow()
        metadata.deployment_stage = deployment_stage
        metadata.updated_at = datetime.utcnow()
        
        await metadata.save()
        logger.info(f"Approved model {model_id} for {deployment_stage}")
        
        return metadata
    
    async def promote_to_production(
        self,
        model_id: str,
        user_id: str
    ) -> ModelRegistryMetadata:
        """
        Promote a model to production
        """
        
        metadata = await self.get_model_metadata(model_id)
        if not metadata:
            raise ValueError(f"Model {model_id} not found in registry")
        
        if metadata.approval_status != "approved":
            raise ValueError(f"Model {model_id} must be approved before promotion to production")
        
        # Demote current production model
        current_production = await ModelRegistryMetadata.find_one({
            "project_id": metadata.project_id,
            "deployment_stage": "production"
        })
        
        if current_production:
            current_production.deployment_stage = "archived"
            current_production.updated_at = datetime.utcnow()
            await current_production.save()
            logger.info(f"Archived previous production model {current_production.model_id}")
        
        # Promote new model
        metadata.deployment_stage = "production"
        metadata.updated_at = datetime.utcnow()
        await metadata.save()
        
        logger.info(f"Promoted model {model_id} to production")
        
        return metadata
    
    async def record_prediction(
        self,
        model_id: str,
        source: str = "web"  # "sdk" or "web"
    ):
        """
        Record that a prediction was made (for tracking usage)
        """
        
        metadata = await self.get_model_metadata(model_id)
        if metadata:
            metadata.total_predictions += 1
            metadata.last_prediction_at = datetime.utcnow()
            metadata.updated_at = datetime.utcnow()
            
            # Initialize usage_stats if not exists
            if not metadata.usage_stats:
                metadata.usage_stats = {
                    "sdk_predictions": 0,
                    "web_predictions": 0,
                    "recent_predictions": [],
                    "prediction_timeline": []
                }
            
            # Update source-specific counts
            if source == "sdk":
                metadata.usage_stats["sdk_predictions"] = metadata.usage_stats.get("sdk_predictions", 0) + 1
            else:
                metadata.usage_stats["web_predictions"] = metadata.usage_stats.get("web_predictions", 0) + 1
            
            # Add to recent predictions (keep last 100)
            recent = metadata.usage_stats.get("recent_predictions", [])
            recent.append({
                "timestamp": datetime.utcnow().isoformat(),
                "source": source
            })
            if len(recent) > 100:
                recent = recent[-100:]
            metadata.usage_stats["recent_predictions"] = recent
            
            # Update timeline (daily aggregation)
            timeline = metadata.usage_stats.get("prediction_timeline", [])
            today = datetime.utcnow().date().isoformat()
            
            # Find or create today's entry
            today_entry = None
            for entry in timeline:
                if entry.get("date") == today:
                    today_entry = entry
                    break
            
            if not today_entry:
                today_entry = {
                    "date": today,
                    "sdk": 0,
                    "web": 0,
                    "total": 0
                }
                timeline.append(today_entry)
                # Keep last 30 days
                if len(timeline) > 30:
                    timeline = timeline[-30:]
            
            today_entry[source] = today_entry.get(source, 0) + 1
            today_entry["total"] = today_entry.get("total", 0) + 1
            metadata.usage_stats["prediction_timeline"] = timeline
            
            await metadata.save()
    
    async def update_production_metrics(
        self,
        model_id: str,
        metrics: Dict[str, Any]
    ):
        """
        Update production metrics for a model
        """
        
        metadata = await self.get_model_metadata(model_id)
        if not metadata:
            raise ValueError(f"Model {model_id} not found in registry")
        
        if not metadata.production_metrics:
            metadata.production_metrics = {}
        
        metadata.production_metrics.update(metrics)
        metadata.updated_at = datetime.utcnow()
        await metadata.save()
        
        logger.info(f"Updated production metrics for model {model_id}")
    
    async def get_production_model(
        self,
        project_id: str
    ) -> Optional[Model]:
        """
        Get the current production model for a project
        """
        
        metadata = await ModelRegistryMetadata.find_one({
            "project_id": project_id,
            "deployment_stage": "production"
        })
        
        if not metadata:
            return None
        
        return await Model.get(metadata.model_id)
    
    async def get_models_by_stage(
        self,
        project_id: str,
        deployment_stage: str
    ) -> List[Dict[str, Any]]:
        """
        Get all models in a specific deployment stage
        """
        
        metadata_list = await ModelRegistryMetadata.find({
            "project_id": project_id,
            "deployment_stage": deployment_stage
        }).to_list()
        
        results = []
        for metadata in metadata_list:
            model = await Model.get(metadata.model_id)
            if model:
                results.append({
                    "model_id": metadata.model_id,
                    "version": model.version,
                    "metrics": model.metrics,
                    "created_at": model.created_at,
                    "approval_status": metadata.approval_status,
                    "total_predictions": metadata.total_predictions,
                    "tags": metadata.tags
                })
        
        return results
    
    async def compare_models(
        self,
        model_id_1: str,
        model_id_2: str
    ) -> Dict[str, Any]:
        """
        Compare two models comprehensively side by side
        Includes metrics, feature importance, training data, and recommendations
        """
        
        model1 = await Model.get(model_id_1)
        model2 = await Model.get(model_id_2)
        
        if not model1 or not model2:
            raise ValueError("One or both models not found")
        
        metadata1 = await self.get_model_metadata(model_id_1)
        metadata2 = await self.get_model_metadata(model_id_2)
        
        metrics1 = model1.metrics or {}
        metrics2 = model2.metrics or {}
        
        # Calculate comprehensive metric differences
        metric_comparison = self._calculate_metric_differences(metrics1, metrics2)
        
        # Compare feature importance
        feature_comparison = self._compare_feature_importance(
            metrics1.get("feature_importances", {}),
            metrics2.get("feature_importances", {})
        )
        
        # Compare confusion matrices
        confusion_comparison = self._compare_confusion_matrices(
            metrics1.get("confusion_matrix"),
            metrics2.get("confusion_matrix")
        )
        
        # Compare classification reports
        classification_comparison = self._compare_classification_reports(
            metrics1.get("classification_report", {}),
            metrics2.get("classification_report", {})
        )
        
        # Compare training data
        training_data_comparison = self._compare_training_data(metadata1, metadata2)
        
        # Determine winner and recommendation
        winner, recommendation = self._determine_winner(metric_comparison, metrics1, metrics2)
        
        return {
            "model_1": {
                "id": model_id_1,
                "version": model1.version,
                "metrics": metrics1,
                "created_at": model1.created_at,
                "deployment_stage": metadata1.deployment_stage if metadata1 else "unknown",
                "approval_status": metadata1.approval_status if metadata1 else "unknown",
                "total_predictions": metadata1.total_predictions if metadata1 else 0,
                "training_duration": metadata1.training_duration_seconds if metadata1 else None,
                "training_datasets": len(metadata1.training_dataset_ids) if metadata1 else 0,
                "tags": metadata1.tags if metadata1 else []
            },
            "model_2": {
                "id": model_id_2,
                "version": model2.version,
                "metrics": metrics2,
                "created_at": model2.created_at,
                "deployment_stage": metadata2.deployment_stage if metadata2 else "unknown",
                "approval_status": metadata2.approval_status if metadata2 else "unknown",
                "total_predictions": metadata2.total_predictions if metadata2 else 0,
                "training_duration": metadata2.training_duration_seconds if metadata2 else None,
                "training_datasets": len(metadata2.training_dataset_ids) if metadata2 else 0,
                "tags": metadata2.tags if metadata2 else []
            },
            "comparison": {
                "metrics": metric_comparison,
                "feature_importance": feature_comparison,
                "confusion_matrix": confusion_comparison,
                "classification_report": classification_comparison,
                "training_data": training_data_comparison
            },
            "winner": winner,
            "recommendation": recommendation,
            "summary": self._generate_comparison_summary(metric_comparison, winner)
        }
    
    def _calculate_metric_differences(
        self,
        metrics1: Dict[str, Any],
        metrics2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate differences between two metric sets"""
        
        differences = {}
        
        # Key metrics to compare (higher is better for these)
        higher_is_better = ["accuracy", "precision", "recall", "f1_score", "roc_auc", "mean_score"]
        
        # Compare common metrics
        common_metrics = set(metrics1.keys()) & set(metrics2.keys())
        
        for metric in common_metrics:
            val1 = metrics1[metric]
            val2 = metrics2[metric]
            
            # Only compare numeric values
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                diff = val2 - val1
                pct_change = (diff / val1 * 100) if val1 != 0 else 0
                
                # Determine if improvement (depends on metric type)
                is_improvement = diff > 0 if metric in higher_is_better else diff < 0
                
                differences[metric] = {
                    "model_1": val1,
                    "model_2": val2,
                    "difference": diff,
                    "percent_change": pct_change,
                    "improved": is_improvement,
                    "significance": "high" if abs(pct_change) > 5 else "medium" if abs(pct_change) > 1 else "low"
                }
        
        return differences
    
    def _compare_feature_importance(
        self,
        features1: Dict[str, float],
        features2: Dict[str, float]
    ) -> Dict[str, Any]:
        """Compare feature importance between two models"""
        
        if not features1 or not features2:
            return {"available": False, "message": "Feature importance not available for one or both models"}
        
        common_features = set(features1.keys()) & set(features2.keys())
        
        if not common_features:
            return {"available": False, "message": "No common features found"}
        
        feature_diffs = {}
        for feature in common_features:
            val1 = features1[feature]
            val2 = features2[feature]
            diff = val2 - val1
            pct_change = (diff / val1 * 100) if val1 != 0 else 0
            
            feature_diffs[feature] = {
                "model_1": val1,
                "model_2": val2,
                "difference": diff,
                "percent_change": pct_change
            }
        
        # Find top 5 most changed features
        sorted_features = sorted(
            feature_diffs.items(),
            key=lambda x: abs(x[1]["percent_change"]),
            reverse=True
        )[:5]
        
        return {
            "available": True,
            "common_features": len(common_features),
            "differences": feature_diffs,
            "top_changes": {k: v for k, v in sorted_features}
        }
    
    def _compare_confusion_matrices(
        self,
        cm1: Optional[List],
        cm2: Optional[List]
    ) -> Dict[str, Any]:
        """Compare confusion matrices between two models"""
        
        if not cm1 or not cm2:
            return {"available": False, "message": "Confusion matrix not available for one or both models"}
        
        try:
            # Convert to numpy arrays
            cm1_arr = np.array(cm1)
            cm2_arr = np.array(cm2)
            
            if cm1_arr.shape != cm2_arr.shape:
                return {"available": False, "message": "Confusion matrices have different shapes"}
            
            # Calculate differences
            diff = cm2_arr - cm1_arr
            
            # Calculate key metrics from confusion matrices
            def calc_metrics(cm):
                tn, fp, fn, tp = cm.flatten() if len(cm.flatten()) == 4 else (0, 0, 0, 0)
                total = tn + fp + fn + tp
                if total == 0:
                    return {}
                return {
                    "true_negatives": int(tn),
                    "false_positives": int(fp),
                    "false_negatives": int(fn),
                    "true_positives": int(tp),
                    "total": int(total),
                    "accuracy": float((tn + tp) / total) if total > 0 else 0,
                    "precision": float(tp / (tp + fp)) if (tp + fp) > 0 else 0,
                    "recall": float(tp / (tp + fn)) if (tp + fn) > 0 else 0
                }
            
            metrics1 = calc_metrics(cm1_arr)
            metrics2 = calc_metrics(cm2_arr)
            
            return {
                "available": True,
                "model_1": {
                    "matrix": cm1,
                    "metrics": metrics1
                },
                "model_2": {
                    "matrix": cm2,
                    "metrics": metrics2
                },
                "difference": diff.tolist(),
                "metric_changes": {
                    k: {
                        "model_1": metrics1.get(k, 0),
                        "model_2": metrics2.get(k, 0),
                        "difference": metrics2.get(k, 0) - metrics1.get(k, 0)
                    }
                    for k in ["accuracy", "precision", "recall"]
                    if k in metrics1 and k in metrics2
                }
            }
        except Exception as e:
            logger.error(f"Error comparing confusion matrices: {str(e)}")
            return {"available": False, "message": f"Error comparing confusion matrices: {str(e)}"}
    
    def _compare_classification_reports(
        self,
        report1: Dict[str, Any],
        report2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare classification reports between two models"""
        
        if not report1 or not report2:
            return {"available": False, "message": "Classification report not available for one or both models"}
        
        # Compare class-level metrics
        class_comparison = {}
        
        # Get all classes from both reports
        classes1 = set(k for k in report1.keys() if k not in ["accuracy", "macro avg", "weighted avg"])
        classes2 = set(k for k in report2.keys() if k not in ["accuracy", "macro avg", "weighted avg"])
        common_classes = classes1 & classes2
        
        for class_name in common_classes:
            if isinstance(report1[class_name], dict) and isinstance(report2[class_name], dict):
                class_comparison[class_name] = {
                    "precision": {
                        "model_1": report1[class_name].get("precision", 0),
                        "model_2": report2[class_name].get("precision", 0),
                        "difference": report2[class_name].get("precision", 0) - report1[class_name].get("precision", 0)
                    },
                    "recall": {
                        "model_1": report1[class_name].get("recall", 0),
                        "model_2": report2[class_name].get("recall", 0),
                        "difference": report2[class_name].get("recall", 0) - report1[class_name].get("recall", 0)
                    },
                    "f1_score": {
                        "model_1": report1[class_name].get("f1-score", 0),
                        "model_2": report2[class_name].get("f1-score", 0),
                        "difference": report2[class_name].get("f1-score", 0) - report1[class_name].get("f1-score", 0)
                    }
                }
        
        # Compare aggregate metrics
        aggregate_comparison = {}
        for agg_type in ["macro avg", "weighted avg"]:
            if agg_type in report1 and agg_type in report2:
                aggregate_comparison[agg_type] = {
                    "precision": {
                        "model_1": report1[agg_type].get("precision", 0),
                        "model_2": report2[agg_type].get("precision", 0),
                        "difference": report2[agg_type].get("precision", 0) - report1[agg_type].get("precision", 0)
                    },
                    "recall": {
                        "model_1": report1[agg_type].get("recall", 0),
                        "model_2": report2[agg_type].get("recall", 0),
                        "difference": report2[agg_type].get("recall", 0) - report1[agg_type].get("recall", 0)
                    },
                    "f1_score": {
                        "model_1": report1[agg_type].get("f1-score", 0),
                        "model_2": report2[agg_type].get("f1-score", 0),
                        "difference": report2[agg_type].get("f1-score", 0) - report1[agg_type].get("f1-score", 0)
                    }
                }
        
        return {
            "available": True,
            "class_comparison": class_comparison,
            "aggregate_comparison": aggregate_comparison,
            "accuracy": {
                "model_1": report1.get("accuracy", 0),
                "model_2": report2.get("accuracy", 0),
                "difference": report2.get("accuracy", 0) - report1.get("accuracy", 0)
            }
        }
    
    def _compare_training_data(
        self,
        metadata1: Optional[ModelRegistryMetadata],
        metadata2: Optional[ModelRegistryMetadata]
    ) -> Dict[str, Any]:
        """Compare training data between two models"""
        
        if not metadata1 or not metadata2:
            return {"available": False, "message": "Training metadata not available for one or both models"}
        
        datasets1 = set(metadata1.training_dataset_ids or [])
        datasets2 = set(metadata2.training_dataset_ids or [])
        
        common_datasets = datasets1 & datasets2
        unique_to_1 = datasets1 - datasets2
        unique_to_2 = datasets2 - datasets1
        
        return {
            "available": True,
            "model_1": {
                "dataset_count": len(datasets1),
                "datasets": list(datasets1),
                "training_duration": metadata1.training_duration_seconds
            },
            "model_2": {
                "dataset_count": len(datasets2),
                "datasets": list(datasets2),
                "training_duration": metadata2.training_duration_seconds
            },
            "common_datasets": list(common_datasets),
            "unique_to_model_1": list(unique_to_1),
            "unique_to_model_2": list(unique_to_2),
            "dataset_overlap_percent": (len(common_datasets) / max(len(datasets1), len(datasets2)) * 100) if max(len(datasets1), len(datasets2)) > 0 else 0
        }
    
    def _determine_winner(
        self,
        metric_comparison: Dict[str, Any],
        metrics1: Dict[str, Any],
        metrics2: Dict[str, Any]
    ) -> tuple:
        """Determine which model performs better and provide recommendation"""
        
        # Key metrics to consider (weighted)
        key_metrics = {
            "accuracy": 0.3,
            "f1_score": 0.25,
            "precision": 0.2,
            "recall": 0.15,
            "roc_auc": 0.1
        }
        
        score1 = 0
        score2 = 0
        improvements = []
        degradations = []
        
        for metric, weight in key_metrics.items():
            if metric in metric_comparison:
                comp = metric_comparison[metric]
                diff = comp["difference"]
                
                if comp["improved"]:
                    score2 += weight
                    improvements.append(f"{metric}: +{comp['percent_change']:.2f}%")
                else:
                    score1 += weight
                    degradations.append(f"{metric}: {comp['percent_change']:.2f}%")
        
        if score2 > score1:
            winner = "model_2"
            recommendation = f"Model 2 performs better overall. " \
                           f"Key improvements: {', '.join(improvements[:3]) if improvements else 'Multiple metrics improved'}"
        elif score1 > score2:
            winner = "model_1"
            recommendation = f"Model 1 performs better overall. " \
                           f"Model 2 shows: {', '.join(degradations[:3]) if degradations else 'Multiple metrics degraded'}"
        else:
            winner = "tie"
            recommendation = "Models perform similarly. Consider other factors like training time, " \
                           "deployment stage, or prediction volume."
        
        return winner, recommendation
    
    def _generate_comparison_summary(
        self,
        metric_comparison: Dict[str, Any],
        winner: str
    ) -> Dict[str, Any]:
        """Generate a summary of the comparison"""
        
        improvements = sum(1 for m in metric_comparison.values() if m.get("improved", False))
        total_metrics = len(metric_comparison)
        
        significant_changes = [
            k for k, v in metric_comparison.items()
            if v.get("significance") == "high"
        ]
        
        return {
            "winner": winner,
            "total_metrics_compared": total_metrics,
            "metrics_improved": improvements,
            "metrics_degraded": total_metrics - improvements,
            "significant_changes": significant_changes,
            "overall_trend": "improvement" if improvements > total_metrics / 2 else "degradation" if improvements < total_metrics / 2 else "mixed"
        }
    
    async def get_registry_summary(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Get a summary of all models in the registry for a project
        """
        
        all_metadata = await ModelRegistryMetadata.find({
            "project_id": project_id
        }).to_list()
        
        # Count by stage
        stage_counts = {}
        for metadata in all_metadata:
            stage = metadata.deployment_stage
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
        
        # Count by approval status
        approval_counts = {}
        for metadata in all_metadata:
            status = metadata.approval_status
            approval_counts[status] = approval_counts.get(status, 0) + 1
        
        # Total predictions
        total_predictions = sum(m.total_predictions for m in all_metadata)
        
        return {
            "project_id": project_id,
            "total_models": len(all_metadata),
            "by_deployment_stage": stage_counts,
            "by_approval_status": approval_counts,
            "total_predictions_served": total_predictions,
            "production_model_count": stage_counts.get("production", 0)
        }

