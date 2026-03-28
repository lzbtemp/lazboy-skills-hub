#!/usr/bin/env python3
"""
ML Model Evaluation Script

Accepts a predictions CSV file and task type, calculates relevant metrics,
generates visualizations, and outputs a comprehensive evaluation report.

Usage:
    python evaluate_model.py --predictions predictions.csv --task classification
    python evaluate_model.py --predictions predictions.csv --task regression --output report/
    python evaluate_model.py --predictions predictions.csv --task classification --threshold 0.3
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import numpy as np
    import pandas as pd
except ImportError:
    print("Error: numpy and pandas are required. Install with: pip install numpy pandas")
    sys.exit(1)

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
    print("Warning: matplotlib not available. Plots will be skipped.")

try:
    from sklearn import metrics as sk_metrics
except ImportError:
    print("Error: scikit-learn is required. Install with: pip install scikit-learn")
    sys.exit(1)


def load_predictions(filepath: str) -> pd.DataFrame:
    """Load predictions CSV file with validation."""
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    df = pd.read_csv(filepath)

    required_columns = {"actual", "predicted"}
    available = set(df.columns.str.lower())
    if not required_columns.issubset(available):
        # Try common alternative names
        column_map = {
            "y_true": "actual",
            "y_pred": "predicted",
            "true": "actual",
            "pred": "predicted",
            "label": "actual",
            "prediction": "predicted",
            "target": "actual",
            "ground_truth": "actual",
        }
        df.columns = df.columns.str.lower()
        df = df.rename(columns=column_map)

        if "actual" not in df.columns or "predicted" not in df.columns:
            print(
                f"Error: CSV must contain 'actual' and 'predicted' columns. "
                f"Found: {list(df.columns)}"
            )
            sys.exit(1)
    else:
        df.columns = df.columns.str.lower()

    return df


def evaluate_classification(
    df: pd.DataFrame,
    threshold: float = 0.5,
    output_dir: str = ".",
) -> dict[str, Any]:
    """Calculate classification metrics and generate visualizations."""
    y_true = df["actual"].values
    y_pred_raw = df["predicted"].values

    # Determine if predictions are probabilities or class labels
    unique_preds = np.unique(y_pred_raw)
    is_probability = np.all((y_pred_raw >= 0) & (y_pred_raw <= 1)) and len(unique_preds) > 10

    if is_probability:
        y_prob = y_pred_raw
        y_pred = (y_pred_raw >= threshold).astype(int)
    else:
        y_prob = None
        y_pred = y_pred_raw

    classes = np.unique(y_true)
    is_binary = len(classes) == 2

    results: dict[str, Any] = {
        "task": "classification",
        "num_samples": len(y_true),
        "num_classes": len(classes),
        "classes": classes.tolist(),
        "threshold": threshold if is_probability else None,
    }

    # Core metrics
    results["accuracy"] = float(sk_metrics.accuracy_score(y_true, y_pred))

    if is_binary:
        pos_label = classes[1] if len(classes) == 2 else 1
        results["precision"] = float(
            sk_metrics.precision_score(y_true, y_pred, pos_label=pos_label, zero_division=0)
        )
        results["recall"] = float(
            sk_metrics.recall_score(y_true, y_pred, pos_label=pos_label, zero_division=0)
        )
        results["f1"] = float(
            sk_metrics.f1_score(y_true, y_pred, pos_label=pos_label, zero_division=0)
        )
        results["specificity"] = float(
            sk_metrics.recall_score(
                y_true, y_pred, pos_label=classes[0], zero_division=0
            )
        )

        if y_prob is not None:
            results["auc_roc"] = float(sk_metrics.roc_auc_score(y_true, y_prob))
            results["auc_pr"] = float(
                sk_metrics.average_precision_score(y_true, y_prob)
            )
            results["log_loss"] = float(sk_metrics.log_loss(y_true, y_prob))
            results["brier_score"] = float(sk_metrics.brier_score_loss(y_true, y_prob))
    else:
        for avg in ["macro", "micro", "weighted"]:
            results[f"precision_{avg}"] = float(
                sk_metrics.precision_score(y_true, y_pred, average=avg, zero_division=0)
            )
            results[f"recall_{avg}"] = float(
                sk_metrics.recall_score(y_true, y_pred, average=avg, zero_division=0)
            )
            results[f"f1_{avg}"] = float(
                sk_metrics.f1_score(y_true, y_pred, average=avg, zero_division=0)
            )

    # Matthews Correlation Coefficient
    results["mcc"] = float(sk_metrics.matthews_corrcoef(y_true, y_pred))

    # Cohen's Kappa
    results["cohens_kappa"] = float(sk_metrics.cohen_kappa_score(y_true, y_pred))

    # Confusion matrix
    cm = sk_metrics.confusion_matrix(y_true, y_pred, labels=classes)
    results["confusion_matrix"] = cm.tolist()

    # Per-class metrics
    report = sk_metrics.classification_report(y_true, y_pred, output_dict=True, zero_division=0)
    results["classification_report"] = report

    # Generate plots
    if plt is not None:
        _plot_confusion_matrix(cm, classes, output_dir)

        if y_prob is not None and is_binary:
            _plot_roc_curve(y_true, y_prob, output_dir)
            _plot_precision_recall_curve(y_true, y_prob, output_dir)
            _plot_threshold_analysis(y_true, y_prob, output_dir)

    return results


def evaluate_regression(
    df: pd.DataFrame,
    output_dir: str = ".",
) -> dict[str, Any]:
    """Calculate regression metrics and generate visualizations."""
    y_true = df["actual"].values.astype(float)
    y_pred = df["predicted"].values.astype(float)

    results: dict[str, Any] = {
        "task": "regression",
        "num_samples": len(y_true),
    }

    results["mse"] = float(sk_metrics.mean_squared_error(y_true, y_pred))
    results["rmse"] = float(np.sqrt(results["mse"]))
    results["mae"] = float(sk_metrics.mean_absolute_error(y_true, y_pred))
    results["r_squared"] = float(sk_metrics.r2_score(y_true, y_pred))
    results["median_ae"] = float(sk_metrics.median_absolute_error(y_true, y_pred))
    results["max_error"] = float(sk_metrics.max_error(y_true, y_pred))
    results["explained_variance"] = float(
        sk_metrics.explained_variance_score(y_true, y_pred)
    )

    # MAPE (handle zero actuals)
    nonzero_mask = y_true != 0
    if nonzero_mask.any():
        results["mape"] = float(
            np.mean(np.abs((y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask])) * 100
        )
    else:
        results["mape"] = None

    # Residual statistics
    residuals = y_true - y_pred
    results["residual_mean"] = float(np.mean(residuals))
    results["residual_std"] = float(np.std(residuals))
    results["residual_skewness"] = float(
        pd.Series(residuals).skew()
    )

    # Percentile errors
    abs_errors = np.abs(residuals)
    for p in [50, 90, 95, 99]:
        results[f"error_p{p}"] = float(np.percentile(abs_errors, p))

    # Generate plots
    if plt is not None:
        _plot_residuals(y_true, y_pred, output_dir)
        _plot_actual_vs_predicted(y_true, y_pred, output_dir)
        _plot_error_distribution(residuals, output_dir)

    return results


# --- Plotting functions ---


def _plot_confusion_matrix(
    cm: np.ndarray, classes: np.ndarray, output_dir: str
) -> None:
    """Plot and save confusion matrix heatmap."""
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)
    ax.set(
        xticks=np.arange(cm.shape[1]),
        yticks=np.arange(cm.shape[0]),
        xticklabels=classes,
        yticklabels=classes,
        title="Confusion Matrix",
        ylabel="Actual",
        xlabel="Predicted",
    )
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    # Add text annotations
    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(
                j, i, format(cm[i, j], "d"),
                ha="center", va="center",
                color="white" if cm[i, j] > thresh else "black",
            )
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "confusion_matrix.png"), dpi=150)
    plt.close(fig)


def _plot_roc_curve(y_true: np.ndarray, y_prob: np.ndarray, output_dir: str) -> None:
    """Plot and save ROC curve."""
    fpr, tpr, _ = sk_metrics.roc_curve(y_true, y_prob)
    auc = sk_metrics.roc_auc_score(y_true, y_prob)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(fpr, tpr, linewidth=2, label=f"Model (AUC = {auc:.4f})")
    ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="Random")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "roc_curve.png"), dpi=150)
    plt.close(fig)


def _plot_precision_recall_curve(
    y_true: np.ndarray, y_prob: np.ndarray, output_dir: str
) -> None:
    """Plot and save Precision-Recall curve."""
    precision, recall, _ = sk_metrics.precision_recall_curve(y_true, y_prob)
    ap = sk_metrics.average_precision_score(y_true, y_prob)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(recall, precision, linewidth=2, label=f"Model (AP = {ap:.4f})")
    baseline = np.mean(y_true)
    ax.axhline(y=baseline, color="k", linestyle="--", linewidth=1, label=f"Baseline ({baseline:.3f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall Curve")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "precision_recall_curve.png"), dpi=150)
    plt.close(fig)


def _plot_threshold_analysis(
    y_true: np.ndarray, y_prob: np.ndarray, output_dir: str
) -> None:
    """Plot metrics across different classification thresholds."""
    thresholds = np.arange(0.05, 1.0, 0.05)
    precisions, recalls, f1s = [], [], []

    for t in thresholds:
        y_pred_t = (y_prob >= t).astype(int)
        precisions.append(sk_metrics.precision_score(y_true, y_pred_t, zero_division=0))
        recalls.append(sk_metrics.recall_score(y_true, y_pred_t, zero_division=0))
        f1s.append(sk_metrics.f1_score(y_true, y_pred_t, zero_division=0))

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(thresholds, precisions, label="Precision", linewidth=2)
    ax.plot(thresholds, recalls, label="Recall", linewidth=2)
    ax.plot(thresholds, f1s, label="F1", linewidth=2)
    ax.set_xlabel("Threshold")
    ax.set_ylabel("Score")
    ax.set_title("Metrics vs. Classification Threshold")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "threshold_analysis.png"), dpi=150)
    plt.close(fig)


def _plot_residuals(
    y_true: np.ndarray, y_pred: np.ndarray, output_dir: str
) -> None:
    """Plot residuals vs predicted values."""
    residuals = y_true - y_pred

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Residuals vs Predicted
    axes[0].scatter(y_pred, residuals, alpha=0.5, s=10)
    axes[0].axhline(y=0, color="r", linestyle="--", linewidth=1)
    axes[0].set_xlabel("Predicted Values")
    axes[0].set_ylabel("Residuals")
    axes[0].set_title("Residuals vs. Predicted")
    axes[0].grid(True, alpha=0.3)

    # Residuals vs Actual
    axes[1].scatter(y_true, residuals, alpha=0.5, s=10)
    axes[1].axhline(y=0, color="r", linestyle="--", linewidth=1)
    axes[1].set_xlabel("Actual Values")
    axes[1].set_ylabel("Residuals")
    axes[1].set_title("Residuals vs. Actual")
    axes[1].grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "residuals.png"), dpi=150)
    plt.close(fig)


def _plot_actual_vs_predicted(
    y_true: np.ndarray, y_pred: np.ndarray, output_dir: str
) -> None:
    """Plot actual vs predicted scatter plot."""
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(y_true, y_pred, alpha=0.5, s=10)
    min_val = min(y_true.min(), y_pred.min())
    max_val = max(y_true.max(), y_pred.max())
    ax.plot([min_val, max_val], [min_val, max_val], "r--", linewidth=1, label="Perfect prediction")
    ax.set_xlabel("Actual")
    ax.set_ylabel("Predicted")
    ax.set_title("Actual vs. Predicted")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "actual_vs_predicted.png"), dpi=150)
    plt.close(fig)


def _plot_error_distribution(residuals: np.ndarray, output_dir: str) -> None:
    """Plot distribution of prediction errors."""
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.hist(residuals, bins=50, edgecolor="black", alpha=0.7)
    ax.axvline(x=0, color="r", linestyle="--", linewidth=1)
    ax.axvline(x=np.mean(residuals), color="orange", linestyle="-", linewidth=1, label=f"Mean: {np.mean(residuals):.4f}")
    ax.set_xlabel("Residual (Actual - Predicted)")
    ax.set_ylabel("Frequency")
    ax.set_title("Error Distribution")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "error_distribution.png"), dpi=150)
    plt.close(fig)


# --- Report generation ---


def generate_markdown_report(results: dict[str, Any], output_dir: str) -> str:
    """Generate a markdown evaluation report."""
    lines = [
        "# Model Evaluation Report",
        f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Task**: {results['task']}",
        f"**Samples**: {results['num_samples']:,}",
        "",
    ]

    if results["task"] == "classification":
        lines.append("## Classification Metrics\n")

        if results.get("num_classes", 2) == 2:
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            for key, label in [
                ("accuracy", "Accuracy"),
                ("precision", "Precision"),
                ("recall", "Recall"),
                ("f1", "F1 Score"),
                ("specificity", "Specificity"),
                ("mcc", "Matthews Correlation Coefficient"),
                ("cohens_kappa", "Cohen's Kappa"),
                ("auc_roc", "AUC-ROC"),
                ("auc_pr", "AUC-PR"),
                ("log_loss", "Log Loss"),
                ("brier_score", "Brier Score"),
            ]:
                if key in results and results[key] is not None:
                    lines.append(f"| {label} | {results[key]:.4f} |")

            if results.get("threshold") is not None:
                lines.append(f"\n*Classification threshold*: {results['threshold']}")
        else:
            lines.append(f"**Number of classes**: {results['num_classes']}\n")
            lines.append("| Metric | Macro | Micro | Weighted |")
            lines.append("|--------|-------|-------|----------|")
            for metric_name in ["precision", "recall", "f1"]:
                macro = results.get(f"{metric_name}_macro", 0)
                micro = results.get(f"{metric_name}_micro", 0)
                weighted = results.get(f"{metric_name}_weighted", 0)
                lines.append(
                    f"| {metric_name.title()} | {macro:.4f} | {micro:.4f} | {weighted:.4f} |"
                )

        # Confusion matrix
        lines.append("\n## Confusion Matrix\n")
        cm = results["confusion_matrix"]
        classes = results["classes"]
        header = "| | " + " | ".join(f"Pred {c}" for c in classes) + " |"
        separator = "|" + "|".join(["---"] * (len(classes) + 1)) + "|"
        lines.append(header)
        lines.append(separator)
        for i, row in enumerate(cm):
            row_str = " | ".join(str(v) for v in row)
            lines.append(f"| **Actual {classes[i]}** | {row_str} |")

        # Per-class report
        lines.append("\n## Per-Class Metrics\n")
        report = results["classification_report"]
        lines.append("| Class | Precision | Recall | F1 | Support |")
        lines.append("|-------|-----------|--------|-----|---------|")
        for cls in [str(c) for c in classes]:
            if cls in report:
                r = report[cls]
                lines.append(
                    f"| {cls} | {r['precision']:.4f} | {r['recall']:.4f} | "
                    f"{r['f1-score']:.4f} | {int(r['support'])} |"
                )

        if plt is not None:
            lines.append("\n## Visualizations\n")
            lines.append("- ![Confusion Matrix](confusion_matrix.png)")
            if results.get("auc_roc") is not None:
                lines.append("- ![ROC Curve](roc_curve.png)")
                lines.append("- ![Precision-Recall Curve](precision_recall_curve.png)")
                lines.append("- ![Threshold Analysis](threshold_analysis.png)")

    elif results["task"] == "regression":
        lines.append("## Regression Metrics\n")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for key, label in [
            ("mse", "Mean Squared Error"),
            ("rmse", "Root Mean Squared Error"),
            ("mae", "Mean Absolute Error"),
            ("median_ae", "Median Absolute Error"),
            ("max_error", "Max Error"),
            ("r_squared", "R-squared"),
            ("explained_variance", "Explained Variance"),
            ("mape", "MAPE (%)"),
        ]:
            if key in results and results[key] is not None:
                lines.append(f"| {label} | {results[key]:.4f} |")

        lines.append("\n## Residual Statistics\n")
        lines.append("| Statistic | Value |")
        lines.append("|-----------|-------|")
        for key, label in [
            ("residual_mean", "Mean"),
            ("residual_std", "Std Dev"),
            ("residual_skewness", "Skewness"),
            ("error_p50", "P50 Absolute Error"),
            ("error_p90", "P90 Absolute Error"),
            ("error_p95", "P95 Absolute Error"),
            ("error_p99", "P99 Absolute Error"),
        ]:
            if key in results and results[key] is not None:
                lines.append(f"| {label} | {results[key]:.4f} |")

        if plt is not None:
            lines.append("\n## Visualizations\n")
            lines.append("- ![Residuals](residuals.png)")
            lines.append("- ![Actual vs Predicted](actual_vs_predicted.png)")
            lines.append("- ![Error Distribution](error_distribution.png)")

    report_text = "\n".join(lines)
    report_path = os.path.join(output_dir, "evaluation_report.md")
    with open(report_path, "w") as f:
        f.write(report_text)

    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate ML model predictions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --predictions preds.csv --task classification
  %(prog)s --predictions preds.csv --task regression --output results/
  %(prog)s --predictions preds.csv --task classification --threshold 0.3
        """,
    )
    parser.add_argument(
        "--predictions", "-p", required=True,
        help="Path to CSV file with 'actual' and 'predicted' columns",
    )
    parser.add_argument(
        "--task", "-t", required=True, choices=["classification", "regression"],
        help="Task type: classification or regression",
    )
    parser.add_argument(
        "--output", "-o", default="./evaluation_output",
        help="Output directory for reports and plots (default: ./evaluation_output)",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.5,
        help="Classification threshold for probability predictions (default: 0.5)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Also output results as JSON",
    )

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Load data
    print(f"Loading predictions from: {args.predictions}")
    df = load_predictions(args.predictions)
    print(f"Loaded {len(df):,} predictions")

    # Evaluate
    print(f"Evaluating as {args.task} task...")
    if args.task == "classification":
        results = evaluate_classification(df, threshold=args.threshold, output_dir=args.output)
    else:
        results = evaluate_regression(df, output_dir=args.output)

    # Generate report
    report_path = generate_markdown_report(results, args.output)
    print(f"Report saved to: {report_path}")

    # Optionally save JSON
    if args.json:
        json_path = os.path.join(args.output, "evaluation_results.json")
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"JSON results saved to: {json_path}")

    # Print summary to stdout
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    if args.task == "classification":
        print(f"  Accuracy:  {results['accuracy']:.4f}")
        if "f1" in results:
            print(f"  F1 Score:  {results['f1']:.4f}")
            print(f"  Precision: {results['precision']:.4f}")
            print(f"  Recall:    {results['recall']:.4f}")
        if "auc_roc" in results:
            print(f"  AUC-ROC:   {results['auc_roc']:.4f}")
        print(f"  MCC:       {results['mcc']:.4f}")
    else:
        print(f"  RMSE:      {results['rmse']:.4f}")
        print(f"  MAE:       {results['mae']:.4f}")
        print(f"  R-squared: {results['r_squared']:.4f}")
        if results.get("mape") is not None:
            print(f"  MAPE:      {results['mape']:.2f}%")
    print("=" * 60)


if __name__ == "__main__":
    main()
