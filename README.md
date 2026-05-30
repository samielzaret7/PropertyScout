# PropertyScout PR

**🔗 Live app: [propertyscoutpr.streamlit.app](https://propertyscoutpr.streamlit.app/)**

A Streamlit dashboard for exploring the Puerto Rico real estate market. Browse thousands of property listings scraped from clasificadosonline.com, filter by region, price, type, and more, and track market trends with interactive analytics.

> **Data** is sourced from clasificadosonline.com via an automated scraper pipeline (see [Clasificados-Online-Real-Estate-Scraper](https://github.com/samielzaret7/Clasificados-Online-Real-Estate-Scraper)).

## Features

- **Market Overview** — KPI cards (total listings, median price, price drops, under-contract rate), breakdowns by region, property type, and listing status, plus a top-brokers leaderboard.
- **Property Search** — Filter by region, municipality, property type, listing status, price range, bedrooms, bathrooms, neighbourhood type, and broker. Toggle between a card grid with images and a sortable data table. Pagination, price-drop/increase badges, and days-on-market tracking.
- **Market Analytics** — Price distribution histograms, box plots by type, median price by municipality, weekly listing volume over time, price-change analysis, price vs. bedrooms scatter, and regional statistics.
- **Global Filters** — Region, broker, and year filters persist across all pages via session state.

## Tech Stack

- **Frontend:** Streamlit, Plotly
- **Backend:** Supabase (PostgreSQL) with a `properties_enriched` SQL view
- **Data pipeline:** [Clasificados-Online-Real-Estate-Scraper](https://github.com/samielzaret7/Clasificados-Online-Real-Estate-Scraper) scraper

## Setup

1. Clone the repo and install dependencies:

   ```bash
   git clone https://github.com/samielzaret7/PropertyScout.git
   cd PropertyScout
   pip install -r requirements.txt
   ```

2. Copy the environment template and fill in your Supabase credentials:

   ```bash
   cp .env.example .env
   ```

   You need the **anon (publishable) key**, not the service role key. Find it in: Supabase Dashboard → Project Settings → API → Project API keys.

3. Set up the database by running `supabase_setup.sql` in the Supabase SQL Editor. This creates the `municipios` reference table and the `properties_enriched` view.

4. Run the app:

   ```bash
   streamlit run app.py
   ```

## Project Structure

```
PropertyScout/
├── app.py                  # Home page — KPI overview
├── pages/
│   ├── 01_Search.py        # Filter-driven property browser
│   └── 02_Analytics.py     # Market charts and statistics
├── utils/
│   ├── data_loader.py      # Cached Supabase queries with pagination
│   ├── formatting.py       # Price/label formatting helpers
│   ├── sidebar.py          # Shared sidebar filter components
│   └── supabase_client.py  # Supabase client initialisation
├── supabase_setup.sql      # DB schema (view + reference table)
├── PR_Municipios.csv       # Municipality-to-region mapping (import to Supabase)
├── .streamlit/config.toml  # Streamlit theme configuration
├── requirements.txt
└── README.md
```

## Related Projects

- **[Clasificados-Online-Real-Estate-Scraper](https://github.com/samielzaret7/Clasificados-Online-Real-Estate-Scraper)** — The scraper that feeds property data into Supabase.
- **[Agent-Dashboard](https://github.com/samielzaret7/Agent-Dashboard)** — Agent-facing dashboard with authentication and property assignment, sharing the same Supabase backend.
