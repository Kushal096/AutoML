import os
import pickle
import joblib
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

import pandas as pd
import numpy as np
from fastapi import HTTPException

from app.models import Project, Model, System
from app.services.model_registry_service import ModelRegistryService

logger = logging.getLogger(__name__)


def convert_numpy_types(obj: Any) -> Any:
    """
    Recursively convert numpy types to native Python types for JSON serialization
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, pd.Series):
        return convert_numpy_types(obj.to_dict())
    elif isinstance(obj, pd.DataFrame):
        return convert_numpy_types(obj.to_dict('records'))
    else:
        return obj


class PredictionService:
    """Service for making predictions using trained models"""
    
    def __init__(self):
        self.storage_base_path = Path("model_storage")
        self.registry_service = ModelRegistryService()
    
    async def load_model(self, project_id: str) -> Tuple[Any, Model, System]:
        """Load the latest trained model for a project"""
        
        # Get latest model
        model = await Model.find(
            Model.project_id == project_id
        ).sort(-Model.version).first_or_none()
        
        if not model:
            raise HTTPException(
                status_code=404,
                detail="No trained model found for this project. Please train a model first."
            )
        
        # Get project and system info
        project = await Project.get(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        system = await System.get(project.system_id)
        if not system:
            raise HTTPException(status_code=404, detail="System not found")
        
        # Load model artifact
        if not model.storage_path or not os.path.exists(model.storage_path):
            raise HTTPException(
                status_code=500,
                detail="Model file not found. Model may be corrupted."
            )
        
        try:
            # Try joblib first (for sklearn models)
            try:
                model_artifact = joblib.load(model.storage_path)
            except:
                # Fall back to pickle
                with open(model.storage_path, 'rb') as f:
                    model_artifact = pickle.load(f)
            
            return model_artifact, model, system
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load model: {str(e)}"
            )
    
    async def predict_single(
        self, 
        project_id: str, 
        user_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        customer_id: Optional[str] = None,
        top_k: int = 10,
        source: str = "web"  # "sdk" or "web"
    ) -> Dict[str, Any]:
        """Make a single prediction"""
        
        model_artifact, model, system = await self.load_model(project_id)
        system_name = system.name.lower()
        
        # Track prediction in Model Registry with source
        try:
            await self.registry_service.record_prediction(str(model.id), source=source)
        except Exception as e:
            logger.warning(f"Failed to record prediction in registry: {str(e)}")
        
        # Route to appropriate prediction method based on system type
        if "recommendation" in system_name:
            result = await self._predict_recommendation(
                model_artifact, model, user_id, top_k
            )
        elif "churn" in system_name:
            result = await self._predict_churn(
                model_artifact, model, customer_id or user_id, input_data
            )
        else:
            result = await self._predict_generic(
                model_artifact, model, input_data
            )
        
        # Ensure all numpy types are converted (double-check)
        return convert_numpy_types(result)
    
    async def predict_batch(
        self, 
        project_id: str,
        users: Optional[List[str]] = None,
        customers: Optional[List[str]] = None,
        input_data: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Make batch predictions"""
        
        model_artifact, model, system = await self.load_model(project_id)
        system_name = system.name.lower()
        
        results = []
        
        # Route to appropriate prediction method based on system type
        if "recommendation" in system_name:
            if not users:
                raise HTTPException(
                    status_code=400,
                    detail="'users' list is required for recommendation systems"
                )
            
            for user_id in users:
                try:
                    prediction = await self._predict_recommendation(
                        model_artifact, model, user_id, top_k
                    )
                    results.append({
                        "user_id": user_id,
                        "predictions": prediction["predictions"],
                        "status": "success"
                    })
                except Exception as e:
                    results.append({
                        "user_id": user_id,
                        "predictions": [],
                        "status": "error",
                        "error": str(e)
                    })
        
        elif "churn" in system_name:
            if not customers and not users:
                raise HTTPException(
                    status_code=400,
                    detail="'customers' or 'users' list is required for churn prediction"
                )
            
            customer_list = customers or users
            for i, customer_id in enumerate(customer_list):
                try:
                    data = input_data[i] if input_data and i < len(input_data) else None
                    prediction = await self._predict_churn(
                        model_artifact, model, customer_id, data
                    )
                    results.append({
                        "customer_id": customer_id,
                        "predictions": prediction["predictions"],
                        "status": "success"
                    })
                except Exception as e:
                    results.append({
                        "customer_id": customer_id,
                        "predictions": None,
                        "status": "error",
                        "error": str(e)
                    })
        
        else:
            if not input_data:
                raise HTTPException(
                    status_code=400,
                    detail="'input_data' is required for this system type"
                )
            
            for i, data in enumerate(input_data):
                try:
                    prediction = await self._predict_generic(
                        model_artifact, model, data
                    )
                    results.append({
                        "index": i,
                        "predictions": prediction["predictions"],
                        "status": "success"
                    })
                except Exception as e:
                    results.append({
                        "index": i,
                        "predictions": None,
                        "status": "error",
                        "error": str(e)
                    })
        
        # Convert numpy types in batch results
        return convert_numpy_types(results)
    
    async def _predict_recommendation(
        self, 
        model_artifact: Any, 
        model: Model,
        user_id: str,
        top_k: int
    ) -> Dict[str, Any]:
        """Make recommendation prediction"""
        
        try:
            # Extract model components
            user_item_matrix = model_artifact.get("user_item_matrix")
            item_similarity = model_artifact.get("item_similarity")
            
            if user_item_matrix is None or item_similarity is None:
                raise ValueError("Invalid recommendation model format")
            
            # For demo: generate random user index if user_id is new
            # In production, you'd have a user mapping
            user_idx = hash(user_id) % user_item_matrix.shape[0]
            
            # Get user's interaction vector
            user_vector = user_item_matrix[user_idx]
            
            # Calculate scores for all items
            scores = np.dot(user_vector, item_similarity)
            
            # Get top-k items (excluding already interacted items)
            interacted_items = np.where(user_vector > 0)[0]
            scores[interacted_items] = -np.inf  # Exclude already interacted
            
            top_items = np.argsort(scores)[-top_k:][::-1]
            top_scores = scores[top_items]
            
            recommendations = [
                {
                    "item_id": f"item_{int(item_idx)}",
                    "score": float(score),
                    "rank": int(rank + 1)
                }
                for rank, (item_idx, score) in enumerate(zip(top_items, top_scores))
                if score > -np.inf
            ]
            
            result = {
                "predictions": recommendations,
                "metadata": {
                    "user_id": user_id,
                    "total_recommendations": len(recommendations),
                    "model_type": "collaborative_filtering"
                }
            }
            
            # Convert numpy types to native Python types
            return convert_numpy_types(result)
            
        except Exception as e:
            logger.error(f"Recommendation prediction failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Prediction failed: {str(e)}"
            )
    
    async def _predict_churn(
        self, 
        model_artifact: Any, 
        model: Model,
        customer_id: str,
        input_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make churn prediction"""
        
        try:
            # If no input data provided, create dummy features
            if not input_data:
                # Generate random features for demo
                input_data = {
                    "age": 35,
                    "usage": 150,
                    "tenure": 12,
                    "plan_type": "basic"
                }
            
            # Convert to DataFrame
            df = pd.DataFrame([input_data])
            
            # Check if model_artifact is a package with preprocessing info
            if isinstance(model_artifact, dict) and 'model' in model_artifact:
                trained_model = model_artifact['model']
                feature_names = model_artifact.get('feature_names', [])
                label_encoders = model_artifact.get('label_encoders', {})
                
                # Apply the same preprocessing as training
                # Remove ID columns
                feature_cols = [col for col in df.columns if 'id' not in col.lower()]
                X = df[feature_cols]
                
                # Apply label encoders for categorical columns
                for col, encoder in label_encoders.items():
                    if col in X.columns:
                        try:
                            X[col] = encoder.transform(X[col].astype(str))
                        except ValueError:
                            # Handle unseen categories by using the first category
                            X[col] = 0
                
                # Ensure all columns are numeric and match training features
                X = X.select_dtypes(include=[np.number])
                
                # Ensure we have the same features as training
                for feature in feature_names:
                    if feature not in X.columns:
                        X[feature] = 0  # Default value for missing features
                
                # Reorder columns to match training
                X = X[feature_names]
                
            else:
                # Fallback to old method
                trained_model = model_artifact
                
                # Handle categorical variables using simple encoding
                if 'plan_type' in df.columns:
                    plan_type_mapping = {'basic': 0, 'standard': 1, 'premium': 2}
                    df['plan_type'] = df['plan_type'].map(plan_type_mapping).fillna(0)
                
                # Select features
                feature_cols = [col for col in df.columns if 'id' not in col.lower()]
                X = df[feature_cols].select_dtypes(include=[np.number])
            
            # Make prediction
            if hasattr(trained_model, 'predict_proba'):
                proba_result = trained_model.predict_proba(X)[0]
                churn_probability = float(proba_result[1])
                pred_result = trained_model.predict(X)[0]
                churn_prediction = int(pred_result)
            else:
                # For models without predict_proba
                pred_result = trained_model.predict(X)[0]
                churn_prediction = int(pred_result)
                churn_probability = float(churn_prediction)
            
            # Convert pandas Series to dict and ensure native types
            input_processed = X.iloc[0].to_dict()
            
            result = {
                "predictions": {
                    "customer_id": customer_id,
                    "will_churn": bool(churn_prediction),
                    "churn_probability": churn_probability,
                    "risk_level": "high" if churn_probability > 0.7 else "medium" if churn_probability > 0.4 else "low"
                },
                "metadata": {
                    "model_type": "churn_prediction",
                    "features_used": list(X.columns),
                    "input_processed": input_processed
                }
            }
            
            # Convert numpy types to native Python types
            return convert_numpy_types(result)
            
        except Exception as e:
            logger.error(f"Churn prediction failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Prediction failed: {str(e)}"
            )
    
    async def _predict_generic(
        self, 
        model_artifact: Any, 
        model: Model,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make generic classification prediction"""
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame([input_data])
            
            # Check if model_artifact is a package with preprocessing info
            if isinstance(model_artifact, dict) and 'model' in model_artifact:
                trained_model = model_artifact['model']
                feature_names = model_artifact.get('feature_names', [])
                label_encoder = model_artifact.get('label_encoder', None)
                
                # Select only numeric features
                X = df.select_dtypes(include=[np.number])
                
                # Ensure we have the same features as training
                for feature in feature_names:
                    if feature not in X.columns:
                        X[feature] = 0  # Default value for missing features
                
                # Reorder columns to match training
                X = X[feature_names]
            else:
                # Fallback to old method
                trained_model = model_artifact
                label_encoder = None
                
                # Select only numeric features
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                X = df[numeric_cols]
            
            # Make prediction
            if hasattr(trained_model, 'predict_proba'):
                probabilities = trained_model.predict_proba(X)[0]
                pred_result = trained_model.predict(X)[0]
                prediction = int(pred_result)
                
                # Decode prediction if label encoder exists
                if label_encoder:
                    predicted_label = label_encoder.inverse_transform([prediction])[0]
                    # Create probability dict with original labels
                    prob_dict = {
                        str(label_encoder.inverse_transform([i])[0]): float(prob)
                        for i, prob in enumerate(probabilities)
                    }
                else:
                    predicted_label = prediction
                    prob_dict = {str(i): float(prob) for i, prob in enumerate(probabilities)}
                
                max_prob = max(probabilities)
                
                result = {
                    "predictions": {
                        "class": predicted_label,
                        "class_encoded": prediction,
                        "probabilities": prob_dict,
                        "confidence": float(max_prob)
                    },
                    "metadata": {
                        "model_type": "classification",
                        "features_used": list(X.columns)
                    }
                }
            else:
                pred_result = trained_model.predict(X)[0]
                prediction = int(pred_result)
                
                # Decode prediction if label encoder exists
                if label_encoder:
                    predicted_label = label_encoder.inverse_transform([prediction])[0]
                else:
                    predicted_label = prediction
                
                result = {
                    "predictions": {
                        "class": predicted_label,
                        "class_encoded": prediction
                    },
                    "metadata": {
                        "model_type": "classification",
                        "features_used": list(X.columns)
                    }
                }
            
            # Convert numpy types to native Python types
            return convert_numpy_types(result)
            
        except Exception as e:
            logger.error(f"Generic prediction failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Prediction failed: {str(e)}"
            )

