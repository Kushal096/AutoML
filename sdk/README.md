# MLOps SDK

Python SDK for interacting with the MLOps Platform.

## Installation

```bash
pip install mlops-sdk
```

Or install from source:
```bash
cd sdk
pip install -e .
```

## Quick Start

```python
from mlops_sdk import MLOpsClient
import pandas as pd

# Initialize client
client = MLOpsClient(base_url="http://localhost:8000")

# Login
client.login(email="user@example.com", password="password")

# List available systems
systems = client.list_systems()
print(systems)

# Create a project (use system name directly!)
project = client.create_project(
    name="My Recommendation System",
    system="Recommendation"  # Just use the system name!
)
project_id = project["id"]

# Upload data
data = pd.DataFrame({
    "user_id": [1, 2, 3],
    "item_id": [10, 20, 30],
    "rating": [5, 4, 3]
})
client.upload_data(project_id, data)

# Train model
result = client.train(project_id)
print(f"Model trained! Version: {result['version']}")

# Make predictions
predictions = client.predict(
    project_id=project_id,
    user_id="user_123",
    top_k=10
)
print(predictions)

# Monitor drift
drift = client.get_drift_status(project_id)
print(f"Drift detected: {drift['summary']['drift_alerts']}")
```

## API Reference

### Authentication

```python
# Signup
client.signup(name="John Doe", email="john@example.com", password="secure123")

# Login
client.login(email="john@example.com", password="secure123")

# Refresh API key
client.refresh_api_key()
```

### Projects

```python
# Create project (use system name)
project = client.create_project(name="My Project", system="Recommendation")

# Or use system ID if you prefer
project = client.create_project(name="My Project", system="<system_id>")

# List projects
projects = client.list_projects()

# Get project
project = client.get_project(project_id)

# Delete project
client.delete_project(project_id)
```

### Data Upload

```python
# Upload DataFrame
client.upload_data(project_id, df)

# Upload from file
client.upload_data(project_id, "data.csv")

# Upload with column mapping
client.upload_data(
    project_id, 
    df,
    column_mapping={"user_col": "user_id", "item_col": "item_id"}
)
```

### Training

```python
# Train model
result = client.train(project_id)

# Retrain model
result = client.retrain(project_id)

# Get training status
status = client.get_training_status(project_id)

# Get models
models = client.get_models(project_id)
```

### Predictions

```python
# Single prediction (Recommendation)
pred = client.predict(project_id=pid, user_id="u123", top_k=10)

# Single prediction (Churn)
pred = client.predict(
    project_id=pid,
    customer_id="c123",
    input_data={"age": 35, "usage": 150}
)

# Batch predictions
preds = client.predict_batch(
    project_id=pid,
    users=["u1", "u2", "u3"],
    top_k=5
)
```

### Monitoring

```python
# Get metrics
metrics = client.get_metrics(project_id)

# Get drift status
drift = client.get_drift_status(project_id, days=7)

# Detect drift in new data
drift = client.detect_drift(project_id, {"feature1": 123})

# Get dashboard
dashboard = client.get_dashboard(project_id)

# Get alerts
alerts = client.get_alerts(project_id)
```

## Error Handling

```python
from mlops_sdk import MLOpsClient, AuthenticationError, APIError

try:
    client = MLOpsClient()
    client.login(email="wrong@email.com", password="wrong")
except AuthenticationError as e:
    print(f"Auth failed: {e}")
except APIError as e:
    print(f"API error: {e.status_code} - {e}")
```

## License

MIT License

