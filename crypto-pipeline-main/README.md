# 🚀 Live Crypto Price Pipeline

> A production-style **data engineering pipeline** that continuously ingests live cryptocurrency market data from the CoinGecko API, stores it as an append-only time-series database in DuckDB, performs analytical SQL transformations, and visualizes insights through an interactive Streamlit dashboard and Apache Superset.

---

# 📖 Overview

Most beginner API projects fetch data once, print it, and stop.

This project solves a more realistic **data engineering** problem:

> **How do you continuously collect live data, preserve historical records, prevent duplicate ingestion, and generate analytics over time?**

The pipeline polls the CoinGecko public API at configurable intervals, validates incoming data, stores immutable historical snapshots, and exposes analytical views for monitoring market trends.

The architecture is intentionally lightweight while demonstrating many concepts used in real-world data platforms.

---

# 🏗️ Architecture

```text
                    +----------------------+
                    |   CoinGecko API      |
                    +----------+-----------+
                               |
                        Live REST Polling
                               |
                               ▼
                    +----------------------+
                    |      poll.py         |
                    |----------------------|
                    | Validation           |
                    | Deduplication        |
                    | Error Handling       |
                    +----------+-----------+
                               |
                               ▼
                    +----------------------+
                    |      DuckDB          |
                    | Append-only Storage  |
                    +----------+-----------+
                               |
                     SQL Analytics Layer
                               |
          +--------------------+-------------------+
          |                                        |
          ▼                                        ▼
 +---------------------+                 +---------------------+
 | Streamlit Dashboard |                 | Apache Superset     |
 +---------------------+                 +---------------------+
```

---

# ✨ Key Features

- ✅ Continuous live cryptocurrency price ingestion
- ✅ Incremental append-only storage
- ✅ Automatic duplicate prevention
- ✅ Historical time-series preservation
- ✅ SQL analytical layer using DuckDB
- ✅ Interactive Streamlit dashboard
- ✅ Apache Superset BI integration
- ✅ Rolling moving averages
- ✅ Top gainers & losers analysis
- ✅ Volatility analysis
- ✅ Data quality validation
- ✅ Failure-tolerant polling
- ✅ Unit tests with mock datasets
- ✅ Lightweight single-file database
- ✅ Production-style project structure

---

# 📂 Project Structure

```
crypto-pipeline/

│
├── db/
│   └── crypto.duckdb
│
├── analytics.sql
├── dashboard.py
├── poll.py
├── schema.sql
├── requirements.txt
├── test_pipeline.py
├── config.toml
└── README.md
```

---

# ⚙️ Pipeline Workflow

Every polling cycle performs the following steps:

1. Request latest market prices from CoinGecko.
2. Validate incoming JSON.
3. Normalize the schema.
4. Round timestamps to the nearest minute.
5. Insert records into DuckDB.
6. Ignore duplicate records.
7. Log failures without stopping ingestion.
8. Preserve every successful snapshot.
9. Refresh analytics automatically.

---

# 🗄️ Database Design

The database is intentionally **append-only**.

Each polling cycle inserts a new snapshot instead of updating previous rows.

Primary key:

```sql
(polled_at, coin_id)
```

This guarantees:

- Historical accuracy
- Duplicate prevention
- Reliable time-series analytics

---

# 📊 Analytics

The project includes several SQL analytics built using DuckDB window functions.

## 1. Latest Snapshot

Returns the newest available price for every cryptocurrency.

---

## 2. Rolling Moving Average

Computes moving averages across recent polling intervals.

Useful for observing short-term price trends.

---

## 3. Top Gainers & Losers

Calculates percentage price movement across the collected observation window.

---

## 4. Volatility Ranking

Ranks cryptocurrencies by standard deviation of price.

Higher standard deviation indicates higher volatility.

---

## 5. Poll Gap Detection

Detects missing polling intervals caused by:

- Internet outages
- Machine shutdown
- API failures

---

# 📈 Dashboard

The Streamlit dashboard provides interactive visualizations including:

- Live price trends
- Market capitalization
- Trading volume
- Moving averages
- Percentage changes
- Volatility rankings

---

# 📊 Apache Superset

The project also integrates with Apache Superset for Business Intelligence dashboards.

Example visualizations include:

- Line Charts
- Time Series Analysis
- KPI Cards
- Leaderboards
- Interactive Filters
- Historical Exploration

---

# 🧪 Testing

The project includes automated tests for:

- Duplicate prevention
- SQL analytics
- Data validation
- Mock API responses
- Database integrity

Run tests:

```bash
python test_pipeline.py
```

---

# ⚡ Installation

Clone the repository.

```bash
git clone https://github.com/<your-username>/crypto-pipeline.git

cd crypto-pipeline
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Initialize the database.

```bash
python poll.py
```

Run continuous polling.

```bash
python poll.py --loop 300
```

Launch the dashboard.

```bash
streamlit run dashboard.py
```

---

# 💾 Technologies Used

| Category | Technology |
|-----------|------------|
| Language | Python |
| Database | DuckDB |
| SQL Engine | DuckDB SQL |
| API | CoinGecko |
| Dashboard | Streamlit |
| BI Tool | Apache Superset |
| Testing | PyTest |
| Scheduling | Cron / Loop |
| Data Processing | Pandas |

---

# 🎯 Design Decisions

### Why DuckDB?

- Zero configuration
- Embedded database
- Extremely fast analytical queries
- Supports window functions
- Single portable database file

---

### Why Append-only?

Updating rows destroys historical information.

Keeping every snapshot enables:

- Trend analysis
- Moving averages
- Volatility
- Historical comparisons

---

### Why Database-Level Deduplication?

Instead of checking duplicates in Python, uniqueness is enforced by the database.

Benefits:

- Simpler code
- Better reliability
- Restart-safe ingestion

---

### Why Round Polling Timestamps?

Polling a few seconds apart should still belong to the same logical interval.

Timestamp normalization prevents accidental duplicate snapshots.

---

### Why Ignore Failed Polls?

Transient API failures should never stop the pipeline.

Instead:

- Failure is logged
- Next cycle continues
- Missing intervals remain visible for auditing

---

# 🚫 What This Project Does NOT Do

To keep the project focused on data engineering, several features are intentionally excluded.

- ❌ Machine Learning
- ❌ Price Prediction
- ❌ Trading Bots
- ❌ Buy/Sell Recommendations
- ❌ Portfolio Management
- ❌ Authentication
- ❌ Multi-user Support
- ❌ Kafka Streaming
- ❌ Spark Processing
- ❌ Multi-exchange Aggregation
- ❌ Cloud Deployment

These additions would increase infrastructure complexity without improving the core learning objective of incremental data ingestion and analytical processing.

---

# 📚 Learning Outcomes

This project demonstrates practical experience with:

- Incremental ETL pipelines
- Time-series database design
- SQL window functions
- Analytical query optimization
- Data validation
- Error handling
- Idempotent ingestion
- Dashboard development
- Business Intelligence integration
- Production-style project organization

---

# 🔮 Future Improvements

Potential enhancements include:

- Docker deployment
- Airflow orchestration
- Historical backfilling
- REST API
- Prometheus metrics
- Grafana monitoring
- Cloud storage
- Data warehouse integration
- Partitioned storage
- Real-time WebSocket ingestion

---

# 📄 License

This project is intended for educational and portfolio purposes.

---

## ⭐ If you found this project useful, consider giving it a star!