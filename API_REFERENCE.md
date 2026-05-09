# Taranga MLOps API Reference

## 🔐 Authentication
- `POST /api/v1/auth/signup` - Create account
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/regenerate-api-key` - Regenerate API key

## 🏥 Health
- `GET /api/v1/health` - Health check

## 🎯 Systems
- `GET /api/v1/systems` - List ML systems
- `POST /api/v1/systems` - Create system

## 📁 Projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects` - List projects
- `GET /api/v1/projects/{id}` - Get project
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

## 📊 Datasets
- `POST /api/v1/datasets/{project_id}/upload` - Upload file
- `POST /api/v1/datasets/{project_id}/upload_sdk` - Upload JSON data
- `GET /api/v1/datasets/{project_id}` - List datasets
- `GET /api/v1/datasets/{dataset_id}/columns` - Get columns
- `DELETE /api/v1/datasets/{dataset_id}` - Delete dataset

## 🎓 Training
- `POST /api/v1/projects/{project_id}/train` - Train model
- `POST /api/v1/projects/{project_id}/retrain` - Retrain model
- `GET /api/v1/projects/{project_id}/models` - Get latest model
- `GET /api/v1/projects/{project_id}/models/all` - Get all models
- `GET /api/v1/projects/{project_id}/training/status` - Training status
- `GET /api/v1/projects/{project_id}/models/{model_id}/details` - Model details

## 🔮 Predictions
- `POST /api/v1/predictions/predict` - Single prediction
- `POST /api/v1/predictions/batch` - Batch predictions

## 📈 Monitoring - **WITH VISUALIZATIONS** 📊
- `POST /api/v1/monitoring/drift/detect` - Detect drift
- `GET /api/v1/monitoring/drift/history` - Drift history
- `GET /api/v1/monitoring/metrics/history` - **Metrics history with visualizations**
  - Accuracy evolution plot
  - F1 score evolution plot
  - Model comparison radar chart
- `GET /api/v1/monitoring/dashboard` - Dashboard data

## 🧬 Feature Store (NEW)
- `POST /api/v1/projects/{project_id}/features/definitions` - Create feature
- `GET /api/v1/projects/{project_id}/features/definitions` - List features
- `POST /api/v1/projects/{project_id}/features/auto-generate` - Auto-generate features
- `POST /api/v1/projects/{project_id}/features/sets` - Create feature set
- `GET /api/v1/projects/{project_id}/features/sets` - List feature sets
- `POST /api/v1/projects/{project_id}/features/get` - Get feature values
- `GET /api/v1/projects/{project_id}/features/{name}/statistics` - Feature stats

## 📦 Model Registry (NEW)
- `GET /api/v1/projects/{project_id}/registry/models/{model_id}/metadata` - Model metadata
- `GET /api/v1/projects/{project_id}/registry/models/{model_id}/lineage` - Model lineage
- `POST /api/v1/projects/{project_id}/registry/models/{model_id}/approve` - Approve model
- `POST /api/v1/projects/{project_id}/registry/models/{model_id}/promote` - Promote to production
- `GET /api/v1/projects/{project_id}/registry/production` - Get production model
- `GET /api/v1/projects/{project_id}/registry/stage/{stage}` - Models by stage
- `POST /api/v1/projects/{project_id}/registry/compare` - Compare models
- `GET /api/v1/projects/{project_id}/registry/summary` - Registry summary

## 📊 Dashboard (NEW) - **WITH VISUALIZATIONS** 📈
- `GET /api/v1/dashboard/overview` - **Comprehensive dashboard with 5+ visualizations**
  - System usage pie chart
  - Project status distribution
  - Accuracy/F1 trends
  - Deployment stages bar chart
  - Health score gauge
- `GET /api/v1/dashboard/projects` - Project-level detailed dashboard
- `GET /api/v1/dashboard/analytics?days=30` - Time-series analytics & trends
- `GET /api/v1/dashboard/system/{system_id}` - System-specific dashboard

---

**Total APIs: 47** | **New APIs: 19** (Feature Store: 7, Model Registry: 8, Dashboard: 4)

