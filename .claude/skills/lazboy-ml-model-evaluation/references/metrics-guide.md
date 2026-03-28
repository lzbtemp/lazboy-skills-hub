# ML Metrics Reference Guide

A comprehensive reference for selecting and interpreting machine learning evaluation metrics.

---

## Table of Contents

1. [Classification Metrics](#1-classification-metrics)
2. [Regression Metrics](#2-regression-metrics)
3. [Ranking Metrics](#3-ranking-metrics)
4. [NLP Metrics](#4-nlp-metrics)
5. [Metric Selection Guide](#5-metric-selection-guide)
6. [Common Pitfalls](#6-common-pitfalls)

---

## 1. Classification Metrics

### Confusion Matrix

The foundation for most classification metrics. For binary classification:

```
                    Predicted
                 Neg       Pos
Actual  Neg  [ TN        FP  ]
        Pos  [ FN        TP  ]
```

- **True Positive (TP)**: Correctly predicted positive
- **True Negative (TN)**: Correctly predicted negative
- **False Positive (FP)**: Incorrectly predicted positive (Type I error)
- **False Negative (FN)**: Incorrectly predicted negative (Type II error)

For multiclass problems, the confusion matrix is NxN where N is the number of classes.

### Accuracy

```
Accuracy = (TP + TN) / (TP + TN + FP + FN)
```

- **Range**: 0 to 1
- **When to use**: Balanced classes, equal cost of errors
- **When to avoid**: Imbalanced datasets (see [Accuracy Paradox](#accuracy-paradox))
- **Example**: 950 correct out of 1000 predictions = 0.95 accuracy

### Precision (Positive Predictive Value)

```
Precision = TP / (TP + FP)
```

- **Range**: 0 to 1
- **Interpretation**: "Of all items predicted positive, how many are actually positive?"
- **When to use**: When false positives are costly (spam detection, fraud alerts)
- **Trade-off**: Higher precision often means lower recall

### Recall (Sensitivity, True Positive Rate)

```
Recall = TP / (TP + FN)
```

- **Range**: 0 to 1
- **Interpretation**: "Of all actual positive items, how many did we catch?"
- **When to use**: When false negatives are costly (disease screening, security threats)
- **Trade-off**: Higher recall often means lower precision

### Specificity (True Negative Rate)

```
Specificity = TN / (TN + FP)
```

- **Range**: 0 to 1
- **Interpretation**: "Of all actual negative items, how many did we correctly identify?"
- **When to use**: When false positive rate matters (diagnostic tests)

### F1 Score

```
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

- **Range**: 0 to 1
- **Interpretation**: Harmonic mean of precision and recall
- **When to use**: When you need a single metric balancing precision and recall
- **Variants**:
  - **Macro F1**: Average F1 across classes (treats all classes equally)
  - **Micro F1**: Calculate TP/FP/FN globally, then compute F1 (equivalent to accuracy for single-label)
  - **Weighted F1**: Weight each class's F1 by its support (sample count)

### F-beta Score

```
F_beta = (1 + beta^2) * (Precision * Recall) / (beta^2 * Precision + Recall)
```

- **beta < 1**: Weights precision higher (e.g., F0.5 for spam detection)
- **beta = 1**: Equal weight (standard F1)
- **beta > 1**: Weights recall higher (e.g., F2 for disease screening)

### AUC-ROC (Area Under the Receiver Operating Characteristic Curve)

The ROC curve plots True Positive Rate (Recall) vs. False Positive Rate at various classification thresholds.

- **Range**: 0 to 1 (0.5 = random, 1.0 = perfect)
- **Interpretation**: Probability that the model ranks a random positive example higher than a random negative example
- **When to use**: Comparing models, threshold-independent evaluation
- **When to avoid**: Highly imbalanced data (use AUC-PR instead)
- **Multiclass**: Use one-vs-rest or one-vs-one strategies

### AUC-PR (Area Under the Precision-Recall Curve)

The PR curve plots Precision vs. Recall at various thresholds.

- **Range**: 0 to 1 (baseline = proportion of positives)
- **When to use**: Imbalanced datasets where the positive class is rare
- **Advantage over AUC-ROC**: More informative when negatives vastly outnumber positives

### Cohen's Kappa

```
Kappa = (Observed Agreement - Expected Agreement) / (1 - Expected Agreement)
```

- **Range**: -1 to 1 (0 = agreement by chance, 1 = perfect agreement)
- **When to use**: Comparing against chance-level performance, inter-rater agreement
- **Interpretation guide**: < 0 = poor, 0-0.20 = slight, 0.21-0.40 = fair, 0.41-0.60 = moderate, 0.61-0.80 = substantial, 0.81-1.0 = near-perfect

### Matthews Correlation Coefficient (MCC)

```
MCC = (TP*TN - FP*FN) / sqrt((TP+FP)(TP+FN)(TN+FP)(TN+FN))
```

- **Range**: -1 to 1 (0 = random, 1 = perfect, -1 = inverse)
- **When to use**: Imbalanced classes; considered one of the most informative single metrics for binary classification
- **Advantage**: Uses all four confusion matrix quadrants

### Log Loss (Cross-Entropy Loss)

```
Log Loss = -(1/N) * SUM[ y*log(p) + (1-y)*log(1-p) ]
```

- **Range**: 0 to infinity (lower is better)
- **When to use**: When probability calibration matters (not just rank ordering)
- **Sensitivity**: Heavily penalizes confident wrong predictions

### Brier Score

```
Brier Score = (1/N) * SUM[ (predicted_probability - actual_outcome)^2 ]
```

- **Range**: 0 to 1 (lower is better)
- **When to use**: Assessing probability calibration

---

## 2. Regression Metrics

### Mean Squared Error (MSE)

```
MSE = (1/N) * SUM[ (y_actual - y_predicted)^2 ]
```

- **Range**: 0 to infinity (lower is better)
- **Units**: Squared units of the target variable
- **Properties**: Penalizes large errors heavily (quadratic), differentiable
- **When to use**: When large errors are particularly undesirable

### Root Mean Squared Error (RMSE)

```
RMSE = sqrt(MSE)
```

- **Range**: 0 to infinity (lower is better)
- **Units**: Same units as the target variable
- **When to use**: When you want an interpretable error metric in original units
- **Comparison**: More sensitive to outliers than MAE

### Mean Absolute Error (MAE)

```
MAE = (1/N) * SUM[ |y_actual - y_predicted| ]
```

- **Range**: 0 to infinity (lower is better)
- **Units**: Same units as the target variable
- **Properties**: Robust to outliers compared to MSE/RMSE
- **When to use**: When all errors should be weighted equally regardless of magnitude

### Mean Absolute Percentage Error (MAPE)

```
MAPE = (100/N) * SUM[ |y_actual - y_predicted| / |y_actual| ]
```

- **Range**: 0% to infinity (lower is better)
- **When to use**: When relative error matters more than absolute error
- **When to avoid**: When actual values are near zero (causes division explosion)

### Symmetric Mean Absolute Percentage Error (sMAPE)

```
sMAPE = (100/N) * SUM[ |y_actual - y_predicted| / ((|y_actual| + |y_predicted|) / 2) ]
```

- **Range**: 0% to 200%
- **Advantage over MAPE**: Handles zero actual values more gracefully

### R-squared (Coefficient of Determination)

```
R² = 1 - (SS_residual / SS_total)
   = 1 - SUM[(y - y_hat)^2] / SUM[(y - y_mean)^2]
```

- **Range**: -infinity to 1 (1 = perfect, 0 = predicts the mean, negative = worse than mean)
- **Interpretation**: Proportion of variance in the target explained by the model
- **When to use**: Comparing models, understanding explanatory power
- **Caution**: Can be misleadingly high with many features (use Adjusted R-squared)

### Adjusted R-squared

```
Adjusted R² = 1 - [(1-R²)(N-1) / (N-k-1)]
```

Where N = number of samples, k = number of features.

- **When to use**: Comparing models with different numbers of features
- **Advantage**: Penalizes adding features that don't improve the model

### Huber Loss

```
L_delta(a) = 0.5 * a^2                  if |a| <= delta
           = delta * (|a| - 0.5*delta)  if |a| > delta
```

- **When to use**: When you want a metric between MSE and MAE (robust to outliers but still differentiable)

---

## 3. Ranking Metrics

### Normalized Discounted Cumulative Gain (NDCG)

```
DCG@k  = SUM_i=1_to_k [ (2^rel_i - 1) / log2(i + 1) ]
IDCG@k = DCG of the ideal ranking
NDCG@k = DCG@k / IDCG@k
```

- **Range**: 0 to 1
- **When to use**: Search engines, recommendation systems with graded relevance
- **Properties**: Accounts for position (earlier results matter more), handles graded relevance

### Mean Reciprocal Rank (MRR)

```
MRR = (1/|Q|) * SUM[ 1 / rank_of_first_relevant_result ]
```

- **Range**: 0 to 1
- **When to use**: When only the first relevant result matters (navigational queries, QA)
- **Limitation**: Only considers the first relevant item

### Mean Average Precision (MAP)

```
AP = SUM_k [ Precision@k * rel(k) ] / (number of relevant documents)
MAP = mean of AP across all queries
```

- **Range**: 0 to 1
- **When to use**: Information retrieval, when all relevant documents matter
- **Properties**: Considers both precision and recall at every position

### Precision@k and Recall@k

```
Precision@k = (relevant items in top k) / k
Recall@k    = (relevant items in top k) / (total relevant items)
```

- **When to use**: Evaluating top-k recommendations or search results

### Hit Rate@k

```
Hit Rate@k = (queries with at least one relevant item in top k) / (total queries)
```

- **When to use**: Recommendation systems where any relevant result in top-k is a success

---

## 4. NLP Metrics

### BLEU (Bilingual Evaluation Understudy)

```
BLEU = BP * exp( SUM_n [ w_n * log(precision_n) ] )
BP   = min(1, exp(1 - reference_length/candidate_length))
```

- **Range**: 0 to 1 (higher is better)
- **When to use**: Machine translation evaluation
- **Properties**: Based on n-gram precision with brevity penalty
- **Variants**: BLEU-1 (unigrams), BLEU-4 (up to 4-grams, most common)
- **Limitations**: Does not capture meaning, word order (beyond n-gram), or fluency well

### ROUGE (Recall-Oriented Understudy for Gisting Evaluation)

| Variant | Description |
|---------|-------------|
| **ROUGE-N** | N-gram recall between candidate and reference |
| **ROUGE-1** | Unigram overlap (captures content) |
| **ROUGE-2** | Bigram overlap (captures fluency) |
| **ROUGE-L** | Longest common subsequence (captures sentence-level structure) |
| **ROUGE-Lsum** | ROUGE-L applied to summary-level (split by newlines) |

- **Range**: 0 to 1 (higher is better)
- **When to use**: Text summarization, text generation evaluation
- **Reports**: Precision, recall, and F1 for each variant

### Perplexity

```
Perplexity = exp( -(1/N) * SUM[ log P(token_i | context) ] )
```

- **Range**: 1 to infinity (lower is better)
- **Interpretation**: How "surprised" the model is by the test data. A perplexity of k means the model is as uncertain as if choosing uniformly among k options at each step.
- **When to use**: Evaluating language models
- **Caution**: Only comparable across models with the same vocabulary

### BERTScore

Uses contextual embeddings (BERT) to compute similarity between generated and reference text.

- **Range**: 0 to 1 (higher is better)
- **Reports**: Precision, recall, and F1
- **Advantage over BLEU/ROUGE**: Captures semantic similarity, not just surface-level n-gram overlap
- **When to use**: Tasks where paraphrasing is acceptable

### METEOR

```
METEOR = F_mean * (1 - Penalty)
```

Combines unigram precision and recall with a penalty for fragmentation.

- **Range**: 0 to 1
- **Advantage over BLEU**: Considers synonyms and stemming, correlates better with human judgment
- **When to use**: Machine translation (alternative or complement to BLEU)

### CIDEr (Consensus-based Image Description Evaluation)

- **When to use**: Image captioning
- **Properties**: Based on TF-IDF weighted n-grams, captures consensus among multiple references

### Word Error Rate (WER)

```
WER = (Substitutions + Insertions + Deletions) / Reference Length
```

- **Range**: 0 to infinity (lower is better; can exceed 1.0)
- **When to use**: Speech recognition (ASR) evaluation

---

## 5. Metric Selection Guide

### By Task Type

| Task | Primary Metric | Secondary Metrics | Avoid |
|------|---------------|-------------------|-------|
| **Balanced binary classification** | F1, AUC-ROC | Accuracy, MCC | — |
| **Imbalanced binary classification** | AUC-PR, F1 (positive class) | MCC, Recall | Accuracy |
| **Multiclass classification** | Macro F1, Weighted F1 | Per-class F1, Confusion Matrix | Micro F1 alone |
| **Regression** | RMSE, MAE | R-squared, MAPE | MSE alone (not interpretable) |
| **Regression with outliers** | MAE, Huber Loss | Median Absolute Error | MSE, RMSE |
| **Search / Retrieval** | NDCG@k, MAP | MRR, Precision@k | — |
| **Recommendation** | NDCG@k, Hit Rate@k | Precision@k, Recall@k | — |
| **Machine translation** | BLEU-4 | METEOR, BERTScore | BLEU alone |
| **Summarization** | ROUGE-L, ROUGE-2 | BERTScore | BLEU |
| **Language modeling** | Perplexity | — | — |
| **Speech recognition** | WER | — | — |
| **Probability estimation** | Brier Score, Log Loss | Calibration curve | Accuracy |

### By Business Requirement

| Requirement | Recommended Metric |
|-------------|-------------------|
| "We cannot miss positive cases" | Recall (sensitivity) |
| "Alerts must be reliable" | Precision |
| "Errors in either direction are equally bad" | F1 Score |
| "Rank the best items first" | NDCG@k |
| "We need accurate probabilities" | Log Loss, Brier Score |
| "Dollar cost of errors matters" | Custom cost-weighted metric |
| "Model must be fair across groups" | Equalized odds, Demographic parity |

---

## 6. Common Pitfalls

### Accuracy Paradox

**Problem**: With a 95% negative / 5% positive dataset, a model that always predicts "negative" achieves 95% accuracy.

**Solution**: Use metrics that account for class distribution: F1, AUC-PR, MCC.

**Example**:
- Dataset: 9500 negative, 500 positive
- "Always negative" model: 95% accuracy, 0% recall, undefined precision, 0 F1
- A useful model with 80% accuracy might have 60% recall and 40% precision -- clearly better

### Class Imbalance

**Problem**: Standard metrics are misleading when classes are heavily imbalanced.

**Solutions**:
1. Use AUC-PR instead of AUC-ROC
2. Report per-class metrics, not just averages
3. Use stratified sampling for train/test splits
4. Consider cost-sensitive learning or resampling

### Threshold Dependency

**Problem**: Precision, recall, F1, and accuracy all depend on the classification threshold. Comparing models at a fixed threshold (e.g., 0.5) can be misleading.

**Solution**: Use threshold-independent metrics (AUC-ROC, AUC-PR) for model comparison, then choose the threshold based on business requirements.

### Leakage in Evaluation

**Problem**: Information from the test set leaks into training, inflating metrics.

**Common causes**:
- Preprocessing (scaling, encoding) fit on the full dataset before splitting
- Time-series data split randomly instead of chronologically
- Duplicate or near-duplicate samples across train and test sets
- Target encoding computed on the full dataset

**Solution**: Always preprocess within cross-validation folds. Use temporal splits for time-series data. Deduplicate before splitting.

### Overfitting to the Validation Set

**Problem**: Repeatedly tuning hyperparameters on the same validation set effectively leaks information.

**Solution**: Use a three-way split (train / validation / test) or nested cross-validation. Report final metrics only on the held-out test set.

### Metric Gaming

**Problem**: Optimizing a single metric can lead to degenerate models.

**Examples**:
- Optimizing recall alone: predict everything as positive (100% recall, terrible precision)
- Optimizing BLEU: short, safe translations score well but lack detail

**Solution**: Always report multiple complementary metrics. Define a primary metric but set minimum thresholds on secondary metrics.

### Ignoring Confidence Intervals

**Problem**: Reporting point estimates without uncertainty hides whether differences are statistically significant.

**Solution**: Report confidence intervals (bootstrap), run significance tests (paired t-test, McNemar's test), or report standard deviations across cross-validation folds.

### Comparing Metrics Across Datasets

**Problem**: The same metric value means different things on different datasets (e.g., 0.9 AUC-ROC on an easy dataset vs. a hard one).

**Solution**: Always compare against meaningful baselines (random, majority class, previous model, human performance).

### Ignoring Calibration

**Problem**: A model can have excellent AUC-ROC but poorly calibrated probabilities. If you use predicted probabilities for downstream decisions, calibration matters.

**Solution**: Plot calibration curves (reliability diagrams), report Brier score, and apply calibration methods (Platt scaling, isotonic regression) if needed.

### Survivorship Bias in Online Metrics

**Problem**: In production, you only observe outcomes for the items you showed/recommended, not the ones you didn't.

**Solution**: Use techniques like inverse propensity scoring, doubly robust estimation, or controlled experiments (A/B tests) for unbiased evaluation.
