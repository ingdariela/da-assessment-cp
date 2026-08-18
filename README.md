```markdown
# 📊 Data Analysis - ATP (Dashboard & FinOps Assessment)

A comprehensive, production-grade **Streamlit** dashboard designed for **Data Quality Audits** and **Financial-Operational (FinOps) Impact Assessment** of customer accounts and utility/energy orders[cite: 1, 2, 3]. It bridges data engineering and executive financial oversight by tracking data hygiene, migration shifts, revenue discrepancies, and operational metrics.

---

## 🏗️ Project Architecture & Layout

The project follows a modular service-oriented architecture separating backend ingestion, data transformation logic, UI components, and page views.

```text
├── app.py                      # Main entry point: page routing, global CSS, layout configs
├── src/
│   ├── database.py             # MySQL DB engine initialization & Parquet-to-SQL loader
│   ├── data_loader.py          # Execution script for loading local parquet files
│   └── config.py               # Global configuration mappings (regions, date frequencies)
├── services/
│   ├── data_service.py         # Data cleaning, normalization, merging, and filtering utilities
│   ├── plot_service.py         # Standardized Plotly chart generators and profiling tables
│   └── ui_service.py           # Reusable UI metrics and audit tab layouts
└── ui_pages/
    ├── data_qa.py              # Data Quality & Profiling module
    └── finops.py               # FinOps Analysis module (Volume, Billing, Duplicates, Segmentation)

```

---

## 🚀 Key Features & Modules

### 1. Global Navigation & Dynamic Sidebar (`app.py`)

* **Persistent Sidebar Styles:** Injects custom CSS to force sidebar visibility and eliminate collapse elements for a clean dashboard experience.


* **Global Filters:** Dynamically filters the session datasets by **Customer Name**, **Energy Type**, and **Geographic Region**.


* **Context Banner:** Displays instant KPIs for the selected customer (order volume share, active regions, and rate categories).



### 2. Data Quality & Profiling Audit (`data_qa.py` & `ui_service.py`)

* **Deduplication Tracking:** Evaluates raw vs. clean records across total datasets and split migration phases (**PRE** vs. **POST** migration).


* **Conflict Resolution Logs:** Identifies conflicting duplicate records sharing the same `order_id` and tracks numerical variances (delta differences in `billed_rate`, `qty_ordered`, and `qty_delivered`).


* **Data Profiling Tables:** Automated calculation of non-null counts, null percentages, unique value distributions, and data types for columns.



### 3. Financial & Operational Impact Analysis - FinOps (`finops.py`)

Divided into four primary analytical tabs tailored for CTOs and CFOs:

* **📦 Volume & Operations Explorer (CTO Focus):**
* Tracks total ordered vs. delivered units and volume fulfillment percentages.


* Compares pre-migration and post-migration performance metrics.


* Renders monthly fulfillment trends with a vertical marker for the October 2024 system migration date.


* Displays 100% stacked bar charts showing order status mix (`DELIVERED`, `PARTIAL`, `FAILED`, `PENDING`) across eras.




* **💰 Billing & Rates Explorer (CFO Focus):**
* Reconciles billed revenue (`qty_delivered * billed_rate`) against expected contracted revenue (`qty_delivered * contracted_rate`).


* Computes financial discrepancies and projects **Annualized Run-Rate Revenue Leakage**.


* Provides monthly revenue trend lines ($) and financial discrepancy percentages (%) with migration threshold markers.


* Breakdown of discrepancies by rate category.




* **⚠️ Data Integrity & Duplicates:**
* Quantifies phantom revenue and overstated order demand caused by duplicate records in raw data files.


* Side-by-side comparative financial tables of raw data versus cleaned working datasets.




* **👥 Customer Segmentation & Tiers:**
* Evaluates net performance across **Anchor Clients vs. Standard Clients**, **Account Tiers**, and **Regions**.


* Utilizes normalized percentage shares (%) to eliminate volume distortion bias between pre- and post-migration eras.





---

## 🛠️ Tech Stack

* **Frontend Framework:** [Streamlit](https://streamlit.io/), `streamlit-option-menu`

* **Visualizations:** [Plotly Express](https://plotly.com/python/plotly-express/)

* **Data Processing & Manipulation:** Pandas, NumPy


* **Database & ORM:** MySQL, PyMySQL, SQLAlchemy


* **Environment Management:** Python-Dotenv



---

## ⚙️ Installation & Setup Guide

### Prerequisites

* Python 3.9+
* A running MySQL server instance.

### 1. Clone & Configure Environment

Create a `.env` file in the root project directory and define your database connection parameters:

```env
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=atp_data_analysis

```

### 2. Install Dependencies

Install the required Python packages:

```bash
pip install streamlit streamlit-option-menu pandas numpy plotly pymysql sqlalchemy python-dotenv

```

### 3. Initialize and Load Database

Run the ingestion script to parse local source Parquet files (`files/accounts.parquet` and `files/orders.parquet`) into the MySQL database:

```bash
python src/data_loader.py

```

### 4. Run the Streamlit Dashboard

Launch the application locally:

```bash
streamlit run app.py

```

---

## 📈 Data Cleaning & Standardization Logic (`data_service.py`)

* **String Unicode Normalization:** Applies `NFKC` normalization and whitespace cleanup across all text and categorical columns.


* **Geographical Mapping:** Standardizes region variants (e.g., `"NE"`, `"NORTH EAST"`) into unified master tags via `config.py`.


* **Customer Info Parsing:** Splits compound customer name strings into clean identifiers and metadata properties.



```

```
