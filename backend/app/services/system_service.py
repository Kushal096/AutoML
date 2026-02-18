from app.models import System
import logging

logger = logging.getLogger(__name__)


async def seed_systems():
    """
    Seed the database with predefined system types
    """
    systems_data = [
        # General Categories
        {
            "name": "Recommendation",
            "description": "Machine learning systems for product/content recommendation",
            "default_pipeline": {
                "steps": ["data_preprocessing", "feature_engineering", "model_training", "evaluation"],
                "algorithms": ["collaborative_filtering", "content_based", "matrix_factorization"],
                "metrics": ["precision", "recall", "ndcg"]
            }
        },
        {
            "name": "Churn Prediction",
            "description": "Systems for predicting customer churn and retention",
            "default_pipeline": {
                "steps": ["data_preprocessing", "feature_engineering", "model_training", "evaluation"],
                "algorithms": ["logistic_regression", "random_forest", "xgboost", "neural_networks"],
                "metrics": ["accuracy", "precision", "recall", "f1_score", "auc_roc"]
            }
        },
        {
            "name": "Fraud Detection",
            "description": "Machine learning systems for detecting fraudulent activities",
            "default_pipeline": {
                "steps": ["data_preprocessing", "anomaly_detection", "model_training", "evaluation"],
                "algorithms": ["isolation_forest", "one_class_svm", "autoencoder", "ensemble_methods"],
                "metrics": ["precision", "recall", "f1_score", "false_positive_rate"]
            }
        },
        {
            "name": "Price Optimization",
            "description": "Systems for dynamic pricing and price optimization",
            "default_pipeline": {
                "steps": ["market_analysis", "feature_engineering", "model_training", "evaluation"],
                "algorithms": ["linear_regression", "gradient_boosting", "reinforcement_learning"],
                "metrics": ["mape", "rmse", "profit_margin"]
            }
        },
        {
            "name": "Sentiment Analysis",
            "description": "Natural language processing for sentiment classification",
            "default_pipeline": {
                "steps": ["text_preprocessing", "feature_extraction", "model_training", "evaluation"],
                "algorithms": ["naive_bayes", "svm", "lstm", "transformer_models"],
                "metrics": ["accuracy", "precision", "recall", "f1_score"]
            }
        },
        {
            "name": "Demand Forecasting",
            "description": "Time series forecasting for demand prediction",
            "default_pipeline": {
                "steps": ["data_preprocessing", "time_series_analysis", "model_training", "evaluation"],
                "algorithms": ["arima", "lstm", "prophet", "seasonal_decomposition"],
                "metrics": ["mae", "mape", "rmse", "seasonal_error"]
            }
        },
        
        # Recommendation Sub-types
        {
            "name": "Collaborative Filtering",
            "description": "User-item collaborative filtering for recommendations",
            "default_pipeline": {
                "steps": ["data_preprocessing", "similarity_computation", "recommendation_generation"],
                "algorithms": ["user_based_cf", "item_based_cf", "matrix_factorization"],
                "metrics": ["precision", "recall", "ndcg", "map"]
            }
        },
        {
            "name": "Content-Based Filtering",
            "description": "Content-based recommendation using item features",
            "default_pipeline": {
                "steps": ["feature_extraction", "similarity_computation", "recommendation_generation"],
                "algorithms": ["tf_idf", "cosine_similarity", "neural_embeddings"],
                "metrics": ["precision", "recall", "diversity"]
            }
        },
        {
            "name": "Popularity-Based",
            "description": "Simple popularity-based recommendations",
            "default_pipeline": {
                "steps": ["aggregation", "ranking", "recommendation_generation"],
                "algorithms": ["view_count", "rating_average", "trending"],
                "metrics": ["coverage", "popularity_bias"]
            }
        },
        {
            "name": "Hybrid Recommendation",
            "description": "Hybrid approach combining multiple recommendation techniques",
            "default_pipeline": {
                "steps": ["multi_model_training", "ensemble", "recommendation_generation"],
                "algorithms": ["weighted_hybrid", "switching_hybrid", "cascade_hybrid"],
                "metrics": ["precision", "recall", "ndcg", "diversity"]
            }
        },
        
        # Churn Sub-types
        {
            "name": "Customer Churn",
            "description": "Predict customer churn and retention",
            "default_pipeline": {
                "steps": ["data_preprocessing", "feature_engineering", "model_training", "evaluation"],
                "algorithms": ["logistic_regression", "random_forest", "xgboost"],
                "metrics": ["accuracy", "precision", "recall", "f1_score", "auc_roc"]
            }
        },
        {
            "name": "Subscription Churn",
            "description": "Predict subscription cancellations",
            "default_pipeline": {
                "steps": ["data_preprocessing", "feature_engineering", "model_training", "evaluation"],
                "algorithms": ["survival_analysis", "random_forest", "gradient_boosting"],
                "metrics": ["accuracy", "precision", "recall", "churn_rate"]
            }
        },
        {
            "name": "Product Churn",
            "description": "Predict product abandonment",
            "default_pipeline": {
                "steps": ["usage_analysis", "feature_engineering", "model_training", "evaluation"],
                "algorithms": ["logistic_regression", "decision_trees", "neural_networks"],
                "metrics": ["accuracy", "precision", "recall", "retention_rate"]
            }
        },
        {
            "name": "Revenue Churn",
            "description": "Predict revenue loss from customer churn",
            "default_pipeline": {
                "steps": ["revenue_analysis", "feature_engineering", "model_training", "evaluation"],
                "algorithms": ["regression", "gradient_boosting", "ensemble_methods"],
                "metrics": ["mae", "rmse", "revenue_retention"]
            }
        },
        {
            "name": "Early Churn Detection",
            "description": "Detect churn signals early in customer lifecycle",
            "default_pipeline": {
                "steps": ["behavioral_analysis", "feature_engineering", "model_training", "evaluation"],
                "algorithms": ["time_series", "anomaly_detection", "classification"],
                "metrics": ["early_detection_rate", "precision", "recall"]
            }
        },
        {
            "name": "Late Churn Analysis",
            "description": "Analyze and predict long-term customer churn",
            "default_pipeline": {
                "steps": ["historical_analysis", "feature_engineering", "model_training", "evaluation"],
                "algorithms": ["survival_analysis", "cox_regression", "random_forest"],
                "metrics": ["accuracy", "time_to_churn", "retention_curve"]
            }
        }
    ]
    
    try:
        for system_data in systems_data:
            # Check if system already exists
            existing_system = await System.find_one(System.name == system_data["name"])
            
            if not existing_system:
                system = System(**system_data)
                await system.insert()
                logger.info(f"Created system: {system_data['name']}")
            else:
                logger.info(f"System already exists: {system_data['name']}")
        
        logger.info("System seeding completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to seed systems: {str(e)}")
        raise


async def get_system_by_name(name: str) -> System:
    """
    Get a system by name
    """
    return await System.find_one(System.name == name)