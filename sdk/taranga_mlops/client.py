"""Main client for Taranga MLOps SDK"""

import requests
from typing import Dict, Any, List, Optional
import pandas as pd
from .exceptions import TarangaError, AuthenticationError, APIError


class TarangaClient:
    """
    Main client for interacting with Taranga MLOps Platform
    
    Example:
        >>> client = TarangaClient(base_url="http://localhost:8000")
        >>> client.login(email="user@example.com", password="password")
        >>> project = client.create_project("My Project", system_id="...")
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        """
        Initialize Taranga client
        
        Args:
            base_url: Base URL of the Taranga API
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_version = "v1"
        self.api_key = api_key
        self.access_token = None
        self.session = requests.Session()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {"Content-Type": "application/json"}
        
        # Identify SDK requests
        headers["X-Request-Source"] = "sdk"
        headers["User-Agent"] = "Taranga-MLOps-SDK/1.0"
        
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif self.api_key:
            headers["X-API-Key"] = self.api_key
        
        return headers
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to API"""
        url = f"{self.base_url}/api/{self.api_version}{endpoint}"
        
        headers = self._get_headers()
        if files:
            # Remove Content-Type for multipart/form-data
            headers.pop("Content-Type", None)
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data if not files else None,
                files=files,
                data=data if files else None,
                params=params,
                headers=headers
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Authentication failed. Please login or check your API key.")
            
            if response.status_code >= 400:
                # Try to parse JSON error response
                error_msg = "Unknown error"
                try:
                    if response.text:
                        error_data = response.json()
                        error_msg = error_data.get("detail", error_data.get("message", str(error_data)))
                    else:
                        error_msg = f"HTTP {response.status_code} error"
                except (ValueError, TypeError):
                    # If response is not JSON, use the raw text or status code
                    if response.text:
                        error_msg = response.text[:500]  # Limit error message length
                    else:
                        error_msg = f"HTTP {response.status_code} error: {response.reason or 'Unknown error'}"
                
                raise APIError(
                    f"API request failed: {error_msg}",
                    status_code=response.status_code,
                    response=response
                )
            
            # Parse successful response
            try:
                return response.json() if response.text else {}
            except (ValueError, TypeError):
                # If response is not JSON, return the text
                return {"response": response.text} if response.text else {}
            
        except requests.RequestException as e:
            raise TarangaError(f"Request failed: {str(e)}")
    
    # Authentication Methods
    
    def signup(self, name: str, email: str, password: str) -> Dict[str, Any]:
        """
        Create a new user account
        
        Args:
            name: User's full name
            email: User's email
            password: User's password (min 8 characters)
            
        Returns:
            User information including ID and creation timestamp
        """
        return self._make_request(
            "POST",
            "/auth/signup",
            data={"name": name, "email": email, "password": password}
        )
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Login and get access token
        
        Args:
            email: User's email
            password: User's password
            
        Returns:
            User info with access_token and api_key
        """
        result = self._make_request(
            "POST",
            "/auth/login",
            data={"email": email, "password": password}
        )
        
        # Store tokens
        self.access_token = result.get("access_token")
        self.api_key = result.get("api_key")
        
        return result
    
    def refresh_api_key(self) -> str:
        """Refresh API key"""
        result = self._make_request("POST", "/auth/refresh-api-key")
        self.api_key = result.get("api_key")
        return self.api_key
    
    # System Methods
    
    def list_systems(self) -> List[Dict[str, Any]]:
        """Get list of available ML systems"""
        return self._make_request("GET", "/systems")
    
    def get_system(self, system_id: str) -> Dict[str, Any]:
        """Get details of a specific system"""
        return self._make_request("GET", f"/systems/{system_id}")
    
    def get_system_by_name(self, system_name: str) -> Optional[Dict[str, Any]]:
        """
        Get system by name
        
        Args:
            system_name: Name of the system (e.g., "Recommendation", "Churn Prediction")
            
        Returns:
            System information or None if not found
        """
        systems = self.list_systems()
        for system in systems:
            if system['name'].lower() == system_name.lower():
                return system
        return None
    
    # Project Methods
    
    def create_project(self, name: str, system: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new project
        
        Args:
            name: Project name
            system: Optional system name (e.g., "Recommendation", "Churn Prediction") or system_id.
                   If not provided, the system will be automatically determined by LLM during dataset upload.
            
        Returns:
            Project information including project_id
            
        Example:
            >>> # Let LLM determine the system based on your data and context
            >>> client.create_project("My Project")
            >>> # Or specify the system explicitly
            >>> client.create_project("Churn Model", "Churn Prediction")
        """
        # Prepare request data
        data = {"name": name}
        
        # Only process system if provided
        if system:
            # Check if system is an ID or name
            system_id = system
            
            # If it doesn't look like an ID (not a hex string), treat as name
            if not (len(system) == 24 and all(c in '0123456789abcdef' for c in system.lower())):
                # It's a name, look it up
                system_obj = self.get_system_by_name(system)
                if not system_obj:
                    raise ValueError(
                        f"System '{system}' not found. Available systems: "
                        f"{', '.join([s['name'] for s in self.list_systems()])}"
                    )
                system_id = system_obj['id']
            
            data["system_id"] = system_id
        
        return self._make_request(
            "POST",
            "/projects",
            data=data
        )
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """List all user's projects"""
        return self._make_request("GET", "/projects")
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project details"""
        return self._make_request("GET", f"/projects/{project_id}")
    
    def delete_project(self, project_id: str) -> Dict[str, Any]:
        """Delete a project"""
        return self._make_request("DELETE", f"/projects/{project_id}")
    
    # Dataset Methods
    
    def upload_data(
        self, 
        project_id: str, 
        data: Any,
        column_mapping: Optional[Dict[str, str]] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload dataset to a project with intelligent LLM analysis
        
        Args:
            project_id: Project ID
            data: Can be pandas DataFrame, dict, or file path (CSV/Excel)
            column_mapping: Optional manual mapping of columns to system schema
            context: Optional context for LLM to analyze (e.g., "I want a movie recommendation system")
            
        Returns:
            Dataset information including dataset_id, llm_analysis, and suggested mappings
        """
        # Handle pandas DataFrame
        if isinstance(data, pd.DataFrame):
            data_dict = data.to_dict(orient='list')
            payload = {"data": data_dict}
            if context:
                payload["context"] = context
            return self._make_request(
                "POST",
                f"/datasets/{project_id}/upload_sdk",
                data=payload
            )
        
        # Handle dict
        elif isinstance(data, dict):
            payload = {"data": data}
            if context:
                payload["context"] = context
            return self._make_request(
                "POST",
                f"/datasets/{project_id}/upload_sdk",
                data=payload
            )
        
        # Handle file path
        elif isinstance(data, str):
            with open(data, 'rb') as f:
                files = {'file': f}
                form_data = {'project_id': project_id}
                if column_mapping:
                    import json
                    form_data['column_mapping'] = json.dumps(column_mapping)
                if context:
                    form_data['context'] = context
                
                return self._make_request(
                    "POST",
                    "/datasets/upload",
                    data=form_data,
                    files=files
                )
        
        else:
            raise ValueError("Data must be pandas DataFrame, dict, or file path")
    
    def list_datasets(self, project_id: str) -> List[Dict[str, Any]]:
        """List all datasets for a project"""
        return self._make_request("GET", f"/datasets/project/{project_id}")
    
    def get_dataset_schema(self, project_id: str) -> Dict[str, Any]:
        """Get dataset schema requirements for a project"""
        return self._make_request("GET", f"/datasets/project/{project_id}/schema")
    
    # Training Methods
    
    def train(self, project_id: str) -> Dict[str, Any]:
        """
        Train a model for a project
        
        Args:
            project_id: Project ID
            
        Returns:
            Training results including model_id, version, and metrics
        """
        return self._make_request("POST", f"/projects/{project_id}/train")
    
    def retrain(self, project_id: str) -> Dict[str, Any]:
        """Retrain model with updated data"""
        return self._make_request("POST", f"/projects/{project_id}/retrain")
    
    def get_training_status(self, project_id: str) -> Dict[str, Any]:
        """Get current training status"""
        return self._make_request("GET", f"/projects/{project_id}/training/status")
    
    def get_models(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all model versions for a project"""
        result = self._make_request("GET", f"/projects/{project_id}/models/all")
        return result.get("models", [])
    
    def get_latest_model(self, project_id: str) -> Dict[str, Any]:
        """Get latest model for a project"""
        return self._make_request("GET", f"/projects/{project_id}/models")
    
    def compare_models(self, project_id: str, model_id_1: str, model_id_2: str) -> Dict[str, Any]:
        """
        Compare two models side by side
        
        Args:
            project_id: Project ID
            model_id_1: First model ID to compare
            model_id_2: Second model ID to compare
            
        Returns:
            Comprehensive comparison including metrics, features, confusion matrices, etc.
        """
        return self._make_request(
            "POST",
            f"/projects/{project_id}/registry/compare",
            data={
                "model_id_1": model_id_1,
                "model_id_2": model_id_2
            }
        )
    
    def get_model_details(self, project_id: str, model_id: str) -> Dict[str, Any]:
        """
        Get detailed statistics and visualizations for a specific model
        
        Args:
            project_id: Project ID
            model_id: Model ID
            
        Returns:
            Detailed model information including metrics and visualizations
        """
        return self._make_request("GET", f"/projects/{project_id}/models/{model_id}/details")
    
    # Prediction Methods
    
    def predict(
        self,
        project_id: str,
        user_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Make a single prediction
        
        Args:
            project_id: Project ID
            user_id: User ID (for recommendation systems)
            customer_id: Customer ID (for churn prediction)
            input_data: Input features (for other systems)
            top_k: Number of recommendations to return
            
        Returns:
            Predictions from the trained model
        """
        return self._make_request(
            "POST",
            "/predict",
            data={
                "project_id": project_id,
                "user_id": user_id,
                "customer_id": customer_id,
                "input_data": input_data,
                "top_k": top_k
            }
        )
    
    def predict_batch(
        self,
        project_id: str,
        users: Optional[List[str]] = None,
        customers: Optional[List[str]] = None,
        input_data: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Make batch predictions
        
        Args:
            project_id: Project ID
            users: List of user IDs (for recommendation)
            customers: List of customer IDs (for churn)
            input_data: List of input features
            top_k: Number of recommendations per user
            
        Returns:
            Batch predictions
        """
        return self._make_request(
            "POST",
            "/predict_batch",
            data={
                "project_id": project_id,
                "users": users,
                "customers": customers,
                "input_data": input_data,
                "top_k": top_k
            }
        )
    
    # Monitoring Methods
    
    def get_metrics(self, project_id: str) -> Dict[str, Any]:
        """
        Get model metrics history with visualizations
        
        Args:
            project_id: Project ID
            
        Returns:
            Metrics history for all model versions including comparison visualizations
        """
        return self._make_request("GET", f"/monitoring/metrics/{project_id}")
    
    def get_drift_status(self, project_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Get drift detection history with visualizations
        
        Args:
            project_id: Project ID
            days: Number of days to look back
            
        Returns:
            Drift history including timeline visualizations
        """
        return self._make_request(
            "GET",
            f"/monitoring/drift/history/{project_id}",
            params={"days": days}
        )
    
    def detect_drift(self, project_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect drift in new data"""
        return self._make_request(
            "POST",
            "/monitoring/drift/detect",
            data={"project_id": project_id, "data": data}
        )
    
    # ==================== Dashboard APIs ====================
    
    def get_dashboard_overview(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard overview with all key metrics
        
        Returns:
            Dict containing:
            - Project statistics
            - Model performance metrics
            - System usage breakdown
            - Recent activity
            - Health indicators
            - Top performing models
        """
        return self._make_request("GET", "/dashboard/overview")
    
    def get_projects_dashboard(self) -> Dict[str, Any]:
        """
        Get detailed project-level dashboard
        
        Returns:
            Dict with per-project metrics and details
        """
        return self._make_request("GET", "/dashboard/projects")
    
    def get_analytics_dashboard(self, days: int = 30) -> Dict[str, Any]:
        """
        Get time-series analytics and trends
        
        Args:
            days: Number of days to analyze (default: 30)
            
        Returns:
            Dict with trends for projects, models, predictions, and drift
        """
        return self._make_request("GET", "/dashboard/analytics", params={"days": days})
    
    def get_system_dashboard(self, system_id: str) -> Dict[str, Any]:
        """
        Get dashboard for a specific ML system
        
        Args:
            system_id: System ID
            
        Returns:
            Dict with system-specific metrics and usage
        """
        return self._make_request("GET", f"/dashboard/system/{system_id}")
    
    def get_dashboard(self, project_id: str) -> Dict[str, Any]:
        """Get monitoring dashboard data"""
        return self._make_request("GET", f"/monitoring/dashboard/{project_id}")
    
    def get_alerts(self, project_id: str) -> Dict[str, Any]:
        """Get active drift alerts"""
        return self._make_request("GET", f"/monitoring/alerts/{project_id}")
    
    # Convenience aliases for common methods
    
    def upload_dataset(self, project_id: str, data: Any, context: Optional[str] = None, 
                      column_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Alias for upload_data with LLM context support"""
        return self.upload_data(project_id, data, column_mapping, context)
    
    def train_model(self, project_id: str) -> Dict[str, Any]:
        """Alias for train"""
        return self.train(project_id)


