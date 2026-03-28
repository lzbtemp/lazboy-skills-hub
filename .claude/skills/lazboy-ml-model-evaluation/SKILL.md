---
name: lazboy-ml-model-evaluation
description: "Evaluate and validate machine learning models for La-Z-Boy business applications. Covers model metrics, A/B testing, bias detection, model monitoring, and documentation. Use when building, evaluating, or deploying ML models for demand forecasting, recommendation, or classification."
version: "1.0.0"
category: Data/AI
tags: [data, ai, ml, python, evaluation]
---

# La-Z-Boy ML Model Evaluation Skill

Standards for evaluating and deploying ML models at La-Z-Boy.

**Reference files — load when needed:**
- `references/model-card-template.md` — model documentation template
- `references/metrics-guide.md` — metrics selection guide by problem type

**Scripts — run when needed:**
- `scripts/evaluate_model.py` — generate evaluation report with metrics and visualizations
- `scripts/detect_bias.py` — check model predictions for demographic bias

---

## 1. La-Z-Boy ML Use Cases

| Use Case | Type | Key Metric |
|---|---|---|
| Demand forecasting | Regression | MAPE < 15% |
| Product recommendation | Ranking | NDCG@10 > 0.4 |
| Customer churn prediction | Classification | F1 > 0.75 |
| Image quality detection | Classification | Precision > 0.95 |
| Price optimization | Regression | MAE < $50 |

## 2. Evaluation Metrics by Problem Type

### Classification
```python
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score

def evaluate_classifier(y_true, y_pred, y_prob):
    print(classification_report(y_true, y_pred))
    print(f"AUC-ROC: {roc_auc_score(y_true, y_prob):.4f}")
    print(f"Confusion Matrix:\n{confusion_matrix(y_true, y_pred)}")
```

### Regression
```python
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np

def evaluate_regressor(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    print(f"MAE: {mae:.2f}, RMSE: {rmse:.2f}, MAPE: {mape:.1f}%")
```

## 3. Model Validation Checklist

- [ ] Train/test split is time-based (not random) for time series
- [ ] Cross-validation used (k=5 minimum)
- [ ] Model tested on holdout set from different time period
- [ ] Feature importance analyzed and documented
- [ ] Predictions sanity-checked against business rules
- [ ] Model compared against simple baseline

## 4. Bias Detection

```python
def check_bias(df, predictions, sensitive_col):
    """Check prediction fairness across demographic groups."""
    groups = df.groupby(sensitive_col)
    for name, group in groups:
        positive_rate = predictions[group.index].mean()
        print(f"{name}: {positive_rate:.3f} positive rate")
    # Flag if disparity > 20%
```

## 5. Model Card Template

Every deployed model must have a model card:

```markdown
# Model Card: [Model Name]

## Overview
- **Purpose**: What business problem does this solve?
- **Owner**: Team and individual responsible
- **Last trained**: Date
- **Version**: Semantic version

## Performance
- **Primary metric**: [metric] = [value]
- **Baseline comparison**: [% improvement over baseline]
- **Data used**: [description and date range]

## Limitations
- Known failure modes
- Data requirements
- Populations not represented in training data

## Monitoring
- Prediction drift threshold: [value]
- Retraining trigger: [condition]
```

## 6. Production Monitoring

Track these metrics post-deployment:
- **Prediction drift**: Compare distribution of predictions vs training
- **Data drift**: Monitor input feature distributions
- **Latency**: p95 inference time < 100ms
- **Error rate**: Failed predictions < 0.1%
