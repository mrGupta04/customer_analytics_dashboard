# Data Pipeline + Fullstack Dashboard Assignment

This repository contains a full end-to-end solution for the technical round assignment:

1. Clean raw CSVs with `pandas`.
2. Merge datasets and generate business analysis outputs.
3. Expose outputs through a FastAPI backend.
4. Visualize metrics in a responsive frontend dashboard.

## Project Structure

```text
.
|-- clean_data.py
|-- analyze.py
|-- requirements.txt
|-- docker-compose.yml
|-- backend/
|   |-- app.py
|   |-- requirements.txt
|   `-- Dockerfile
|-- frontend/
|   |-- index.html
|   |-- styles.css
|   `-- app.jsx
|-- data/
|   |-- raw/
|   |   |-- customers.csv
|   |   |-- orders.csv
|   |   `-- products.csv
|   `-- processed/
`-- tests/
    `-- test_clean_data.py
```

## Tech Stack

- Python 3.9+
- pandas, numpy
- FastAPI + uvicorn
- React + Chart.js
- pytest

## Setup

1. Create and activate a virtual environment.
2. Install dependencies.

```bash
pip install -r requirements.txt
```

## Run End-to-End Pipeline

Run the scripts in this order:

```bash
python clean_data.py
python analyze.py
```

Generated outputs in `data/processed/`:

- `customers_clean.csv`
- `orders_clean.csv`
- `monthly_revenue.csv`
- `top_customers.csv`
- `category_performance.csv`
- `regional_analysis.csv`

## Run Backend

```bash
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload --port 8000
```

API endpoints:

- `GET /health`
- `GET /api/revenue`
- `GET /api/top-customers`
- `GET /api/categories`
- `GET /api/regions`

## Run Frontend

From the repo root:

```bash
python -m http.server 5500 --bind 127.0.0.1
```

Open:

- `http://127.0.0.1:5500/frontend/index.html`
- Do not use `http://127.0.0.1:5500/` (that shows directory listing from repo root).
- Frontend is implemented in React (CDN + JSX runtime in `frontend/app.jsx`; no npm build step required).

Alternative (if you serve from `frontend/` directly):

```bash
cd frontend
python -m http.server 5500 --bind 127.0.0.1
```

Then open:

- `http://127.0.0.1:5500/index.html`

The frontend expects backend API at `http://127.0.0.1:8000`.

## Bonus Features Included

- Date range filter for Revenue Trend chart.
- Search box for Top Customers table.
- Sortable Top Customers table.
- Dockerized backend (`backend/Dockerfile` + `docker-compose.yml`) with bind mount for processed CSVs.
- 4 pytest tests for core data-cleaning functions.

## Run Tests

```bash
pytest -q
```

## Docker (Backend)

```bash
docker compose up --build
```

This starts backend on `http://127.0.0.1:8000` and bind-mounts `./data/processed` into the container.

## Assumptions

- Revenue metrics use `status == "completed"` orders only.
- Unknown/unmapped statuses are normalized to `pending`.
- Regions missing in customer data are filled with `Unknown`.
- `orders.product` is joined to `products.product_name` exactly as required.
- Churn is computed against the latest `order_date` in the cleaned orders data:
- a customer is churned when they have no completed order in the previous 90 days.
