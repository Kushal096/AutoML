# FastAPI MongoDB Backend

A well-structured FastAPI server with MongoDB integration using modern Python async patterns.

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization
│   ├── core/
│   │   ├── config.py        # Configuration settings
│   │   └── database.py      # MongoDB connection setup
│   ├── api/
│   │   ├── __init__.py      # API router setup
│   │   └── endpoints/
│   │       └── health.py    # Health check endpoint
│   ├── models/              # Beanie document models
│   │   └── __init__.py
│   └── services/            # Business logic services
│       └── __init__.py
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
└── README.md               # This file
```

## Prerequisites

- Python 3.8+
- MongoDB (local installation or Docker)

## Setup

### 1. Install MongoDB

**Using Docker (Recommended):**
```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

**Or install MongoDB locally:**
- Follow the [official MongoDB installation guide](https://docs.mongodb.com/manual/installation/)

### 2. Python Environment Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
cp .env.example .env
# Edit .env file with your MongoDB connection string if different
```

### 4. Run the Server

```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

- **GET** `/` - Root endpoint with API information
- **GET** `/api/v1/health` - Health check endpoint (includes database connectivity check)

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Features

- ✅ Modern FastAPI structure with proper separation of concerns
- ✅ MongoDB integration using Motor (async) and Beanie ODM
- ✅ CORS enabled for frontend integration
- ✅ Environment-based configuration
- ✅ Proper application lifecycle management
- ✅ Health check with database connectivity verification
- ✅ Auto-generated API documentation
- ✅ Structured logging

## Adding New Features

### 1. Database Models
Create Beanie document models in `app/models/` and add them to the `document_models` list in `app/core/database.py`.

### 2. API Endpoints
Add new endpoint files in `app/api/endpoints/` and include the routers in `app/api/__init__.py`.

### 3. Business Logic
Implement services in `app/services/` to keep your endpoint handlers clean.

## MongoDB Collections

The database will be created automatically when the first document is inserted. Collections are created by Beanie based on your document models.

## Development

The server runs with auto-reload enabled in development mode. Make changes to the code and the server will restart automatically.

## Production

For production deployment:
- Set `DEBUG=False` in your environment
- Use a production MongoDB instance
- Configure proper logging
- Use a production ASGI server like Gunicorn with Uvicorn workers
- Implement authentication and authorization as needed
- Add monitoring and health checks