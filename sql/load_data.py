"""
Loads uk_hpi_stage1_cleaned.csv into the normalized MySQL schema
(regions, categories, price_history).

The cleaned CSV is "wide": one row per region/month with ~50 columns.
This script "melts" it into "long" format: one row per region + category
+ month, matching price_history's structure.
"""

import pandas as pd
import mysql.connector
from mysql.connector import Error

CSV_PATH = "uk_hpi_stage1_cleaned.csv"

DB_CONFIG = {
    "host": "localhost",
    "user": "hpi_user",
    "password": "hpi_password",
    "database": "uk_hpi",
}

NATION_LEVEL = {
    "United Kingdom", "Great Britain", "England and Wales",
    "England", "Wales", "Scotland", "Northern Ireland",
}
REGION_LEVEL = {
    "North East", "North West", "Yorkshire and The Humber", "East Midlands",
    "West Midlands Region", "East of England", "London", "South East", "South West",
}

# Maps each category to (price_col, index_col, 1m_col, 12m_col, volume_col_or_None, reliability_flag_col)
CATEGORY_MAP = {
    "All":          ("AveragePrice", "Index", "1m%Change", "12m%Change", "SalesVolume", None),
    "Detached":     ("DetachedPrice", "DetachedIndex", "Detached1m%Change", "Detached12m%Change", None, "HasPropertyTypeBreakdown"),
    "SemiDetached": ("SemiDetachedPrice", "SemiDetachedIndex", "SemiDetached1m%Change", "SemiDetached12m%Change", None, "HasPropertyTypeBreakdown"),
    "Terraced":     ("TerracedPrice", "TerracedIndex", "Terraced1m%Change", "Terraced12m%Change", None, "HasPropertyTypeBreakdown"),
    "Flat":         ("FlatPrice", "FlatIndex", "Flat1m%Change", "Flat12m%Change", None, "HasPropertyTypeBreakdown"),
    "Cash":         ("CashPrice", "CashIndex", "Cash1m%Change", "Cash12m%Change", "CashSalesVolume", "HasFundingBreakdown"),
    "Mortgage":     ("MortgagePrice", "MortgageIndex", "Mortgage1m%Change", "Mortgage12m%Change", "MortgageSalesVolume", "HasFundingBreakdown"),
    "FTB":          ("FTBPrice", "FTBIndex", "FTB1m%Change", "FTB12m%Change", None, "HasBuyerTypeBreakdown"),
    "FOO":          ("FOOPrice", "FOOIndex", "FOO1m%Change", "FOO12m%Change", None, "HasBuyerTypeBreakdown"),
    "New":          ("NewPrice", "NewIndex", "New1m%Change", "New12m%Change", "NewSalesVolume", "HasPropertyTypeBreakdown"),
    "Old":          ("OldPrice", "OldIndex", "Old1m%Change", "Old12m%Change", "OldSalesVolume", "HasPropertyTypeBreakdown"),
}

CATEGORY_GROUP = {
    "All": "Headline",
    "Detached": "PropertyType", "SemiDetached": "PropertyType",
    "Terraced": "PropertyType", "Flat": "PropertyType",
    "Cash": "Funding", "Mortgage": "Funding",
    "FTB": "BuyerType", "FOO": "BuyerType",
    "New": "BuildStatus", "Old": "BuildStatus",
}


def region_tier(name: str) -> str:
    if name in NATION_LEVEL:
        return "Nation"
    if name in REGION_LEVEL:
        return "Region"
    return "Local Authority"


def load_regions(cursor, df: pd.DataFrame) -> dict:
    """Insert unique regions, return {region_name: region_id}."""
    regions = df[["RegionName", "AreaCode"]].drop_duplicates()
    region_ids = {}
    for _, row in regions.iterrows():
        tier = region_tier(row["RegionName"])
        cursor.execute(
            """INSERT INTO regions (region_name, area_code, region_tier)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE region_id = LAST_INSERT_ID(region_id)""",
            (row["RegionName"], row["AreaCode"], tier),
        )
        region_ids[row["RegionName"]] = cursor.lastrowid
    return region_ids


def load_categories(cursor) -> dict:
    """Insert the fixed set of categories, return {category_name: category_id}."""
    category_ids = {}
    for name, group in CATEGORY_GROUP.items():
        cursor.execute(
            """INSERT INTO categories (category_name, category_group)
               VALUES (%s, %s)
               ON DUPLICATE KEY UPDATE category_id = LAST_INSERT_ID(category_id)""",
            (name, group),
        )
        category_ids[name] = cursor.lastrowid
    return category_ids


def melt_and_load(cursor, df: pd.DataFrame, region_ids: dict, category_ids: dict):
    """For each category, extract its 4-5 columns and insert as rows into price_history."""
    total_inserted = 0
    insert_sql = """
        INSERT INTO price_history
            (region_id, category_id, price_date, average_price, price_index,
             change_1m_pct, change_12m_pct, sales_volume, is_data_reliable)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE average_price = VALUES(average_price)
    """

    for category_name, (price_col, idx_col, c1_col, c12_col, vol_col, flag_col) in CATEGORY_MAP.items():
        category_id = category_ids[category_name]
        cols = ["RegionName", "Date", price_col, idx_col, c1_col, c12_col]
        if vol_col:
            cols.append(vol_col)
        if flag_col:
            cols.append(flag_col)

        sub = df[cols].copy()
        sub = sub.dropna(subset=[price_col])  # only load rows that actually have a value for this category

        rows = []
        for _, r in sub.iterrows():
            region_id = region_ids[r["RegionName"]]
            price_date = pd.to_datetime(r["Date"]).date()
            volume = int(r[vol_col]) if vol_col and pd.notna(r[vol_col]) else None
            reliable = bool(r[flag_col]) if flag_col else True
            rows.append((
                region_id, category_id, price_date,
                float(r[price_col]) if pd.notna(r[price_col]) else None,
                float(r[idx_col]) if pd.notna(r[idx_col]) else None,
                float(r[c1_col]) if pd.notna(r[c1_col]) else None,
                float(r[c12_col]) if pd.notna(r[c12_col]) else None,
                volume, reliable,
            ))

        if rows:
            cursor.executemany(insert_sql, rows)
            total_inserted += len(rows)
            print(f"  {category_name}: {len(rows)} rows")

    return total_inserted


def main():
    print(f"Reading {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH)
    df["Date"] = pd.to_datetime(df["Date"])
    print(f"  {len(df)} rows, {df['RegionName'].nunique()} regions")

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        print("Loading regions...")
        region_ids = load_regions(cursor, df)
        conn.commit()
        print(f"  {len(region_ids)} regions loaded")

        print("Loading categories...")
        category_ids = load_categories(cursor)
        conn.commit()
        print(f"  {len(category_ids)} categories loaded")

        print("Melting and loading price_history (this is the slow part)...")
        total = melt_and_load(cursor, df, region_ids, category_ids)
        conn.commit()
        print(f"Done. {total} total price_history rows inserted.")

    except Error as e:
        conn.rollback()
        print(f"Error, rolled back: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
