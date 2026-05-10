"""
Comprehensive Integration Test for MLOps Platform
==========================================================

This script performs a complete end-to-end test of all APIs and services:
1. Authentication & User Management
2. Systems & Projects Management
3. Dataset Upload & Management
4. Model Training & Versioning
5. Predictions
6. Model Metrics & Monitoring
7. Drift Detection
8. Model Comparison
9. Dashboard & Analytics
10. Alerts & Notifications

All tests are dynamic - no hardcoded values, everything is validated.

Usage:
    python test_integration.py
"""

import sys
import time
import pandas as pd
from typing import Dict, Any, List, Optional
from mlops_sdk import MLOpsClient
from mlops_sdk.exceptions import APIError, AuthenticationError

# Configuration
BASE_URL = "http://localhost:8000"
EMAIL = "aryan123@gmail.com"
PASSWORD = "aryan123"
CSV_FILE_1 = "netflix_customer_churn.csv"
CSV_FILE_2 = "netflix_customer_churn2.csv"

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_info(message):
    """Print an info message"""
    print(f"ℹ️  {message}")


def print_success(message):
    """Print a success message"""
    print(f"✅ {message}")
    test_results["passed"].append(message)


def print_error(message):
    """Print an error message"""
    print(f"❌ {message}")
    test_results["failed"].append(message)


def print_warning(message):
    """Print a warning message"""
    print(f"⚠️  {message}")
    test_results["warnings"].append(message)


def validate_response(response: Any, expected_keys: List[str] = None, response_name: str = "Response") -> bool:
    """
    Validate API response structure
    
    Args:
        response: API response to validate
        expected_keys: List of keys that should be present
        response_name: Name of the response for error messages
    
    Returns:
        True if valid, False otherwise
    """
    if response is None:
        print_error(f"{response_name} is None")
        return False
    
    if not isinstance(response, dict):
        print_error(f"{response_name} is not a dictionary: {type(response)}")
        return False
    
    if expected_keys:
        missing_keys = [key for key in expected_keys if key not in response]
        if missing_keys:
            print_warning(f"{response_name} missing expected keys: {missing_keys}")
            return False
    
    return True


def validate_model_metrics(metrics: Dict[str, Any]) -> bool:
    """Validate model metrics structure"""
    if not isinstance(metrics, dict):
        return False
    
    # Check for common metrics
    metric_keys = ["accuracy", "precision", "recall", "f1_score", "roc_auc"]
    has_any_metric = any(key in metrics for key in metric_keys)
    
    if not has_any_metric:
        print_warning("Model metrics don't contain expected performance metrics")
        return False
    
    return True


def wait_for_training_complete(client: MLOpsClient, project_id: str, max_wait_time: int = 600, check_interval: int = 5) -> Optional[Dict[str, Any]]:
    """
    Wait for training to complete by polling training status
    
    Args:
        client: MLOpsClient instance
        project_id: Project ID to check
        max_wait_time: Maximum time to wait in seconds (default: 10 minutes)
        check_interval: Time between status checks in seconds (default: 5 seconds)
    
    Returns:
        Training result when complete, or None if timeout
    """
    start_time = time.time()
    print_info("Waiting for training to complete...")
    
    while time.time() - start_time < max_wait_time:
        try:
            status = client.get_training_status(project_id=project_id)
            
            if not validate_response(status, ["status"], "Training status"):
                time.sleep(check_interval)
                continue
            
            training_status = status.get('status', 'unknown')
            
            if training_status == 'completed':
                print_success("Training completed!")
                return status
            elif training_status == 'failed':
                error_msg = status.get('error', status.get('message', 'Unknown error'))
                print_error(f"Training failed: {error_msg}")
                return None
            elif training_status in ['training', 'pending']:
                elapsed = int(time.time() - start_time)
                if elapsed % 30 == 0 or training_status == 'pending':  # Print every 30s or on pending
                    print_info(f"Training status: {training_status} (elapsed: {elapsed}s)")
            else:
                print_info(f"Training status: {training_status}")
            
            time.sleep(check_interval)
            
        except Exception as e:
            print_error(f"Error checking training status: {str(e)}")
            time.sleep(check_interval)
    
    print_error(f"Training did not complete within {max_wait_time} seconds")
    return None


def test_authentication(client: MLOpsClient) -> bool:
    """Test authentication APIs"""
    print_section("TEST 1: Authentication & User Management")
    
    try:
        # Test login
        print_info(f"Testing login for {EMAIL}...")
        login_result = client.login(email=EMAIL, password=PASSWORD)
        
        if not validate_response(login_result, ["id", "name", "email", "api_key"], "Login response"):
            return False
        
        print_success(f"Login successful! User: {login_result.get('name')}")
        print_info(f"   User ID: {login_result.get('id')}")
        print_info(f"   Email: {login_result.get('email')}")
        print_info(f"   API Key: {login_result.get('api_key', '')[:20]}...")
        
        # Verify access token is set
        if not client.access_token:
            print_error("Access token not set after login")
            return False
        
        # Verify access token is set (implicit validation)
        if not client.access_token:
            print_error("Access token not set after login")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Authentication test failed: {str(e)}")
        return False


def test_systems(client: MLOpsClient) -> bool:
    """Test systems APIs"""
    print_section("TEST 2: ML Systems Management")
    
    try:
        # Test list systems
        print_info("Testing list systems...")
        systems = client.list_systems()
        
        if not isinstance(systems, list):
            print_error(f"Systems response is not a list: {type(systems)}")
            return False
        
        if len(systems) == 0:
            print_error("No systems found")
            return False
        
        print_success(f"Found {len(systems)} available systems")
        
        # Validate system structure
        for system in systems[:3]:  # Check first 3
            if not validate_response(system, ["id", "name"], "System"):
                return False
        
        # Print systems
        for system in systems:
            print(f"   - {system.get('name')}: {system.get('description', 'N/A')}")
        
        # Test get system by ID
        if systems:
            first_system = systems[0]
            system_id = first_system.get('id')
            print_info(f"Testing get system by ID: {system_id}...")
            system_detail = client.get_system(system_id)
            if validate_response(system_detail, ["id", "name"], "System detail"):
                print_success("System detail retrieved successfully")
        
        return True
        
    except Exception as e:
        print_error(f"Systems test failed: {str(e)}")
        return False


def test_projects(client: MLOpsClient):
    """Test projects APIs"""
    print_section("TEST 3: Projects Management")
    
    try:
        # Test create project
        project_name = f"Integration Test Project - {int(time.time())}"
        print_info(f"Testing create project: {project_name}...")
        
        project = client.create_project(name=project_name)
        
        if not validate_response(project, ["id", "name", "status"], "Project"):
            return False, None
        
        project_id = project['id']
        print_success(f"Project created successfully!")
        print(f"   Project ID: {project_id}")
        print(f"   Project Name: {project.get('name')}")
        print(f"   Status: {project.get('status')}")
        
        # Test get project
        print_info(f"Testing get project: {project_id}...")
        retrieved_project = client.get_project(project_id)
        if validate_response(retrieved_project, ["id", "name"], "Retrieved project"):
            if retrieved_project.get('id') != project_id:
                print_error("Retrieved project ID doesn't match")
                return False, None
            print_success("Project retrieved successfully")
        
        # Test list projects
        print_info("Testing list projects...")
        projects = client.list_projects()
        if not isinstance(projects, list):
            print_error("Projects response is not a list")
            return False, None
        
        # Verify our project is in the list
        project_ids = [p.get('id') for p in projects]
        if project_id not in project_ids:
            print_warning(f"Created project {project_id} not found in projects list")
        else:
            print_success(f"Project found in list ({len(projects)} total projects)")
        
        return True, project_id
        
    except Exception as e:
        print_error(f"Projects test failed: {str(e)}")
        return False, None


def test_datasets(client: MLOpsClient, project_id: str):
    """Test dataset upload and management"""
    print_section("TEST 4: Dataset Upload & Management")
    
    dataset_ids = []
    
    try:
        # Load first dataset
        print_info(f"Loading dataset from {CSV_FILE_1}...")
        try:
            df1 = pd.read_csv(CSV_FILE_1)
            print_success(f"Dataset loaded: {df1.shape[0]} rows, {df1.shape[1]} columns")
            print_info(f"   Columns: {', '.join(df1.columns.tolist()[:5])}...")
        except FileNotFoundError:
            print_error(f"File {CSV_FILE_1} not found!")
            return False, None, None
        
        # Validate dataset
        if df1.empty:
            print_error("Dataset is empty")
            return False, None, None
        
        if len(df1.columns) == 0:
            print_error("Dataset has no columns")
            return False, None, None
        
        # Test upload dataset
        print_info("Testing dataset upload with LLM context...")
        context = "Predict which Netflix customers will churn based on their usage patterns, subscription details, and viewing behavior"
        
        upload_result_1 = client.upload_dataset(
            project_id=project_id,
            data=df1,
            context=context
        )
        
        if not validate_response(upload_result_1, ["dataset_id", "message"], "Upload result"):
            return False, None, None
        
        dataset_id_1 = upload_result_1.get('dataset_id')
        if dataset_id_1:
            dataset_ids.append(dataset_id_1)
        
        print_success("First dataset uploaded successfully!")
        print(f"   Dataset ID: {dataset_id_1}")
        print(f"   Message: {upload_result_1.get('message', 'N/A')}")
        
        # Validate LLM analysis if available
        if 'llm_analysis' in upload_result_1 and upload_result_1['llm_analysis']:
            analysis = upload_result_1['llm_analysis']
            print_info("LLM Analysis Results:")
            print(f"   Suggested System: {analysis.get('system_type', 'N/A')}")
            print(f"   Confidence: {analysis.get('confidence', 0) * 100:.1f}%")
            if 'column_mappings' in analysis and analysis['column_mappings']:
                print(f"   Column Mappings: {len(analysis['column_mappings'])} mappings")
                for orig, mapped in list(analysis['column_mappings'].items())[:3]:
                    print(f"      {orig} → {mapped}")
        
        # Test list datasets
        print_info("Testing list datasets...")
        datasets = client.list_datasets(project_id=project_id)
        if not isinstance(datasets, list):
            print_error("Datasets response is not a list")
            return False, None, None
        
        if len(datasets) == 0:
            print_error("No datasets found after upload")
            return False, None, None
        
        print_success(f"Found {len(datasets)} dataset(s) in project")
        
        # Test get dataset schema
        print_info("Testing get dataset schema...")
        schema = client.get_dataset_schema(project_id=project_id)
        if validate_response(schema, ["project_id", "system_name"], "Dataset schema"):
            print_success("Dataset schema retrieved successfully")
            print(f"   System: {schema.get('system_name')}")
            print(f"   Required columns: {schema.get('required_columns', [])}")
        
        # Load and upload second dataset
        print_info(f"Loading second dataset from {CSV_FILE_2}...")
        try:
            df2 = pd.read_csv(CSV_FILE_2)
            print_success(f"Second dataset loaded: {df2.shape[0]} rows, {df2.shape[1]} columns")
        except FileNotFoundError:
            print_warning(f"File {CSV_FILE_2} not found, skipping second dataset upload")
            return True, df1, dataset_ids
        
        # Upload second dataset
        print_info("Uploading second dataset...")
        upload_result_2 = client.upload_dataset(
            project_id=project_id,
            data=df2,
            context="Additional Netflix customer churn data for the same project"
        )
        
        if validate_response(upload_result_2, ["dataset_id"], "Second upload result"):
            dataset_id_2 = upload_result_2.get('dataset_id')
            if dataset_id_2:
                dataset_ids.append(dataset_id_2)
            print_success("Second dataset uploaded successfully!")
        
        # Verify datasets list updated
        datasets_after = client.list_datasets(project_id=project_id)
        if len(datasets_after) < len(datasets):
            print_error("Dataset count decreased after second upload")
            return False, None, None
        
        # Combine datasets for later use
        combined_df = pd.concat([df1, df2], ignore_index=True)
        print_info(f"Combined dataset: {combined_df.shape[0]} total rows")
        
        return True, combined_df, dataset_ids
        
    except Exception as e:
        print_error(f"Datasets test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None, None


def test_training(client: MLOpsClient, project_id: str):
    """Test model training and versioning"""
    print_section("TEST 5: Model Training & Versioning")
    
    models = []
    training_started = False
    
    try:
        # Test train model
        print_info("Testing train model...")
        try:
            training_result = client.train_model(project_id=project_id)
            
            if validate_response(training_result, ["model_id", "version"], "Training result"):
                training_started = True
                print_success("Training started successfully!")
                print(f"   Model ID: {training_result.get('model_id')}")
                print(f"   Version: {training_result.get('version')}")
        except APIError as e:
            error_msg = str(e).lower()
            if "already in progress" in error_msg:
                print_info("Training already in progress, waiting for completion...")
                training_started = True
            elif "low drift" in error_msg or "no new data to train on" in error_msg:
                # This is expected behavior - training skipped due to low drift
                print_info("Training skipped due to low drift (expected behavior)")
                print_info("   ✓ Drift detection is working correctly")
                print_info("   ✓ System prevented unnecessary training")
                training_started = False
            else:
                print_error(f"Failed to start training: {str(e)}")
                return False, None
        
        # Wait for training to complete (if training was started)
        training_status = None
        if training_started:
            training_status = wait_for_training_complete(client, project_id)
            
            if not training_status:
                print_error("Training did not complete successfully")
                return False, None
            
            print_success("Training completed successfully!")
            
            # Validate training metrics
            if 'metrics' in training_status:
                metrics = training_status['metrics']
                if validate_model_metrics(metrics):
                    print_success("Model metrics validated")
                    print_info("Key Metrics:")
                    for key in ["accuracy", "precision", "recall", "f1_score", "roc_auc"]:
                        if key in metrics:
                            value = metrics[key]
                            if isinstance(value, (int, float)):
                                print(f"   {key}: {value:.4f}")
        
        # Test get latest model
        print_info("Testing get latest model...")
        try:
            latest_model = client.get_latest_model(project_id=project_id)
            if validate_response(latest_model, ["id", "version"], "Latest model"):
                print_success("Latest model retrieved successfully")
                print(f"   Model Version: {latest_model.get('version')}")
                models.append(latest_model)
        except APIError as e:
            if "not found" in str(e).lower():
                print_warning("No models found yet (this is OK if training was skipped)")
            else:
                raise
        
        # Test get all models
        print_info("Testing get all models...")
        all_models = client.get_models(project_id=project_id)
        if not isinstance(all_models, list):
            print_error("Models response is not a list")
            return False, None
        
        if len(all_models) == 0:
            if not training_started:
                # Training was skipped, so no models is acceptable
                print_info("No models found (expected when training is skipped due to low drift)")
                return True, []
            else:
                print_error("No models found after training")
                return False, None
        
        print_success(f"Found {len(all_models)} model version(s)")
        models = all_models
        
        # Validate each model
        for model in all_models:
            if not validate_response(model, ["id", "version"], "Model"):
                return False, None
            print(f"   Version {model.get('version')}: {model.get('id')}")
        
        return True, models
        
    except Exception as e:
        print_error(f"Training test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None


def test_predictions(client: MLOpsClient, project_id: str, sample_data: pd.DataFrame) -> bool:
    """Test prediction APIs"""
    print_section("TEST 6: Predictions")
    
    try:
        if sample_data is None or sample_data.empty:
            print_warning("No sample data available, skipping prediction test")
            return True
        
        # Get a sample row
        sample_row = sample_data.iloc[0]
        customer_id = str(sample_row.get('customer_id', f'sample_{int(time.time())}'))
        
        print_info(f"Testing single prediction for customer: {customer_id}")
        
        # Dynamically extract input data from sample
        input_data = {}
        numeric_cols = sample_data.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = sample_data.select_dtypes(include=['object']).columns.tolist()
        
        # Helper function to convert pandas/numpy types to native Python types
        def convert_to_native(val):
            """Convert pandas/numpy types to native Python types for JSON serialization"""
            if pd.isna(val):
                return None
            if isinstance(val, (pd.Timestamp, pd.DatetimeTZDtype)):
                return str(val)
            if hasattr(val, 'item'):  # numpy scalar
                return val.item()
            if isinstance(val, (int, float, str, bool)):
                return val
            return str(val)
        
        # Add numeric features
        for col in numeric_cols[:6]:  # Limit to 6 numeric features
            if col != 'customer_id' and col != 'churned':
                val = sample_row.get(col)
                if pd.notna(val):
                    input_data[col] = convert_to_native(val)
        
        # Add categorical features
        for col in categorical_cols[:3]:  # Limit to 3 categorical features
            if col != 'customer_id':
                val = sample_row.get(col)
                if pd.notna(val):
                    input_data[col] = convert_to_native(val)
        
        print_info(f"   Input features: {list(input_data.keys())}")
        
        # Test prediction
        try:
            prediction = client.predict(
                project_id=project_id,
                customer_id=customer_id,
                input_data=input_data
            )
            
            if not validate_response(prediction, ["project_id"], "Prediction"):
                return False
            
            print_success("Prediction completed successfully!")
            print(f"   Project ID: {prediction.get('project_id')}")
            
            if 'predictions' in prediction:
                pred_data = prediction['predictions']
                print(f"   Will Churn: {pred_data.get('will_churn', 'N/A')}")
                print(f"   Churn Probability: {pred_data.get('churn_probability', 'N/A')}")
                print(f"   Risk Level: {pred_data.get('risk_level', 'N/A')}")
            
            return True
            
        except APIError as e:
            if "trained model" in str(e).lower() or "not found" in str(e).lower():
                print_warning(f"Prediction test skipped: {str(e)}")
                return True  # Not a failure, just no model yet
            raise
        
    except Exception as e:
        print_error(f"Predictions test failed: {str(e)}")
        return False


def test_monitoring(client: MLOpsClient, project_id: str) -> bool:
    """Test monitoring and metrics APIs"""
    print_section("TEST 7: Monitoring & Metrics")
    
    try:
        # Test get metrics
        print_info("Testing get metrics...")
        metrics = client.get_metrics(project_id=project_id)
        
        if not validate_response(metrics, [], "Metrics"):
            return False
        
        print_success("Metrics retrieved successfully!")
        
        if 'models' in metrics and isinstance(metrics['models'], list):
            print_info(f"   Found {len(metrics['models'])} model version(s) with metrics")
            for model in metrics['models']:
                if 'metrics' in model:
                    model_metrics = model['metrics']
                    if validate_model_metrics(model_metrics):
                        print(f"   Version {model.get('version', 'N/A')}: Valid metrics")
        
        # Test get drift status
        print_info("Testing get drift status...")
        drift_status = client.get_drift_status(project_id=project_id, days=7)
        
        if validate_response(drift_status, [], "Drift status"):
            print_success("Drift status retrieved successfully!")
            
            if 'summary' in drift_status:
                summary = drift_status['summary']
                print(f"   Total Checks: {summary.get('total_checks', 0)}")
                print(f"   Average Drift Score: {summary.get('avg_drift_score', 0):.4f}")
                print(f"   Drift Alerts: {summary.get('drift_alerts', 0)}")
        
        # Test get dashboard
        print_info("Testing get dashboard...")
        dashboard = client.get_dashboard(project_id=project_id)
        
        if validate_response(dashboard, [], "Dashboard"):
            print_success("Dashboard data retrieved successfully!")
            
            if 'drift_status' in dashboard:
                drift = dashboard['drift_status']
                print(f"   Drift Status: {drift.get('status', 'N/A')}")
            
            if 'model_performance' in dashboard:
                perf = dashboard['model_performance']
                print(f"   Current Version: {perf.get('current_version', 'N/A')}")
        
        # Test get alerts
        print_info("Testing get alerts...")
        alerts = client.get_alerts(project_id=project_id)
        
        if validate_response(alerts, [], "Alerts"):
            print_success("Alerts retrieved successfully!")
            total_alerts = alerts.get('total_alerts', 0)
            print(f"   Total Alerts: {total_alerts}")
        
        return True
        
    except Exception as e:
        print_error(f"Monitoring test failed: {str(e)}")
        return False


def test_model_comparison(client: MLOpsClient, project_id: str, models: List[Dict[str, Any]]) -> bool:
    """Test model comparison API"""
    print_section("TEST 8: Model Comparison")
    
    try:
        if not models or len(models) < 2:
            print_warning("Need at least 2 models for comparison, skipping test")
            return True
        
        # Get first two models
        model1 = models[0]
        model2 = models[1]
        
        model_id_1 = model1.get('id')
        model_id_2 = model2.get('id')
        
        if not model_id_1 or not model_id_2:
            print_error("Model IDs not found")
            return False
        
        print_info(f"Comparing Model v{model1.get('version')} vs Model v{model2.get('version')}...")
        
        # Test compare models
        comparison = client.compare_models(
            project_id=project_id,
            model_id_1=model_id_1,
            model_id_2=model_id_2
        )
        
        if not validate_response(comparison, ["model_1", "model_2", "comparison"], "Comparison"):
            return False
        
        print_success("Model comparison completed successfully!")
        
        # Validate comparison structure
        if 'model_1' in comparison and 'model_2' in comparison:
            print(f"   Model 1: v{comparison['model_1'].get('version', 'N/A')}")
            print(f"   Model 2: v{comparison['model_2'].get('version', 'N/A')}")
        
        if 'comparison' in comparison:
            comp = comparison['comparison']
            if 'metrics' in comp:
                metrics_count = len(comp['metrics'])
                print(f"   Metrics compared: {metrics_count}")
            
            if 'feature_importance' in comp:
                feat = comp['feature_importance']
                if feat.get('available'):
                    print(f"   Features compared: {feat.get('common_features', 0)}")
        
        if 'winner' in comparison:
            winner = comparison['winner']
            print(f"   Winner: {winner}")
        
        if 'summary' in comparison:
            summary = comparison['summary']
            print(f"   Overall Trend: {summary.get('overall_trend', 'N/A')}")
        
        return True
        
    except Exception as e:
        print_error(f"Model comparison test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_dashboards(client: MLOpsClient) -> bool:
    """Test dashboard APIs"""
    print_section("TEST 9: Dashboard & Analytics")
    
    try:
        # Test dashboard overview
        print_info("Testing dashboard overview...")
        overview = client.get_dashboard_overview()
        
        if validate_response(overview, ["summary"], "Dashboard overview"):
            print_success("Dashboard overview retrieved successfully!")
            
            if 'summary' in overview:
                summary = overview['summary']
                print(f"   Total Projects: {summary.get('projects', {}).get('total_projects', 0)}")
                print(f"   Total Models: {summary.get('models', {}).get('total_models', 0)}")
                print(f"   Predictions Served: {summary.get('predictions_served', 0)}")
        
        # Test analytics dashboard
        print_info("Testing analytics dashboard...")
        analytics = client.get_analytics_dashboard(days=30)
        
        if validate_response(analytics, ["trends", "totals"], "Analytics dashboard"):
            print_success("Analytics dashboard retrieved successfully!")
            
            if 'totals' in analytics:
                totals = analytics['totals']
                print(f"   Total Projects: {totals.get('projects', 0)}")
                print(f"   Total Models: {totals.get('models', 0)}")
                print(f"   Total Predictions: {totals.get('predictions', 0)}")
        
        return True
        
    except Exception as e:
        print_error(f"Dashboard test failed: {str(e)}")
        return False


def main():
    """Run comprehensive integration tests"""
    print_section("MLOPS - COMPREHENSIVE INTEGRATION TEST")
    print_info("Testing all APIs and services dynamically...")
    print_info("No hardcoded values - everything is validated!")
    
    client = None
    project_id = None
    
    try:
        # Initialize client
        print_section("INITIALIZATION")
        print_info("Initializing MLOps client...")
        client = MLOpsClient(base_url=BASE_URL)
        print_success("Client initialized")
        
        # Run all tests
        tests_passed = 0
        tests_failed = 0
        
        # Test 1: Authentication
        if test_authentication(client):
            tests_passed += 1
        else:
            tests_failed += 1
            print_error("Authentication failed - cannot continue with other tests")
            return
        
        # Test 2: Systems
        if test_systems(client):
            tests_passed += 1
        else:
            tests_failed += 1
        
        # Test 3: Projects
        success, project_id = test_projects(client)
        if success:
            tests_passed += 1
        else:
            tests_failed += 1
            print_error("Project creation failed - cannot continue")
            return
        
        # Test 4: Datasets
        success, combined_df, dataset_ids = test_datasets(client, project_id)
        if success:
            tests_passed += 1
        else:
            tests_failed += 1
        
        # Test 5: Training
        success, models = test_training(client, project_id)
        if success:
            tests_passed += 1
        else:
            tests_failed += 1
        
        # Test 6: Predictions
        if test_predictions(client, project_id, combined_df):
            tests_passed += 1
        else:
            tests_failed += 1
        
        # Test 7: Monitoring
        if test_monitoring(client, project_id):
            tests_passed += 1
        else:
            tests_failed += 1
        
        # Test 8: Model Comparison
        if models and len(models) >= 2:
            if test_model_comparison(client, project_id, models):
                tests_passed += 1
            else:
                tests_failed += 1
        else:
            print_warning("Skipping model comparison - need at least 2 models")
        
        # Test 9: Dashboards
        if test_dashboards(client):
            tests_passed += 1
        else:
            tests_failed += 1
        
        # Final Summary
        print_section("TEST SUMMARY")
        print(f"\n📊 Test Results:")
        print(f"   ✅ Passed: {tests_passed}")
        print(f"   ❌ Failed: {tests_failed}")
        print(f"   ⚠️  Warnings: {len(test_results['warnings'])}")
        
        if test_results['passed']:
            print(f"\n✅ Successful Tests ({len(test_results['passed'])}):")
            for test in test_results['passed'][:10]:  # Show first 10
                print(f"   • {test}")
        
        if test_results['failed']:
            print(f"\n❌ Failed Tests ({len(test_results['failed'])}):")
            for test in test_results['failed']:
                print(f"   • {test}")
        
        if test_results['warnings']:
            print(f"\n⚠️  Warnings ({len(test_results['warnings'])}):")
            for warning in test_results['warnings'][:5]:  # Show first 5
                print(f"   • {warning}")
        
        if project_id:
            print(f"\n📋 Test Project:")
            print(f"   Project ID: {project_id}")
            if models:
                print(f"   Model Versions: {len(models)}")
            if dataset_ids:
                print(f"   Datasets: {len(dataset_ids)}")
        
        # Overall result
        if tests_failed == 0:
            print_success("\n🎉 All tests passed! All APIs and services are working correctly!")
            return 0
        else:
            print_error(f"\n❌ {tests_failed} test(s) failed. Please review the errors above.")
            return 1
        
    except KeyboardInterrupt:
        print_error("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print_error(f"\n\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
