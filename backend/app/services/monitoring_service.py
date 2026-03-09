import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path

from app.models import Project, Model, Dataset, DriftMetric, System, ModelRegistryMetadata, DriftBaseline

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for monitoring model performance and detecting drift"""
    
    def __init__(self):
        self.drift_threshold = 0.1  # KL divergence threshold
    
    async def detect_drift(
        self, 
        project_id: str, 
        new_data: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Detect drift by comparing new data with baseline (training data)
        """
        try:
            # Verify project access
            project = await Project.get(project_id)
            if not project or project.user_id != user_id:
                raise ValueError("Project not found or access denied")
            
            # Get latest model
            model = await Model.find(
                {"project_id": project_id}
            ).sort("-version").first_or_none()
            
            if not model:
                raise ValueError("No trained model found for drift detection")
            
            # Get baseline dataset
            datasets = await Dataset.find({"project_id": project_id}).to_list()
            if not datasets:
                raise ValueError("No baseline dataset found")
            
            # Load baseline data
            baseline_df = await self._load_baseline_data(datasets)
            new_df = pd.DataFrame([new_data])
            
            # Calculate drift for each feature
            drift_results = []
            overall_drift_score = 0.0
            
            for column in baseline_df.select_dtypes(include=[np.number]).columns:
                if column in new_df.columns:
                    drift_score = self._calculate_drift(
                        baseline_df[column].values,
                        new_df[column].values
                    )
                    
                    # Save drift metric
                    drift_metric = DriftMetric(
                        project_id=project_id,
                        model_id=str(model.id),
                        feature_name=column,
                        drift_score=drift_score
                    )
                    await drift_metric.insert()
                    
                    drift_results.append({
                        "feature": column,
                        "drift_score": drift_score,
                        "status": "drift_detected" if drift_score > self.drift_threshold else "normal"
                    })
                    
                    overall_drift_score += drift_score
            
            overall_drift_score /= len(drift_results) if drift_results else 1
            
            return {
                "project_id": project_id,
                "model_id": str(model.id),
                "model_version": model.version,
                "overall_drift_score": overall_drift_score,
                "drift_detected": overall_drift_score > self.drift_threshold,
                "features": drift_results,
                "threshold": self.drift_threshold,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Drift detection failed: {str(e)}")
            raise
    
    async def get_drift_history(
        self,
        project_id: str,
        user_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get drift history for the last N days"""
        
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != user_id:
            raise ValueError("Project not found or access denied")
        
        # Get drift metrics from last N days
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        drift_metrics = await DriftMetric.find(
            {
                "project_id": project_id,
                "detected_at": {"$gte": cutoff_date}
            }
        ).sort("-detected_at").to_list()
        
        # Group by feature
        feature_drift = {}
        for metric in drift_metrics:
            if metric.feature_name not in feature_drift:
                feature_drift[metric.feature_name] = []
            
            feature_drift[metric.feature_name].append({
                "drift_score": metric.drift_score,
                "detected_at": metric.detected_at,
                "model_id": metric.model_id
            })
        
        # Calculate summary statistics
        all_scores = [m.drift_score for m in drift_metrics]
        summary = {
            "total_checks": len(drift_metrics),
            "avg_drift_score": np.mean(all_scores) if all_scores else 0.0,
            "max_drift_score": max(all_scores) if all_scores else 0.0,
            "drift_alerts": sum(1 for s in all_scores if s > self.drift_threshold)
        }
        
        return {
            "project_id": project_id,
            "period_days": days,
            "summary": summary,
            "feature_drift": feature_drift,
            "threshold": self.drift_threshold
        }
    
    async def get_model_metrics_history(
        self,
        project_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get metrics for all model versions"""
        
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != user_id:
            raise ValueError("Project not found or access denied")
        
        # Get all models
        models = await Model.find(
            {"project_id": project_id}
        ).sort("-version").to_list()
        
        metrics_history = []
        for model in models:
            metrics_history.append({
                "model_id": str(model.id),
                "version": model.version,
                "metrics": model.metrics,
                "created_at": model.created_at
            })
        
        return {
            "models": metrics_history,
            "total_models": len(models)
        }
    
    async def get_monitoring_dashboard(
        self,
        project_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive monitoring dashboard data"""
        
        # Verify project access
        project = await Project.get(project_id)
        if not project or project.user_id != user_id:
            raise ValueError("Project not found or access denied")
        
        # Get system info
        system = await System.get(project.system_id)
        
        # Get latest model
        latest_model = await Model.find(
            {"project_id": project_id}
        ).sort("-version").first_or_none()
        
        # Get recent drift metrics (last 24 hours)
        cutoff_date = datetime.utcnow() - timedelta(hours=24)
        recent_drift = await DriftMetric.find(
            {
                "project_id": project_id,
                "detected_at": {"$gte": cutoff_date}
            }
        ).to_list()
        
        # Calculate drift status
        drift_scores = [m.drift_score for m in recent_drift]
        avg_drift = np.mean(drift_scores) if drift_scores else 0.0
        
        drift_status = {
            "status": "critical" if avg_drift > 0.2 else "warning" if avg_drift > 0.1 else "healthy",
            "avg_drift_score": avg_drift,
            "checks_last_24h": len(recent_drift),
            "alerts": sum(1 for s in drift_scores if s > self.drift_threshold)
        }
        
        # Get model performance
        model_performance = {
            "current_version": latest_model.version if latest_model else 0,
            "metrics": latest_model.metrics if latest_model else {},
            "trained_at": latest_model.created_at if latest_model else None
        }
        
        return {
            "project_id": project_id,
            "project_name": project.name,
            "system_type": system.name if system else "unknown",
            "project_status": project.status,
            "drift_status": drift_status,
            "model_performance": model_performance,
            "timestamp": datetime.utcnow()
        }
    
    def _calculate_drift(self, baseline: np.ndarray, new_data: np.ndarray) -> float:
        """
        Calculate drift score using KL divergence
        Returns a score between 0 and 1 (higher = more drift)
        """
        try:
            # Create histograms
            bins = np.linspace(
                min(baseline.min(), new_data.min()),
                max(baseline.max(), new_data.max()),
                20
            )
            
            baseline_hist, _ = np.histogram(baseline, bins=bins, density=True)
            new_hist, _ = np.histogram(new_data, bins=bins, density=True)
            
            # Add small epsilon to avoid division by zero
            epsilon = 1e-10
            baseline_hist = baseline_hist + epsilon
            new_hist = new_hist + epsilon
            
            # Normalize
            baseline_hist = baseline_hist / baseline_hist.sum()
            new_hist = new_hist / new_hist.sum()
            
            return self._calculate_drift_from_histograms(baseline_hist, new_hist)
            
        except Exception as e:
            logger.warning(f"Drift calculation failed: {str(e)}")
            return 0.0
    
    def _calculate_drift_from_histograms(self, baseline_hist: np.ndarray, new_hist: np.ndarray) -> float:
        """
        Calculate drift score from pre-computed histograms using KL divergence
        Returns a score between 0 and 1 (higher = more drift)
        """
        try:
            # Calculate KL divergence
            kl_div = np.sum(new_hist * np.log(new_hist / baseline_hist))
            
            # Normalize to 0-1 range (clamp at 1.0)
            drift_score = min(kl_div / 2.0, 1.0)
            
            return float(drift_score)
            
        except Exception as e:
            logger.warning(f"Drift calculation from histograms failed: {str(e)}")
            return 0.0
    
    async def detect_drift_on_dataset(
        self,
        project_id: str,
        new_dataset_path: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Detect drift by comparing a new dataset with baseline (training data)
        This is used when a new dataset is uploaded and we want to check for drift
        
        Args:
            project_id: Project ID
            new_dataset_path: Path to the newly uploaded dataset file
            user_id: User ID for access verification
            
        Returns:
            Dict with drift detection results
        """
        try:
            # Verify project access
            project = await Project.get(project_id)
            if not project or project.user_id != user_id:
                raise ValueError("Project not found or access denied")
            
            # Get latest model
            model = await Model.find(
                {"project_id": project_id}
            ).sort("-version").first_or_none()
            
            if not model:
                logger.info(f"No trained model found for project {project_id}, skipping drift detection")
                return {
                    "drift_detected": False,
                    "message": "No trained model found, drift detection skipped"
                }
            
            # Try to get saved baseline statistics from database (preferred method)
            drift_baseline = await DriftBaseline.find(
                {"model_id": str(model.id)}
            ).sort("-created_at").first_or_none()
            
            if drift_baseline and drift_baseline.feature_statistics:
                # Use saved baseline statistics (works even if dataset files are deleted)
                logger.info(f"Using saved drift baseline from database for model {model.id} (version {drift_baseline.model_version})")
                logger.info(f"Baseline has {len(drift_baseline.feature_columns)} features: {drift_baseline.feature_columns}")
                baseline_stats = drift_baseline.feature_statistics
                baseline_columns = drift_baseline.feature_columns
                baseline_df = None  # Not needed when using saved baseline
                use_saved_baseline = True
            else:
                # Fallback: Try to load from dataset files (may not work if files were deleted)
                logger.info(f"No saved drift baseline found, attempting to load from dataset files...")
                all_datasets = await Dataset.find({"project_id": project_id}).to_list()
                
                # Try to get training dataset IDs from model registry
                registry_metadata = await ModelRegistryMetadata.find(
                    {"model_id": str(model.id)}
                ).first_or_none()
                
                baseline_datasets = []
                if registry_metadata and registry_metadata.training_dataset_ids:
                    training_dataset_ids = set(registry_metadata.training_dataset_ids)
                    baseline_datasets = [d for d in all_datasets if str(d.id) in training_dataset_ids]
                else:
                    # Find the new dataset and exclude it
                    new_dataset = None
                    for d in all_datasets:
                        d_path = str(Path(d.storage_path).resolve()) if d.storage_path else None
                        new_path = str(Path(new_dataset_path).resolve())
                        if d_path == new_path:
                            new_dataset = d
                            break
                    
                    if new_dataset:
                        baseline_datasets = [d for d in all_datasets if str(d.id) != str(new_dataset.id)]
                    else:
                        baseline_datasets = [
                            d for d in all_datasets 
                            if d.storage_path and str(Path(d.storage_path).resolve()) != str(Path(new_dataset_path).resolve())
                        ]
                
                if not baseline_datasets:
                    logger.warning(f"No baseline datasets found for project {project_id}")
                    return {
                        "drift_detected": False,
                        "message": "No baseline data available (datasets may have been deleted). Please retrain the model to enable drift detection."
                    }
                
                # Load baseline data from files
                logger.info(f"Loading baseline data from {len(baseline_datasets)} datasets: {[d.name for d in baseline_datasets]}")
                baseline_df = await self._load_baseline_data(baseline_datasets)
                logger.info(f"Baseline data loaded: {len(baseline_df)} rows, {len(baseline_df.columns)} columns")
                
                if baseline_df.empty:
                    logger.warning(f"Baseline data is empty - dataset files may have been deleted")
                    return {
                        "drift_detected": False,
                        "message": "Baseline dataset files not found (deleted for privacy). Please retrain the model to enable drift detection."
                    }
                
                baseline_columns = baseline_df.select_dtypes(include=[np.number]).columns.tolist()
                use_saved_baseline = False
            
            # Load new dataset
            new_path = Path(new_dataset_path)
            if not new_path.exists():
                # Try with absolute path
                new_path = Path(new_dataset_path).resolve()
                if not new_path.exists():
                    logger.warning(f"New dataset file not found: {new_dataset_path} (resolved: {new_path})")
                    return {
                        "drift_detected": False,
                        "message": f"New dataset file not found: {new_dataset_path}"
                    }
            
            logger.info(f"Loading new dataset from: {new_path}")
            new_df = pd.read_csv(new_path)
            logger.info(f"New dataset loaded: {len(new_df)} rows, {len(new_df.columns)} columns")
            
            # Calculate drift for each numerical feature
            drift_results = []
            overall_drift_score = 0.0
            feature_count = 0
            
            new_numeric_cols = new_df.select_dtypes(include=[np.number]).columns.tolist()
            matching_columns = [col for col in baseline_columns if col in new_numeric_cols]
            
            logger.info(f"Baseline has {len(baseline_columns)} numerical columns: {baseline_columns}")
            logger.info(f"New dataset has {len(new_numeric_cols)} numerical columns: {new_numeric_cols}")
            logger.info(f"Found {len(matching_columns)} matching columns for drift detection: {matching_columns}")
            
            if not matching_columns:
                logger.warning(f"⚠️ No matching numerical columns between baseline and new dataset!")
                return {
                    "drift_detected": False,
                    "error": "No matching numerical columns found between baseline and new dataset",
                    "message": f"Baseline has {len(baseline_columns)} columns, new dataset has {len(new_numeric_cols)} columns, but none match."
                }
            
            for column in matching_columns:
                new_sample = new_df[column].dropna()
                
                if len(new_sample) > 0:
                    # Sample if dataset is too large
                    if len(new_sample) > 1000:
                        new_sample = new_sample.sample(n=1000, random_state=42)
                    
                    if use_saved_baseline:
                        # Use saved baseline statistics
                        baseline_stat = baseline_stats.get(column)
                        if baseline_stat:
                            # Reconstruct baseline histogram from saved data
                            baseline_hist = np.array(baseline_stat["histogram"])
                            baseline_bin_edges = np.array(baseline_stat["bin_edges"])
                            
                            # Create histogram for new data using same bins
                            new_hist, _ = np.histogram(new_sample.values, bins=baseline_bin_edges, density=True)
                            new_hist = new_hist + 1e-10
                            new_hist = new_hist / new_hist.sum()
                            
                            # Calculate KL divergence
                            drift_score = self._calculate_drift_from_histograms(baseline_hist, new_hist)
                        else:
                            logger.warning(f"No saved baseline statistics for column {column}")
                            continue
                    else:
                        # Use loaded baseline data
                        baseline_sample = baseline_df[column].dropna()
                        
                        if len(baseline_sample) > 0:
                            # Sample if dataset is too large
                            if len(baseline_sample) > 1000:
                                baseline_sample = baseline_sample.sample(n=1000, random_state=42)
                            
                            drift_score = self._calculate_drift(
                                baseline_sample.values,
                                new_sample.values
                            )
                        else:
                            continue
                        
                        # Save drift metric
                        drift_metric = DriftMetric(
                            project_id=project_id,
                            model_id=str(model.id),
                            feature_name=column,
                            drift_score=drift_score
                        )
                        await drift_metric.insert()
                        
                        drift_results.append({
                            "feature": column,
                            "drift_score": drift_score,
                            "status": "drift_detected" if drift_score > self.drift_threshold else "normal"
                        })
                        
                        overall_drift_score += drift_score
                        feature_count += 1
            
            if feature_count > 0:
                overall_drift_score /= feature_count
            
            drift_detected = overall_drift_score > self.drift_threshold
            logger.info(f"Drift detection completed for project {project_id}: overall_score={overall_drift_score:.4f}, threshold={self.drift_threshold}, drift_detected={drift_detected}, features_checked={feature_count}")
            
            return {
                "project_id": project_id,
                "model_id": str(model.id),
                "model_version": model.version,
                "overall_drift_score": overall_drift_score,
                "drift_detected": drift_detected,
                "features": drift_results,
                "threshold": self.drift_threshold,
                "features_checked": feature_count,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Dataset drift detection failed for project {project_id}: {str(e)}", exc_info=True)
            # Don't raise - drift detection failure shouldn't break dataset upload
            return {
                "drift_detected": False,
                "error": str(e),
                "message": "Drift detection failed but dataset upload succeeded"
            }
    
    async def _load_baseline_data(self, datasets: List[Dataset]) -> pd.DataFrame:
        """Load and merge baseline datasets"""
        dataframes = []
        failed_datasets = []
        
        for dataset in datasets:
            if dataset.storage_path:
                dataset_path = Path(dataset.storage_path)
                # Try both relative and absolute paths
                if not dataset_path.exists():
                    dataset_path = dataset_path.resolve()
                
                if dataset_path.exists():
                    try:
                        df = pd.read_csv(dataset_path)
                        logger.info(f"Successfully loaded baseline dataset {dataset.name}: {len(df)} rows, {len(df.columns)} columns")
                        dataframes.append(df)
                    except Exception as e:
                        logger.warning(f"Failed to load dataset {dataset.name} from {dataset_path}: {str(e)}")
                        failed_datasets.append(dataset.name)
                else:
                    logger.warning(f"Baseline dataset file not found: {dataset_path} (dataset: {dataset.name})")
                    failed_datasets.append(dataset.name)
            else:
                logger.warning(f"Dataset {dataset.name} has no storage_path")
                failed_datasets.append(dataset.name)
        
        if not dataframes:
            logger.error(f"❌ No baseline datasets could be loaded! Failed datasets: {failed_datasets}")
            logger.error("This usually means the training datasets were deleted for privacy reasons.")
            logger.error("Drift detection requires access to the original training data.")
            # Return empty DataFrame instead of dummy data to make the problem obvious
            return pd.DataFrame()
        
        result = pd.concat(dataframes, ignore_index=True)
        logger.info(f"✅ Merged baseline data: {len(result)} rows, {len(result.columns)} columns from {len(dataframes)} datasets")
        return result

