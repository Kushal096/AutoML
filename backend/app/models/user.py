from datetime import datetime
from typing import Optional, List, Dict, Any
from beanie import Document, Indexed
from pydantic import BaseModel, Field, EmailStr
from pymongo import IndexModel
import uuid


class User(Document):
    name: str
    email: Indexed(EmailStr, unique=True)
    password_hash: str
    api_key: Indexed(str, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    class Settings:
        name = "users"
        indexes = [
            IndexModel("email", unique=True),
            IndexModel("api_key", unique=True)
        ]


class System(Document):
    name: str
    description: Optional[str] = None
    default_pipeline: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "systems"


class Project(Document):
    user_id: str  # Reference to User._id
    name: str
    system_id: Optional[str] = None  # Reference to System._id - will be set by LLM during upload
    status: str = "created"  # created, training, trained
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "projects"


class Dataset(Document):
    project_id: str  # Reference to Project._id
    name: Optional[str] = None
    storage_path: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None  # csv, excel
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "uploaded"  # uploaded, processing, processed, failed
    
    # LLM-based intelligent analysis
    user_context: Optional[str] = None  # User's description of what they want to do
    llm_analysis: Optional[Dict[str, Any]] = None  # LLM's analysis result
    suggested_system_type: Optional[str] = None  # LLM's suggested system type
    column_mappings: Optional[Dict[str, str]] = None  # LLM's suggested column mappings

    class Settings:
        name = "datasets"


class DataColumn(Document):
    dataset_id: str  # Reference to Dataset._id
    project_id: str  # Reference to Project._id
    column_name: str
    original_type: str  # Original pandas dtype
    mapped_type: str  # user_id, item_id, interaction, feature, etc.
    is_required: bool = False
    sample_values: Optional[List[str]] = None
    null_count: Optional[int] = None
    unique_count: Optional[int] = None

    class Settings:
        name = "data_columns"


class Model(Document):
    project_id: str  # Reference to Project._id
    version: int
    storage_path: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "models"
    
    model_config = {"protected_namespaces": ()}


class DriftMetric(Document):
    project_id: str  # Reference to Project._id
    model_id: str  # Reference to Model._id
    feature_name: str
    drift_score: float
    detected_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "drift_metrics"
    
    model_config = {"protected_namespaces": ()}


class DriftBaseline(Document):
    """
    Stores baseline statistics for drift detection
    This allows drift detection even after training dataset files are deleted
    """
    project_id: str  # Reference to Project._id
    model_id: str  # Reference to Model._id
    model_version: int
    
    # Baseline statistics for each numerical feature
    # Format: {feature_name: {"histogram": [...], "min": float, "max": float, "mean": float, "std": float}}
    feature_statistics: Dict[str, Any] = {}
    
    # Column names that were used for training
    feature_columns: List[str] = []
    
    # Total number of samples in baseline
    baseline_sample_count: int = 0
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "drift_baselines"
        indexes = [
            IndexModel([("project_id", 1), ("model_id", 1)]),
            IndexModel([("model_id", 1)])
        ]
    
    model_config = {"protected_namespaces": ()}


# ============================================================================
# FEATURE STORE - Critical component for ML pipeline
# ============================================================================

class FeatureDefinition(Document):
    """
    Defines a feature transformation/computation logic
    This is the 'recipe' for creating features
    """
    name: str  # Feature name (e.g., "user_avg_purchase_amount")
    description: Optional[str] = None
    feature_type: str  # "numerical", "categorical", "embedding", "derived"
    data_type: str  # "float", "int", "string", "array"
    transformation_logic: Optional[Dict[str, Any]] = None  # JSON describing transformation
    source_columns: List[str] = []  # Source columns from raw data
    project_id: Optional[str] = None  # If project-specific, else shared
    version: int = 1
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str  # User ID
    
    class Settings:
        name = "feature_definitions"


class FeatureSet(Document):
    """
    A collection of features used together (e.g., for a specific model)
    """
    name: str
    description: Optional[str] = None
    project_id: str
    feature_names: List[str]  # List of feature names
    version: int = 1
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "feature_sets"


class FeatureValue(Document):
    """
    Stores computed feature values (materialized features)
    This enables fast serving without recomputation
    """
    feature_name: str
    entity_id: str  # user_id, customer_id, item_id, etc.
    entity_type: str  # "user", "customer", "item", etc.
    value: Any  # The actual feature value
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    feature_set_id: Optional[str] = None
    project_id: str
    
    class Settings:
        name = "feature_values"
        indexes = [
            IndexModel([("feature_name", 1), ("entity_id", 1)]),
            IndexModel([("project_id", 1), ("computed_at", -1)])
        ]


class ModelRegistryMetadata(Document):
    """
    Enhanced model registry with comprehensive metadata
    Extends the basic Model document with lineage and governance
    """
    model_id: str  # Reference to Model._id
    project_id: str
    
    # Training metadata
    training_dataset_ids: List[str] = []  # Which datasets were used
    feature_set_id: Optional[str] = None  # Which feature set was used
    training_duration_seconds: Optional[float] = None
    training_parameters: Optional[Dict[str, Any]] = None
    
    # Model lineage
    parent_model_id: Optional[str] = None  # If retrained from another model
    experiment_id: Optional[str] = None
    
    # Governance
    approval_status: str = "pending"  # "pending", "approved", "rejected", "production"
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    deployment_stage: str = "development"  # "development", "staging", "production"
    
    # Performance tracking
    production_metrics: Optional[Dict[str, Any]] = None  # Metrics in production
    last_prediction_at: Optional[datetime] = None
    total_predictions: int = 0
    usage_stats: Optional[Dict[str, Any]] = None  # SDK vs web usage, timeline, etc.
    
    # Tags and metadata
    tags: List[str] = []
    custom_metadata: Optional[Dict[str, Any]] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "model_registry_metadata"
    
    model_config = {"protected_namespaces": ()}


class TrainingLogs(Document):
    project_id: str  # Reference to Project._id
    model_id: Optional[str] = None  # Reference to Model._id (optional during training start)
    status: str  # "started", "training", "completed", "failed"
    logs: str  # Training logs as text
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "training_logs"
    
    model_config = {"protected_namespaces": ()}


# Pydantic schemas for request/response
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72, description="Password must be between 8-72 characters")


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=72)


class SignupResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    created_at: datetime
    is_active: bool
    message: str = "Account created successfully"


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    api_key: str
    access_token: str
    token_type: str = "bearer"
    created_at: datetime
    is_active: bool


class SystemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    default_pipeline: Optional[Dict[str, Any]] = None


class SystemResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    default_pipeline: Optional[Dict[str, Any]]
    created_at: datetime


class ProjectCreate(BaseModel):
    name: str
    system_id: Optional[str] = None  # Optional - will be set by LLM during dataset upload


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    name: str
    system_id: Optional[str] = None  # Optional - will be set by LLM during dataset upload
    status: str
    created_at: datetime
    updated_at: datetime


class ApiKeyResponse(BaseModel):
    api_key: str
    message: str


class TrainModelResponse(BaseModel):
    message: str
    model_id: str
    version: int
    metrics: Dict[str, Any]
    training_logs: str


class ModelResponse(BaseModel):
    id: str
    project_id: str
    version: int
    storage_path: Optional[str]
    metrics: Optional[Dict[str, Any]]
    created_at: datetime


class ModelListResponse(BaseModel):
    models: List[ModelResponse]
    latest_version: int
    total_models: int
# Dataset schemas
class DatasetResponse(BaseModel):
    id: str
    project_id: str
    name: Optional[str]
    storage_path: Optional[str]
    file_size: Optional[int]
    file_type: Optional[str]
    row_count: Optional[int]
    column_count: Optional[int]
    metadata: Optional[Dict[str, Any]]
    uploaded_at: datetime
    status: str
    user_context: Optional[str] = None
    llm_analysis: Optional[Dict[str, Any]] = None
    suggested_system_type: Optional[str] = None
    column_mappings: Optional[Dict[str, str]] = None


class DataColumnResponse(BaseModel):
    id: str
    dataset_id: str
    project_id: str
    column_name: str
    original_type: str
    mapped_type: str
    is_required: bool
    sample_values: Optional[List[str]]
    null_count: Optional[int]
    unique_count: Optional[int]


class DatasetUploadResponse(BaseModel):
    dataset_id: str
    message: str
    columns: List[DataColumnResponse]
    llm_analysis: Optional[Dict[str, Any]] = None  # LLM's intelligent analysis
    suggested_system_type: Optional[str] = None  # Recommended system type
    column_mappings: Optional[Dict[str, str]] = None  # Recommended column mappings
    # Dataset statistics
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    dataset_name: Optional[str] = None
    # Drift detection results (if model exists and drift was checked)
    drift_detection: Optional[Dict[str, Any]] = None


class ColumnMappingRequest(BaseModel):
    column_mappings: Dict[str, str]  # column_name -> mapped_type


# Prediction schemas
class PredictionRequest(BaseModel):
    project_id: str
    user_id: Optional[str] = None  # For recommendation systems
    customer_id: Optional[str] = None  # For churn prediction
    input_data: Optional[Dict[str, Any]] = None  # For other systems
    top_k: Optional[int] = 10  # Number of recommendations to return


class BatchPredictionRequest(BaseModel):
    project_id: str
    users: Optional[List[str]] = None  # For recommendation systems
    customers: Optional[List[str]] = None  # For churn prediction
    input_data: Optional[List[Dict[str, Any]]] = None  # For other systems
    top_k: Optional[int] = 10


class PredictionResponse(BaseModel):
    project_id: str
    model_version: int
    predictions: Any  # Can be list of items, probability, etc.
    metadata: Optional[Dict[str, Any]] = None
    
    model_config = {"protected_namespaces": ()}


class BatchPredictionResponse(BaseModel):
    project_id: str
    model_version: int
    predictions: List[Dict[str, Any]]  # List of {id: predictions}
    metadata: Optional[Dict[str, Any]] = None
    
    model_config = {"protected_namespaces": ()}


def generate_api_key() -> str:
    """Generate a unique API key"""
    return f"tk-{uuid.uuid4().hex[:32]}"