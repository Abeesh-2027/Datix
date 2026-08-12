import pandas as pd
import numpy as np
from scipy import stats
import re



def get_dataset_overview(df: pd.DataFrame) -> dict:
    """Return high-level stats about the dataset."""
    return {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "total_cells": df.shape[0] * df.shape[1],
        "missing_cells": int(df.isnull().sum().sum()),
        "missing_pct": round(df.isnull().sum().sum() / (df.shape[0] * df.shape[1]) * 100, 2),
        "duplicate_rows": int(df.duplicated().sum()),
        "memory_usage_kb": round(df.memory_usage(deep=True).sum() / 1024, 2),
    }


def get_column_report(df: pd.DataFrame) -> pd.DataFrame:
    """Per-column diagnostics."""
    records = []
    for col in df.columns:
        s = df[col]
        missing = int(s.isnull().sum())
        dtype = str(s.dtype)
        unique = int(s.nunique(dropna=True))
        pct_missing = round(missing / len(s) * 100, 2)

        issues = []
        if missing > 0:
            issues.append(f"{missing} missing ({pct_missing}%)")
        if unique == 1:
            issues.append("constant column")
        if dtype == "object":
            numeric_coercible = pd.to_numeric(s.dropna(), errors="coerce").notna().sum()
            if 0 < numeric_coercible < s.dropna().shape[0]:
                issues.append("mixed types")
            if s.dropna().apply(lambda x: str(x) != str(x).strip()).any():
                issues.append("leading/trailing whitespace")
        if dtype in ("float64", "int64"):
            z = np.abs(stats.zscore(s.dropna()))
            n_outliers = int((z > 3).sum())
            if n_outliers:
                issues.append(f"{n_outliers} outlier(s)")

        records.append({
            "Column": col,
            "Dtype": dtype,
            "Missing": missing,
            "Missing %": pct_missing,
            "Unique": unique,
            "Issues": "; ".join(issues) if issues else "✓ OK",
        })
    return pd.DataFrame(records)



def remove_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    return df, f"Removed {removed} duplicate row(s)."


def drop_empty_rows(df: pd.DataFrame, threshold: float = 1.0) -> tuple[pd.DataFrame, str]:
    before = len(df)
    min_valid = int(np.ceil(df.shape[1] * (1 - threshold + 0.001)))
    df = df.dropna(thresh=max(1, min_valid))
    removed = before - len(df)
    return df, f"Dropped {removed} row(s) that were entirely (or mostly) empty."


def drop_constant_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    const_cols = [c for c in df.columns if df[c].nunique(dropna=True) <= 1]
    df = df.drop(columns=const_cols)
    return df, f"Dropped {len(const_cols)} constant column(s): {const_cols}."


def fix_column_names(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    old = df.columns.tolist()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )
    new = df.columns.tolist()
    changed = [(o, n) for o, n in zip(old, new) if o != n]
    return df, f"Renamed {len(changed)} column(s). Examples: {changed[:5]}"


def strip_whitespace(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    obj_cols = df.select_dtypes(include="object").columns
    count = 0
    for col in obj_cols:
        before = df[col].copy()
        df[col] = df[col].str.strip()
        count += (before != df[col]).sum()
    return df, f"Stripped whitespace in {len(obj_cols)} text column(s) — {count} cell(s) changed."


def standardize_text_case(df: pd.DataFrame, case: str = "lower") -> tuple[pd.DataFrame, str]:
    obj_cols = df.select_dtypes(include="object").columns
    for col in obj_cols:
        if case == "lower":
            df[col] = df[col].str.lower()
        elif case == "upper":
            df[col] = df[col].str.upper()
        elif case == "title":
            df[col] = df[col].str.title()
    return df, f"Converted {len(obj_cols)} text column(s) to {case} case."


def remove_duplicate_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Drop columns that are exact duplicates of an earlier column (by value, not name)."""
    seen = {}
    dupes = []
    keep_cols = []
    for col in df.columns:
        fingerprint = pd.util.hash_pandas_object(df[col], index=False).sum()
        if fingerprint in seen and df[col].equals(df[seen[fingerprint]]):
            dupes.append(col)
        else:
            seen[fingerprint] = col
            keep_cols.append(col)
    df = df[keep_cols]
    return df, f"Removed {len(dupes)} duplicate column(s): {dupes}."


def strip_currency_percent(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Strip common currency symbols (₹ $ € £ ¥) and % signs so the values can be coerced to numeric."""
    obj_cols = df.select_dtypes(include="object").columns
    cleaned = []
    pattern = r"[₹$€£¥,%\s]"
    for col in obj_cols:
        sample = df[col].dropna().astype(str).head(50)
        if sample.str.contains(r"[₹$€£¥%]").mean() >= 0.5:
            df[col] = df[col].astype(str).str.replace(pattern, "", regex=True)
            cleaned.append(col)
    return df, f"Stripped currency/percent symbols from {len(cleaned)} column(s): {cleaned}."


def convert_boolean_like(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Convert text columns like yes/no, true/false, y/n into real booleans."""
    obj_cols = df.select_dtypes(include="object").columns
    bool_map = {"yes": True, "no": False, "true": True, "false": False, "y": True, "n": False}
    converted = []
    for col in obj_cols:
        vals = set(df[col].dropna().astype(str).str.strip().str.lower().unique())
        if vals and vals.issubset(bool_map.keys()):
            df[col] = df[col].astype(str).str.strip().str.lower().map(bool_map)
            converted.append(col)
    return df, f"Converted {len(converted)} column(s) to boolean: {converted}."


def coerce_numeric_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    converted = []
    for col in df.select_dtypes(include="object").columns:
        converted_series = pd.to_numeric(df[col].str.replace(",", "").str.strip(), errors="coerce")
        ratio = converted_series.notna().sum() / max(df[col].notna().sum(), 1)
        if ratio >= 0.8:
            df[col] = converted_series
            converted.append(col)
    return df, f"Coerced {len(converted)} column(s) to numeric: {converted}."


def format_date_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """
    Convert all datetime64 columns (and any object columns that look like dates)
    to clean YYYY-MM-DD string format — removes the ' 00:00:00' time component.
    """
    converted = []

    
    dt_cols = df.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns.tolist()

   
    for col in df.select_dtypes(include="object").columns:
        if col in dt_cols:
            continue
        sample = df[col].dropna().head(50)
        parsed = pd.to_datetime(sample, errors="coerce")
        if parsed.notna().sum() / max(len(sample), 1) >= 0.8:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            dt_cols.append(col)

    for col in dt_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
        converted.append(col)

    return df, f"Formatted {len(converted)} date column(s) to YYYY-MM-DD: {converted}."


def parse_dates(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """
    Parse object columns that look like dates into datetime64,
    then immediately format them as YYYY-MM-DD strings (no time component).
    """
    converted = []
    for col in df.select_dtypes(include="object").columns:
        sample = df[col].dropna().head(50)
        parsed = pd.to_datetime(sample, errors="coerce")
        if parsed.notna().sum() / max(len(sample), 1) >= 0.8:
            # Parse then strip time → clean date string
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
            converted.append(col)
    return df, f"Parsed & formatted {len(converted)} column(s) as date (YYYY-MM-DD): {converted}."


def fill_missing_numeric(df: pd.DataFrame, strategy: str = "median") -> tuple[pd.DataFrame, str]:
    num_cols = df.select_dtypes(include=[np.number]).columns
    total_filled = 0
    for col in num_cols:
        missing = df[col].isnull().sum()
        if missing == 0:
            continue
        if strategy == "mean":
            df[col] = df[col].fillna(df[col].mean())
        elif strategy == "median":
            df[col] = df[col].fillna(df[col].median())
        elif strategy == "zero":
            df[col] = df[col].fillna(0)
        elif strategy == "ffill":
            df[col] = df[col].ffill()
        elif strategy == "bfill":
            df[col] = df[col].bfill()
        total_filled += missing
    return df, f"Filled {total_filled} missing numeric value(s) using '{strategy}'."


def fill_missing_categorical(df: pd.DataFrame, strategy: str = "mode") -> tuple[pd.DataFrame, str]:
    obj_cols = df.select_dtypes(include="object").columns
    total_filled = 0
    for col in obj_cols:
        missing = df[col].isnull().sum()
        if missing == 0:
            continue
        if strategy == "mode":
            mode_val = df[col].mode()
            df[col] = df[col].fillna(mode_val[0] if len(mode_val) else "Unknown")
        elif strategy == "unknown":
            df[col] = df[col].fillna("Unknown")
        elif strategy == "ffill":
            df[col] = df[col].ffill()
        elif strategy == "bfill":
            df[col] = df[col].bfill()
        total_filled += missing
    return df, f"Filled {total_filled} missing categorical value(s) using '{strategy}'."


def remove_outliers_zscore(df: pd.DataFrame, threshold: float = 3.0) -> tuple[pd.DataFrame, str]:
    num_cols = df.select_dtypes(include=[np.number]).columns
    before = len(df)
    if len(num_cols) == 0:
        return df, "No numeric columns — outlier removal skipped."
    z_scores = np.abs(stats.zscore(df[num_cols].dropna()))
    mask = (z_scores < threshold).all(axis=1)
    valid_idx = df[num_cols].dropna().index[mask]
    df = df.loc[df.index.isin(valid_idx) | df[num_cols].isnull().any(axis=1)]
    removed = before - len(df)
    return df, f"Removed {removed} row(s) with Z-score > {threshold} in numeric columns."


def cap_outliers_iqr(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    num_cols = df.select_dtypes(include=[np.number]).columns
    capped = 0
    for col in num_cols:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        out = ((df[col] < lower) | (df[col] > upper)).sum()
        df[col] = df[col].clip(lower=lower, upper=upper)
        capped += out
    return df, f"Capped {capped} outlier value(s) in {len(num_cols)} numeric column(s) using IQR."


def remove_html_tags(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    obj_cols = df.select_dtypes(include="object").columns
    count = 0
    for col in obj_cols:
        before = df[col].copy()
        df[col] = df[col].str.replace(r"<[^>]+>", "", regex=True)
        count += (before != df[col]).sum()
    return df, f"Removed HTML tags from {len(obj_cols)} text column(s) — {count} cell(s) changed."


def remove_special_characters(df: pd.DataFrame, keep_pattern: str = r"[^a-zA-Z0-9\s\.,\-_]") -> tuple[pd.DataFrame, str]:
    obj_cols = df.select_dtypes(include="object").columns
    count = 0
    for col in obj_cols:
        before = df[col].copy()
        df[col] = df[col].str.replace(keep_pattern, "", regex=True)
        count += (before != df[col]).sum()
    return df, f"Removed special characters from {len(obj_cols)} text column(s) — {count} cell(s) changed."


def normalize_numeric(df: pd.DataFrame, method: str = "minmax") -> tuple[pd.DataFrame, str]:
    num_cols = df.select_dtypes(include=[np.number]).columns
    for col in num_cols:
        if method == "minmax":
            mn, mx = df[col].min(), df[col].max()
            if mx != mn:
                df[col] = (df[col] - mn) / (mx - mn)
        elif method == "zscore":
            mu, sigma = df[col].mean(), df[col].std()
            if sigma != 0:
                df[col] = (df[col] - mu) / sigma
    return df, f"Normalized {len(num_cols)} numeric column(s) using '{method}'."


def drop_high_missing_columns(df: pd.DataFrame, threshold: float = 0.5) -> tuple[pd.DataFrame, str]:
    missing_frac = df.isnull().mean()
    drop_cols = missing_frac[missing_frac > threshold].index.tolist()
    df = df.drop(columns=drop_cols)
    return df, f"Dropped {len(drop_cols)} column(s) with >{int(threshold*100)}% missing: {drop_cols}."


def reset_index(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    df = df.reset_index(drop=True)
    return df, "Reset DataFrame index."


def round_numeric_columns(df: pd.DataFrame, decimals: int = 4) -> tuple[pd.DataFrame, str]:
    """
    Round float columns to remove floating-point noise introduced by
    arithmetic earlier in the pipeline (IQR capping, mean/median fill,
    normalization, etc.) — e.g. 97.49999999999999 -> 97.5. This keeps the
    cleaned data (previews, downloads) displaying the correct values.
    """
    float_cols = df.select_dtypes(include=["float64", "float32"]).columns
    for col in float_cols:
        df[col] = df[col].round(decimals)
    return df, f"Rounded {len(float_cols)} numeric column(s) to {decimals} decimal places to remove floating-point noise."



def run_cleaning_pipeline(
    df: pd.DataFrame,
    options: dict,
) -> tuple[pd.DataFrame, list[str]]:
    log = []

    if options.get("fix_column_names", True):
        df, msg = fix_column_names(df)
        log.append(msg)

    if options.get("remove_duplicates", True):
        df, msg = remove_duplicates(df)
        log.append(msg)

    if options.get("drop_empty_rows", True):
        df, msg = drop_empty_rows(df)
        log.append(msg)

    if options.get("drop_constant_columns", True):
        df, msg = drop_constant_columns(df)
        log.append(msg)

    if options.get("drop_high_missing", False):
        thr = options.get("high_missing_threshold", 0.5)
        df, msg = drop_high_missing_columns(df, threshold=thr)
        log.append(msg)

    if options.get("strip_whitespace", True):
        df, msg = strip_whitespace(df)
        log.append(msg)

    case = options.get("standardize_case", "none")
    if case and case != "none":
        df, msg = standardize_text_case(df, case=case)
        log.append(msg)

    if options.get("remove_duplicate_columns", False):
        df, msg = remove_duplicate_columns(df)
        log.append(msg)

    if options.get("strip_currency", False):
        df, msg = strip_currency_percent(df)
        log.append(msg)

    if options.get("coerce_numeric", True):
        df, msg = coerce_numeric_columns(df)
        log.append(msg)

    if options.get("convert_boolean", False):
        df, msg = convert_boolean_like(df)
        log.append(msg)


    if options.get("parse_dates", True):
        df, msg = parse_dates(df)
        log.append(msg)

    df, msg = format_date_columns(df)
    if "0 date" not in msg:   
        log.append(msg)

    fill_num = options.get("fill_numeric", "median")
    if fill_num and fill_num != "none":
        df, msg = fill_missing_numeric(df, strategy=fill_num)
        log.append(msg)

    fill_cat = options.get("fill_categorical", "mode")
    if fill_cat and fill_cat != "none":
        df, msg = fill_missing_categorical(df, strategy=fill_cat)
        log.append(msg)

    outlier = options.get("outlier_method", "iqr")
    if outlier == "zscore":
        thr = options.get("zscore_threshold", 3.0)
        df, msg = remove_outliers_zscore(df, threshold=thr)
        log.append(msg)
    elif outlier == "iqr":
        df, msg = cap_outliers_iqr(df)
        log.append(msg)

    if options.get("remove_html", False):
        df, msg = remove_html_tags(df)
        log.append(msg)

    if options.get("remove_special_chars", False):
        df, msg = remove_special_characters(df)
        log.append(msg)

    norm = options.get("normalize", "none")
    if norm and norm != "none":
        df, msg = normalize_numeric(df, method=norm)
        log.append(msg)

    df, msg = round_numeric_columns(df)
    log.append(msg)

    if options.get("reset_index", True):
        df, msg = reset_index(df)
        log.append(msg)

    return df, log