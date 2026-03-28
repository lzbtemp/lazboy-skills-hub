#!/usr/bin/env python3
"""
Bias Detection Script for ML Model Predictions

Detects bias in model predictions across demographic groups by calculating
fairness metrics including disparate impact ratio, equalized odds, and
demographic parity.

Usage:
    python detect_bias.py --predictions preds.csv --demographics gender age_group
    python detect_bias.py --predictions preds.csv --demographics gender --threshold 0.5
    python detect_bias.py --predictions preds.csv --demographics race --output bias_report/
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any

try:
    import numpy as np
    import pandas as pd
except ImportError:
    print("Error: numpy and pandas are required. Install with: pip install numpy pandas")
    sys.exit(1)

try:
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
    )
except ImportError:
    print("Error: scikit-learn is required. Install with: pip install scikit-learn")
    sys.exit(1)

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


# --- Fairness Metrics ---


def selection_rate(y_pred: np.ndarray) -> float:
    """Calculate the positive prediction rate."""
    return float(np.mean(y_pred))


def disparate_impact_ratio(
    y_pred: np.ndarray, group_mask: np.ndarray
) -> dict[str, Any]:
    """
    Calculate disparate impact ratio between two groups.

    The ratio of the selection rate for the unprivileged group to the
    selection rate for the privileged group. Values below 0.8 (the
    four-fifths rule) indicate potential adverse impact.
    """
    privileged_rate = selection_rate(y_pred[group_mask])
    unprivileged_rate = selection_rate(y_pred[~group_mask])

    if privileged_rate == 0:
        ratio = float("inf") if unprivileged_rate > 0 else 1.0
    else:
        ratio = unprivileged_rate / privileged_rate

    return {
        "privileged_selection_rate": privileged_rate,
        "unprivileged_selection_rate": unprivileged_rate,
        "disparate_impact_ratio": ratio,
        "passes_four_fifths_rule": ratio >= 0.8,
    }


def equalized_odds(
    y_true: np.ndarray, y_pred: np.ndarray, group_mask: np.ndarray
) -> dict[str, Any]:
    """
    Calculate equalized odds metrics.

    Equalized odds requires that the true positive rate and false positive
    rate are equal across groups.
    """
    def _rates(y_t: np.ndarray, y_p: np.ndarray) -> tuple[float, float]:
        cm = confusion_matrix(y_t, y_p, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        return tpr, fpr

    priv_tpr, priv_fpr = _rates(y_true[group_mask], y_pred[group_mask])
    unpriv_tpr, unpriv_fpr = _rates(y_true[~group_mask], y_pred[~group_mask])

    return {
        "privileged_tpr": priv_tpr,
        "privileged_fpr": priv_fpr,
        "unprivileged_tpr": unpriv_tpr,
        "unprivileged_fpr": unpriv_fpr,
        "tpr_difference": abs(priv_tpr - unpriv_tpr),
        "fpr_difference": abs(priv_fpr - unpriv_fpr),
        "equalized_odds_difference": max(
            abs(priv_tpr - unpriv_tpr), abs(priv_fpr - unpriv_fpr)
        ),
    }


def demographic_parity_difference(
    y_pred: np.ndarray, group_mask: np.ndarray
) -> dict[str, Any]:
    """
    Calculate demographic parity difference.

    Demographic parity requires that the selection rate (positive prediction
    rate) is equal across groups.
    """
    priv_rate = selection_rate(y_pred[group_mask])
    unpriv_rate = selection_rate(y_pred[~group_mask])

    return {
        "privileged_selection_rate": priv_rate,
        "unprivileged_selection_rate": unpriv_rate,
        "demographic_parity_difference": abs(priv_rate - unpriv_rate),
    }


def group_performance_metrics(
    y_true: np.ndarray, y_pred: np.ndarray
) -> dict[str, float]:
    """Calculate standard performance metrics for a group."""
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "selection_rate": float(np.mean(y_pred)),
        "positive_rate": float(np.mean(y_true)),
        "n_samples": int(len(y_true)),
    }


# --- Analysis ---


def analyze_demographic(
    df: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    demographic_col: str,
    disparity_threshold: float = 0.1,
) -> dict[str, Any]:
    """Analyze fairness metrics for a single demographic attribute."""
    groups = df[demographic_col].unique()
    groups = sorted([g for g in groups if pd.notna(g)])

    if len(groups) < 2:
        return {
            "demographic": demographic_col,
            "error": f"Need at least 2 groups, found {len(groups)}",
        }

    result: dict[str, Any] = {
        "demographic": demographic_col,
        "groups": {},
        "pairwise_comparisons": [],
        "flags": [],
    }

    # Per-group metrics
    for group in groups:
        mask = df[demographic_col] == group
        result["groups"][str(group)] = group_performance_metrics(
            y_true[mask], y_pred[mask]
        )

    # Pairwise comparisons (each pair of groups)
    for i, g1 in enumerate(groups):
        for g2 in groups[i + 1:]:
            mask_g1 = (df[demographic_col] == g1).values
            mask_g2 = (df[demographic_col] == g2).values
            combined_mask = mask_g1 | mask_g2

            # Use g1 as privileged group (the one with higher selection rate)
            rate_g1 = selection_rate(y_pred[mask_g1])
            rate_g2 = selection_rate(y_pred[mask_g2])

            if rate_g1 >= rate_g2:
                privileged_mask = mask_g1[combined_mask]
                privileged_name, unprivileged_name = str(g1), str(g2)
            else:
                privileged_mask = mask_g2[combined_mask]
                privileged_name, unprivileged_name = str(g2), str(g1)

            comparison = {
                "privileged_group": privileged_name,
                "unprivileged_group": unprivileged_name,
                "disparate_impact": disparate_impact_ratio(
                    y_pred[combined_mask], privileged_mask
                ),
                "equalized_odds": equalized_odds(
                    y_true[combined_mask], y_pred[combined_mask], privileged_mask
                ),
                "demographic_parity": demographic_parity_difference(
                    y_pred[combined_mask], privileged_mask
                ),
            }
            result["pairwise_comparisons"].append(comparison)

            # Flag significant disparities
            di = comparison["disparate_impact"]["disparate_impact_ratio"]
            if di < 0.8:
                result["flags"].append({
                    "type": "DISPARATE_IMPACT",
                    "severity": "HIGH",
                    "message": (
                        f"Disparate impact ratio {di:.3f} between "
                        f"{privileged_name} and {unprivileged_name} "
                        f"(below 0.8 four-fifths threshold)"
                    ),
                })

            eo_diff = comparison["equalized_odds"]["equalized_odds_difference"]
            if eo_diff > disparity_threshold:
                result["flags"].append({
                    "type": "EQUALIZED_ODDS",
                    "severity": "HIGH" if eo_diff > 0.2 else "MEDIUM",
                    "message": (
                        f"Equalized odds difference {eo_diff:.3f} between "
                        f"{privileged_name} and {unprivileged_name} "
                        f"(above {disparity_threshold} threshold)"
                    ),
                })

            dp_diff = comparison["demographic_parity"]["demographic_parity_difference"]
            if dp_diff > disparity_threshold:
                result["flags"].append({
                    "type": "DEMOGRAPHIC_PARITY",
                    "severity": "HIGH" if dp_diff > 0.2 else "MEDIUM",
                    "message": (
                        f"Demographic parity difference {dp_diff:.3f} between "
                        f"{privileged_name} and {unprivileged_name} "
                        f"(above {disparity_threshold} threshold)"
                    ),
                })

    # Check for performance disparities
    accuracies = {g: result["groups"][str(g)]["accuracy"] for g in groups}
    max_acc = max(accuracies.values())
    min_acc = min(accuracies.values())
    if max_acc - min_acc > disparity_threshold:
        worst_group = min(accuracies, key=accuracies.get)
        best_group = max(accuracies, key=accuracies.get)
        result["flags"].append({
            "type": "PERFORMANCE_DISPARITY",
            "severity": "HIGH" if (max_acc - min_acc) > 0.15 else "MEDIUM",
            "message": (
                f"Accuracy gap of {max_acc - min_acc:.3f} between "
                f"{best_group} ({max_acc:.3f}) and "
                f"{worst_group} ({min_acc:.3f})"
            ),
        })

    return result


# --- Visualization ---


def plot_group_metrics(
    analysis: dict[str, Any], output_dir: str
) -> None:
    """Generate plots for bias analysis."""
    if plt is None:
        return

    demographic = analysis["demographic"]
    groups = analysis["groups"]

    if not groups:
        return

    group_names = list(groups.keys())
    metrics_to_plot = ["accuracy", "precision", "recall", "f1", "selection_rate"]

    fig, axes = plt.subplots(1, len(metrics_to_plot), figsize=(4 * len(metrics_to_plot), 5))
    if len(metrics_to_plot) == 1:
        axes = [axes]

    for ax, metric in zip(axes, metrics_to_plot):
        values = [groups[g][metric] for g in group_names]
        bars = ax.bar(group_names, values, color=plt.cm.Set2(range(len(group_names))))
        ax.set_title(metric.replace("_", " ").title())
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Score")
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                f"{val:.3f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
        ax.tick_params(axis="x", rotation=45)

    fig.suptitle(f"Metrics by {demographic}", fontsize=14)
    fig.tight_layout()
    fig.savefig(
        os.path.join(output_dir, f"bias_{demographic}_metrics.png"), dpi=150
    )
    plt.close(fig)


# --- Report Generation ---


def generate_bias_report(
    analyses: list[dict[str, Any]], output_dir: str
) -> str:
    """Generate a markdown bias detection report."""
    lines = [
        "# Bias Detection Report",
        f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    # Executive summary
    total_flags = sum(len(a.get("flags", [])) for a in analyses)
    high_flags = sum(
        1
        for a in analyses
        for f in a.get("flags", [])
        if f["severity"] == "HIGH"
    )

    lines.append("## Executive Summary\n")
    lines.append(f"- **Demographics analyzed**: {len(analyses)}")
    lines.append(f"- **Total flags**: {total_flags}")
    lines.append(f"- **High severity flags**: {high_flags}")

    if high_flags > 0:
        lines.append(
            "\n> **WARNING**: High-severity bias indicators detected. "
            "Review findings and consider mitigation before deployment."
        )

    # All flags summary
    if total_flags > 0:
        lines.append("\n## Flags Summary\n")
        lines.append("| Severity | Type | Description |")
        lines.append("|----------|------|-------------|")
        for analysis in analyses:
            for flag in analysis.get("flags", []):
                lines.append(
                    f"| **{flag['severity']}** | {flag['type']} | {flag['message']} |"
                )

    # Detailed results per demographic
    for analysis in analyses:
        demographic = analysis["demographic"]
        lines.append(f"\n## {demographic}\n")

        if "error" in analysis:
            lines.append(f"*Error*: {analysis['error']}\n")
            continue

        # Group metrics table
        groups = analysis["groups"]
        if groups:
            lines.append("### Performance by Group\n")
            lines.append(
                "| Group | N | Accuracy | Precision | Recall | F1 | Selection Rate | Base Rate |"
            )
            lines.append(
                "|-------|---|----------|-----------|--------|-----|----------------|-----------|"
            )
            for group_name, metrics in groups.items():
                lines.append(
                    f"| {group_name} | {metrics['n_samples']:,} | "
                    f"{metrics['accuracy']:.4f} | {metrics['precision']:.4f} | "
                    f"{metrics['recall']:.4f} | {metrics['f1']:.4f} | "
                    f"{metrics['selection_rate']:.4f} | {metrics['positive_rate']:.4f} |"
                )

        # Pairwise comparisons
        comparisons = analysis.get("pairwise_comparisons", [])
        if comparisons:
            lines.append("\n### Pairwise Fairness Metrics\n")
            for comp in comparisons:
                priv = comp["privileged_group"]
                unpriv = comp["unprivileged_group"]
                lines.append(f"#### {priv} vs. {unpriv}\n")

                di = comp["disparate_impact"]
                lines.append("**Disparate Impact**\n")
                lines.append(f"- Privileged selection rate: {di['privileged_selection_rate']:.4f}")
                lines.append(f"- Unprivileged selection rate: {di['unprivileged_selection_rate']:.4f}")
                lines.append(f"- Disparate impact ratio: {di['disparate_impact_ratio']:.4f}")
                status = "PASS" if di["passes_four_fifths_rule"] else "FAIL"
                lines.append(f"- Four-fifths rule: **{status}**\n")

                eo = comp["equalized_odds"]
                lines.append("**Equalized Odds**\n")
                lines.append(f"- TPR difference: {eo['tpr_difference']:.4f}")
                lines.append(f"- FPR difference: {eo['fpr_difference']:.4f}")
                lines.append(f"- Max difference: {eo['equalized_odds_difference']:.4f}\n")

                dp = comp["demographic_parity"]
                lines.append("**Demographic Parity**\n")
                lines.append(
                    f"- Difference: {dp['demographic_parity_difference']:.4f}\n"
                )

        if plt is not None:
            lines.append(
                f"\n![Metrics by {demographic}](bias_{demographic}_metrics.png)\n"
            )

    # Recommendations
    lines.append("\n## Recommendations\n")
    if high_flags > 0:
        lines.append(
            "1. **Investigate root causes**: Examine training data distribution "
            "for underrepresented groups."
        )
        lines.append(
            "2. **Consider resampling**: Balance training data across demographic groups."
        )
        lines.append(
            "3. **Apply fairness constraints**: Use in-processing techniques "
            "(e.g., adversarial debiasing, fairness-constrained optimization)."
        )
        lines.append(
            "4. **Threshold adjustment**: Consider group-specific thresholds "
            "to equalize performance metrics."
        )
        lines.append(
            "5. **Monitor in production**: Track fairness metrics over time "
            "as data distributions shift."
        )
    else:
        lines.append(
            "No high-severity bias indicators detected. Continue monitoring "
            "fairness metrics in production."
        )

    report_text = "\n".join(lines)
    report_path = os.path.join(output_dir, "bias_report.md")
    with open(report_path, "w") as f:
        f.write(report_text)

    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect bias in ML model predictions across demographic groups",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --predictions preds.csv --demographics gender
  %(prog)s --predictions preds.csv --demographics gender age_group race
  %(prog)s --predictions preds.csv --demographics gender --disparity-threshold 0.05

The predictions CSV must contain:
  - 'actual' column: ground truth labels (binary: 0/1)
  - 'predicted' column: model predictions (0/1 or probabilities)
  - One or more demographic columns specified via --demographics
        """,
    )
    parser.add_argument(
        "--predictions", "-p", required=True,
        help="Path to CSV with actual, predicted, and demographic columns",
    )
    parser.add_argument(
        "--demographics", "-d", nargs="+", required=True,
        help="Column names for demographic attributes to analyze",
    )
    parser.add_argument(
        "--threshold", "-t", type=float, default=0.5,
        help="Classification threshold for probability predictions (default: 0.5)",
    )
    parser.add_argument(
        "--disparity-threshold", type=float, default=0.1,
        help="Threshold for flagging metric disparities (default: 0.1)",
    )
    parser.add_argument(
        "--output", "-o", default="./bias_output",
        help="Output directory for report and plots (default: ./bias_output)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Also output results as JSON",
    )

    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Load data
    print(f"Loading predictions from: {args.predictions}")
    df = pd.read_csv(args.predictions)
    df.columns = df.columns.str.lower()

    # Validate columns
    if "actual" not in df.columns or "predicted" not in df.columns:
        column_map = {
            "y_true": "actual", "y_pred": "predicted",
            "true": "actual", "pred": "predicted",
            "label": "actual", "prediction": "predicted",
            "target": "actual",
        }
        df = df.rename(columns=column_map)

    if "actual" not in df.columns or "predicted" not in df.columns:
        print(f"Error: CSV must contain 'actual' and 'predicted' columns. Found: {list(df.columns)}")
        sys.exit(1)

    # Check demographic columns exist
    missing_cols = [d for d in args.demographics if d.lower() not in df.columns]
    if missing_cols:
        print(f"Error: Demographic columns not found in CSV: {missing_cols}")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)

    y_true = df["actual"].values
    y_pred_raw = df["predicted"].values

    # Convert probabilities to binary predictions if needed
    unique_preds = np.unique(y_pred_raw[~np.isnan(y_pred_raw.astype(float))])
    is_probability = np.all((y_pred_raw >= 0) & (y_pred_raw <= 1)) and len(unique_preds) > 2
    if is_probability:
        print(f"Detected probability predictions. Applying threshold: {args.threshold}")
        y_pred = (y_pred_raw.astype(float) >= args.threshold).astype(int)
    else:
        y_pred = y_pred_raw.astype(int)

    # Ensure binary labels
    y_true = y_true.astype(int)

    print(f"Loaded {len(df):,} predictions")
    print(f"Base positive rate: {np.mean(y_true):.4f}")
    print(f"Model selection rate: {np.mean(y_pred):.4f}")
    print(f"Analyzing demographics: {args.demographics}\n")

    # Run analysis for each demographic
    analyses = []
    for demo_col in args.demographics:
        demo_col_lower = demo_col.lower()
        print(f"Analyzing: {demo_col}")
        analysis = analyze_demographic(
            df, y_true, y_pred, demo_col_lower, args.disparity_threshold
        )
        analyses.append(analysis)
        plot_group_metrics(analysis, args.output)

        # Print flag summary
        flags = analysis.get("flags", [])
        if flags:
            for flag in flags:
                severity_marker = "!!!" if flag["severity"] == "HIGH" else "!"
                print(f"  {severity_marker} [{flag['type']}] {flag['message']}")
        else:
            print("  No bias flags detected.")
        print()

    # Generate report
    report_path = generate_bias_report(analyses, args.output)
    print(f"Bias report saved to: {report_path}")

    if args.json:
        json_path = os.path.join(args.output, "bias_results.json")
        with open(json_path, "w") as f:
            json.dump(analyses, f, indent=2, default=str)
        print(f"JSON results saved to: {json_path}")

    # Summary
    total_flags = sum(len(a.get("flags", [])) for a in analyses)
    high_flags = sum(
        1 for a in analyses for f in a.get("flags", []) if f["severity"] == "HIGH"
    )
    print(f"\nTotal flags: {total_flags} ({high_flags} high severity)")
    if high_flags > 0:
        print("ACTION REQUIRED: High-severity bias detected. Review report for details.")
        sys.exit(2)


if __name__ == "__main__":
    main()
