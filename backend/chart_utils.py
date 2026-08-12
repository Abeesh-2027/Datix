import io
import base64

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

PALETTE = ["#63b3ed", "#9f7aea", "#68d391", "#f6ad55", "#fc8181", "#4fd1c5", "#f687b3", "#b794f4"]

CHART_GUIDE = [
    {"type": "Bar", "icon": "📊", "best_for": "Comparing a value across categories (e.g. Sales by Country)", "group": False},
    {"type": "Horizontal Bar", "icon": "📊", "best_for": "Ranking many categories with long labels (e.g. Top 10 Products)", "group": False},
    {"type": "Grouped Bar", "icon": "📊", "best_for": "Comparing sub-categories side by side (e.g. Sales by Country & Year)", "group": True},
    {"type": "Stacked Bar", "icon": "📊", "best_for": "Showing part-to-whole composition per category (e.g. Sales by Category)", "group": True},
    {"type": "100% Stacked Bar", "icon": "📊", "best_for": "Comparing percentage composition across categories", "group": True},
    {"type": "Line", "icon": "📈", "best_for": "Showing a trend over an ordered sequence or time", "group": False},
    {"type": "Area", "icon": "📈", "best_for": "Emphasizing magnitude of a trend over time", "group": False},
    {"type": "Scatter", "icon": "🔵", "best_for": "Relationship / correlation between two numeric variables", "group": False},
    {"type": "Pie", "icon": "🥧", "best_for": "Share of a whole across a few categories (≤8)", "group": False},
    {"type": "Donut", "icon": "🍩", "best_for": "Same as Pie, with a cleaner center for a total/label", "group": False},
    {"type": "Box", "icon": "📦", "best_for": "Spread, median and outliers of one numeric column", "group": False},
]

GROUPED_TYPES = {"Grouped Bar", "Stacked Bar", "100% Stacked Bar"}


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _style_axes(ax):
    ax.tick_params(colors="#2d3748", labelsize=8)
    for spine in ax.spines.values():
        spine.set_color("#e2e8f0")


def get_columns(df: pd.DataFrame) -> dict:
    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    detected_dates = []
    for col in df.select_dtypes(include="object").columns:
        try:
            pd.to_datetime(df[col].dropna().head(10))
            detected_dates.append(col)
        except Exception:
            pass
    date_cols = list(df.select_dtypes(include="datetime64").columns) + detected_dates
    return {
        "all": df.columns.tolist(),
        "numeric": num_cols,
        "categorical": cat_cols,
        "date": date_cols,
    }


def basic_chart(df: pd.DataFrame, chart_type: str, x_col: str, y_col: str,
                 group_col: str = None, color_idx: int = 0, top_n: int = 50, show_grid: bool = True) -> str:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor("#f7f9fc")
    ax.set_facecolor("#edf2f7")
    color = PALETTE[color_idx % len(PALETTE)]
    data = df.head(top_n)

    if chart_type in GROUPED_TYPES:
        if not group_col:
            raise ValueError(f"'{chart_type}' needs a grouping column.")
        pivot = data.groupby([x_col, group_col])[y_col].sum().unstack(fill_value=0)
        # keep the chart readable: cap categories and series shown
        pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index[:25]]
        pivot = pivot[pivot.sum(axis=0).sort_values(ascending=False).index[:8]]
        x = np.arange(len(pivot.index))

        if chart_type == "Grouped Bar":
            n = len(pivot.columns)
            w = 0.8 / max(n, 1)
            for i, col in enumerate(pivot.columns):
                ax.bar(x + i * w - 0.4 + w / 2, pivot[col], width=w,
                       color=PALETTE[i % len(PALETTE)], label=str(col), edgecolor="#ffffff", linewidth=0.4)
        else:
            plot_pivot = pivot
            if chart_type == "100% Stacked Bar":
                row_sums = pivot.sum(axis=1).replace(0, np.nan)
                plot_pivot = pivot.div(row_sums, axis=0).fillna(0) * 100
            bottom = np.zeros(len(plot_pivot))
            for i, col in enumerate(plot_pivot.columns):
                ax.bar(x, plot_pivot[col], bottom=bottom, width=0.6,
                       color=PALETTE[i % len(PALETTE)], label=str(col), edgecolor="#ffffff", linewidth=0.4)
                bottom += plot_pivot[col].values

        ax.set_xticks(x)
        ax.set_xticklabels([str(v) for v in pivot.index], rotation=45, ha="right")
        ax.legend(frameon=False, labelcolor="#2d3748", fontsize=8, ncol=min(4, len(pivot.columns)))
        ax.set_xlabel(x_col, color="#4a5568", fontsize=9)
        ax.set_ylabel(("% of " + y_col) if chart_type == "100% Stacked Bar" else y_col, color="#4a5568", fontsize=9)
        _style_axes(ax)
        if show_grid:
            ax.grid(axis="y", color="#cbd5e0", linewidth=0.4, zorder=0)
        plt.tight_layout()
        return _fig_to_base64(fig)

    if chart_type == "Bar":
        ax.bar(data[x_col].astype(str), data[y_col], color=color, edgecolor="#ffffff", linewidth=0.5)
        plt.xticks(rotation=45, ha="right")
    elif chart_type == "Horizontal Bar":
        ax.barh(data[x_col].astype(str), data[y_col], color=color, edgecolor="#ffffff", linewidth=0.5)
    elif chart_type == "Line":
        ax.plot(data[x_col], data[y_col], color=color, marker="o", markersize=4, linewidth=2)
        plt.xticks(rotation=45, ha="right")
    elif chart_type == "Area":
        ax.fill_between(range(len(data)), data[y_col], color=color, alpha=0.35)
        ax.plot(range(len(data)), data[y_col], color=color, linewidth=2)
    elif chart_type == "Scatter":
        ax.scatter(data[x_col], data[y_col], color=color, alpha=0.65, s=60, edgecolors="#ffffff", linewidths=0.4)
    elif chart_type in ("Pie", "Donut"):
        pie_d = df.groupby(x_col)[y_col].sum().head(8)
        wedge_kw = {"linewidth": 1.5, "edgecolor": "#ffffff"}
        if chart_type == "Donut":
            wedge_kw["width"] = 0.55
        ax.pie(pie_d, labels=pie_d.index, autopct="%1.1f%%", colors=PALETTE[:len(pie_d)],
               wedgeprops=wedge_kw, textprops={"color": "#2d3748", "fontsize": 9})
    elif chart_type == "Box":
        ax.boxplot([df[y_col].dropna()], patch_artist=True,
                   boxprops=dict(facecolor=color, color="#2b6cb0", alpha=0.8),
                   medianprops=dict(color="#ffffff", linewidth=2),
                   whiskerprops=dict(color="#4a5568"), capprops=dict(color="#4a5568"),
                   flierprops=dict(marker="o", color=color, alpha=0.5))
        ax.set_xticklabels([y_col])
    else:
        raise ValueError(f"Unknown chart type: {chart_type}")

    if chart_type not in ("Pie", "Donut", "Box"):
        ax.set_xlabel(x_col, color="#4a5568", fontsize=9)
        ax.set_ylabel(y_col, color="#4a5568", fontsize=9)
    _style_axes(ax)
    if show_grid and chart_type not in ("Pie", "Donut"):
        ax.grid(axis="y", color="#cbd5e0", linewidth=0.4, zorder=0)
    plt.tight_layout()
    return _fig_to_base64(fig)


def distribution_chart(df: pd.DataFrame, col: str, bins: int = 25) -> dict:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor("#f7f9fc")
    series = df[col].dropna()

    axes[0].set_facecolor("#edf2f7")
    axes[0].hist(series, bins=bins, color="#63b3ed", edgecolor="#ffffff", linewidth=0.4, alpha=0.85, density=True)
    try:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(series)
        xs = np.linspace(series.min(), series.max(), 200)
        axes[0].plot(xs, kde(xs), color="#9f7aea", linewidth=2.5, label="KDE")
        axes[0].legend(frameon=False, labelcolor="#2d3748")
    except Exception:
        pass
    axes[0].set_title("Histogram + KDE", color="#2d3748", fontsize=10, pad=10)
    axes[0].set_xlabel(col, color="#4a5568", fontsize=9)
    axes[0].tick_params(colors="#2d3748")
    for sp in axes[0].spines.values():
        sp.set_color("#e2e8f0")

    axes[1].set_facecolor("#edf2f7")
    try:
        parts = axes[1].violinplot(series.dropna(), positions=[0], showmedians=False)
        for pc in parts["bodies"]:
            pc.set_facecolor("#63b3ed")
            pc.set_alpha(0.4)
        for partname in ("cbars", "cmins", "cmaxes"):
            if partname in parts:
                parts[partname].set_color("#4a5568")
    except Exception:
        pass
    axes[1].boxplot(series.dropna(), positions=[0], widths=0.15, patch_artist=True,
                     boxprops=dict(facecolor="#9f7aea", alpha=0.7),
                     medianprops=dict(color="#ffffff", linewidth=2.5),
                     whiskerprops=dict(color="#4a5568"), capprops=dict(color="#4a5568"),
                     flierprops=dict(marker=".", color="#63b3ed", alpha=0.4))
    axes[1].set_title("Violin + Box Plot", color="#2d3748", fontsize=10, pad=10)
    axes[1].set_xticks([0])
    axes[1].set_xticklabels([col], fontsize=9, color="#2d3748")
    axes[1].tick_params(axis="y", colors="#2d3748")
    for sp in axes[1].spines.values():
        sp.set_color("#e2e8f0")

    plt.tight_layout()
    image = _fig_to_base64(fig)

    stats = series.describe().rename("Value").reset_index()
    stats.columns = ["Statistic", "Value"]
    extra = pd.DataFrame({
        "Statistic": ["skewness", "kurtosis", "missing"],
        "Value": [round(series.skew(), 4), round(series.kurtosis(), 4), int(df[col].isnull().sum())]
    })
    table = pd.concat([stats, extra], ignore_index=True)
    table["Value"] = table["Value"].astype(float).round(4)
    return {"image": image, "stats": table.to_dict(orient="records")}


def correlation_chart(df: pd.DataFrame, cols: list, method: str = "pearson") -> dict:
    corr_matrix = df[cols].corr(method=method)
    fig, ax = plt.subplots(figsize=(max(6, len(cols) * 0.9), max(5, len(cols) * 0.8)))
    fig.patch.set_facecolor("#f7f9fc")

    cmap = LinearSegmentedColormap.from_list("custom", ["#fc8181", "#ffffff", "#63b3ed"])
    mask = np.zeros_like(corr_matrix, dtype=bool)
    mask[np.triu_indices_from(mask)] = True

    sns.heatmap(corr_matrix, mask=mask, cmap=cmap, vmin=-1, vmax=1, annot=True, fmt=".2f",
                annot_kws={"size": 8, "color": "#2d3748"}, ax=ax, linewidths=0.5, linecolor="#e2e8f0",
                cbar_kws={"shrink": 0.8})
    ax.tick_params(colors="#2d3748", labelsize=8)
    plt.tight_layout()
    image = _fig_to_base64(fig)

    pairs = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i + 1, len(corr_matrix.columns)):
            pairs.append({
                "Column A": corr_matrix.columns[i],
                "Column B": corr_matrix.columns[j],
                "Correlation": round(float(corr_matrix.iloc[i, j]), 4),
            })
    pairs.sort(key=lambda r: abs(r["Correlation"]), reverse=True)
    return {"image": image, "pairs": pairs}


def multivariable_chart(df: pd.DataFrame, x: str, y: str, hue: str = None, size_col: str = None) -> str:
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#f7f9fc")
    ax.set_facecolor("#edf2f7")

    sizes = None
    if size_col and size_col != "None":
        raw_s = df[size_col].fillna(0).abs()
        if raw_s.max() > 0:
            sizes = 30 + (raw_s / raw_s.max()) * 200

    if hue and hue != "None":
        for i, (grp, gdf) in enumerate(df.groupby(hue)):
            s = sizes.loc[gdf.index] if sizes is not None else 60
            ax.scatter(gdf[x], gdf[y], label=str(grp), color=PALETTE[i % len(PALETTE)],
                       alpha=0.65, s=s, edgecolors="#ffffff", linewidths=0.3)
        ax.legend(frameon=False, labelcolor="#2d3748", fontsize=8, ncol=3)
    else:
        ax.scatter(df[x], df[y], s=sizes if sizes is not None else 60,
                   color="#63b3ed", alpha=0.65, edgecolors="#ffffff", linewidths=0.3)

    try:
        z = np.polyfit(df[x].dropna(), df[y].dropna(), 1)
        p = np.poly1d(z)
        xs = np.linspace(df[x].min(), df[x].max(), 100)
        ax.plot(xs, p(xs), color="#fc8181", linewidth=1.8, linestyle="--", label="Trend")
    except Exception:
        pass

    ax.set_xlabel(x, color="#4a5568", fontsize=9)
    ax.set_ylabel(y, color="#4a5568", fontsize=9)
    _style_axes(ax)
    ax.grid(color="#cbd5e0", linewidth=0.4, zorder=0)
    plt.tight_layout()
    return _fig_to_base64(fig)


def timeseries_chart(df: pd.DataFrame, date_col: str, val_col: str, agg: str = "sum") -> str:
    ts_df = df[[date_col, val_col]].copy()
    ts_df[date_col] = pd.to_datetime(ts_df[date_col], errors="coerce")
    ts_df = ts_df.dropna(subset=[date_col])
    ts_df = ts_df.groupby(date_col)[val_col].agg(agg).reset_index().sort_values(date_col)

    fig, ax = plt.subplots(figsize=(11, 4))
    fig.patch.set_facecolor("#f7f9fc")
    ax.set_facecolor("#edf2f7")
    ax.fill_between(ts_df[date_col], ts_df[val_col], color="#63b3ed", alpha=0.2)
    ax.plot(ts_df[date_col], ts_df[val_col], color="#63b3ed", linewidth=2, marker="o", markersize=3)

    if len(ts_df) > 5:
        roll_w = min(7, len(ts_df) // 3)
        ts_df["rolling"] = ts_df[val_col].rolling(roll_w, center=True).mean()
        ax.plot(ts_df[date_col], ts_df["rolling"], color="#9f7aea", linewidth=2, linestyle="--",
                label=f"{roll_w}-period MA")
        ax.legend(frameon=False, labelcolor="#2d3748", fontsize=8)

    ax.set_xlabel(date_col, color="#4a5568", fontsize=9)
    ax.set_ylabel(f"{agg}({val_col})", color="#4a5568", fontsize=9)
    _style_axes(ax)
    plt.xticks(rotation=45, ha="right")
    ax.grid(axis="y", color="#cbd5e0", linewidth=0.4, zorder=0)
    plt.tight_layout()
    return _fig_to_base64(fig)


def missing_heatmap(df: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(max(6, min(df.shape[1] * 0.6, 18)), 3.5))
    fig.patch.set_facecolor("#f7f9fc")
    ax.set_facecolor("#edf2f7")
    missing_matrix = df.isnull().astype(int)
    sns.heatmap(missing_matrix.T, cmap=sns.color_palette(["#e2e8f0", "#63b3ed"], as_cmap=True), ax=ax,
                cbar=False, linewidths=0, yticklabels=True, xticklabels=False)
    ax.tick_params(colors="#2d3748", labelsize=8)
    ax.set_ylabel("")
    ax.set_xlabel("Rows →", color="#4a5568", fontsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    plt.tight_layout()
    return _fig_to_base64(fig)


def dtype_pie(df: pd.DataFrame) -> str:
    dtype_counts = df.dtypes.astype(str).value_counts()
    fig, ax = plt.subplots(figsize=(4, 3.5))
    fig.patch.set_facecolor("#f7f9fc")
    ax.set_facecolor("#f7f9fc")
    wedges, texts, autotexts = ax.pie(dtype_counts.values, labels=dtype_counts.index, autopct="%1.0f%%",
                                       colors=PALETTE[:len(dtype_counts)], startangle=140,
                                       textprops={"color": "#2d3748", "fontsize": 9},
                                       wedgeprops={"linewidth": 1.5, "edgecolor": "#ffffff"})
    for at in autotexts:
        at.set_color("#1a202c")
        at.set_fontsize(9)
    plt.tight_layout()
    return _fig_to_base64(fig)


def missing_comparison_chart(df_raw: pd.DataFrame, df_clean: pd.DataFrame):
    miss_before = df_raw.isnull().sum()
    miss_after = df_clean.reindex(columns=df_raw.columns).isnull().sum()
    compare = pd.DataFrame({"Before": miss_before, "After": miss_after}).fillna(0)
    compare = compare[compare["Before"] > 0]
    if compare.empty:
        return None
    fig, ax2 = plt.subplots(figsize=(max(6, len(compare) * 0.9), 4))
    fig.patch.set_facecolor("#f7f9fc")
    ax2.set_facecolor("#edf2f7")
    x = np.arange(len(compare))
    w = 0.38
    ax2.bar(x - w / 2, compare["Before"], width=w, color="#fc8181", label="Before", zorder=3)
    ax2.bar(x + w / 2, compare["After"], width=w, color="#68d391", label="After", zorder=3)
    ax2.set_xticks(x)
    ax2.set_xticklabels(compare.index, rotation=40, ha="right", color="#2d3748", fontsize=9)
    ax2.tick_params(axis="y", colors="#2d3748")
    ax2.set_ylabel("Missing count", color="#4a5568")
    ax2.grid(axis="y", color="#cbd5e0", linewidth=0.5, zorder=0)
    for spine in ax2.spines.values():
        spine.set_color("#e2e8f0")
    ax2.legend(frameon=False, labelcolor="#2d3748")
    plt.tight_layout()
    return _fig_to_base64(fig)
