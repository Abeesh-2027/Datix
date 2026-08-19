import io
import json
import os
import uuid

import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, session, send_file, render_template
from flask_cors import CORS

try:
    from dotenv import load_dotenv
    load_dotenv() 
except ImportError:
    pass

from cleaning import (
    get_dataset_overview,
    get_column_report,
    run_cleaning_pipeline,
    format_date_columns,
)
import chart_utils
import analysis_utils
import chat_service
import db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "datix-dev-secret-change-me")

app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_UPLOAD_MB", 50)) * 1024 * 1024

_allowed_origins = [
    "https://datix-five.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]

CORS(
    app,
    resources={r"/api/*": {"origins": _allowed_origins}},
    supports_credentials=True,
    allow_headers=["Content-Type", "X-Session-Id"],
)


_is_production = os.environ.get("RENDER", "") != "" or os.environ.get("FLASK_ENV") == "production"
if _is_production:
    app.config.update(
        SESSION_COOKIE_SAMESITE="None",
        SESSION_COOKIE_SECURE=True,
    )


db.init_db()

STORE = {}


def _new_bucket():
    return {"raw": None, "clean": None, "filtered": None, "log": None, "chat": [], "_hydrated": False}


def _sid() -> str:
    """
    Resolve a stable session id for this client.

    Cross-site cookies (frontend on Vercel, backend on Render) get blocked by
    default in Safari, Firefox, and Brave, and are being phased out in Chrome.
    When that happens Flask's cookie-based `session` silently resets on every
    request, so we'd never find the client's uploaded data again.

    To work around this, the frontend generates its own id (stored in
    localStorage, which is first-party and always available) and sends it via
    the `X-Session-Id` header. We prefer that header when present. If it's
    missing (e.g. a raw curl request, or same-origin local dev), we fall back
    to the normal cookie-based Flask session.
    """
    header_sid = request.headers.get("X-Session-Id") or request.args.get("sid")
    if header_sid:
        STORE.setdefault(header_sid, _new_bucket())
        return header_sid

    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    sid = session["sid"]
    STORE.setdefault(sid, _new_bucket())
    return sid


def _state():
    sid = _sid()
    st = STORE[sid]
    # The in-memory dict is just a per-worker cache. The first time this
    # worker sees this session id, pull the real state from the database
    # (in case another worker, or a previous restart, has it).
    if not st.get("_hydrated"):
        persisted = db.load_session(sid)
        if persisted:
            st.update(persisted)
        st["_hydrated"] = True
    return st


def _persist():
    """Write the current session's state to the database so every worker
    (and future restarts) can see it. Call this after any route mutates
    raw/clean/filtered/log/chat."""
    sid = _sid()
    db.save_session(sid, STORE[sid])


def _active_df():
    st = _state()
    if st["filtered"] is not None:
        return st["filtered"]
    if st["clean"] is not None:
        return st["clean"]
    return st["raw"]


def _require(df, name="dataset"):
    if df is None:
        raise ValueError(f"No {name} available yet.")
    return df


def _json_records(df: pd.DataFrame):
    return df.replace({np.nan: None}).to_dict(orient="records")


def _read_csv_robust(fh, sep=","):
    encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]
    last_err = None
    for enc in encodings:
        try:
            fh.seek(0)
            return pd.read_csv(fh, sep=sep, encoding=enc, engine="python", on_bad_lines="skip")
        except Exception as e:
            last_err = e
    raise last_err


def _read_excel_robust(fh, name):
    fh.seek(0)
    if name.endswith(".xls"):
        return pd.read_excel(fh, engine="xlrd")
    return pd.read_excel(fh, engine="openpyxl")


def _read_json_robust(fh):
    fh.seek(0)
    try:
        return pd.read_json(fh)
    except Exception:
        pass
    try:
        fh.seek(0)
        return pd.read_json(fh, lines=True)
    except Exception:
        pass
    fh.seek(0)
    raw = json.load(fh)
    if isinstance(raw, dict):
        if all(isinstance(v, (list, dict)) for v in raw.values()):
            try:
                return pd.DataFrame(raw)
            except Exception:
                return pd.json_normalize(raw)
        return pd.json_normalize(raw)
    return pd.json_normalize(raw)


def _read_parquet_robust(fh):
    fh.seek(0)
    try:
        return pd.read_parquet(fh, engine="pyarrow")
    except ImportError:
        fh.seek(0)
        return pd.read_parquet(fh, engine="fastparquet")


def load_file(file_storage):
    name = file_storage.filename.lower()
    fh = io.BytesIO(file_storage.read())
    if name.endswith(".csv"):
        df = _read_csv_robust(fh, sep=",")
    elif name.endswith((".xls", ".xlsx", ".xlsm")):
        df = _read_excel_robust(fh, name)
    elif name.endswith(".json"):
        df = _read_json_robust(fh)
    elif name.endswith(".parquet"):
        df = _read_parquet_robust(fh)
    elif name.endswith(".tsv"):
        df = _read_csv_robust(fh, sep="\t")
    else:
        raise ValueError("Unsupported file type.")

    if df is None or df.empty:
        raise ValueError("The file was read but contains no data.")

    df, _ = format_date_columns(df)
    return df


def df_to_bytes(df: pd.DataFrame, fmt: str) -> bytes:
    buf = io.BytesIO()
    if fmt == "csv":
        df.to_csv(buf, index=False)
    elif fmt == "excel":
        df.to_excel(buf, index=False, engine="openpyxl")
    elif fmt == "json":
        df.to_json(buf, orient="records")
    elif fmt == "parquet":
        df.to_parquet(buf, index=False)
    return buf.getvalue()


def err(message, code=400):
    return jsonify({"error": message}), code


@app.route("/")
def index():
    try:
        return render_template("index.html")
    except Exception:
        return jsonify({"status": "ok", "service": "datix-backend"})


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok"})



@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return err("No file uploaded.")
    f = request.files["file"]
    if not f.filename:
        return err("No file selected.")
    try:
        df = load_file(f)
    except ImportError as e:
        return err(f"Missing dependency: {e}")
    except Exception as e:
        return err(f"Error reading file: {e}")

    st = _state()
    st["raw"] = df
    st["clean"] = None
    st["filtered"] = None
    st["log"] = None
    st["chat"] = []
    _persist()

    return jsonify({
        "filename": f.filename,
        "overview": get_dataset_overview(df),
        "column_report": _json_records(get_column_report(df)),
        "preview": _json_records(df.head(100)),
        "columns": df.columns.tolist(),
    })


@app.route("/api/overview")
def api_overview():
    st = _state()
    which = request.args.get("dataset", "raw")
    df = st["clean"] if which == "clean" else st["raw"]
    if df is None:
        return err("No dataset loaded.", 404)
    return jsonify(get_dataset_overview(df))


@app.route("/api/column-report")
def api_column_report():
    st = _state()
    which = request.args.get("dataset", "raw")
    df = st["clean"] if which == "clean" else st["raw"]
    if df is None:
        return err("No dataset loaded.", 404)
    return jsonify(_json_records(get_column_report(df)))


@app.route("/api/clean", methods=["POST"])
def api_clean():
    st = _state()
    if st["raw"] is None:
        return err("Upload a dataset first.", 404)
    options = request.get_json(force=True) or {}
    df_clean, log = run_cleaning_pipeline(st["raw"].copy(), options)
    st["clean"] = df_clean
    st["log"] = log
    st["filtered"] = None
    st["chat"] = []
    _persist()

    raw = st["raw"]
    over_raw = get_dataset_overview(raw)
    over_clean = get_dataset_overview(df_clean)
    return jsonify({
        "overview": over_clean,
        "raw_overview": over_raw,
        "log": log,
        "preview": _json_records(df_clean.head(100)),
        "column_report": _json_records(get_column_report(df_clean)),
        "columns": df_clean.columns.tolist(),
        "rows_delta": raw.shape[0] - df_clean.shape[0],
        "cols_delta": raw.shape[1] - df_clean.shape[1],
    })


@app.route("/api/data")
def api_data():
    """Return active (filtered > clean > raw) dataset rows, paginated-ish."""
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    limit = request.args.get("limit", type=int)
    data = df.head(limit) if limit else df
    return jsonify({"rows": _json_records(data), "total": len(df), "columns": df.columns.tolist()})


NUMERIC_FILTER_CONDITIONS = ["=", ">", "<", ">=", "<="]
TEXT_FILTER_CONDITIONS = ["equals", "contains"]


@app.route("/api/filter", methods=["POST"])
def api_filter():
    st = _state()
    df = st["clean"] if st["clean"] is not None else st["raw"]
    if df is None:
        return err("No dataset loaded.", 404)
    body = request.get_json(force=True) or {}
    col = body.get("column")
    condition = body.get("condition")
    value = body.get("value")

    if col not in df.columns:
        return err(f"Unknown column '{col}'.")
    if value is None or str(value).strip() == "":
        return err("Enter a value to filter by.")

    try:
        is_numeric = pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col])
        if is_numeric:
            if condition not in NUMERIC_FILTER_CONDITIONS:
                return err(
                    f"'{condition}' isn't valid for numeric column '{col}'. "
                    f"Use one of: {', '.join(NUMERIC_FILTER_CONDITIONS)}."
                )
            series = pd.to_numeric(df[col], errors="coerce")
            try:
                num_value = float(value)
            except (TypeError, ValueError):
                return err(f"'{value}' is not a valid number for column '{col}'.")
            ops = {
                "=": lambda s, v: np.isclose(s, v, equal_nan=False),
                ">": lambda s, v: s > v,
                "<": lambda s, v: s < v,
                ">=": lambda s, v: s >= v,
                "<=": lambda s, v: s <= v,
            }
            
            mask = pd.Series(ops[condition](series, num_value), index=series.index).fillna(False)
            filtered = df[mask]
        else:
            if condition not in TEXT_FILTER_CONDITIONS:
                return err(
                    f"'{condition}' isn't valid for text column '{col}'. "
                    f"Use one of: {', '.join(TEXT_FILTER_CONDITIONS)}."
                )
            col_series = df[col].astype(str)
            if condition == "contains":
                filtered = df[col_series.str.contains(str(value), case=False, na=False, regex=False)]
            else:
                filtered = df[col_series.str.lower() == str(value).lower()]
        st["filtered"] = filtered
        _persist()
        return jsonify({"rows": _json_records(filtered.head(200)), "total": len(filtered)})
    except Exception as e:
        return err(f"Filter error: {e}")


@app.route("/api/filter", methods=["DELETE"])
def api_clear_filter():
    st = _state()
    st["filtered"] = None
    _persist()
    return jsonify({"ok": True})


@app.route("/api/download")
def api_download():
    st = _state()
    fmt = request.args.get("format", "csv")
    which = request.args.get("dataset", "active")
    if which == "active":
        df = _active_df()
        which = "filtered" if st["filtered"] is not None else ("clean" if st["clean"] is not None else "raw")
    elif which == "clean":
        df = st["clean"]
    else:
        df = st["raw"]
    if df is None:
        return err("No dataset loaded.", 404)
    mimetypes = {
        "csv": "text/csv",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json": "application/json",
        "parquet": "application/octet-stream",
    }
    exts = {"csv": "csv", "excel": "xlsx", "json": "json", "parquet": "parquet"}
    data = df_to_bytes(df, fmt)
    return send_file(
        io.BytesIO(data),
        mimetype=mimetypes.get(fmt, "application/octet-stream"),
        as_attachment=True,
        download_name=f"{which}_data.{exts.get(fmt, 'bin')}",
    )


@app.route("/api/charts/missing-heatmap")
def api_missing_heatmap():
    st = _state()
    df = st["raw"]
    if df is None:
        return err("No dataset loaded.", 404)
    if df.isnull().sum().sum() == 0:
        return jsonify({"image": None, "message": "No missing values detected."})
    return jsonify({"image": chart_utils.missing_heatmap(df)})


@app.route("/api/charts/dtype-pie")
def api_dtype_pie():
    st = _state()
    which = request.args.get("dataset", "raw")
    df = st["clean"] if which == "clean" else st["raw"]
    if df is None:
        return err("No dataset loaded.", 404)
    return jsonify({"image": chart_utils.dtype_pie(df)})


@app.route("/api/charts/missing-comparison")
def api_missing_comparison():
    st = _state()
    if st["raw"] is None or st["clean"] is None:
        return err("Clean the dataset first.", 404)
    image = chart_utils.missing_comparison_chart(st["raw"], st["clean"])
    return jsonify({"image": image})


@app.route("/api/columns")
def api_columns():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    return jsonify(chart_utils.get_columns(df))


@app.route("/api/chart/basic")
def api_chart_basic():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    try:
        group = request.args.get("group") or None
        if group in ("", "None"):
            group = None
        image = chart_utils.basic_chart(
            df,
            chart_type=request.args.get("type", "Bar"),
            x_col=request.args["x"],
            y_col=request.args["y"],
            group_col=group,
            color_idx=request.args.get("color_idx", 0, type=int),
            top_n=request.args.get("top_n", 50, type=int),
            show_grid=request.args.get("grid", "true") == "true",
        )
        return jsonify({"image": image})
    except Exception as e:
        return err(f"Chart error: {e}")


@app.route("/api/chart/guide")
def api_chart_guide():
    return jsonify(chart_utils.CHART_GUIDE)


@app.route("/api/chart/distribution")
def api_chart_distribution():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    try:
        result = chart_utils.distribution_chart(df, request.args["col"], request.args.get("bins", 25, type=int))
        return jsonify(result)
    except Exception as e:
        return err(f"Chart error: {e}")


@app.route("/api/chart/correlation")
def api_chart_correlation():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    cols = request.args.get("cols", "")
    cols = [c for c in cols.split(",") if c]
    if len(cols) < 2:
        return err("Select at least 2 numeric columns.")
    try:
        result = chart_utils.correlation_chart(df, cols, request.args.get("method", "pearson"))
        return jsonify(result)
    except Exception as e:
        return err(f"Chart error: {e}")


@app.route("/api/chart/multivariable")
def api_chart_multivariable():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    try:
        image = chart_utils.multivariable_chart(
            df,
            x=request.args["x"],
            y=request.args["y"],
            hue=request.args.get("hue"),
            size_col=request.args.get("size"),
        )
        return jsonify({"image": image})
    except Exception as e:
        return err(f"Chart error: {e}")


@app.route("/api/chart/timeseries")
def api_chart_timeseries():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    try:
        image = chart_utils.timeseries_chart(
            df,
            date_col=request.args["date_col"],
            val_col=request.args["val_col"],
            agg=request.args.get("agg", "sum"),
        )
        return jsonify({"image": image})
    except Exception as e:
        return err(f"Time series error: {e}")


@app.route("/api/analysis/overview")
def api_analysis_overview():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    return jsonify(analysis_utils.overview(df))


@app.route("/api/analysis/group")
def api_analysis_group():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    try:
        result = analysis_utils.group_analysis(
            df,
            group_by=request.args["group_by"],
            value_col=request.args["value"],
            agg=request.args.get("agg", "mean"),
            top_n=request.args.get("top_n", 10, type=int),
        )
        return jsonify(result)
    except Exception as e:
        return err(f"Group analysis error: {e}")


@app.route("/api/analysis/group-heatmap")
def api_analysis_group_heatmap():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    cols = [c for c in request.args.get("cols", "").split(",") if c]
    if not cols:
        return err("Select at least one numeric column.")
    try:
        image = analysis_utils.group_heatmap(df, request.args["group_by"], cols)
        return jsonify({"image": image})
    except Exception as e:
        return err(f"Heatmap error: {e}")


@app.route("/api/analysis/outliers")
def api_analysis_outliers():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    try:
        result = analysis_utils.outlier_detection(
            df,
            col=request.args["col"],
            method=request.args.get("method", "IQR"),
            threshold=request.args.get("threshold", 1.5, type=float),
        )
        return jsonify(result)
    except Exception as e:
        return err(f"Outlier detection error: {e}")


@app.route("/api/analysis/profile")
def api_analysis_profile():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    return jsonify(analysis_utils.data_profile(df))


@app.route("/api/analysis/value-counts")
def api_analysis_value_counts():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    result = analysis_utils.value_counts_chart(df, request.args["col"], request.args.get("top_n", 15, type=int))
    return jsonify(result)


@app.route("/api/analysis/kpi")
def api_analysis_kpi():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    cols = [c for c in request.args.get("cols", "").split(",") if c]
    if not cols:
        return err("Select at least one KPI column.")
    result = analysis_utils.kpi_dashboard(
        df, cols, filter_col=request.args.get("filter_col"), filter_val=request.args.get("filter_val")
    )
    return jsonify(result)

@app.route("/api/chat/status")
def api_chat_status():
    return jsonify(chat_service.status())


@app.route("/api/chat/insights")
def api_chat_insights():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    return jsonify({"insights": chat_service.quick_insights(df)})


@app.route("/api/chat/suggested-questions")
def api_chat_suggested():
    return jsonify(chat_service.SUGGESTED_QUESTIONS)


@app.route("/api/chat/quick-action", methods=["POST"])
def api_chat_quick_action():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    action = (request.get_json(force=True) or {}).get("action")
    prompt = chat_service.QUICK_ACTIONS.get(action)
    if not prompt:
        return err("Unknown quick action.")
    st = _state()
    result = chat_service.ask_groq([{"role": "user", "content": prompt}], df)
    st["chat"].append({"role": "user", "content": prompt})
    st["chat"].append({"role": "assistant", "content": result})
    _persist()
    return jsonify({"response": result, "history": st["chat"]})


@app.route("/api/chat", methods=["GET"])
def api_chat_history():
    return jsonify(_state()["chat"])


@app.route("/api/chat", methods=["POST"])
def api_chat_send():
    df = _active_df()
    if df is None:
        return err("No dataset loaded.", 404)
    message = (request.get_json(force=True) or {}).get("message", "").strip()
    if not message:
        return err("Message is empty.")
    st = _state()
    st["chat"].append({"role": "user", "content": message})
    result = chat_service.ask_groq(st["chat"], df)
    st["chat"].append({"role": "assistant", "content": result})
    _persist()
    return jsonify({"response": result, "history": st["chat"]})


@app.route("/api/chat", methods=["DELETE"])
def api_chat_clear():
    _state()["chat"] = []
    _persist()
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=port)