import httpx
import logging
from typing import List, Dict, Any, Optional
import json

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service to interact with Ollama LLM for intelligent dataset analysis
    """
    
    OLLAMA_BASE_URL = "https://d680fd980f67.ngrok-free.app"
    MODEL_NAME = "llama3.1:8b"
    TIMEOUT = 60.0  # 60 seconds timeout
    
    @classmethod
    async def analyze_dataset_for_ml_system(
        cls,
        columns: List[str],
        context: str,
        sample_data: Optional[Dict[str, List[Any]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze dataset columns and context to determine:
        1. Which ML system type to use
        2. Which columns are most important
        3. Whether columns need to be renamed
        4. Column mapping recommendations
        
        Args:
            columns: List of column names from the dataset
            context: User-provided context (e.g., "I want a movie recommendation system")
            sample_data: Optional sample values for each column
            
        Returns:
            {
                "system_type": "collaborative_filtering" | "content_based_filtering" | "popularity_based" | 
                              "hybrid_recommendation" | "customer_churn" | "subscription_churn" | 
                              "product_churn" | "revenue_churn" | "early_churn_detection" | 
                              "late_churn_analysis" | "fraud_detection" | "sentiment_analysis" | 
                              "demand_forecasting" | "price_optimization",
                "confidence": 0.95,
                "key_columns": ["user_id", "movie_id", "rating"],
                "column_mappings": {
                    "userId": "user_id",
                    "movieId": "item_id",
                    "rating": "interaction"
                },
                "reasoning": "Based on the context and columns, this appears to be...",
                "additional_features": ["timestamp", "genre"]
            }
        """
        try:
            # Construct the prompt
            prompt = cls._build_analysis_prompt(columns, context, sample_data)
            
            # Call Ollama API
            response = await cls._call_ollama(prompt)
            
            # Parse the response
            analysis = cls._parse_llm_response(response)
            
            logger.info(f"LLM Analysis: System={analysis.get('system_type')}, Confidence={analysis.get('confidence')}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {str(e)}")
            # Fallback to basic heuristics
            return cls._fallback_analysis(columns, context)
    
    @classmethod
    def _build_analysis_prompt(
        cls,
        columns: List[str],
        context: str,
        sample_data: Optional[Dict[str, List[Any]]] = None
    ) -> str:
        """
        Build a detailed prompt for the LLM
        """
        prompt = f"""You are an expert ML system architect. Analyze the following dataset and determine the best ML system type and column mappings.

**User Context:** {context}

**Available Columns:** {', '.join(columns)}
"""
        
        if sample_data:
            prompt += "\n**Sample Data:**\n"
            for col, values in list(sample_data.items())[:5]:  # Show first 5 columns
                sample_str = ', '.join([str(v) for v in values[:3]])  # First 3 values
                prompt += f"  - {col}: {sample_str}...\n"
        
        prompt += """
**Supported ML Systems:**

RECOMMENDATION SYSTEMS:
1. **collaborative_filtering**: User-item collaborative filtering
   - Required: user_id, item_id, rating/interaction
   
2. **content_based_filtering**: Content-based recommendations
   - Required: item_id, item_features, user_id (optional)
   
3. **popularity_based**: Simple popularity recommendations
   - Required: item_id, view_count/rating
   
4. **hybrid_recommendation**: Hybrid recommendation approach
   - Required: user_id, item_id, rating, item_features

CHURN PREDICTION SYSTEMS:
5. **customer_churn**: General customer churn prediction
   - Required: customer_id, churn (0/1), tenure, features
   
6. **subscription_churn**: Subscription cancellation prediction
   - Required: customer_id, subscription_status, subscription_date, churn
   
7. **product_churn**: Product abandonment prediction
   - Required: customer_id, product_id, usage_frequency, churn
   
8. **revenue_churn**: Revenue loss prediction
   - Required: customer_id, revenue, churn, payment_history
   
9. **early_churn_detection**: Early churn signal detection
   - Required: customer_id, signup_date, early_signals, churn
   
10. **late_churn_analysis**: Long-term churn analysis
    - Required: customer_id, tenure, lifetime_value, churn

OTHER SYSTEMS:
11. **fraud_detection**: Fraudulent activity detection
    - Required: transaction_id, is_fraud (target), features
    
12. **sentiment_analysis**: Text sentiment classification
    - Required: text, sentiment (target)
    
13. **demand_forecasting**: Time-series demand forecasting
    - Required: date/timestamp, demand/sales, features

14. **price_optimization**: Dynamic pricing optimization
    - Required: product_id, price, demand/sales, features

**Your Task:**
Analyze the dataset and context, then respond ONLY with a valid JSON object (no markdown, no extra text).

The JSON must contain:
- system_type: One of the supported system types listed above
- confidence: A number between 0.0 and 1.0 indicating your confidence
- key_columns: Array of the most important column names from the dataset
- column_mappings: Object mapping original column names to standardized ML system column names
- reasoning: A clear explanation of why you chose this system type
- additional_features: Array of other useful columns that could enhance the model

**Rules:**
- system_type MUST be one of: collaborative_filtering, content_based_filtering, popularity_based, hybrid_recommendation, customer_churn, subscription_churn, product_churn, revenue_churn, early_churn_detection, late_churn_analysis, fraud_detection, sentiment_analysis, demand_forecasting, price_optimization
- confidence should be 0.0 to 1.0
- column_mappings should map original column names to standardized names
- Only include columns that exist in the dataset
- Be smart about recognizing variations (userId vs user_id vs UserID vs viewer_id)
- Choose the MOST SPECIFIC system type that matches the use case
"""
        
        return prompt
    
    @classmethod
    async def _call_ollama(cls, prompt: str) -> str:
        """
        Call the Ollama API
        """
        url = f"{cls.OLLAMA_BASE_URL}/api/generate"
        
        payload = {
            "model": cls.MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "format": "json"  # Request JSON format
        }
        
        async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
    
    @classmethod
    def _parse_llm_response(cls, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response into structured data
        """
        try:
            # Try to parse as JSON
            parsed = json.loads(response)
            
            # Validate required fields
            required_fields = ["system_type", "confidence", "key_columns", "column_mappings"]
            for field in required_fields:
                if field not in parsed:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate system_type
            valid_systems = [
                # Recommendation systems
                "collaborative_filtering", "content_based_filtering", "popularity_based", "hybrid_recommendation",
                # Churn systems
                "customer_churn", "subscription_churn", "product_churn", "revenue_churn", 
                "early_churn_detection", "late_churn_analysis",
                # Other systems
                "fraud_detection", "sentiment_analysis", "demand_forecasting", "price_optimization",
                # Legacy support
                "recommendation", "churn_prediction"
            ]
            if parsed["system_type"] not in valid_systems:
                logger.warning(f"Invalid system_type: {parsed['system_type']}, defaulting to collaborative_filtering")
                parsed["system_type"] = "collaborative_filtering"
            
            # Ensure confidence is between 0 and 1
            parsed["confidence"] = max(0.0, min(1.0, float(parsed.get("confidence", 0.5))))
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            logger.error(f"Response was: {response}")
            raise ValueError("LLM did not return valid JSON")
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            raise
    
    @classmethod
    def _fallback_analysis(cls, columns: List[str], context: str) -> Dict[str, Any]:
        """
        Fallback heuristic-based analysis if LLM fails
        """
        logger.warning("Using fallback heuristic analysis")
        
        context_lower = context.lower()
        columns_lower = [c.lower() for c in columns]
        column_mappings = {}  # Initialize column mappings
        
        # Simple keyword-based detection
        if any(word in context_lower for word in ["recommend", "recommendation", "suggest"]):
            # Determine specific recommendation type
            if any(word in context_lower for word in ["collaborative", "user-item"]):
                system_type = "collaborative_filtering"
            elif any(word in context_lower for word in ["content", "feature", "attribute"]):
                system_type = "content_based_filtering"
            elif any(word in context_lower for word in ["popular", "trending", "top"]):
                system_type = "popularity_based"
            elif any(word in context_lower for word in ["hybrid", "combined", "ensemble"]):
                system_type = "hybrid_recommendation"
            else:
                system_type = "collaborative_filtering"  # Default recommendation type
            
            # Look for user/item patterns
            user_col = next((c for c in columns if any(u in c.lower() for u in ["user", "customer", "member", "viewer"])), None)
            item_col = next((c for c in columns if any(i in c.lower() for i in ["item", "product", "movie", "book", "film"])), None)
            rating_col = next((c for c in columns if any(r in c.lower() for r in ["rating", "score", "interaction", "stars"])), None)
            
            key_columns = [c for c in [user_col, item_col, rating_col] if c]
            
        elif any(word in context_lower for word in ["churn", "retention", "leave", "cancel"]):
            # Determine specific churn type
            if any(word in context_lower for word in ["subscription", "subscribe"]):
                system_type = "subscription_churn"
            elif any(word in context_lower for word in ["product", "usage"]):
                system_type = "product_churn"
            elif any(word in context_lower for word in ["revenue", "money", "payment"]):
                system_type = "revenue_churn"
            elif any(word in context_lower for word in ["early", "new", "recent"]):
                system_type = "early_churn_detection"
            elif any(word in context_lower for word in ["late", "long-term", "lifetime"]):
                system_type = "late_churn_analysis"
            else:
                system_type = "customer_churn"  # Default churn type
            
            customer_col = next((c for c in columns if any(u in c.lower() for u in ["customer", "user", "id", "account"])), None)
            churn_col = next((c for c in columns if any(ch in c.lower() for ch in ["churn", "churned", "left", "cancel", "status"])), None)
            
            key_columns = [c for c in [customer_col, churn_col] if c]
            
            # Generate column mappings for churn systems
            if customer_col and "customer_id" not in [c.lower() for c in columns]:
                # Map customer column to customer_id
                column_mappings[customer_col] = "customer_id"
            if churn_col and churn_col.lower() not in ["churn", "customer_id"]:
                # Map churned/churn_status/etc to churn
                column_mappings[churn_col] = "churn"
            
        elif any(word in context_lower for word in ["fraud", "anomaly", "suspicious"]):
            system_type = "fraud_detection"
            key_columns = [c for c in columns if any(k in c.lower() for k in ["transaction", "fraud", "id"])]
            
        elif any(word in context_lower for word in ["sentiment", "opinion", "review", "text"]):
            system_type = "sentiment_analysis"
            key_columns = [c for c in columns if any(k in c.lower() for k in ["text", "review", "comment", "sentiment"])]
            
        elif any(word in context_lower for word in ["forecast", "predict", "demand", "sales"]):
            system_type = "demand_forecasting"
            key_columns = [c for c in columns if any(k in c.lower() for k in ["date", "time", "sales", "demand"])]
            
        elif any(word in context_lower for word in ["price", "pricing", "cost"]):
            system_type = "price_optimization"
            key_columns = [c for c in columns if any(k in c.lower() for k in ["price", "product", "demand", "sales"])]
            
        else:
            # Default to recommendation
            system_type = "recommendation"
            key_columns = columns[:3]  # Just take first 3 columns
        
        return {
            "system_type": system_type,
            "confidence": 0.5,  # Low confidence for fallback
            "key_columns": key_columns,
            "column_mappings": column_mappings,
            "reasoning": "Fallback heuristic analysis based on keywords",
            "additional_features": []
        }
    
    @classmethod
    async def validate_column_mapping(
        cls,
        system_type: str,
        column_mappings: Dict[str, str],
        available_columns: List[str]
    ) -> Dict[str, Any]:
        """
        Validate if the column mappings are sufficient for the chosen system type
        
        Returns:
            {
                "is_valid": True/False,
                "missing_columns": [],
                "warnings": [],
                "suggestions": []
            }
        """
        # Define required columns for each system
        system_requirements = {
            # Recommendation systems
            "collaborative_filtering": ["user_id", "item_id", "rating"],
            "content_based_filtering": ["item_id", "item_features"],
            "popularity_based": ["item_id", "view_count"],
            "hybrid_recommendation": ["user_id", "item_id", "rating"],
            # Churn systems
            "customer_churn": ["customer_id", "churn"],
            "subscription_churn": ["customer_id", "subscription_status", "churn"],
            "product_churn": ["customer_id", "product_id", "churn"],
            "revenue_churn": ["customer_id", "revenue", "churn"],
            "early_churn_detection": ["customer_id", "signup_date", "churn"],
            "late_churn_analysis": ["customer_id", "tenure", "churn"],
            # Other systems
            "fraud_detection": ["transaction_id", "is_fraud"],
            "sentiment_analysis": ["text", "sentiment"],
            "demand_forecasting": ["timestamp", "target"],
            "price_optimization": ["product_id", "price", "demand"],
            # Legacy support
            "recommendation": ["user_id", "item_id", "interaction"],
            "churn_prediction": ["customer_id", "churn"]
        }
        
        required = system_requirements.get(system_type, [])
        mapped_values = set(column_mappings.values())
        
        missing = [col for col in required if col not in mapped_values]
        
        return {
            "is_valid": len(missing) == 0,
            "missing_columns": missing,
            "warnings": [f"Missing required column: {col}" for col in missing],
            "suggestions": [f"Map one of your columns to '{col}'" for col in missing]
        }

