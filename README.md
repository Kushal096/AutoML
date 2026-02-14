# Taranga MLOps Platform

A comprehensive Machine Learning Operations platform that automates the entire ML lifecycle from data ingestion to model deployment and monitoring. Built for the Taranga v1.0 Software Hackathon.

## Overview

Taranga is an end-to-end MLOps platform designed to make machine learning accessible and manageable. Whether you're building a recommendation system, predicting customer churn, or deploying any ML model, Taranga provides the infrastructure and tools you need.

The platform combines a powerful **web dashboard** with a **Python SDK**, giving you flexibility to work however you prefer - through an intuitive UI or programmatically through code.

## ✨ Key Features

### Intelligent System Detection
Upload your dataset and let our AI-powered analysis automatically detect what type of ML system you need. No need to manually configure algorithms or preprocessing steps.

### Automated Training Pipeline
Train models with a single click. The platform handles:
- Data preprocessing and validation
- Algorithm selection and hyperparameter tuning
- Model versioning and artifact storage
- Performance metrics tracking

### Real-time Monitoring
Keep your models healthy with continuous monitoring:
- Track prediction volumes and response times
- Detect data drift before it impacts performance
- Compare model versions side-by-side
- Get alerts when issues arise

### Model Registry & Comparison
Manage multiple model versions with ease:
- Track all model iterations with full lineage
- Compare metrics across different versions
- Promote models through staging to production
- Roll back to previous versions when needed

### Beautiful Dashboard
A clean, modern interface built with React that provides:
- Real-time analytics and visualizations
- Project management and organization
- Dataset upload and management
- Interactive prediction interface

### Python SDK
Integrate ML capabilities directly into your Python applications:
- Simple, intuitive API
- Full feature parity with web interface
- Pandas DataFrame support
- Async-ready for high performance

### 🔐Secure & Scalable
Enterprise-ready security and architecture:
- JWT-based authentication
- API key management
- Role-based access control
- MongoDB for scalable data storage

## 🏗️ Architecture

The platform is built with a modern, scalable architecture:

- **Frontend**: React 19 with TypeScript, Tailwind CSS, and Recharts for visualizations
- **Backend**: FastAPI (Python) providing RESTful APIs with automatic OpenAPI documentation
- **Database**: MongoDB for flexible, scalable data storage
- **SDK**: Python package for programmatic access

All components communicate via REST APIs, making the system modular and easy to extend.

## 📋 Prerequisites

- **Python 3.10+** for backend and SDK
- **Node.js 18+** for the web frontend
- **MongoDB** for data storage
- **Git** for version control

## 🚀 Quick Start

### 1. Set Up MongoDB

Using Docker (recommended):
```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

Or install MongoDB locally following the [official guide](https://docs.mongodb.com/manual/installation/).

### 2. Start the Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Backend runs at `http://localhost:8000` with API docs at `/docs`

### 3. Start the Web Interface

```bash
cd web
npm install  # or pnpm install
npm run dev
```

Frontend runs at `http://localhost:5173`

### 4. Install Python SDK (Optional)

```bash
cd sdk
pip install -e .
```

## 📖 Usage

### Web Dashboard

1. **Create an account** at http://localhost:5173
2. **Create a project** - give it a name and select your ML system type
3. **Upload your data** - CSV or Excel files supported
4. **Train your model** - one click to start training
5. **Monitor & predict** - view metrics, make predictions, check for drift

### Python SDK

```python
from taranga_mlops import TarangaClient
import pandas as pd

# Initialize and authenticate
client = TarangaClient(base_url="http://localhost:8000")
client.login(email="user@example.com", password="password")

# Create a project
project = client.create_project(name="Customer Churn Model")

# Upload data
data = pd.read_csv("customer_data.csv")
client.upload_data(project["id"], data)

# Train model
result = client.train(project["id"])

# Make predictions
predictions = client.predict(
    project_id=project["id"],
    data=new_customer_data
)

# Monitor performance
metrics = client.get_metrics(project["id"])
drift_status = client.get_drift_status(project["id"])
```

## 🎓 Supported ML Systems

### Recommendation Systems
Build personalized recommendation engines using:
- Collaborative filtering
- Content-based filtering
- Hybrid approaches

### Churn Prediction
Predict customer churn with:
- Gradient boosting models
- Feature importance analysis
- Probability scoring

### More Coming Soon
The platform is designed to be extensible for additional ML use cases including fraud detection, sentiment analysis, and demand forecasting.

## 📁 Project Structure

```
├── backend/          # FastAPI server and ML services
├── web/             # React dashboard
├── sdk/             # Python SDK package
└── README.md        # This file
```

Each directory contains its own README with detailed documentation.

## 🔧 Configuration

### Backend Environment Variables

Create `backend/.env`:
```env
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=taranga_db
SECRET_KEY=your-secret-key-here
```

### Frontend Configuration

The frontend automatically connects to the backend at `http://localhost:8000/api/v1`. For production, update the API URL in the environment configuration.

## 🐛 Troubleshooting

**MongoDB Connection Issues**
- Verify MongoDB is running: `docker ps`
- Check connection string in backend/.env

**Port Conflicts**
- Backend uses port 8000
- Frontend uses port 5173
- MongoDB uses port 27017

**Module Import Errors**
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

## 🤝 Development

This project was built for the Taranga v1.0 Software Hackathon. The codebase is structured for easy understanding and extension.

### Tech Stack
- **Backend**: FastAPI, Beanie (MongoDB ODM), Pydantic
- **Frontend**: React 19, TypeScript, Tailwind CSS, Recharts
- **Database**: MongoDB
- **ML Libraries**: scikit-learn, pandas, numpy

## 📝 License

MIT License - feel free to use this project as a foundation for your own MLOps platform.

---

**Built with ❤️ for the Taranga v1.0 Software Hackathon**

---

**Built with ❤️ for the Taranga v1.0 Software Hackathon**