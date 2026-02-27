import os
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from fastapi import UploadFile, HTTPException
import aiofiles
from pathlib import Path
import uuid
from datetime import datetime
import logging

from app.models import Dataset, DataColumn, Project, System
from app.services.system_schemas import SystemSchemaResolver
from app.services.llm_service import LLMService
from app.core.config import settings

logger = logging.getLogger(__name__)

# Import Feature Store service for auto-generation
try:
    from app.services.feature_store_service import FeatureStoreService
    FEATURE_STORE_AVAILABLE = True
except ImportError:
    FEATURE_STORE_AVAILABLE = False
    logger.warning("Feature Store service not available")

# Storage directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class DatasetService:
    
    @staticmethod
    async def cleanup_old_files(max_age_hours: int = 24):
        """
        Clean up temporary dataset files older than max_age_hours.
        This is a safety mechanism to remove orphaned files.
        """
        try:
            now = datetime.now()
            deleted_count = 0
            
            for file_path in UPLOAD_DIR.glob("*.csv"):
                # Check file age
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                age_hours = (now - file_time).total_seconds() / 3600
                
                if age_hours > max_age_hours:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"Cleaned up old file: {file_path} (age: {age_hours:.1f} hours)")
                    except Exception as e:
                        logger.warning(f"Failed to delete old file {file_path}: {str(e)}")
            
            if deleted_count > 0:
                logger.info(f"Cleanup completed: {deleted_count} old files removed")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            return 0
    
    @staticmethod
    async def validate_dataset(
        df: pd.DataFrame, 
        system_name: str,
        column_mapping: Optional[Dict[str, str]] = None
    ) -> bool:
        """Validate dataset based on system requirements"""
        
        # Basic validations that apply to all datasets
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="Dataset cannot be empty"
            )
        
        if len(df.columns) == 0:
            raise HTTPException(
                status_code=400,
                detail="Dataset must have at least one column"
            )
        
        # System-specific validation
        schema = SystemSchemaResolver.get_schema(system_name)
        return schema.validate_dataset(df, column_mapping)
        
        return True
    
    @staticmethod
    def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Basic preprocessing of the dataframe"""
        # Handle missing values with generic strategies
        df = df.copy()
        
        # For each column, apply appropriate fill strategy based on data type
        for col in df.columns:
            if df[col].dtype == 'object':
                # For text/categorical columns, fill with 'missing' or mode
                mode_value = df[col].mode()
                fill_value = mode_value[0] if not mode_value.empty else 'missing'
                df[col] = df[col].fillna(fill_value)
            else:
                # For numeric columns, fill with median or 0
                median_value = df[col].median()
                fill_value = median_value if pd.notna(median_value) else 0
                df[col] = df[col].fillna(fill_value)
        
        return df
    
    @staticmethod
    async def save_uploaded_file(file: UploadFile, project_id: str) -> str:
        """
        DEPRECATED: For privacy, we no longer save raw data files.
        This method is kept for backward compatibility but returns empty path.
        Data is processed in-memory only.
        """
        logger.warning("save_uploaded_file called but file storage is disabled for privacy")
        return ""  # Return empty path - data not saved
    
    @staticmethod
    def read_file_to_dataframe(file_path: str) -> pd.DataFrame:
        """Read CSV or Excel file into pandas DataFrame"""
        file_extension = file_path.split('.')[-1].lower()
        
        try:
            if file_extension == 'csv':
                df = pd.read_csv(file_path)
            elif file_extension in ['xlsx', 'xls']:
                df = pd.read_excel(file_path)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format: {file_extension}"
                )
            
            return df
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Error reading file: {str(e)}"
            )
    
    @staticmethod
    def analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze dataframe to extract metadata"""
        return {
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': df.columns.tolist(),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'null_counts': df.isnull().sum().to_dict(),
            'unique_counts': df.nunique().to_dict()
        }
    
    @staticmethod
    async def create_data_columns(
        dataset_id: str, 
        project_id: str, 
        df: pd.DataFrame,
        system_name: str,
        column_mapping: Optional[Dict[str, str]] = None
    ) -> List[DataColumn]:
        """Create DataColumn documents for each column in the dataframe"""
        columns = []
        
        # Get system schema for better column type inference
        try:
            schema = SystemSchemaResolver.get_schema(system_name)
        except:
            schema = None
        
        for col_name in df.columns:
            # Get sample values (first 5 non-null values)
            sample_values = df[col_name].dropna().head(5).astype(str).tolist()
            
            # Determine mapped type
            if column_mapping and col_name in column_mapping:
                mapped_type = column_mapping[col_name]
            else:
                # Infer mapped type based on system-specific patterns
                mapped_type = DatasetService._infer_column_type(col_name.lower(), system_name)
            
            # Determine if column is required based on system schema
            is_required = False
            if schema:
                is_required = mapped_type in schema.required_columns
            
            data_column = DataColumn(
                dataset_id=dataset_id,
                project_id=project_id,
                column_name=col_name,
                original_type=str(df[col_name].dtype),
                mapped_type=mapped_type,
                is_required=is_required,
                sample_values=sample_values,
                null_count=int(df[col_name].isnull().sum()),
                unique_count=int(df[col_name].nunique())
            )
            
            await data_column.insert()
            columns.append(data_column)
        
        return columns
    
    @staticmethod
    def _infer_column_type(column_name: str, system_name: str) -> str:
        """Infer column type based on system-specific patterns"""
        try:
            schema = SystemSchemaResolver.get_schema(system_name)
            mappings = schema.infer_column_types([column_name])
            return mappings.get(column_name, 'feature')
        except:
            # Fallback to generic patterns if system not found
            patterns = {
                'user_id': ['user_id', 'userid', 'user', 'customer_id', 'customerid'],
                'item_id': ['item_id', 'itemid', 'item', 'product_id', 'productid'],
                'interaction': ['interaction', 'rating', 'score', 'feedback'],
                'timestamp': ['timestamp', 'time', 'date', 'created_at'],
                'label': ['label', 'target', 'class', 'category', 'churn']
            }
            
            col_lower = column_name.lower()
            for type_name, pattern_list in patterns.items():
                if any(pattern in col_lower for pattern in pattern_list):
                    return type_name
            
            return 'feature'
    
    @staticmethod
    async def process_web_upload(
        file: UploadFile, 
        project_id: str, 
        user_id: str,
        column_mapping: Optional[Dict[str, str]] = None,
        user_context: Optional[str] = None
    ) -> Tuple[Dataset, List[DataColumn]]:
        """Process file uploaded from web form with intelligent LLM analysis"""
        
        # Verify project exists and belongs to user
        project = await Project.get(project_id)
        if not project or project.user_id != user_id:
            raise HTTPException(
                status_code=404,
                detail="Project not found or access denied"
            )
        
        # Get system information (may be None if not set yet - will be determined by LLM)
        system = None
        if project.system_id:
            system = await System.get(project.system_id)
            if not system:
                raise HTTPException(
                    status_code=400,
                    detail="Project system not found"
                )
        
        try:
            # Read file directly from upload (no saving for privacy)
            contents = await file.read()
            
            # Determine file type and read into dataframe
            if file.filename.endswith('.csv'):
                import io
                df = pd.read_csv(io.BytesIO(contents))
            elif file.filename.endswith(('.xlsx', '.xls')):
                import io
                df = pd.read_excel(io.BytesIO(contents))
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Only CSV and Excel files are supported"
                )
            
            logger.info(f"File read successfully: {df.shape}")
            
            # === NEW: LLM-based intelligent analysis ===
            llm_analysis = None
            suggested_system_type = None
            llm_column_mappings = {}
            
            if user_context:
                try:
                    # Extract sample data for LLM
                    sample_data = {col: df[col].head(3).tolist() for col in df.columns}
                    
                    # Call LLM for analysis
                    llm_analysis = await LLMService.analyze_dataset_for_ml_system(
                        columns=df.columns.tolist(),
                        context=user_context,
                        sample_data=sample_data
                    )
                    
                    suggested_system_type = llm_analysis.get("system_type")
                    llm_column_mappings = llm_analysis.get("column_mappings", {})
                    
                    # Filter out None values from column mappings
                    llm_column_mappings = {k: v for k, v in llm_column_mappings.items() if v is not None}
                    
                    logger.info(f"LLM Analysis: {suggested_system_type} with confidence {llm_analysis.get('confidence')}")
                    
                    # Update project system_id if not set and LLM suggested a system
                    if not project.system_id and suggested_system_type:
                        # Map LLM system type to database system name
                        system_type_mapping = {
                            'collaborative_filtering': 'Collaborative Filtering',
                            'content_based_filtering': 'Content-Based Filtering',
                            'popularity_based': 'Popularity-Based',
                            'hybrid_recommendation': 'Hybrid Recommendation',
                            'customer_churn': 'Customer Churn',
                            'subscription_churn': 'Subscription Churn',
                            'product_churn': 'Product Churn',
                            'revenue_churn': 'Revenue Churn',
                            'early_churn_detection': 'Early Churn Detection',
                            'late_churn_analysis': 'Late Churn Analysis',
                            'fraud_detection': 'Fraud Detection',
                            'sentiment_analysis': 'Sentiment Analysis',
                            'demand_forecasting': 'Demand Forecasting',
                            'price_optimization': 'Price Optimization'
                        }
                        
                        db_system_name = system_type_mapping.get(suggested_system_type.lower())
                        
                        if db_system_name:
                            # Find the system by mapped name
                            all_systems = await System.find_all().to_list()
                            matching_system = None
                            for sys in all_systems:
                                if sys.name == db_system_name:
                                    matching_system = sys
                                    break
                            
                            if matching_system:
                                project.system_id = str(matching_system.id)
                                await project.save()
                                system = matching_system
                                logger.info(f"Updated project system_id to {system.name} based on LLM analysis")
                            else:
                                logger.warning(f"Database system '{db_system_name}' not found")
                        else:
                            logger.warning(f"LLM suggested system '{suggested_system_type}' has no mapping to database system")
                    
                    # Use LLM mappings if no manual mapping provided
                    if not column_mapping and llm_column_mappings:
                        column_mapping = llm_column_mappings
                        logger.info(f"Using LLM column mappings: {column_mapping}")
                        
                except Exception as e:
                    logger.error(f"LLM analysis failed: {str(e)}")
                    # Continue without LLM analysis
            
            # System-aware validation - skip if system not set yet or if using LLM mappings
            if column_mapping:
                logger.info("Skipping strict validation - using LLM-provided column mappings")
            elif system:
                await DatasetService.validate_dataset(df, system.name, column_mapping)
            else:
                logger.info("Skipping validation - system not set yet (will be determined by LLM)")
            
            # Preprocess data
            df_processed = DatasetService.preprocess_dataframe(df)
            
            # PRIVACY: Save temporarily for training, will be deleted after
            filename = f"{project_id}_{uuid.uuid4()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_web.csv"
            processed_file_path = UPLOAD_DIR / filename
            df_processed.to_csv(processed_file_path, index=False)
            logger.info(f"Temporary file created (will be deleted after training): {processed_file_path}")
            
            # Analyze dataframe
            metadata = DatasetService.analyze_dataframe(df_processed)
            
            # Create dataset document with LLM analysis
            dataset = Dataset(
                project_id=project_id,
                name=file.filename,
                storage_path=str(processed_file_path),
                file_size=os.path.getsize(processed_file_path),
                file_type=file.filename.split('.')[-1].lower(),
                row_count=metadata['row_count'],
                column_count=metadata['column_count'],
                metadata=metadata,
                status="processed",  # Will change to "processed_and_deleted" after training
                user_context=user_context,
                llm_analysis=llm_analysis,
                suggested_system_type=suggested_system_type,
                column_mappings=llm_column_mappings
            )
            
            await dataset.insert()
            
            # Create data columns with system awareness
            system_name = system.name if system else (suggested_system_type or "generic")
            columns = await DatasetService.create_data_columns(
                str(dataset.id), project_id, df_processed, system_name, column_mapping
            )
            
            return dataset, columns
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Web upload processing failed: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process uploaded file: {str(e)}"
            )
    
    @staticmethod
    async def process_sdk_upload(
        data: Dict[str, Any], 
        project_id: str, 
        user_id: str,
        user_context: Optional[str] = None
    ) -> Tuple[Dataset, List[DataColumn]]:
        """Process data uploaded from SDK (JSON/DataFrame) with intelligent LLM analysis"""
        
        # Verify project exists and belongs to user
        project = await Project.get(project_id)
        if not project or project.user_id != user_id:
            raise HTTPException(
                status_code=404,
                detail="Project not found or access denied"
            )
        
        # Get system information (may be None if not set yet - will be determined by LLM)
        system = None
        if project.system_id:
            system = await System.get(project.system_id)
            if not system:
                raise HTTPException(
                    status_code=400,
                    detail="Project system not found"
                )
        
        try:
            logger.info(f"Processing SDK upload for project {project_id}")
            
            # Convert JSON to DataFrame
            df = pd.DataFrame(data)
            logger.info(f"DataFrame created with shape: {df.shape}")
            logger.info(f"DataFrame columns: {list(df.columns)}")
            
            # === NEW: LLM-based intelligent analysis ===
            llm_analysis = None
            suggested_system_type = None
            llm_column_mappings = {}
            column_mapping = None
            
            if user_context:
                try:
                    # Extract sample data for LLM
                    sample_data = {col: df[col].head(3).tolist() for col in df.columns}
                    
                    # Call LLM for analysis
                    llm_analysis = await LLMService.analyze_dataset_for_ml_system(
                        columns=df.columns.tolist(),
                        context=user_context,
                        sample_data=sample_data
                    )
                    
                    suggested_system_type = llm_analysis.get("system_type")
                    llm_column_mappings = llm_analysis.get("column_mappings", {})
                    
                    # Filter out None values from column mappings
                    llm_column_mappings = {k: v for k, v in llm_column_mappings.items() if v is not None}
                    
                    logger.info(f"LLM Analysis: {suggested_system_type} with confidence {llm_analysis.get('confidence')}")
                    
                    # Update project system_id if not set and LLM suggested a system
                    if not project.system_id and suggested_system_type:
                        # Map LLM system type to database system name
                        system_type_mapping = {
                            'collaborative_filtering': 'Collaborative Filtering',
                            'content_based_filtering': 'Content-Based Filtering',
                            'popularity_based': 'Popularity-Based',
                            'hybrid_recommendation': 'Hybrid Recommendation',
                            'customer_churn': 'Customer Churn',
                            'subscription_churn': 'Subscription Churn',
                            'product_churn': 'Product Churn',
                            'revenue_churn': 'Revenue Churn',
                            'early_churn_detection': 'Early Churn Detection',
                            'late_churn_analysis': 'Late Churn Analysis',
                            'fraud_detection': 'Fraud Detection',
                            'sentiment_analysis': 'Sentiment Analysis',
                            'demand_forecasting': 'Demand Forecasting',
                            'price_optimization': 'Price Optimization'
                        }
                        
                        db_system_name = system_type_mapping.get(suggested_system_type.lower())
                        
                        if db_system_name:
                            # Find the system by mapped name
                            all_systems = await System.find_all().to_list()
                            matching_system = None
                            for sys in all_systems:
                                if sys.name == db_system_name:
                                    matching_system = sys
                                    break
                            
                            if matching_system:
                                project.system_id = str(matching_system.id)
                                await project.save()
                                system = matching_system
                                logger.info(f"Updated project system_id to {system.name} based on LLM analysis")
                            else:
                                logger.warning(f"Database system '{db_system_name}' not found")
                        else:
                            logger.warning(f"LLM suggested system '{suggested_system_type}' has no mapping to database system")
                    
                    # Use LLM mappings
                    if llm_column_mappings:
                        column_mapping = llm_column_mappings
                        logger.info(f"Using LLM column mappings: {column_mapping}")
                        
                except Exception as e:
                    logger.error(f"LLM analysis failed: {str(e)}")
                    # Continue without LLM analysis
            
            # System-aware validation - skip if LLM provided mappings or system not set yet
            if column_mapping:
                logger.info(f"Skipping strict validation - using LLM-provided column mappings: {column_mapping}")
            elif system:
                logger.info(f"Validating dataset for system: {system.name}")
                # Try to use LLM mappings if available, even if column_mapping is None
                validation_mapping = column_mapping if column_mapping else (llm_column_mappings if llm_column_mappings else None)
                await DatasetService.validate_dataset(df, system.name, validation_mapping)
                logger.info("Dataset validation completed successfully")
            else:
                logger.info("Skipping validation - system not set yet (will be determined by LLM)")
            
            # Preprocess data
            df_processed = DatasetService.preprocess_dataframe(df)
            logger.info("Data preprocessing completed")
            
            # PRIVACY: Save temporarily for training, will be deleted after
            filename = f"{project_id}_{uuid.uuid4()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_sdk.csv"
            file_path = UPLOAD_DIR / filename
            df_processed.to_csv(file_path, index=False)
            logger.info(f"Temporary file created (will be deleted after training): {file_path}")
            
            # Analyze dataframe
            metadata = DatasetService.analyze_dataframe(df_processed)
            
            # Create dataset document with LLM analysis (storage_path will be cleared after training)
            dataset = Dataset(
                project_id=project_id,
                name=f"SDK_Upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                storage_path=str(file_path),
                file_size=os.path.getsize(file_path),
                file_type="csv",
                row_count=metadata['row_count'],
                column_count=metadata['column_count'],
                metadata=metadata,
                status="processed",  # Will change to "processed_and_deleted" after training
                user_context=user_context,
                llm_analysis=llm_analysis,
                suggested_system_type=suggested_system_type,
                column_mappings=llm_column_mappings
            )
            
            await dataset.insert()
            
            # Create data columns with system awareness
            system_name = system.name if system else (suggested_system_type or "generic")
            columns = await DatasetService.create_data_columns(
                str(dataset.id), project_id, df_processed, system_name, column_mapping
            )
            
            # Auto-generate features from dataset columns
            if FEATURE_STORE_AVAILABLE:
                try:
                    feature_store = FeatureStoreService()
                    generated_features = await feature_store.auto_generate_features(
                        project_id=project_id,
                        dataset_id=str(dataset.id),
                        user_id=user_id
                    )
                    logger.info(f"Auto-generated {len(generated_features)} features for dataset {dataset.id}")
                except Exception as e:
                    logger.warning(f"Feature auto-generation failed: {str(e)}")
            
            return dataset, columns
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"SDK upload processing failed: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {repr(e)}")
            # Re-raise with more specific error message
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process SDK data: {str(e)}"
            )
    
    @staticmethod
    async def get_project_datasets(project_id: str, user_id: str) -> List[Dataset]:
        """Get all datasets for a project"""
        
        # Strip whitespace from project_id to handle any newlines or spaces
        project_id = project_id.strip()
        
        # Verify project exists and belongs to user
        project = await Project.get(project_id)
        if not project or project.user_id != user_id:
            raise HTTPException(
                status_code=404,
                detail="Project not found or access denied"
            )
        
        datasets = await Dataset.find(Dataset.project_id == project_id).to_list()
        return datasets
    
    @staticmethod
    async def get_dataset_columns(dataset_id: str, user_id: str) -> List[DataColumn]:
        """Get all columns for a dataset"""
        
        # Verify dataset exists and user has access
        dataset = await Dataset.get(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        project = await Project.get(dataset.project_id)
        if not project or project.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )
        
        columns = await DataColumn.find(DataColumn.dataset_id == dataset_id).to_list()
        return columns
    
    @staticmethod
    async def delete_dataset(dataset_id: str, user_id: str) -> bool:
        """Delete a dataset and its associated files"""
        
        # Verify dataset exists and user has access
        dataset = await Dataset.get(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        project = await Project.get(dataset.project_id)
        if not project or project.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )
        
        try:
            # Delete associated data columns
            columns = await DataColumn.find(DataColumn.dataset_id == dataset_id).to_list()
            for column in columns:
                await column.delete()
            
            # Delete file if it exists
            if dataset.storage_path and os.path.exists(dataset.storage_path):
                os.remove(dataset.storage_path)
            
            # Delete dataset document
            await dataset.delete()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete dataset {dataset_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete dataset: {str(e)}"
            )