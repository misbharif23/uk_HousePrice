# UK House Price Index — Data Science Portfolio Project

An end-to-end data science pipeline built on HM Land Registry's UK House Price
Index (UK HPI): cleaning and validating a real government dataset, designing a
normalized MySQL schema, training and evaluating regression models, and
serving predictions through a Flask web app.

## Data Source

- **Dataset:** [UK House Price Index — full file](https://www.gov.uk/government/statistical-data-sets/uk-house-price-index-data-downloads-september-2025) (HM Land Registry, gov.uk)
- **Size:** 150,705 rows × 54 columns
- **Coverage:** 405 regions (UK nations, English regions, local authorities, Northern Ireland districts)
- **Date range:** January 1968 – January 2026, monthly

> The raw and cleaned CSVs are **not** committed to this repo.
>  Download the source file from the link above and follow the steps in notebooks/week1_uk_hpi_cleaning.ipynb` to reproduce `uk_hpi_stage1_cleaned.csv`.

## Project Structure

notebooks/
  week1_uk_hpi_cleaning.ipynb   # cleaning, missing-value analysis, feature engineering, EDA
docs/
  UK_HPI_Preprocessing_Report.docx  # formal write-up of the cleaning stage
sql/
  schema.sql                    # normalized MySQL schema (properties, regions, price_history)
  queries.sql                   # 10+ analysis queries
  load_data.py                  # loads cleaned CSV into MySQL
ml/
  train_model.py                # pulls from MySQL, trains + evaluates regression models
  model.pkl                     # saved trained model
app/
  app.py                        # Flask app: region/type/date -> predicted price
  templates/
requirements.txt
README.md
```

## Data Cleaning — What Made This Non-Trivial

The raw file looks simple (one row per region per month) but has real structure
worth understanding before using it:

**A critical date-parsing bug.** The source file writes dates as `DD/MM/YYYY`
(UK convention). `pandas.to_datetime()` defaults to `MM/DD/YYYY` and will
silently misread months as days unless told `dayfirst=True`. Caught by
comparing converted dates against the raw CSV text before trusting any
date-based aggregation.

**Missing data follows real, discoverable rules — not randomness.** Every
column with gaps was investigated by grouping on region and year to find the
actual mechanism, rather than applying a single blanket assumption

Rather than deleting or imputing any of this, five boolean flag columns
(`HasSeasonalAdjustment`, `HasPropertyTypeBreakdown`, `HasFundingBreakdown`,
`HasBuyerTypeBreakdown`, `HasValidChangeCalc`) were added so downstream
analysis can explicitly scope itself to valid data instead of guessing.

Full methodology and reasoning: see `docs/UK_HPI_Preprocessing_Report.docx`.

## Tech Stack

- **Data cleaning / EDA:** Python, pandas, numpy, matplotlib
- **Database:** MySQL
- **Modeling:** scikit-learn (Linear Regression, Random Forest), XGBoost
- **Serving:** Flask, Chart.js

## Status

- [x] Data cleaning & missing-value analysis
- [x] Feature engineering
- [ ] MySQL schema design & data load
- [ ] Regression model training & evaluation
- [ ] Flask app + deployment

## Setup

Download the raw CSV from the gov.uk link above, place it in `data/`, then
run `notebooks/week1_uk_hpi_cleaning.ipynb` top to bottom to reproduce the
cleaned dataset.
