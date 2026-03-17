"""
AI Assistant API - Context-aware chatbot for MLOps platform
Provides intelligent assistance with access to user's projects, models, datasets, and metrics
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from pydantic import BaseModel

import httpx

from app.models import (
    User, Project, Model, Dataset, System, 
    ModelRegistryMetadata, DriftMetric
)
from app.core.auth import get_current_user
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)
router = APIRouter()


async def _call_ollama_chat(prompt: str) -> str:
    """
    Call Ollama API for chat (plain text response, not JSON)
    """
    OLLAMA_BASE_URL = "https://d680fd980f67.ngrok-free.app"
    MODEL_NAME = "llama3.1:8b"
    TIMEOUT = 60.0
    
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
        # Note: Not requesting JSON format for chat responses
    }
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        return result.get("response", "")


class ChatMessage(BaseModel):
    """Chat message request"""
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = []


class ChatResponse(BaseModel):
    """Chat response"""
    response: str
    suggestions: Optional[List[str]] = []


async def gather_user_context(user_id: str) -> Dict[str, Any]:
    """
    Gather comprehensive context about the user's MLOps environment
    
    Returns:
        Dictionary with projects, models, datasets, metrics, and insights
    """
    try:
        # Get all user projects (excluding deleted)
        projects = await Project.find(
            Project.user_id == user_id,
            Project.status != "deleted"
        ).sort(-Project.created_at).to_list()
        
        project_ids = [str(p.id) for p in projects]
        
        # Get all models
        models = await Model.find({"project_id": {"$in": project_ids}}).sort(-Model.version).to_list()
        
        # Get all datasets
        datasets = await Dataset.find({"project_id": {"$in": project_ids}}).to_list()
        
        # Get systems
        system_ids = list(set([p.system_id for p in projects if p.system_id]))
        systems = await System.find({"_id": {"$in": system_ids}}).to_list()
        
        # Get latest model metrics
        latest_models = {}
        for project_id in project_ids:
            latest_model = await Model.find(
                Model.project_id == project_id
            ).sort(-Model.version).first_or_none()
            if latest_model:
                latest_models[project_id] = {
                    "version": latest_model.version,
                    "accuracy": latest_model.metrics.get("accuracy") if latest_model.metrics else None,
                    "created_at": latest_model.created_at.isoformat() if latest_model.created_at else None
                }
        
        # Get drift metrics summary
        drift_summary = {}
        for project_id in project_ids:
            drift_metrics = await DriftMetric.find(
                DriftMetric.project_id == project_id
            ).sort(-DriftMetric.detected_at).limit(5).to_list()
            
            if drift_metrics:
                avg_drift = sum([d.drift_score for d in drift_metrics]) / len(drift_metrics)
                drift_summary[project_id] = {
                    "recent_checks": len(drift_metrics),
                    "avg_drift_score": avg_drift,
                    "has_alerts": any([d.drift_score > 0.1 for d in drift_metrics])
                }
        
        # Build context summary
        context = {
            "user_id": user_id,
            "projects": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "status": p.status,
                    "system_id": p.system_id,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                }
                for p in projects[:10]  # Limit to 10 most recent
            ],
            "total_projects": len(projects),
            "total_models": len(models),
            "total_datasets": len(datasets),
            "systems": [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "description": s.description
                }
                for s in systems
            ],
            "latest_models": latest_models,
            "drift_summary": drift_summary,
            "project_summary": {
                "by_status": {
                    "created": len([p for p in projects if p.status == "created"]),
                    "training": len([p for p in projects if p.status == "training"]),
                    "trained": len([p for p in projects if p.status == "trained"]),
                    "error": len([p for p in projects if p.status == "error"])
                },
                "by_system": {}
            }
        }
        
        # Count projects by system
        for system in systems:
            system_id = str(system.id)
            count = len([p for p in projects if p.system_id == system_id])
            if count > 0:
                context["project_summary"]["by_system"][system.name] = count
        
        return context
        
    except Exception as e:
        logger.error(f"Failed to gather user context: {str(e)}")
        return {
            "user_id": user_id,
            "projects": [],
            "total_projects": 0,
            "total_models": 0,
            "total_datasets": 0,
            "systems": [],
            "latest_models": {},
            "drift_summary": {},
            "project_summary": {"by_status": {}, "by_system": {}}
        }


def build_assistant_prompt(user_message: str, context: Dict[str, Any], conversation_history: List[Dict[str, str]]) -> str:
    """
    Build a comprehensive prompt for the AI assistant
    """
    prompt = """You are an expert AI assistant for the Taranga MLOps platform. You help users with:
- Understanding their ML projects, models, and datasets
- Interpreting metrics and performance data
- Providing insights about drift detection
- Guiding users on best practices
- Answering questions about the platform features

**User's Current Context:**
"""
    
    # Add user's project information
    if context.get("total_projects", 0) > 0:
        prompt += f"\n- Total Projects: {context['total_projects']}\n"
        prompt += f"- Total Models: {context['total_models']}\n"
        prompt += f"- Total Datasets: {context['total_datasets']}\n"
        
        if context.get("projects"):
            prompt += "\n**Recent Projects:**\n"
            for proj in context["projects"][:5]:
                prompt += f"  - {proj['name']} (Status: {proj['status']}, ID: {proj['id']})\n"
        
        if context.get("systems"):
            prompt += "\n**Available ML Systems:**\n"
            for sys in context["systems"][:5]:
                prompt += f"  - {sys['name']}: {sys.get('description', 'N/A')}\n"
        
        if context.get("latest_models"):
            prompt += "\n**Latest Model Performance:**\n"
            for proj_id, model_info in list(context["latest_models"].items())[:3]:
                proj_name = next((p['name'] for p in context['projects'] if p['id'] == proj_id), proj_id)
                accuracy = model_info.get('accuracy')
                if accuracy is not None:
                    prompt += f"  - {proj_name}: v{model_info['version']}, Accuracy: {accuracy:.2%}\n"
        
        if context.get("drift_summary"):
            prompt += "\n**Drift Detection Status:**\n"
            for proj_id, drift_info in list(context["drift_summary"].items())[:3]:
                proj_name = next((p['name'] for p in context['projects'] if p['id'] == proj_id), proj_id)
                avg_drift = drift_info.get('avg_drift_score', 0)
                has_alerts = drift_info.get('has_alerts', False)
                status_icon = "⚠️" if has_alerts else "✅"
                prompt += f"  - {proj_name}: {status_icon} Avg Drift: {avg_drift:.4f}\n"
    
    # Add conversation history for context
    if conversation_history:
        prompt += "\n**Recent Conversation:**\n"
        for msg in conversation_history[-3:]:  # Last 3 messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt += f"  {role.capitalize()}: {content}\n"
    
    prompt += f"\n**User's Question:**\n{user_message}\n\n"
    
    prompt += """**Your Response Guidelines:**
- Be helpful, concise, and professional
- Use the context provided to give specific, relevant answers
- If asked about a specific project, use the project ID or name from the context
- For metrics questions, reference the actual data when available
- Suggest actionable insights when appropriate
- If you don't have enough information, ask clarifying questions
- Format your response naturally, as if you're a knowledgeable colleague

**Response:**"""
    
    return prompt


@router.post("/assistant/chat", response_model=ChatResponse)
async def chat_with_assistant(
    chat_request: ChatMessage,
    current_user: User = Depends(get_current_user)
):
    """
    Chat with the AI assistant
    
    The assistant has access to:
    - User's projects, models, and datasets
    - Model performance metrics
    - Drift detection results
    - System information
    
    Returns intelligent, context-aware responses
    """
    try:
        user_id = str(current_user.id)
        
        # Gather user context
        logger.info(f"Gathering context for user {user_id}")
        context = await gather_user_context(user_id)
        
        # Build prompt with context
        prompt = build_assistant_prompt(
            user_message=chat_request.message,
            context=context,
            conversation_history=chat_request.conversation_history or []
        )
        
        # Call LLM (use a modified version that doesn't require JSON format)
        logger.info(f"Sending chat request to LLM for user {user_id}")
        response_text = await _call_ollama_chat(prompt)
        
        # Generate suggestions based on context
        suggestions = []
        if context.get("total_projects", 0) == 0:
            suggestions.append("Create your first project")
            suggestions.append("Upload a dataset")
        elif context.get("total_models", 0) == 0:
            suggestions.append("Train a model on your datasets")
        else:
            suggestions.append("View model performance metrics")
            suggestions.append("Check for data drift")
            if context.get("drift_summary"):
                high_drift_projects = [
                    proj_id for proj_id, drift_info in context["drift_summary"].items()
                    if drift_info.get("has_alerts", False)
                ]
                if high_drift_projects:
                    suggestions.append("Review drift alerts")
        
        return ChatResponse(
            response=response_text.strip(),
            suggestions=suggestions[:3]  # Limit to 3 suggestions
        )
        
    except Exception as e:
        logger.error(f"Chat assistant error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {str(e)}"
        )


@router.get("/assistant/context", response_model=dict)
async def get_assistant_context(
    current_user: User = Depends(get_current_user)
):
    """
    Get the current context that the assistant has access to
    Useful for debugging or showing users what the assistant knows
    """
    try:
        user_id = str(current_user.id)
        context = await gather_user_context(user_id)
        return context
    except Exception as e:
        logger.error(f"Failed to get assistant context: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get context: {str(e)}"
        )

