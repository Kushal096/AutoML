from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import pandas as pd
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class BaseSystemSchema(ABC):
    """Base class for system-specific dataset schemas"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """System name"""
        pass
    
    @property
    @abstractmethod
    def required_columns(self) -> List[str]:
        """Required column mappings"""
        pass
    
    @property
    @abstractmethod
    def optional_columns(self) -> List[str]:
        """Optional column mappings"""
        pass
    
    @property
    @abstractmethod
    def algorithms(self) -> List[str]:
        """Supported algorithms for this system"""
        pass
    
    @property
    @abstractmethod
    def metrics(self) -> List[str]:
        """Supported metrics for this system"""
        pass
    
    @abstractmethod
    def validate_dataset(self, df: pd.DataFrame, column_mapping: Optional[Dict[str, str]] = None) -> bool:
        """Validate dataset against system schema"""
        pass
    
    @abstractmethod
    def infer_column_types(self, columns: List[str]) -> Dict[str, str]:
        """Infer column types based on system-specific patterns"""
        pass
    
    def apply_column_mapping(self, df: pd.DataFrame, column_mapping: Dict[str, str]) -> pd.DataFrame:
        """Apply column mapping to dataframe"""
        mapped_df = df.copy()
        
        # Rename columns according to mapping
        # column_mapping format: {original_col: mapped_type}
        # e.g., {'churned': 'churn'} means rename 'churned' to 'churn'
        rename_mapping = {}
        for original_col, mapped_type in column_mapping.items():
            if original_col in df.columns:
                rename_mapping[original_col] = mapped_type
        
        if rename_mapping:
            mapped_df = mapped_df.rename(columns=rename_mapping)
            logger.info(f"Applied column mapping: {rename_mapping}")
        
        return mapped_df


class RecommendationSystemSchema(BaseSystemSchema):
    """Schema for Recommendation System"""
    
    @property
    def name(self) -> str:
        return "recommendation"
    
    @property
    def required_columns(self) -> List[str]:
        return ["user_id", "item_id"]
    
    @property
    def optional_columns(self) -> List[str]:
        return ["interaction", "rating", "timestamp"]
    
    @property
    def algorithms(self) -> List[str]:
        return ["collaborative_filtering", "content_based", "matrix_factorization"]
    
    @property
    def metrics(self) -> List[str]:
        return ["precision", "recall", "ndcg"]
    
    def validate_dataset(self, df: pd.DataFrame, column_mapping: Optional[Dict[str, str]] = None) -> bool:
        """Validate recommendation dataset"""
        
        # Apply column mapping if provided
        if column_mapping:
            df = self.apply_column_mapping(df, column_mapping)
        
        # Check required columns
        missing_required = [col for col in self.required_columns if col not in df.columns]
        if missing_required:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns for recommendation system: {missing_required}"
            )
        
        # Validate data types and values
        errors = []
        
        # user_id and item_id must exist and not be null
        for col in ["user_id", "item_id"]:
            if df[col].isnull().any():
                errors.append(f"{col} cannot contain null values")
        
        # rating must be numeric if present
        if "rating" in df.columns:
            try:
                numeric_ratings = pd.to_numeric(df["rating"], errors='coerce')
                if numeric_ratings.isnull().any():
                    errors.append("rating column contains non-numeric values")
            except Exception as e:
                errors.append(f"rating column validation failed: {str(e)}")
        
        # timestamp must be datetime-parseable if present
        if "timestamp" in df.columns:
            try:
                parsed_timestamps = pd.to_datetime(df["timestamp"], errors='coerce')
                if parsed_timestamps.isnull().any():
                    errors.append("timestamp column contains unparseable datetime values")
            except Exception as e:
                errors.append(f"timestamp column validation failed: {str(e)}")
        
        if errors:
            raise HTTPException(
                status_code=400,
                detail=f"Recommendation dataset validation failed: {'; '.join(errors)}"
            )
        
        return True
    
    def infer_column_types(self, columns: List[str]) -> Dict[str, str]:
        """Infer column types for recommendation system"""
        mappings = {}
        
        patterns = {
            'user_id': ['user_id', 'userid', 'user', 'customer_id', 'customerid', 'client_id'],
            'item_id': ['item_id', 'itemid', 'item', 'product_id', 'productid', 'product'],
            'interaction': ['interaction', 'purchase', 'click', 'view', 'action'],
            'rating': ['rating', 'score', 'feedback', 'preference', 'stars'],
            'timestamp': ['timestamp', 'time', 'date', 'created_at', 'updated_at', 'datetime']
        }
        
        for col in columns:
            col_lower = col.lower()
            mapped = False
            for type_name, pattern_list in patterns.items():
                if any(pattern in col_lower for pattern in pattern_list):
                    mappings[col] = type_name
                    mapped = True
                    break
            
            if not mapped:
                mappings[col] = 'feature'
        
        return mappings


class ChurnPredictionSchema(BaseSystemSchema):
    """Schema for Churn Prediction System"""
    
    @property
    def name(self) -> str:
        return "churn_prediction"
    
    @property
    def required_columns(self) -> List[str]:
        return ["customer_id", "churn"]
    
    @property
    def optional_columns(self) -> List[str]:
        return ["age", "usage", "plan_type", "tenure"]
    
    @property
    def algorithms(self) -> List[str]:
        return ["logistic_regression", "random_forest", "xgboost", "neural_networks"]
    
    @property
    def metrics(self) -> List[str]:
        return ["accuracy", "precision", "recall", "f1_score", "auc_roc"]
    
    def validate_dataset(self, df: pd.DataFrame, column_mapping: Optional[Dict[str, str]] = None) -> bool:
        """Validate churn prediction dataset"""
        
        # Apply column mapping if provided
        if column_mapping:
            df = self.apply_column_mapping(df, column_mapping)
        
        # Check required columns
        missing_required = [col for col in self.required_columns if col not in df.columns]
        if missing_required:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns for churn prediction system: {missing_required}"
            )
        
        # Validate data types and values
        errors = []
        
        # customer_id must not be null
        if df["customer_id"].isnull().any():
            errors.append("customer_id cannot contain null values")
        
        # churn must be binary (0/1 or true/false)
        churn_values = df["churn"].dropna().unique()
        valid_churn_values = {0, 1, True, False, '0', '1', 'true', 'false', 'True', 'False'}
        if not all(val in valid_churn_values for val in churn_values):
            errors.append("churn column must be binary (0/1 or true/false)")
        
        # Numeric columns must be numeric
        numeric_cols = ["age", "usage", "tenure"]
        for col in numeric_cols:
            if col in df.columns:
                try:
                    numeric_values = pd.to_numeric(df[col], errors='coerce')
                    null_ratio = numeric_values.isnull().sum() / len(df[col])
                    if null_ratio > 0.5:  # More than 50% null after conversion
                        errors.append(f"{col} column contains too many non-numeric values")
                except Exception as e:
                    errors.append(f"{col} column validation failed: {str(e)}")
        
        if errors:
            raise HTTPException(
                status_code=400,
                detail=f"Churn prediction dataset validation failed: {'; '.join(errors)}"
            )
        
        return True
    
    def infer_column_types(self, columns: List[str]) -> Dict[str, str]:
        """Infer column types for churn prediction system"""
        mappings = {}
        
        patterns = {
            'customer_id': ['customer_id', 'customerid', 'customer', 'user_id', 'userid', 'client_id'],
            'churn': ['churn', 'churned', 'left', 'cancelled', 'target'],
            'age': ['age', 'years', 'birth'],
            'usage': ['usage', 'spend', 'consumption', 'activity'],
            'plan_type': ['plan', 'subscription', 'tier', 'package'],
            'tenure': ['tenure', 'duration', 'months', 'days', 'period']
        }
        
        for col in columns:
            col_lower = col.lower()
            mapped = False
            for type_name, pattern_list in patterns.items():
                if any(pattern in col_lower for pattern in pattern_list):
                    mappings[col] = type_name
                    mapped = True
                    break
            
            if not mapped:
                mappings[col] = 'feature'
        
        return mappings


class SystemSchemaResolver:
    """Resolver to get appropriate schema based on system type"""
    
    SCHEMAS = {
        "Recommendation": RecommendationSystemSchema(),
        "Churn Prediction": ChurnPredictionSchema(),
    }
    
    # Map specific system types to their generic schema
    SYSTEM_TYPE_MAPPING = {
        # Recommendation systems
        "Collaborative Filtering": "Recommendation",
        "Content-Based Filtering": "Recommendation",
        "Popularity-Based": "Recommendation",
        "Hybrid Recommendation": "Recommendation",
        "Recommendation": "Recommendation",
        
        # Churn prediction systems
        "Customer Churn": "Churn Prediction",
        "Subscription Churn": "Churn Prediction",
        "Product Churn": "Churn Prediction",
        "Revenue Churn": "Churn Prediction",
        "Early Churn Detection": "Churn Prediction",
        "Late Churn Analysis": "Churn Prediction",
        "Churn Prediction": "Churn Prediction",
        
        # Other systems (can be added later)
        "Fraud Detection": "Churn Prediction",  # Uses similar binary classification
        "Sentiment Analysis": "Churn Prediction",  # Uses similar classification
        "Price Optimization": "Recommendation",  # Uses similar techniques
        "Demand Forecasting": "Recommendation",  # Uses similar techniques
    }
    
    @classmethod
    def get_schema(cls, system_name: str) -> BaseSystemSchema:
        """Get schema instance for given system name"""
        # Map specific type to generic type
        generic_type = cls.SYSTEM_TYPE_MAPPING.get(system_name)
        
        if not generic_type:
            available_systems = list(cls.SYSTEM_TYPE_MAPPING.keys())
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported system type: {system_name}. Available: {available_systems}"
            )
        
        return cls.SCHEMAS[generic_type]
    
    @classmethod
    def get_supported_systems(cls) -> List[str]:
        """Get list of supported system names"""
        return list(cls.SCHEMAS.keys())