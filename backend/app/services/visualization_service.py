"""Service for generating visualizations and graphs for ML models"""

import io
import base64
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    confusion_matrix, roc_curve, auc, precision_recall_curve,
    classification_report
)

from app.models import Model, Project, Dataset

logger = logging.getLogger(__name__)

# Set style for better-looking plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 10


class VisualizationService:
    """Service for creating ML model visualizations"""
    
    def __init__(self):
        self.viz_storage_path = Path("visualizations")
        self.viz_storage_path.mkdir(exist_ok=True)
    
    def plot_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string"""
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        return f"data:image/png;base64,{image_base64}"
    
    async def generate_confusion_matrix_plot(
        self,
        confusion_mat: List[List[int]],
        labels: Optional[List[str]] = None
    ) -> str:
        """Generate confusion matrix heatmap"""
        try:
            fig, ax = plt.subplots(figsize=(8, 6))
            
            cm_array = np.array(confusion_mat)
            
            # Create heatmap
            sns.heatmap(
                cm_array,
                annot=True,
                fmt='d',
                cmap='Blues',
                xticklabels=labels or range(len(cm_array)),
                yticklabels=labels or range(len(cm_array)),
                ax=ax,
                cbar_kws={'label': 'Count'}
            )
            
            ax.set_xlabel('Predicted Label', fontsize=12, fontweight='bold')
            ax.set_ylabel('True Label', fontsize=12, fontweight='bold')
            ax.set_title('Confusion Matrix', fontsize=14, fontweight='bold', pad=20)
            
            plt.tight_layout()
            return self.plot_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to generate confusion matrix plot: {str(e)}")
            return ""
    
    async def generate_roc_curve_plot(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        n_classes: int = 2
    ) -> str:
        """Generate ROC curve plot"""
        try:
            fig, ax = plt.subplots(figsize=(8, 6))
            
            if n_classes == 2:
                # Binary classification
                fpr, tpr, _ = roc_curve(y_true, y_pred_proba)
                roc_auc = auc(fpr, tpr)
                
                ax.plot(fpr, tpr, color='darkorange', lw=2,
                       label=f'ROC curve (AUC = {roc_auc:.3f})')
                ax.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--',
                       label='Random Classifier')
                
            else:
                # Multi-class ROC curves
                for i in range(n_classes):
                    fpr, tpr, _ = roc_curve(y_true == i, y_pred_proba[:, i])
                    roc_auc = auc(fpr, tpr)
                    ax.plot(fpr, tpr, lw=2, label=f'Class {i} (AUC = {roc_auc:.3f})')
                
                ax.plot([0, 1], [0, 1], color='black', lw=2, linestyle='--',
                       label='Random Classifier')
            
            ax.set_xlim([0.0, 1.0])
            ax.set_ylim([0.0, 1.05])
            ax.set_xlabel('False Positive Rate', fontsize=12, fontweight='bold')
            ax.set_ylabel('True Positive Rate', fontsize=12, fontweight='bold')
            ax.set_title('Receiver Operating Characteristic (ROC) Curve',
                        fontsize=14, fontweight='bold', pad=20)
            ax.legend(loc="lower right")
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return self.plot_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to generate ROC curve plot: {str(e)}")
            return ""
    
    async def generate_precision_recall_curve_plot(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray
    ) -> str:
        """Generate precision-recall curve plot"""
        try:
            fig, ax = plt.subplots(figsize=(8, 6))
            
            precision, recall, _ = precision_recall_curve(y_true, y_pred_proba)
            pr_auc = auc(recall, precision)
            
            ax.plot(recall, precision, color='purple', lw=2,
                   label=f'PR curve (AUC = {pr_auc:.3f})')
            ax.fill_between(recall, precision, alpha=0.2, color='purple')
            
            ax.set_xlim([0.0, 1.0])
            ax.set_ylim([0.0, 1.05])
            ax.set_xlabel('Recall', fontsize=12, fontweight='bold')
            ax.set_ylabel('Precision', fontsize=12, fontweight='bold')
            ax.set_title('Precision-Recall Curve', fontsize=14, fontweight='bold', pad=20)
            ax.legend(loc="lower left")
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return self.plot_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to generate PR curve plot: {str(e)}")
            return ""
    
    async def generate_feature_importance_plot(
        self,
        feature_names: List[str],
        importances: np.ndarray,
        top_n: int = 15
    ) -> str:
        """Generate feature importance bar plot"""
        try:
            # Sort features by importance
            indices = np.argsort(importances)[::-1][:top_n]
            top_features = [feature_names[i] for i in indices]
            top_importances = importances[indices]
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(top_features)))
            bars = ax.barh(range(len(top_features)), top_importances, color=colors)
            
            ax.set_yticks(range(len(top_features)))
            ax.set_yticklabels(top_features)
            ax.set_xlabel('Importance Score', fontsize=12, fontweight='bold')
            ax.set_ylabel('Features', fontsize=12, fontweight='bold')
            ax.set_title(f'Top {top_n} Feature Importances',
                        fontsize=14, fontweight='bold', pad=20)
            ax.invert_yaxis()
            ax.grid(True, alpha=0.3, axis='x')
            
            # Add value labels on bars
            for i, (bar, val) in enumerate(zip(bars, top_importances)):
                ax.text(val, i, f' {val:.4f}', va='center', fontsize=9)
            
            plt.tight_layout()
            return self.plot_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to generate feature importance plot: {str(e)}")
            return ""
    
    async def generate_metrics_history_plot(
        self,
        models_data: List[Dict[str, Any]],
        metric_name: str = 'accuracy'
    ) -> str:
        """Generate line plot showing metric evolution across model versions"""
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            versions = [m['version'] for m in models_data]
            metrics = [m['metrics'].get(metric_name, 0) for m in models_data]
            
            ax.plot(versions, metrics, marker='o', linewidth=2, markersize=8,
                   color='#2E86AB', label=metric_name.replace('_', ' ').title())
            ax.fill_between(versions, metrics, alpha=0.3, color='#2E86AB')
            
            # Add value labels
            for v, m in zip(versions, metrics):
                ax.annotate(f'{m:.3f}', (v, m), textcoords="offset points",
                          xytext=(0, 10), ha='center', fontsize=9)
            
            ax.set_xlabel('Model Version', fontsize=12, fontweight='bold')
            ax.set_ylabel(metric_name.replace('_', ' ').title(),
                         fontsize=12, fontweight='bold')
            ax.set_title(f'{metric_name.replace("_", " ").title()} Across Model Versions',
                        fontsize=14, fontweight='bold', pad=20)
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return self.plot_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to generate metrics history plot: {str(e)}")
            return ""
    
    async def generate_drift_history_plot(
        self,
        drift_data: Dict[str, List[Dict[str, Any]]],
        threshold: float = 0.1
    ) -> str:
        """Generate drift score timeline plot"""
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            for feature_name, history in drift_data.items():
                if not history:
                    continue
                
                timestamps = [h['detected_at'] for h in history]
                scores = [h['drift_score'] for h in history]
                
                ax.plot(timestamps, scores, marker='o', label=feature_name,
                       linewidth=2, markersize=6, alpha=0.7)
            
            # Add threshold line
            if drift_data:
                ax.axhline(y=threshold, color='red', linestyle='--', linewidth=2,
                          label=f'Drift Threshold ({threshold})')
            
            ax.set_xlabel('Time', fontsize=12, fontweight='bold')
            ax.set_ylabel('Drift Score', fontsize=12, fontweight='bold')
            ax.set_title('Data Drift Over Time', fontsize=14, fontweight='bold', pad=20)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            return self.plot_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to generate drift history plot: {str(e)}")
            return ""
    
    async def generate_model_comparison_plot(
        self,
        models_data: List[Dict[str, Any]],
        metrics: List[str] = ['accuracy', 'f1_score', 'precision', 'recall']
    ) -> str:
        """Generate radar/spider plot comparing multiple metrics across models"""
        try:
            fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(projection='polar'))
            
            # Prepare data
            available_metrics = []
            for metric in metrics:
                if any(metric in m['metrics'] for m in models_data):
                    available_metrics.append(metric)
            
            if not available_metrics:
                return ""
            
            angles = np.linspace(0, 2 * np.pi, len(available_metrics), endpoint=False).tolist()
            angles += angles[:1]  # Complete the circle
            
            # Plot each model
            colors = plt.cm.Set2(np.linspace(0, 1, len(models_data)))
            
            for idx, model in enumerate(models_data[:5]):  # Limit to 5 models
                values = [model['metrics'].get(m, 0) for m in available_metrics]
                values += values[:1]  # Complete the circle
                
                ax.plot(angles, values, 'o-', linewidth=2, label=f'v{model["version"]}',
                       color=colors[idx])
                ax.fill(angles, values, alpha=0.15, color=colors[idx])
            
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels([m.replace('_', ' ').title() for m in available_metrics])
            ax.set_ylim(0, 1)
            ax.set_title('Model Performance Comparison',
                        fontsize=14, fontweight='bold', pad=20)
            ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
            ax.grid(True)
            
            plt.tight_layout()
            return self.plot_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to generate model comparison plot: {str(e)}")
            return ""
    
    async def generate_learning_curve_plot(
        self,
        train_sizes: np.ndarray,
        train_scores: np.ndarray,
        val_scores: np.ndarray
    ) -> str:
        """Generate learning curve plot"""
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            ax.plot(train_sizes, train_scores, 'o-', color='#2E86AB',
                   linewidth=2, markersize=6, label='Training Score')
            ax.plot(train_sizes, val_scores, 'o-', color='#A23B72',
                   linewidth=2, markersize=6, label='Validation Score')
            
            ax.fill_between(train_sizes, train_scores, alpha=0.2, color='#2E86AB')
            ax.fill_between(train_sizes, val_scores, alpha=0.2, color='#A23B72')
            
            ax.set_xlabel('Training Set Size', fontsize=12, fontweight='bold')
            ax.set_ylabel('Score', fontsize=12, fontweight='bold')
            ax.set_title('Learning Curve', fontsize=14, fontweight='bold', pad=20)
            ax.legend(loc='lower right')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return self.plot_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to generate learning curve plot: {str(e)}")
            return ""
    
    async def generate_class_distribution_plot(
        self,
        class_counts: Dict[str, int]
    ) -> str:
        """Generate class distribution pie/bar chart"""
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            labels = list(class_counts.keys())
            sizes = list(class_counts.values())
            colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
            
            # Pie chart
            ax1.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors,
                   startangle=90, textprops={'fontsize': 10})
            ax1.set_title('Class Distribution (Pie Chart)',
                         fontsize=12, fontweight='bold')
            
            # Bar chart
            bars = ax2.bar(labels, sizes, color=colors, edgecolor='black', linewidth=1.5)
            ax2.set_xlabel('Class', fontsize=12, fontweight='bold')
            ax2.set_ylabel('Count', fontsize=12, fontweight='bold')
            ax2.set_title('Class Distribution (Bar Chart)',
                         fontsize=12, fontweight='bold')
            ax2.grid(True, alpha=0.3, axis='y')
            
            # Add value labels on bars
            for bar, size in zip(bars, sizes):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(size)}', ha='center', va='bottom', fontsize=10)
            
            plt.tight_layout()
            return self.plot_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to generate class distribution plot: {str(e)}")
            return ""
    
    async def generate_pie_chart(
        self,
        data: Dict[str, int],
        title: str = "Distribution"
    ) -> str:
        """
        Generate a pie chart for categorical data distribution
        
        Args:
            data: Dictionary with labels and values
            title: Chart title
            
        Returns:
            Base64 encoded image string
        """
        try:
            fig, ax = plt.subplots(figsize=(10, 8))
            
            labels = list(data.keys())
            sizes = list(data.values())
            
            # Create color palette
            colors = plt.cm.Set3(range(len(labels)))
            
            # Create pie chart
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=labels,
                autopct='%1.1f%%',
                colors=colors,
                startangle=90,
                textprops={'fontsize': 12}
            )
            
            # Make percentage text bold
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.axis('equal')  # Equal aspect ratio ensures circular pie
            
            plt.tight_layout()
            return self.plot_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to generate pie chart: {str(e)}")
            return ""
    
    async def generate_bar_chart(
        self,
        data: Dict[str, int],
        title: str = "Bar Chart",
        xlabel: str = "Category",
        ylabel: str = "Count"
    ) -> str:
        """
        Generate a bar chart
        
        Args:
            data: Dictionary with labels and values
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            
        Returns:
            Base64 encoded image string
        """
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            labels = list(data.keys())
            values = list(data.values())
            
            # Create bar chart
            bars = ax.bar(labels, values, color='steelblue', alpha=0.8, edgecolor='navy')
            
            # Add value labels on top of bars
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width()/2.,
                    height,
                    f'{int(height)}',
                    ha='center',
                    va='bottom',
                    fontsize=12,
                    fontweight='bold'
                )
            
            ax.set_xlabel(xlabel, fontsize=12, fontweight='bold')
            ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            return self.plot_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to generate bar chart: {str(e)}")
            return ""
    
    async def generate_gauge_chart(
        self,
        value: float,
        title: str = "Score",
        max_value: float = 100
    ) -> str:
        """
        Generate a gauge/speedometer chart
        
        Args:
            value: Current value
            title: Chart title
            max_value: Maximum value for the gauge
            
        Returns:
            Base64 encoded image string
        """
        try:
            fig, ax = plt.subplots(figsize=(10, 6), subplot_kw={'projection': 'polar'})
            
            # Normalize value to 0-1 range
            normalized_value = value / max_value
            
            # Define color zones
            if normalized_value >= 0.8:
                color = '#2ecc71'  # Green
                status = 'Excellent'
            elif normalized_value >= 0.6:
                color = '#3498db'  # Blue
                status = 'Good'
            elif normalized_value >= 0.4:
                color = '#f39c12'  # Orange
                status = 'Fair'
            else:
                color = '#e74c3c'  # Red
                status = 'Needs Attention'
            
            # Create gauge
            theta = np.linspace(0, np.pi, 100)
            
            # Background arc
            ax.plot(theta, [1] * 100, color='lightgray', linewidth=20, alpha=0.3)
            
            # Value arc
            value_theta = theta[:int(normalized_value * 100)]
            ax.plot(value_theta, [1] * len(value_theta), color=color, linewidth=20)
            
            # Needle
            needle_angle = normalized_value * np.pi
            ax.plot([needle_angle, needle_angle], [0, 0.9], color='black', linewidth=3)
            ax.plot(needle_angle, 0.9, 'o', color='black', markersize=10)
            
            # Remove grid and labels
            ax.set_ylim(0, 1.2)
            ax.set_yticks([])
            ax.set_xticks([])
            ax.spines['polar'].set_visible(False)
            ax.grid(False)
            
            # Add title and value text
            ax.text(
                np.pi/2, 1.4, title,
                ha='center', va='center',
                fontsize=18, fontweight='bold'
            )
            ax.text(
                np.pi/2, 0.5, f'{value:.0f}/{max_value}',
                ha='center', va='center',
                fontsize=24, fontweight='bold',
                color=color
            )
            ax.text(
                np.pi/2, 0.3, status,
                ha='center', va='center',
                fontsize=14,
                color=color
            )
            
            plt.tight_layout()
            return self.plot_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to generate gauge chart: {str(e)}")
            return ""

