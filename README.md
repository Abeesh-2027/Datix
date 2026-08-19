# 🚀 Datix — Cloud AI-Powered Data Analytics Studio

Datix is a browser-based **data cleaning, visualization, statistical analysis, and AI-powered data analytics platform**.

Upload a CSV, Excel, JSON, Parquet, or TSV file and use Datix to clean your data, explore patterns, create visualizations, perform statistical analysis, and ask questions about your dataset using AI.

The AI assistant is powered by **Llama 3 through the Groq Cloud API**, so there is no need to install an AI model or use a local GPU.

---
## Screenshot

## Interface

![image alt]()

## Review a Data Type of data

![image alt]()
![image alt]()

## Clean Data

![image alt]()

## Filter Data

![image alt]()

## Visualization Data

![image alt]()

## Analysis Data

![image alt]()

## Chat on Data

![image alt](https://github.com/Abeesh-2027/Datix/blob/39299fa4cf4faf6ae6ce0f7cf7892a271704cb99/chat.png)

---
## ✨ Features

### 🧹 Data Cleaning

* Drag-and-drop file upload
* Supports:

  * CSV
  * Excel (`.xls`, `.xlsx`)
  * JSON
  * Parquet
  * TSV
* Dataset overview:

  * Rows and columns
  * Missing cells
  * Duplicate rows
  * Total cells
  * Memory usage
* Per-column diagnostics:

  * Data type
  * Missing percentage
  * Unique values
  * Detected issues
* Missing-value heatmap
* Data-type breakdown

### Cleaning Operations

* Fix column names
* Remove duplicate rows and columns
* Remove empty rows
* Remove constant columns
* Remove columns with excessive missing values
* Strip whitespace
* Standardize text case
* Remove HTML tags and special characters
* Convert columns to numeric
* Remove currency and percentage symbols
* Parse and format dates
* Convert Yes/No and True/False values to Boolean

### Missing Value Handling

Supports:

* Mean
* Median
* Zero
* Forward fill
* Backward fill
* Mode
* Unknown

### Outlier Handling

* IQR capping
* Z-score removal
* Numeric normalization

### Other Cleaning Features

* Before/after cleaning comparison
* Cleaning transformation log
* Advanced filtering
* Export cleaned datasets

---

## 📊 Data Visualization

Datix supports multiple chart types.

### Available Charts

* Bar Chart
* Horizontal Bar Chart
* Grouped Bar Chart
* Stacked Bar Chart
* 100% Stacked Bar Chart
* Line Chart
* Area Chart
* Scatter Plot
* Pie Chart
* Donut Chart
* Box Plot

### Advanced Visualization

#### Chart Guide

A built-in chart guide helps you understand which chart type is best for different analytical questions.

#### Distribution Explorer

Includes:

* Histogram
* KDE
* Violin Plot
* Box Plot
* Summary Statistics

#### Correlation Analysis

Supports:

* Pearson correlation
* Spearman correlation
* Kendall correlation
* Correlation heatmap
* Strongest correlation pairs

#### Multi-variable Scatter Plot

Supports:

* X-axis
* Y-axis
* Hue
* Bubble size
* Trend line

#### Time Series Analysis

* Automatic date-column detection
* Time-series visualization
* Rolling averages

---

## 🔬 Statistical Analysis

Datix provides a dedicated analysis section for exploring your dataset.

### Statistical Overview

Includes:

* Numeric statistics
* Categorical statistics
* Data profiling

### Group-by Analysis

Supported aggregations:

* Mean
* Sum
* Count
* Median
* Standard deviation
* Minimum
* Maximum

Also includes group comparison heatmaps.

### Outlier Detection

Supported methods:

* IQR
* Z-score
* Modified Z-score

### Additional Analysis

* Data profiling table
* Value-count explorer
* KPI dashboard
* Optional KPI filters

---

## 🤖 AI Data Assistant

Datix includes an AI chat assistant powered by **Llama 3 through Groq Cloud**.

Ask questions about your dataset using natural language.

### Example Questions

```text
Summarize the sales trends.
```

```text
Which columns have the most missing values?
```

```text
Which category has the highest sales?
```

```text
What are the most important patterns in this dataset?
```

The AI assistant receives context about:

* Dataset shape
* Column names
* Column data types
* Data sample

### Quick Actions

* Auto Insights
* Statistical Summary
* Data Quality Report
* Analysis Suggestions
* Generate Pandas Code

### Additional AI Features

* Streaming responses
* Typing indicator
* Input locking while generating
* Rule-based static insights
* Export chat transcript as `.txt`

No local GPU or AI model installation is required.

---

## 🔎 Advanced Filtering

Datix provides an advanced filtering system.

### Numeric Filters

```text
=
>
<
>=
<=
```

### Text Filters

* Equals
* Contains

Filtered datasets can be exported in multiple formats.

---

## 📥 Export Formats

Datix supports exporting datasets as:

* CSV
* Excel
* JSON
* Parquet

---

## 🏗️ Tech Stack

| Layer           | Technology                                      |
| --------------- | ----------------------------------------------- |
| Backend         | Python, Flask, Gunicorn                         |
| Data Processing | pandas, NumPy, SciPy                            |
| Visualization   | Matplotlib, Seaborn                             |
| AI              | Groq Cloud API + Llama 3                        |
| Frontend        | HTML, CSS, JavaScript                           |
| Deployment      | Render, Railway, or other Python-friendly hosts |

The frontend uses **Vanilla HTML, CSS, and JavaScript**, so no frontend build step is required.

---

## 🔐 Data Storage

Datasets are stored **in memory per browser session** on the server.

Nothing is written to disk unless the user explicitly downloads a file.

---

# 🚀 Installation

## Prerequisites

Before running Datix locally, make sure you have:

* Python 3.10+
* A Groq API key

Get a Groq API key from:

https://console.groq.com/keys

---

## 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/<your-repository>.git
cd <your-repository>
```

---

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

On Windows, you can also create `.env` manually.

Add your Groq API key:

```env
GROQ_API_KEY=gsk_your_real_key_here
```

Optional configuration:

```env
GROQ_MODEL=llama-3.3-70b-versatile
FLASK_DEBUG=true
```

> **Important:** Never commit your `.env` file to GitHub.

The `.gitignore` file already excludes `.env`.

---

## 5. Run the Application

```bash
python app.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

---

# ☁️ Deployment

Datix is a Flask application (backend) with a static HTML/CSS/JS frontend.
It can be deployed either as a single service, or split into two services:
**backend on Render** and **frontend on Vercel**. The split setup is
recommended and documented below.

## Split Deployment: Backend on Render + Frontend on Vercel

This repo is set up as a small monorepo:

```text
.
├── app.py, cleaning.py, chart_utils.py, ...   # Flask backend (deploy to Render)
├── templates/, static/                        # kept for local `python app.py` only
├── render.yaml                                # Render blueprint for the backend
└── frontend/                                  # static frontend (deploy to Vercel)
    ├── index.html
    ├── static/css/style.css
    ├── static/js/app.js
    └── vercel.json
```

### 1. Deploy the backend to Render

1. Push this repo to GitHub.
2. In Render, choose **New → Blueprint** and select the repo (it will pick up
   `render.yaml` at the repo root — the backend's root directory stays `.`,
   no changes needed there).
3. Set the required environment variables on the service:
   * `GROQ_API_KEY` — your Groq API key.
   * `ALLOWED_ORIGINS` — your Vercel frontend URL(s), comma-separated, e.g.
     `https://your-app.vercel.app`. You can add this after step 2 below once
     you know the Vercel URL, then redeploy.
   * `SECRET_KEY` is auto-generated by the blueprint.
4. Deploy. Note the resulting URL, e.g. `https://datix-backend.onrender.com`.

### 2. Deploy the frontend to Vercel

1. In Vercel, choose **Add New → Project**, select the same repo, and set
   **Root Directory** to `frontend`.
2. Framework preset: **Other** (it's plain static HTML/CSS/JS — no build
   command needed).
3. Before deploying (or after, then redeploy), edit
   `frontend/index.html` and set:
   ```html
   <script>
     window.API_BASE_URL = "https://datix-backend.onrender.com";
   </script>
   ```
   to your actual Render backend URL from step 1 (no trailing slash).
4. Deploy. Note the resulting URL, e.g. `https://your-app.vercel.app`.

### 3. Connect them

1. Go back to the Render service and set `ALLOWED_ORIGINS` to the Vercel URL
   from step 2 (e.g. `https://your-app.vercel.app`), then redeploy/restart
   the backend so CORS picks up the new origin.
2. Open the Vercel URL — it should now upload files, clean data, chart, and
   chat against the Render backend.

**How the two talk to each other:**
* `frontend/static/js/app.js` prefixes every `/api/...` call with
  `window.API_BASE_URL` and sends `credentials: 'include'` so the Flask
  session cookie (which tracks each visitor's in-memory dataset) is sent
  cross-site.
* `app.py` enables CORS only for `ALLOWED_ORIGINS`, with
  `supports_credentials=True`, and marks the session cookie
  `SameSite=None; Secure` in production (detected via Render's built-in
  `RENDER=true` env var) so browsers accept it cross-site.
* Render's free tier spins down when idle — the first request after a while
  can take 30-60 seconds while the backend cold-starts.
* Uploaded datasets live in server memory (`STORE` dict in `app.py`), so
  they're lost if the Render service restarts or sleeps; there's no
  database in this project by design.

### Single-service alternative

You can still deploy this as one Flask app (serving `templates/index.html`
directly) to Render, Railway, or another Python host instead of splitting it
— see the sections below. In that case you don't need the `frontend/` folder
or `ALLOWED_ORIGINS`, since everything is same-origin.

## Render

Render is the recommended deployment option.

### Using `render.yaml`

1. Push the project to GitHub.
2. Open Render.
3. Select **New → Blueprint**.
4. Connect your GitHub repository.
5. Render will detect `render.yaml`.

### Manual Configuration

**Build Command**

```bash
pip install -r requirements.txt
```

**Start Command**

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
```

### Environment Variables

Add:

```text
GROQ_API_KEY=your_groq_api_key
SECRET_KEY=your_long_random_secret
GROQ_MODEL=llama-3.3-70b-versatile
```

After deployment, Render will provide a public URL.

> **Note:** Render free-tier services may sleep after inactivity. The first request after sleeping can take approximately 30–60 seconds.

---

## Railway

1. Create a new Railway project.
2. Select **Deploy from GitHub repo**.
3. Select the Datix repository.
4. Add the required environment variables:

   * `GROQ_API_KEY`
   * `SECRET_KEY`
   * `GROQ_MODEL` (optional)
5. Generate a public domain.

Railway can detect the Python application and use the included `Procfile`.

---

## Other Hosting Platforms

Datix can also be deployed to:

* Fly.io
* Heroku
* PythonAnywhere
* AWS EC2 / VM
* Other Python-compatible hosting platforms

The application can be started with:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

Make sure the required environment variables are configured on the hosting platform.

---

# 📤 Push to GitHub

If the project is not already a Git repository:

```bash
git init
git add .
git commit -m "Initial Datix project"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repository>.git
git push -u origin main
```

The `.gitignore` file excludes:

```text
venv/
.env
__pycache__/
```

This helps prevent your virtual environment, API keys, and Python cache files from being committed.

---

# 📱 Responsive Design

Datix is designed to work across:

* Desktop
* Tablet
* Mobile

The application includes:

* Responsive layouts
* Collapsible sidebar
* Mobile hamburger menu
* Fluid chart and metric layouts
* Responsive breakpoints

Since the AI model runs in the cloud, users do not need a powerful computer or local GPU.

---

# 🖥️ Usage

## 1. Clean Your Data

1. Upload your dataset.
2. Review the dataset overview.
3. Check missing values and column diagnostics.
4. Select the required cleaning options.
5. Click **Clean Dataset**.
6. Use **Advanced Filter** if required.
7. Export the cleaned dataset.

---

## 2. Visualize Your Data

1. Select a chart type.
2. Select the required columns.
3. Configure grouping options if required.
4. Render the chart.
5. Use the Chart Guide when you are unsure which visualization to use.

---

## 3. Analyze Your Data

Use the Analyze section to explore:

* Statistics
* Group comparisons
* Outliers
* Data profiles
* Value counts
* KPIs

---

## 4. Ask the AI

Ask questions about your dataset in plain English.

For example:

```text
Summarize the sales trends.
```

```text
Which columns have the most missing values?
```

```text
What are the most important patterns in this dataset?
```

```text
Which category has the highest sales?
```

The **Clean**, **Visualize**, **Analyze**, and **AI Chat** sections become available after a dataset is uploaded.

---

# 📁 Project Structure

```text
datix/
│
├── app.py                  # Flask application and REST API routes
├── cleaning.py             # Data cleaning pipeline
├── chart_utils.py          # Chart generation
├── analysis_utils.py       # Statistical analysis helpers
├── chat_service.py         # Groq/Llama 3 integration
├── requirements.txt        # Python dependencies
├── Procfile                # Gunicorn start command
├── render.yaml             # Render deployment configuration
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore rules
│
├── templates/
│   └── index.html          # Main application page
│
└── static/
    ├── css/
    │   └── style.css       # Application styling
    │
    └── js/
        └── app.js          # Frontend application logic
```

---

# 🔌 REST API

All API endpoints are prefixed with `/api`.

| Endpoint                 | Method              | Description                                        |
| ------------------------ | ------------------- | -------------------------------------------------- |
| `/api/upload`            | POST                | Upload and parse a dataset                         |
| `/api/clean`             | POST                | Run the cleaning pipeline                          |
| `/api/filter`            | POST / DELETE       | Apply or clear the advanced filter                 |
| `/api/download`          | GET                 | Export the active dataset                          |
| `/api/chart/basic`       | GET                 | Render basic/grouped/stacked charts                |
| `/api/chart/guide`       | GET                 | Get the chart-type guide                           |
| `/api/analysis/*`        | GET                 | Run analysis, outlier, profile, and KPI operations |
| `/api/chat`              | GET / POST / DELETE | Chat with Llama 3 about the dataset                |
| `/api/chat/quick-action` | POST                | Run a predefined AI analysis                       |
| `/api/chat/status`       | GET                 | Check Groq configuration and availability          |

---

# 🩹 Troubleshooting

## `GROQ_API_KEY is not set`

### Local Development

Make sure:

1. `.env` exists.
2. `GROQ_API_KEY` is configured.
3. The API key is valid.
4. You restart the application after changing `.env`.

### Production

Set `GROQ_API_KEY` in your hosting platform's environment variables.

Do not put your API key directly in the source code.

---

## `Invalid GROQ_API_KEY`

Check that:

* The key was copied completely.
* There are no extra spaces.
* There are no extra newlines.
* The key has not been revoked.

---

## `Groq rate limit reached`

Groq has usage limits.

If you reach a rate limit:

1. Wait a few seconds.
2. Try again.
3. Check your Groq usage if the problem continues.

---

## Chart or Analysis Errors

Some chart types require specific column types.

For example:

* Y-axis may require numeric data.
* Group-by columns may require categorical data.
* Time-series charts require a date/time column.

Check the error message and select compatible columns.

---

## Large Files Are Slow

For performance:

* Table previews are limited to 100 rows.
* Cleaning and filtering operate on the full dataset in memory.
* Chart and analysis operations run on the dataset in memory.
* Upload size is limited to **50 MB by default** through `MAX_UPLOAD_MB`.

Very large datasets may require additional server memory.

---

## Application Is Slow After Deployment

Free hosting services may sleep after periods of inactivity.

When a new request arrives, the service needs to start again.

This can make the first request slower than normal.

---

# 🔒 Security

* Never commit API keys to GitHub.
* Keep secrets inside environment variables.
* Never commit `.env`.
* Use a strong random `SECRET_KEY` in production.
* Be careful when uploading sensitive datasets.
* Secure publicly deployed instances before using them with confidential data.

---

# 🤝 Contributing

Contributions, improvements, and suggestions are welcome.

### Create a Feature Branch

```bash
git checkout -b feature/my-feature
```

### Make Your Changes

```bash
git add .
git commit -m "Add my feature"
```

### Push Your Branch

```bash
git push origin feature/my-feature
```

Then open a Pull Request on GitHub.

---

# 📜 License

This project is licensed under the **MIT License**.

---

# 🙌 Acknowledgements

Datix is built using:

* [Python](https://www.python.org/)
* [Flask](https://flask.palletsprojects.com/)
* [pandas](https://pandas.pydata.org/)
* [NumPy](https://numpy.org/)
* [SciPy](https://scipy.org/)
* [Matplotlib](https://matplotlib.org/)
* [Seaborn](https://seaborn.pydata.org/)
* [Groq Cloud](https://console.groq.com/)
* Llama 3
  
---

# 👨‍💻 Author

Abeesh

---

⭐ If you find this project useful, consider giving the repository a star!
