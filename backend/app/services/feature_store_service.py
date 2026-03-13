"""
Feature Store Service - Critical component for ML Pipeline
Handles feature engineering, storage, and serving
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from pathlib import Path

from app.models import (
    FeatureDefinition, FeatureSet, FeatureValue,
    Project, Dataset, User
)

logger = logging.getLogger(__name__)


class FeatureStoreService:
    """
    Feature Store Service for managing features across the ML lifecycle
    
    Key Capabilities:
    1. Feature Definition: Define reusable feature transformations
    2. Feature Computation: Compute features from raw data
    3. Feature Storage: Store computed features for fast serving
    4. Feature Serving: Retrieve features for training/inference
    5. Feature Versioning: Track feature evolution
    """
    
    def __init__(self):
        self.storage_path = Path("feature_store")
        self.storage_path.mkdir(exist_ok=True)
    
    # ========================================================================
    # FEATURE DEFINITION MANAGEMENT
    # ========================================================================
    
    async def create_feature_definition(
        self,
        name: str,
        feature_type: str,
        data_type: str,
        source_columns: List[str],
        transformation_logic: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        user_id: str = None
    ) -> FeatureDefinition:
        """
        Create a new feature definition
        
        Example transformation_logic:
        {
            "type": "aggregation",
            "operation": "mean",
            "window": "30d",
            "column": "purchase_amount"
        }
        """
        
        # Check if feature already exists
        existing = await FeatureDefinition.find_one({
            "name": name,
            "project_id": project_id
        })
        
        if existing:
            # Create new version
            version = existing.version + 1
            existing.is_active = False
            await existing.save()
        else:
            version = 1
        
        feature_def = FeatureDefinition(
            name=name,
            description=description,
            feature_type=feature_type,
            data_type=data_type,
            transformation_logic=transformation_logic,
            source_columns=source_columns,
            project_id=project_id,
            version=version,
            created_by=user_id or "system"
        )
        
        await feature_def.insert()
        logger.info(f"Created feature definition: {name} (v{version})")
        
        return feature_def
    
    async def get_feature_definitions(
        self,
        project_id: Optional[str] = None,
        active_only: bool = True
    ) -> List[FeatureDefinition]:
        """Get all feature definitions for a project or globally"""
        
        query = {"is_active": True} if active_only else {}
        
        if project_id:
            query["$or"] = [
                {"project_id": project_id},
                {"project_id": None}  # Include shared features
            ]
        
        return await FeatureDefinition.find(query).to_list()
    
    # ========================================================================
    # FEATURE SET MANAGEMENT
    # ========================================================================
    
    async def create_feature_set(
        self,
        name: str,
        project_id: str,
        feature_names: List[str],
        description: Optional[str] = None
    ) -> FeatureSet:
        """
        Create a feature set (collection of features used together)
        """
        
        # Validate that all features exist
        for feature_name in feature_names:
            feature_def = await FeatureDefinition.find_one({
                "name": feature_name,
                "is_active": True
            })
            if not feature_def:
                raise ValueError(f"Feature '{feature_name}' not found")
        
        # Check if feature set exists
        existing = await FeatureSet.find_one({
            "name": name,
            "project_id": project_id
        })
        
        if existing:
            version = existing.version + 1
            existing.is_active = False
            await existing.save()
        else:
            version = 1
        
        feature_set = FeatureSet(
            name=name,
            description=description,
            project_id=project_id,
            feature_names=feature_names,
            version=version
        )
        
        await feature_set.insert()
        logger.info(f"Created feature set: {name} with {len(feature_names)} features")
        
        return feature_set
    
    async def get_feature_set(
        self,
        project_id: str,
        name: Optional[str] = None,
        feature_set_id: Optional[str] = None
    ) -> Optional[FeatureSet]:
        """Get a feature set by name or ID"""
        
        if feature_set_id:
            return await FeatureSet.get(feature_set_id)
        elif name:
            return await FeatureSet.find_one({
                "name": name,
                "project_id": project_id,
                "is_active": True
            })
        return None
    
    # ========================================================================
    # FEATURE COMPUTATION
    # ========================================================================
    
    async def compute_features(
        self,
        data: pd.DataFrame,
        feature_names: List[str],
        project_id: str
    ) -> pd.DataFrame:
        """
        Compute features from raw data based on feature definitions
        
        This is the core feature engineering logic
        """
        
        result_df = data.copy()
        
        for feature_name in feature_names:
            # Get feature definition
            feature_def = await FeatureDefinition.find_one({
                "name": feature_name,
                "is_active": True
            })
            
            if not feature_def:
                logger.warning(f"Feature '{feature_name}' not found, skipping")
                continue
            
            # Apply transformation
            try:
                result_df[feature_name] = await self._apply_transformation(
                    data, feature_def
                )
                logger.info(f"Computed feature: {feature_name}")
            except Exception as e:
                logger.error(f"Failed to compute feature '{feature_name}': {str(e)}")
                # Use default value based on data type
                if feature_def.data_type == "float":
                    result_df[feature_name] = 0.0
                elif feature_def.data_type == "int":
                    result_df[feature_name] = 0
                else:
                    result_df[feature_name] = None
        
        return result_df
    
    async def _apply_transformation(
        self,
        data: pd.DataFrame,
        feature_def: FeatureDefinition
    ) -> pd.Series:
        """
        Apply a transformation based on feature definition
        """
        
        transformation = feature_def.transformation_logic
        
        if not transformation:
            # No transformation, just return source column
            if feature_def.source_columns:
                return data[feature_def.source_columns[0]]
            else:
                raise ValueError(f"No transformation or source column for {feature_def.name}")
        
        transform_type = transformation.get("type")
        
        # Aggregation transformations
        if transform_type == "aggregation":
            operation = transformation.get("operation", "mean")
            column = transformation.get("column")
            
            if operation == "mean":
                return data[column].fillna(data[column].mean())
            elif operation == "sum":
                return data[column].fillna(0)
            elif operation == "count":
                return data[column].notna().astype(int)
            elif operation == "max":
                return data[column].fillna(data[column].max())
            elif operation == "min":
                return data[column].fillna(data[column].min())
        
        # Mathematical transformations
        elif transform_type == "math":
            operation = transformation.get("operation")
            column = transformation.get("column")
            
            if operation == "log":
                return np.log1p(data[column].clip(lower=0))
            elif operation == "sqrt":
                return np.sqrt(data[column].clip(lower=0))
            elif operation == "square":
                return data[column] ** 2
            elif operation == "normalize":
                mean = data[column].mean()
                std = data[column].std()
                return (data[column] - mean) / (std if std > 0 else 1)
        
        # Categorical encoding
        elif transform_type == "encoding":
            column = transformation.get("column")
            encoding_type = transformation.get("encoding", "label")
            
            if encoding_type == "label":
                return pd.Categorical(data[column]).codes
            elif encoding_type == "onehot":
                # Return first column of one-hot encoding for simplicity
                return pd.get_dummies(data[column], prefix=feature_def.name).iloc[:, 0]
        
        # Binning
        elif transform_type == "binning":
            column = transformation.get("column")
            bins = transformation.get("bins", 5)
            return pd.cut(data[column], bins=bins, labels=False)
        
        # Ratio/derived features
        elif transform_type == "ratio":
            numerator = transformation.get("numerator")
            denominator = transformation.get("denominator")
            return data[numerator] / (data[denominator].replace(0, 1))
        
        # Default: return first source column
        if feature_def.source_columns:
            return data[feature_def.source_columns[0]]
        
        raise ValueError(f"Unknown transformation type: {transform_type}")
    
    # ========================================================================
    # FEATURE STORAGE (MATERIALIZATION)
    # ========================================================================
    
    async def materialize_features(
        self,
        features_df: pd.DataFrame,
        entity_id_column: str,
        entity_type: str,
        project_id: str,
        feature_set_id: Optional[str] = None
    ) -> int:
        """
        Store computed features for fast serving (materialization)
        
        Returns: Number of feature values stored
        """
        
        stored_count = 0
        
        for _, row in features_df.iterrows():
            entity_id = str(row[entity_id_column])
            
            for feature_name in features_df.columns:
                if feature_name == entity_id_column:
                    continue
                
                # Store feature value
                feature_value = FeatureValue(
                    feature_name=feature_name,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    value=row[feature_name],
                    project_id=project_id,
                    feature_set_id=feature_set_id
                )
                
                await feature_value.insert()
                stored_count += 1
        
        logger.info(f"Materialized {stored_count} feature values")
        return stored_count
    
    # ========================================================================
    # FEATURE SERVING
    # ========================================================================
    
    async def get_features_for_entity(
        self,
        entity_id: str,
        feature_names: List[str],
        project_id: str
    ) -> Dict[str, Any]:
        """
        Retrieve features for a specific entity (fast serving)
        """
        
        features = {}
        
        for feature_name in feature_names:
            # Get latest feature value
            feature_value = await FeatureValue.find_one({
                "feature_name": feature_name,
                "entity_id": entity_id,
                "project_id": project_id
            }, sort=[("computed_at", -1)])
            
            if feature_value:
                features[feature_name] = feature_value.value
            else:
                # Feature not found, use default
                logger.warning(f"Feature '{feature_name}' not found for entity '{entity_id}'")
                features[feature_name] = None
        
        return features
    
    async def get_features_batch(
        self,
        entity_ids: List[str],
        feature_names: List[str],
        project_id: str
    ) -> pd.DataFrame:
        """
        Retrieve features for multiple entities (batch serving)
        """
        
        results = []
        
        for entity_id in entity_ids:
            features = await self.get_features_for_entity(
                entity_id, feature_names, project_id
            )
            features['entity_id'] = entity_id
            results.append(features)
        
        return pd.DataFrame(results)
    
    # ========================================================================
    # AUTO FEATURE GENERATION (Smart Feature Engineering)
    # ========================================================================
    
    async def auto_generate_features(
        self,
        project_id: str,
        dataset_id: str,
        user_id: str
    ) -> List[FeatureDefinition]:
        """
        Automatically generate common features based on data types
        This is a smart feature engineering helper
        """
        
        from app.models import Dataset, DataColumn
        
        # Get dataset
        dataset = await Dataset.get(dataset_id)
        if not dataset:
            raise ValueError("Dataset not found")
        
        # Get columns
        columns = await DataColumn.find({"dataset_id": dataset_id}).to_list()
        
        generated_features = []
        
        for col in columns:
            col_name = col.column_name
            col_type = col.original_type
            
            # Numerical features
            if 'int' in col_type or 'float' in col_type:
                # Log transformation
                feature_def = await self.create_feature_definition(
                    name=f"{col_name}_log",
                    feature_type="numerical",
                    data_type="float",
                    source_columns=[col_name],
                    transformation_logic={
                        "type": "math",
                        "operation": "log",
                        "column": col_name
                    },
                    description=f"Log transformation of {col_name}",
                    project_id=project_id,
                    user_id=user_id
                )
                generated_features.append(feature_def)
                
                # Normalized feature
                feature_def = await self.create_feature_definition(
                    name=f"{col_name}_normalized",
                    feature_type="numerical",
                    data_type="float",
                    source_columns=[col_name],
                    transformation_logic={
                        "type": "math",
                        "operation": "normalize",
                        "column": col_name
                    },
                    description=f"Normalized {col_name}",
                    project_id=project_id,
                    user_id=user_id
                )
                generated_features.append(feature_def)
            
            # Categorical features
            elif 'object' in col_type or 'string' in col_type:
                feature_def = await self.create_feature_definition(
                    name=f"{col_name}_encoded",
                    feature_type="categorical",
                    data_type="int",
                    source_columns=[col_name],
                    transformation_logic={
                        "type": "encoding",
                        "encoding": "label",
                        "column": col_name
                    },
                    description=f"Label encoded {col_name}",
                    project_id=project_id,
                    user_id=user_id
                )
                generated_features.append(feature_def)
        
        logger.info(f"Auto-generated {len(generated_features)} features for project {project_id}")
        return generated_features
    
    # ========================================================================
    # FEATURE MONITORING
    # ========================================================================
    
    async def get_feature_statistics(
        self,
        feature_name: str,
        project_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get statistics about a feature (for monitoring)
        """
        
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get recent feature values
        feature_values = await FeatureValue.find({
            "feature_name": feature_name,
            "project_id": project_id,
            "computed_at": {"$gte": cutoff_date}
        }).to_list()
        
        if not feature_values:
            return {
                "feature_name": feature_name,
                "count": 0,
                "message": "No data available"
            }
        
        # Extract values
        values = [fv.value for fv in feature_values if fv.value is not None]
        
        if not values:
            return {
                "feature_name": feature_name,
                "count": 0,
                "message": "No valid values"
            }
        
        # Calculate statistics
        try:
            values_array = np.array(values, dtype=float)
            stats = {
                "feature_name": feature_name,
                "count": len(values),
                "mean": float(np.mean(values_array)),
                "std": float(np.std(values_array)),
                "min": float(np.min(values_array)),
                "max": float(np.max(values_array)),
                "median": float(np.median(values_array)),
                "null_count": len([v for v in feature_values if v.value is None]),
                "period_days": days
            }
        except Exception as e:
            # Non-numeric feature
            stats = {
                "feature_name": feature_name,
                "count": len(values),
                "unique_values": len(set(values)),
                "null_count": len([v for v in feature_values if v.value is None]),
                "period_days": days,
                "type": "categorical"
            }
        
        return stats

