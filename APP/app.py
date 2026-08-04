from flask import Flask, render_template, request
import joblib
import pandas as pd
import mysql.connector

from dotenv import load_dotenv
import os

load_dotenv()

DB_CONFIG = {
    "host": os.environ.get("DB_HOST"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "database": os.environ.get("DB_NAME"),
}

app = Flask(__name__)

# --- Part 2: load the saved model once, connect to MySQL ---
model_bundle = joblib.load("price_model.pkl")
model = model_bundle["model"]
region_encoder = model_bundle["region_encoder"]
category_encoder = model_bundle["category_encoder"]
feature_cols = model_bundle["feature_cols"]



def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


# --- Part 3: helper functions ---
def get_regions_and_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT region_name FROM regions ORDER BY region_name")
    regions = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT category_name FROM categories ORDER BY category_name")
    categories = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT region_tier, region_name FROM regions")
    tier_lookup = {row[1]: row[0] for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    return regions, categories, tier_lookup


def get_recent_sales_volume(region_name, category_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ph.sales_volume FROM price_history ph
        JOIN regions r ON r.region_id = ph.region_id
        JOIN categories c ON c.category_id = ph.category_id
        WHERE r.region_name = %s AND c.category_name = %s AND ph.sales_volume IS NOT NULL
        ORDER BY ph.price_date DESC LIMIT 1
    """, (region_name, category_name))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else 150


# --- Part 4: chart data ---
def get_price_history(region_name, category_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ph.price_date, ph.average_price FROM price_history ph
        JOIN regions r ON r.region_id = ph.region_id
        JOIN categories c ON c.category_id = ph.category_id
        WHERE r.region_name = %s AND c.category_name = %s
        ORDER BY ph.price_date
    """, (region_name, category_name))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    labels = [row[0].strftime("%Y-%m") for row in rows]
    values = [float(row[1]) for row in rows]
    return labels, values


# --- Part 5: homepage route ---
@app.route("/", methods=["GET"])
def index():
    regions, categories, _ = get_regions_and_categories()
    return render_template("index.html", regions=regions, categories=categories)


# --- Part 6: prediction route ---
@app.route("/predict", methods=["POST"])
def predict():
    region_name = request.form["region"]
    category_name = request.form["category"]
    year = int(request.form["year"])
    month = int(request.form["month"])

    _, _, tier_lookup = get_regions_and_categories()
    region_tier = tier_lookup.get(region_name, "Local Authority")
    sales_volume = get_recent_sales_volume(region_name, category_name)

    region_encoded = region_encoder.transform([region_name])[0]
    category_encoded = category_encoder.transform([category_name])[0]

    row = {
        "Year": year, "Month": month,
        "RegionEncoded": region_encoded, "CategoryEncoded": category_encoded,
        "sales_volume": sales_volume,
        "Tier_Nation": 1 if region_tier == "Nation" else 0,
        "Tier_Region": 1 if region_tier == "Region" else 0,
        "Tier_Local Authority": 1 if region_tier == "Local Authority" else 0,
    }
    X_input = pd.DataFrame([row])[feature_cols]
    predicted_price = model.predict(X_input)[0]

    labels, values = get_price_history(region_name, category_name)

    return render_template(
        "result.html",
        region=region_name, category=category_name,
        year=year, month=month,
        predicted_price=round(predicted_price, 0),
        chart_labels=labels, chart_values=values,
    )


# --- Part 7: actually start the server (new — explained below) ---
if __name__ == "__main__":
    app.run(debug=False)