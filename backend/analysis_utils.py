import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns

from chart_utils import _fig_to_base64, _style_axes, PALETTE


def _clean_records(df: pd.DataFrame):
    """Convert a DataFrame to JSON-safe records (NaN -> None, numpy types -> python)."""
    return df.replace({np.nan: None}).to_dict(orient="records")


def overview(df: pd.DataFrame) -> dict:
    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    total_cells = df.shape[0] * df.shape[1]
    missing = int(df.isnull().sum().sum())
    dups = int(df.duplicated().sum())
    mem = round(df.memory_usage(deep=True).sum() / 1024, 2)

    summary = {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "missing": missing,
        "missing_pct": round(missing / total_cells * 100, 1) if total_cells else 0,
        "duplicates": dups,
        "memory_kb": mem,
    }

    numeric_stats = []
    if num_cols:
        desc = df[num_cols].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).T
        desc["skewness"] = df[num_cols].skew()
        desc["kurtosis"] = df[num_cols].kurtosis()
        desc["missing"] = df[num_cols].isnull().sum()
        desc["missing_%"] = (df[num_cols].isnull().mean() * 100).round(2)
        desc["unique"] = df[num_cols].nunique()
        desc = desc.round(4).reset_index().rename(columns={"index": "column"})
        numeric_stats = _clean_records(desc)

    categorical_stats = []
    for col in cat_cols:
        s = df[col]
        top = s.value_counts()
        categorical_stats.append({
            "Column": col,
            "Unique Values": int(s.nunique()),
            "Missing": int(s.isnull().sum()),
            "Missing %": round(s.isnull().mean() * 100, 2),
            "Top Value": str(top.index[0]) if len(top) else "N/A",
            "Top Freq": int(top.iloc[0]) if len(top) else 0,
            "Top Freq %": round(top.iloc[0] / len(s) * 100, 1) if len(top) else 0,
        })

    return {"summary": summary, "numeric_stats": numeric_stats, "categorical_stats": categorical_stats}


def group_analysis(df: pd.DataFrame, group_by: str, value_col: str, agg: str = "mean", top_n: int = 10) -> dict:
    grouped = df.groupby(group_by)[value_col].agg(agg).reset_index()
    grouped.columns = [group_by, f"{agg}_{value_col}"]
    grouped = grouped.sort_values(f"{agg}_{value_col}", ascending=False).head(top_n)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor("#f7f9fc")
    ax.set_facecolor("#edf2f7")
    colors = (PALETTE * (len(grouped) // len(PALETTE) + 1))[:len(grouped)]
    bars = ax.bar(grouped[group_by].astype(str), grouped[f"{agg}_{value_col}"], color=colors,
                   edgecolor="#ffffff", linewidth=0.5)
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h * 1.01, f"{h:,.1f}", ha="center", va="bottom",
                fontsize=7.5, color="#2d3748")
    ax.set_xlabel(group_by, color="#4a5568", fontsize=9)
    ax.set_ylabel(f"{agg}({value_col})", color="#4a5568", fontsize=9)
    _style_axes(ax)
    plt.xticks(rotation=40, ha="right")
    ax.grid(axis="y", color="#cbd5e0", linewidth=0.4, zorder=0)
    plt.tight_layout()
    image = _fig_to_base64(fig)

    return {"image": image, "table": _clean_records(grouped.round(4))}


def group_heatmap(df: pd.DataFrame, group_by: str, heat_cols: list) -> str:
    heat_df = df.groupby(group_by)[heat_cols].mean().head(15)
    fig, ax = plt.subplots(figsize=(max(8, len(heat_cols) * 1.2), max(4, len(heat_df) * 0.5)))
    fig.patch.set_facecolor("#f7f9fc")
    sns.heatmap(heat_df, annot=True, fmt=".1f", cmap=sns.color_palette("Blues", as_cmap=True), ax=ax,
                linewidths=0.4, linecolor="#e2e8f0", annot_kws={"size": 8}, cbar_kws={"shrink": 0.7})
    ax.tick_params(colors="#2d3748", labelsize=8)
    plt.tight_layout()
    return _fig_to_base64(fig)


def outlier_detection(df: pd.DataFrame, col: str, method: str = "IQR", threshold: float = 1.5) -> dict:
    series = df[col].dropna()

    if method == "IQR":
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        outlier_mask = (series < q1 - threshold * iqr) | (series > q3 + threshold * iqr)
    elif method == "Z-Score":
        z_scores = np.abs((series - series.mean()) / series.std())
        outlier_mask = z_scores > threshold
    elif method == "Modified Z-Score":
        median = series.median()
        mad = (series - median).abs().median()
        modified_z = 0.6745 * (series - median) / (mad + 1e-9)
        outlier_mask = modified_z.abs() > threshold
    else:
        raise ValueError(f"Unknown method: {method}")

    n_out = int(outlier_mask.sum())
    pct_out = round(n_out / len(series) * 100, 2) if len(series) else 0

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor("#f7f9fc")

    axes[0].set_facecolor("#edf2f7")
    x_idx = np.arange(len(series))
    axes[0].scatter(x_idx[~outlier_mask], series[~outlier_mask], color="#63b3ed", alpha=0.6, s=20, label="Normal")
    axes[0].scatter(x_idx[outlier_mask], series[outlier_mask], color="#fc8181", alpha=0.9, s=40, marker="X",
                     label=f"Outlier ({n_out})")
    axes[0].set_title("Outlier Scatter Plot", color="#2d3748", fontsize=10)
    axes[0].legend(frameon=False, labelcolor="#2d3748", fontsize=8)
    axes[0].tick_params(colors="#2d3748")
    for sp in axes[0].spines.values():
        sp.set_color("#e2e8f0")

    axes[1].set_facecolor("#edf2f7")
    axes[1].boxplot(series, patch_artist=True, vert=True,
                     boxprops=dict(facecolor="#63b3ed", alpha=0.6),
                     medianprops=dict(color="#ffffff", linewidth=2),
                     flierprops=dict(marker="X", color="#fc8181", markersize=5, alpha=0.7),
                     whiskerprops=dict(color="#4a5568"), capprops=dict(color="#4a5568"))
    axes[1].set_title("Box Plot", color="#2d3748", fontsize=10)
    axes[1].tick_params(colors="#2d3748")
    axes[1].set_xticklabels([col], fontsize=8, color="#2d3748")
    for sp in axes[1].spines.values():
        sp.set_color("#e2e8f0")

    plt.tight_layout()
    image = _fig_to_base64(fig)

    mean_excl = series[~outlier_mask].mean() if n_out < len(series) else None
    outlier_rows = _clean_records(df[outlier_mask.reindex(df.index, fill_value=False)]) if n_out else []

    return {
        "image": image,
        "n_outliers": n_out,
        "pct_outliers": pct_out,
        "n_normal": len(series) - n_out,
        "mean_excl_outliers": round(mean_excl, 2) if mean_excl is not None else None,
        "outlier_rows": outlier_rows[:500],
    }


def data_profile(df: pd.DataFrame) -> list:
    rows = []
    for col in df.columns:
        s = df[col]
        row = {
            "Column": col,
            "Type": str(s.dtype),
            "Non-Null": int(s.count()),
            "Null": int(s.isnull().sum()),
            "Null %": round(s.isnull().mean() * 100, 2),
            "Unique": int(s.nunique()),
            "Unique %": round(s.nunique() / len(s) * 100, 2) if len(s) else 0,
        }
        if pd.api.types.is_numeric_dtype(s):
            row.update({
                "Min": round(float(s.min()), 4) if s.count() else None,
                "Max": round(float(s.max()), 4) if s.count() else None,
                "Mean": round(float(s.mean()), 4) if s.count() else None,
                "Std": round(float(s.std()), 4) if s.count() else None,
                "Skew": round(float(s.skew()), 4) if s.count() else None,
                "Top Values": "-",
            })
        else:
            row.update({"Min": "-", "Max": "-", "Mean": "-", "Std": "-", "Skew": "-"})
            if s.nunique() < 20:
                row["Top Values"] = ", ".join(str(v) for v in s.value_counts().head(3).index)
            else:
                row["Top Values"] = f"(top: {s.value_counts().index[0] if s.count() > 0 else 'N/A'})"
        rows.append(row)
    return rows


def value_counts_chart(df: pd.DataFrame, col: str, top_n: int = 15) -> dict:
    vc = df[col].value_counts().head(top_n)
    if len(vc) == 0:
        return {"image": None, "table": []}
    fig, ax = plt.subplots(figsize=(10, 3.5))
    fig.patch.set_facecolor("#f7f9fc")
    ax.set_facecolor("#edf2f7")
    colors = (PALETTE * (len(vc) // len(PALETTE) + 1))[:len(vc)]
    ax.barh(vc.index.astype(str)[::-1], vc.values[::-1], color=colors, edgecolor="#ffffff", linewidth=0.4)
    ax.tick_params(colors="#2d3748", labelsize=8)
    ax.set_xlabel("Count", color="#4a5568", fontsize=9)
    for sp in ax.spines.values():
        sp.set_color("#e2e8f0")
    ax.grid(axis="x", color="#cbd5e0", linewidth=0.4)
    plt.tight_layout()
    image = _fig_to_base64(fig)
    table = [{"value": str(k), "count": int(v)} for k, v in vc.items()]
    return {"image": image, "table": table}


def kpi_dashboard(df: pd.DataFrame, kpi_cols: list, filter_col: str = None, filter_val=None) -> dict:
    df_kpi = df.copy()
    if filter_col and filter_col != "None" and filter_val is not None:
        df_kpi = df_kpi[df_kpi[filter_col].astype(str) == str(filter_val)]

    cards = []
    for col in kpi_cols:
        total = df_kpi[col].sum()
        avg = df_kpi[col].mean()
        cards.append({"column": col, "total": round(float(total), 2), "avg": round(float(avg), 2)})

    n = len(kpi_cols)
    ncols_grid = min(n, 3) if n else 1
    nrows_grid = (n + ncols_grid - 1) // ncols_grid if n else 1

    fig = plt.figure(figsize=(ncols_grid * 4.5, nrows_grid * 2.5))
    fig.patch.set_facecolor("#f7f9fc")
    gs = gridspec.GridSpec(nrows_grid, ncols_grid, hspace=0.55, wspace=0.35)

    for i, col in enumerate(kpi_cols):
        ax = fig.add_subplot(gs[i // ncols_grid, i % ncols_grid])
        ax.set_facecolor("#edf2f7")
        spark = df_kpi[col].dropna().reset_index(drop=True)
        ax.fill_between(range(len(spark)), spark, alpha=0.25, color=PALETTE[i % len(PALETTE)])
        ax.plot(range(len(spark)), spark, color=PALETTE[i % len(PALETTE)], linewidth=1.5)
        ax.set_title(col, color="#2d3748", fontsize=9, pad=4)
        ax.tick_params(colors="#2d3748", labelsize=7)
        ax.set_xticks([])
        for sp in ax.spines.values():
            sp.set_color("#e2e8f0")

    plt.tight_layout()
    image = _fig_to_base64(fig)
    return {"cards": cards, "image": image, "filtered_rows": len(df_kpi)}
