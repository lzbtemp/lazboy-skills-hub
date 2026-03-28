# Model Card Template

Based on [Google's Model Cards for Model Reporting](https://arxiv.org/abs/1810.03993) framework. Complete each section before deploying a model to production.

---

## 1. Model Details

### Basic Information

| Field | Value |
|-------|-------|
| **Model Name** | _[e.g., Customer Churn Predictor v2.1]_ |
| **Model Version** | _[Semantic version, e.g., 2.1.0]_ |
| **Model Type** | _[Classification / Regression / Ranking / Generative / etc.]_ |
| **Architecture** | _[e.g., XGBoost, BERT-base, ResNet-50, Logistic Regression]_ |
| **Framework** | _[e.g., PyTorch 2.1, TensorFlow 2.15, scikit-learn 1.4]_ |
| **Owner** | _[Team or individual responsible]_ |
| **Contact** | _[Email or Slack channel]_ |
| **Date Created** | _[YYYY-MM-DD]_ |
| **Last Updated** | _[YYYY-MM-DD]_ |
| **License** | _[e.g., Apache 2.0, Proprietary]_ |

### Architecture Details

- **Input format**: _[Describe expected input shape, data types, and preprocessing requirements]_
- **Output format**: _[Describe output shape, e.g., probability scores between 0 and 1]_
- **Number of parameters**: _[e.g., 110M for BERT-base]_
- **Model size on disk**: _[e.g., 438 MB]_
- **Inference latency**: _[e.g., p50: 12ms, p99: 45ms on GPU]_

### Training Data

| Attribute | Details |
|-----------|---------|
| **Dataset name** | _[Name and version]_ |
| **Dataset size** | _[Number of samples, e.g., 1.2M training, 150K validation, 150K test]_ |
| **Date range** | _[Temporal coverage, e.g., 2022-01-01 to 2024-12-31]_ |
| **Data sources** | _[Where the data originates]_ |
| **Sampling strategy** | _[How training data was sampled from the population]_ |
| **Label distribution** | _[Class balance, e.g., 85% negative / 15% positive]_ |
| **Geographic coverage** | _[e.g., US-only, Global, EU + UK]_ |
| **Languages** | _[If applicable, e.g., English only]_ |

**Preprocessing pipeline**:
1. _[Step 1: e.g., Remove records with >50% missing features]_
2. _[Step 2: e.g., Normalize numerical features using StandardScaler]_
3. _[Step 3: e.g., Encode categorical features using target encoding]_
4. _[Step 4: e.g., Apply SMOTE for class balancing]_

**Feature summary** (list top features or attach feature documentation):

| Feature Name | Type | Description | Missing Rate |
|-------------|------|-------------|--------------|
| _feature_1_ | Numerical | _Description_ | _0.5%_ |
| _feature_2_ | Categorical | _Description_ | _2.1%_ |

### Intended Use

- **Primary use case**: _[What the model is designed to do]_
- **Target users**: _[Who should use this model]_
- **Deployment context**: _[Where and how the model will be deployed]_
- **Decision type**: _[Fully automated / Human-in-the-loop / Advisory only]_

### Out-of-Scope Uses

- _[Use case 1 that the model should NOT be used for]_
- _[Use case 2 that the model should NOT be used for]_
- _[Any populations or contexts where the model has not been validated]_

---

## 2. Performance Metrics

### Primary Metrics

Report metrics on the **held-out test set** unless otherwise noted. Include confidence intervals where possible.

#### Classification Metrics

| Metric | Value | 95% CI | Baseline |
|--------|-------|--------|----------|
| **Accuracy** | _[e.g., 0.923]_ | _[0.918, 0.928]_ | _[0.850]_ |
| **Precision** | _[e.g., 0.891]_ | _[0.882, 0.900]_ | _[—]_ |
| **Recall** | _[e.g., 0.867]_ | _[0.855, 0.879]_ | _[—]_ |
| **F1 Score** | _[e.g., 0.879]_ | _[0.869, 0.889]_ | _[—]_ |
| **AUC-ROC** | _[e.g., 0.961]_ | _[0.956, 0.966]_ | _[—]_ |
| **AUC-PR** | _[e.g., 0.884]_ | _[0.872, 0.896]_ | _[—]_ |
| **Log Loss** | _[e.g., 0.187]_ | _[—]_ | _[—]_ |

#### Confusion Matrix

|  | Predicted Negative | Predicted Positive |
|--|-------------------|--------------------|
| **Actual Negative** | TN = _[value]_ | FP = _[value]_ |
| **Actual Positive** | FN = _[value]_ | TP = _[value]_ |

#### Regression Metrics (if applicable)

| Metric | Value | Baseline |
|--------|-------|----------|
| **MSE** | _[value]_ | _[value]_ |
| **RMSE** | _[value]_ | _[value]_ |
| **MAE** | _[value]_ | _[value]_ |
| **R-squared** | _[value]_ | _[value]_ |
| **MAPE** | _[value]_ | _[value]_ |

### Performance by Subgroup

Break down performance across important segments to detect disparities.

| Subgroup | N | Accuracy | Precision | Recall | F1 | AUC |
|----------|---|----------|-----------|--------|-----|-----|
| _Group A_ | _[n]_ | _[val]_ | _[val]_ | _[val]_ | _[val]_ | _[val]_ |
| _Group B_ | _[n]_ | _[val]_ | _[val]_ | _[val]_ | _[val]_ | _[val]_ |
| _Group C_ | _[n]_ | _[val]_ | _[val]_ | _[val]_ | _[val]_ | _[val]_ |

### Threshold Analysis

| Threshold | Precision | Recall | F1 | FPR |
|-----------|-----------|--------|-----|-----|
| 0.3 | _[val]_ | _[val]_ | _[val]_ | _[val]_ |
| 0.5 | _[val]_ | _[val]_ | _[val]_ | _[val]_ |
| 0.7 | _[val]_ | _[val]_ | _[val]_ | _[val]_ |
| 0.9 | _[val]_ | _[val]_ | _[val]_ | _[val]_ |

### Cross-Validation Results

| Fold | Accuracy | F1 | AUC |
|------|----------|----|-----|
| 1 | _[val]_ | _[val]_ | _[val]_ |
| 2 | _[val]_ | _[val]_ | _[val]_ |
| 3 | _[val]_ | _[val]_ | _[val]_ |
| 4 | _[val]_ | _[val]_ | _[val]_ |
| 5 | _[val]_ | _[val]_ | _[val]_ |
| **Mean +/- Std** | _[val]_ | _[val]_ | _[val]_ |

---

## 3. Ethical Considerations

### Potential Harms

- **Allocation harm**: _[Could the model unfairly allocate resources or opportunities?]_
- **Quality-of-service harm**: _[Could the model perform worse for certain groups?]_
- **Stereotyping harm**: _[Could the model reinforce negative stereotypes?]_
- **Denigration harm**: _[Could the model be derogatory toward certain groups?]_
- **Over/under-representation**: _[Are certain groups over- or under-represented in training data?]_

### Sensitive Features

List any features that are protected attributes or proxies for protected attributes.

| Feature | Sensitivity | Mitigation |
|---------|------------|------------|
| _[e.g., zip_code]_ | _[Proxy for race/income]_ | _[Removed / Monitored / Fairness constraint applied]_ |

### Human Oversight

- **Review process**: _[Describe human review of model outputs]_
- **Appeal mechanism**: _[How can affected individuals contest a decision?]_
- **Escalation path**: _[Who is notified when issues are detected?]_

---

## 4. Bias Analysis

### Methodology

- **Fairness definition used**: _[e.g., Demographic parity, Equalized odds, Calibration]_
- **Protected attributes evaluated**: _[e.g., Gender, Race, Age group]_
- **Evaluation framework**: _[e.g., Fairlearn, AIF360, custom]_

### Disparate Impact Analysis

The disparate impact ratio is the selection rate for the unprivileged group divided by the selection rate for the privileged group. A ratio below 0.8 (the "four-fifths rule") indicates potential adverse impact.

| Group Comparison | Selection Rate (Privileged) | Selection Rate (Unprivileged) | Disparate Impact Ratio | Pass? |
|-----------------|---------------------------|------------------------------|----------------------|-------|
| _[e.g., Male vs Female]_ | _[val]_ | _[val]_ | _[val]_ | _[Yes/No]_ |

### Equalized Odds

| Group | True Positive Rate | False Positive Rate | TPR Difference | FPR Difference |
|-------|-------------------|--------------------:|----------------|----------------|
| _Group A_ | _[val]_ | _[val]_ | — | — |
| _Group B_ | _[val]_ | _[val]_ | _[val]_ | _[val]_ |

### Calibration Across Groups

| Group | Predicted Positive Rate | Actual Positive Rate | Calibration Error |
|-------|------------------------|---------------------|-------------------|
| _Group A_ | _[val]_ | _[val]_ | _[val]_ |
| _Group B_ | _[val]_ | _[val]_ | _[val]_ |

### Bias Mitigation Steps Taken

1. _[e.g., Resampled training data to balance representation]_
2. _[e.g., Applied fairness constraints during training]_
3. _[e.g., Post-hoc threshold adjustment per group]_

---

## 5. Limitations

### Known Limitations

- _[Limitation 1: e.g., Model has not been validated on data from outside the US]_
- _[Limitation 2: e.g., Performance degrades when feature X has >30% missing values]_
- _[Limitation 3: e.g., Model assumes stationary distribution; needs retraining quarterly]_

### Failure Modes

| Scenario | Expected Behavior | Actual Behavior | Severity |
|----------|-------------------|-----------------|----------|
| _[e.g., All features missing]_ | _[Graceful fallback]_ | _[Returns NaN]_ | _[High]_ |
| _[e.g., Extreme input values]_ | _[Clipped prediction]_ | _[Unbounded output]_ | _[Medium]_ |

### Data Drift Sensitivity

- **Features most sensitive to drift**: _[List features]_
- **Expected retraining frequency**: _[e.g., Monthly, Quarterly]_
- **Staleness threshold**: _[When should the model be considered stale?]_

---

## 6. Deployment Requirements

### Infrastructure

| Requirement | Specification |
|-------------|---------------|
| **Compute** | _[e.g., 1x NVIDIA T4 GPU or 4 CPU cores]_ |
| **Memory** | _[e.g., 8 GB RAM minimum]_ |
| **Storage** | _[e.g., 2 GB for model artifacts]_ |
| **Runtime** | _[e.g., Python 3.11, ONNX Runtime 1.17]_ |
| **Container** | _[e.g., Docker image tag]_ |

### Dependencies

```
# Key dependencies with pinned versions
[framework]==x.y.z
[library_1]==x.y.z
[library_2]==x.y.z
```

### API Contract

- **Endpoint**: _[e.g., POST /v2/predictions]_
- **Request schema**: _[Link or inline JSON schema]_
- **Response schema**: _[Link or inline JSON schema]_
- **Rate limits**: _[e.g., 1000 req/s]_
- **SLA**: _[e.g., p99 < 100ms, 99.9% uptime]_

### Rollout Plan

- [ ] Shadow mode deployment (log predictions without serving)
- [ ] A/B test with _[X]_% traffic
- [ ] Gradual rollout: _[X]_% -> _[Y]_% -> 100%
- [ ] Rollback criteria: _[Define when to rollback]_

---

## 7. Monitoring Recommendations

### Model Performance Monitoring

| Metric | Frequency | Alert Threshold | Action |
|--------|-----------|----------------|--------|
| **Accuracy** | Daily | < _[threshold]_ | Trigger retraining pipeline |
| **AUC-ROC** | Daily | < _[threshold]_ | Page on-call engineer |
| **Prediction latency (p99)** | Real-time | > _[threshold]_ ms | Scale infrastructure |
| **Error rate** | Real-time | > _[threshold]_% | Trigger circuit breaker |

### Data Quality Monitoring

| Check | Frequency | Description |
|-------|-----------|-------------|
| **Feature drift** | Hourly | PSI or KS test on input features vs. training distribution |
| **Label drift** | Daily | Compare predicted label distribution to expected baseline |
| **Missing value rate** | Real-time | Alert if missing rate exceeds training-time levels |
| **Schema validation** | Real-time | Reject requests with unexpected features or types |
| **Data volume** | Hourly | Alert on significant drops in prediction volume |

### Fairness Monitoring

- **Frequency**: _[e.g., Weekly]_
- **Metrics tracked**: _[Disparate impact ratio, equalized odds by group]_
- **Alert threshold**: _[e.g., Disparate impact ratio < 0.8]_
- **Dashboard**: _[Link to monitoring dashboard]_

### Incident Response

1. **Detection**: Automated alert fires based on thresholds above
2. **Triage**: On-call engineer assesses severity and scope
3. **Mitigation**: Roll back to previous model version if needed
4. **Root cause**: Investigate data pipeline, feature drift, or upstream changes
5. **Resolution**: Retrain, patch, or update monitoring thresholds
6. **Post-mortem**: Document findings and update this model card

---

## Appendix

### Changelog

| Date | Version | Changes |
|------|---------|---------|
| _[YYYY-MM-DD]_ | _[x.y.z]_ | _[Description of changes]_ |

### References

- _[Link to training notebook or pipeline]_
- _[Link to dataset documentation]_
- _[Link to related research papers]_
- _[Link to monitoring dashboard]_

### Reviewers

| Reviewer | Role | Date | Status |
|----------|------|------|--------|
| _[Name]_ | _[ML Engineer]_ | _[Date]_ | _[Approved/Pending]_ |
| _[Name]_ | _[Ethics Review]_ | _[Date]_ | _[Approved/Pending]_ |
| _[Name]_ | _[Domain Expert]_ | _[Date]_ | _[Approved/Pending]_ |
