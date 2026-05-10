# MLOps Platform

This is a full-stack MLOps project that automates the machine learning workflow from dataset upload and system detection to training, monitoring, and model comparison. It was built as a student project for a software hackathon.

## Overview

The platform combines three main pieces:

- a **FastAPI backend** for authentication, datasets, training, monitoring, and model registry logic
- a **React + TypeScript web app** for project management and analytics
- a **Python SDK** for programmatic access from notebooks or scripts

The goal is to make ML workflows feel practical, visual, and easy to extend.

## Key Features

### Intelligent system detection
Upload a dataset and let the platform infer the likely ML system type, such as churn prediction or recommendation.

### Automated training workflow
The backend handles preprocessing, model training, versioning, and metric tracking.

### Monitoring and drift detection
Track metrics over time, compare model versions, and detect dataset drift before it affects performance.

### Model registry and comparison
Store model versions, inspect metadata, and compare runs side by side.

### Web dashboard
The UI includes:

- login and signup screens
- dashboard overview
- project creation and project details pages
- monitoring views
- model comparison and docs pages
- an AI chat assistant for quick guidance

### Python SDK
The SDK provides a simple interface for:

- authentication
- project creation
- dataset upload
- training and retraining
- predictions
- monitoring calls

## Architecture

- **Frontend**: React 19, TypeScript, Tailwind CSS, Recharts
- **Backend**: FastAPI, Beanie, Pydantic, MongoDB
- **SDK**: Python package using `requests` and `pandas`

The services are separated into focused modules for datasets, training, monitoring, prediction, and registry management.

## Repository Structure

```text
├── backend/              FastAPI backend and ML services
├── web/                  React dashboard
├── sdk/                  Python SDK package
├── model_storage/        Saved model and upload artifacts
├── churn_prediction_sample.csv
└── README.md
```

## Requirements

- Python 3.10+
- Node.js 18+
- MongoDB

## Quick Start

### 1. Start MongoDB

Using Docker:

```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 2. Run the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Backend runs on `http://localhost:8000` and the API docs are available at `/docs`.

### 3. Run the web app

```bash
cd web
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`.

### 4. Install the SDK

```bash
cd sdk
pip install -e .
```

## Example Usage

```python
from mlops_sdk import MLOpsClient
import pandas as pd

client = MLOpsClient(base_url="http://localhost:8000")
client.login(email="user@example.com", password="password")

project = client.create_project(name="Customer Churn Model")
data = pd.read_csv("customer_data.csv")
client.upload_data(project["id"], data)

result = client.train(project["id"])
print(result)
```

## Supported Use Cases

- recommendation systems
- customer churn prediction
- monitoring and retraining workflows

## Configuration

Create a `backend/.env` file with values like:

```env
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=mlops_db
SECRET_KEY=your-secret-key-here
```

## Troubleshooting

- Make sure MongoDB is running before starting the backend.
- Confirm the backend is on port 8000 and the frontend on port 5173.
- If imports fail, reactivate the virtual environment and reinstall dependencies.

## Tech Stack

- **Backend**: FastAPI, Beanie, Pydantic
- **Frontend**: React, TypeScript, Tailwind CSS, Recharts
- **Database**: MongoDB
- **ML libraries**: scikit-learn, pandas, numpy

## License

MIT License.

---

Built with ❤️ for the software hackathon.