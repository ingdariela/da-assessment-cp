# Data Analysis - ATP (`README.md`)

---

## Project Overview

The **Data Analysis - ATP** project is a Python-based Streamlit application designed for data quality auditing and financial-operational (FinOps) analysis of customer accounts and orders. It connects to a MySQL database to ingest, clean, profile, and analyze data across pre- and post-migration eras.

---

## Tech Stack

* **Frontend/UI:** Streamlit, Streamlit Option Menu, Plotly Express.


* **Data Processing:** Pandas, NumPy.


* **Database & ORM:** MySQL, PyMySQL, SQLAlchemy, Python Dotenv.



---

## Project Structure

* `app.py`: Main Streamlit application entry point, page routing, global layout customization, and data caching.


* `services/data_service.py`: Data ingestion, cleaning, normalization, merging, and filtering logic.


* `services/plot_service.py`: Plotly charting functions for time-series and data profiling tables.


* `services/ui_service.py`: UI layout components for deduplication metrics, data audits, and tabs.


* `ui_pages/data_qa.py`: Data Quality Audit page module.


* `ui_pages/finops.py`: FinOps Analysis module covering volume, billing, duplicates, and segmentation.


* `src/database.py` & `src/data_loader.py`: Database initialization and Parquet-to-SQL ingestion pipelines.


* `src/config.py`: Configuration mappings for geographical regions and time frequencies.



---

## Setup & Installation

1. **Clone the repository and set up environment variables:**
Create a `.env` file in the root directory with your database credentials:
```env
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=your_db_name

```


2. **Load initial data into MySQL:**
Run the data loader script to parse local Parquet files into the database:


```bash
python src/data_loader.py

```


3. **Run the Streamlit application:**
Launch the dashboard locally:
```bash
streamlit run app.py

```
