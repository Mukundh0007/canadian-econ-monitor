import os
import mysql.connector
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_connection():
    """
    Establishes a connection to the MySQL database.
    Checks streamlit secrets first, then environment variables.
    """
    try:
        # Check if secrets file exists before accessing
        # Or just catch the specific error for secrets
        try:
             if hasattr(st, "secrets") and "mysql" in st.secrets:
                 return mysql.connector.connect(
                    host=st.secrets["mysql"]["host"],
                    port=st.secrets["mysql"]["port"],
                    user=st.secrets["mysql"]["user"],
                    password=st.secrets["mysql"]["password"],
                    database=st.secrets["mysql"]["database"]
                )
        except FileNotFoundError:
            pass # No secrets file, move to env vars
        except Exception:
            pass # Other secrets errors, ignore

        # Fallback to local .env
        # Ensure we look for .env in the project root
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        load_dotenv(env_path)
        
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "canadian_finance")
        )
        return connection
    except Exception as e:
        print(f"DEBUG: Database connection error: {e}") # Print to console for debugging
        try:
             st.error(f"Error connecting to database: {e}")
        except:
             pass
        return None

def run_query(query, params=None):
    """
    Executes a SQL query and returns a pandas DataFrame.
    """
    conn = get_connection()
    if conn:
        try:
            df = pd.read_sql(query, conn, params=params)
            conn.close()
            return df
        except Exception as e:
            st.error(f"Query failed: {e}")
            conn.close()
            return pd.DataFrame()
    return pd.DataFrame()

# ---- Constants ----
VALID_PROVINCES = [
    'Alberta', 'British Columbia', 'Manitoba', 'New Brunswick', 
    'Newfoundland and Labrador', 'Northwest Territories', 'Nova Scotia', 
    'Nunavut', 'Ontario', 'Prince Edward Island', 'Quebec', 
    'Saskatchewan', 'Yukon'
]

# ---- Reusable Queries ----

def get_provinces(only_provinces=False):
    df = run_query("SELECT province_name FROM dim_geography ORDER BY province_name")
    if only_provinces and not df.empty:
        df = df[df['province_name'].isin(VALID_PROVINCES)]
    return df

def get_industries():
    return run_query("SELECT industry_name FROM dim_industry ORDER BY industry_name")

def get_cpi_data(province, start_date, end_date):
    """
    Fetches aggregate CPI (All-items) for a specific province and date range.
    """
    query = """
    SELECT 
        d.full_date as date,
        f.value as cpi
    FROM fact_cpi f
    JOIN dim_date d ON f.date_id = d.date_id
    JOIN dim_geography g ON f.geo_id = g.geo_id
    JOIN dim_product p ON f.product_id = p.product_id
    WHERE g.province_name = %s
      AND d.full_date BETWEEN %s AND %s
      AND p.product_name = 'All-items'
    ORDER BY d.full_date
    """
    return run_query(query, (province, start_date, end_date))

def get_retail_data(province, industry, start_date, end_date):
    """
    Fetches retail sales for a specific province and industry.
    """
    query = """
    SELECT 
        d.full_date as date,
        f.value as sales
    FROM fact_retail_sales f
    JOIN dim_date d ON f.date_id = d.date_id
    JOIN dim_geography g ON f.geo_id = g.geo_id
    JOIN dim_industry i ON f.industry_id = i.industry_id
    WHERE g.province_name = %s
      AND i.industry_name = %s
      AND d.full_date BETWEEN %s AND %s
    ORDER BY d.full_date
    """
    return run_query(query, (province, industry, start_date, end_date))

def get_latest_yoy_growth_by_industry(province, date_limit):
    """
    Calculates YoY Nominal Sales growth for all industries in a province.
    Returns DataFrame: [industry, current_sales, prev_sales, yoy_growth]
    """
    # Current period (approx latest month in DB) vs Same month last year
    # We will pick the latest available date for each industry
    query = """
    WITH LatestDate AS (
        SELECT MAX(d.full_date) as max_date 
        FROM fact_retail_sales f 
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE d.full_date <= %s
    ),
    CurrentSales AS (
        SELECT 
            i.industry_name,
            f.value as current_value
        FROM fact_retail_sales f
        JOIN dim_date d ON f.date_id = d.date_id
        JOIN dim_geography g ON f.geo_id = g.geo_id
        JOIN dim_industry i ON f.industry_id = i.industry_id
        WHERE g.province_name = %s
          AND d.full_date = (SELECT max_date FROM LatestDate)
    ),
    PrevSales AS (
        SELECT 
            i.industry_name,
            f.value as prev_value
        FROM fact_retail_sales f
        JOIN dim_date d ON f.date_id = d.date_id
        JOIN dim_geography g ON f.geo_id = g.geo_id
        JOIN dim_industry i ON f.industry_id = i.industry_id
        WHERE g.province_name = %s
          AND d.full_date = DATE_SUB((SELECT max_date FROM LatestDate), INTERVAL 1 YEAR)
    )
    SELECT 
        c.industry_name,
        c.current_value,
        p.prev_value,
        ((c.current_value - p.prev_value) / p.prev_value) * 100 as yoy_growth
    FROM CurrentSales c
    JOIN PrevSales p ON c.industry_name = p.industry_name
    ORDER BY yoy_growth ASC
    """
    return run_query(query, (date_limit, province, province))



def get_provincial_comparison(industry, date_limit):
    """
    Compare sales growth across provinces for a specific industry.
    Excludes 'Canada' and cities, strictly filters for provinces/territories.
    """
    # We'll use the VALID_PROVINCES list to filter inside the query or post-process.
    # Passing the list to SQL IN clause is cleaner.
    placeholders = ', '.join(['%s'] * len(VALID_PROVINCES))
    
    query = f"""
    WITH LatestDate AS (
        SELECT MAX(d.full_date) as max_date 
        FROM fact_retail_sales f 
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE d.full_date <= %s
    ),
    CurrentSales AS (
        SELECT 
            g.province_name,
            f.value as current_value
        FROM fact_retail_sales f
        JOIN dim_date d ON f.date_id = d.date_id
        JOIN dim_geography g ON f.geo_id = g.geo_id
        JOIN dim_industry i ON f.industry_id = i.industry_id
        WHERE i.industry_name = %s
          AND d.full_date = (SELECT max_date FROM LatestDate)
          AND g.province_name IN ({placeholders})
    ),
    PrevSales AS (
        SELECT 
            g.province_name,
            f.value as prev_value
        FROM fact_retail_sales f
        JOIN dim_date d ON f.date_id = d.date_id
        JOIN dim_geography g ON f.geo_id = g.geo_id
        JOIN dim_industry i ON f.industry_id = i.industry_id
        WHERE i.industry_name = %s
          AND d.full_date = DATE_SUB((SELECT max_date FROM LatestDate), INTERVAL 1 YEAR)
          AND g.province_name IN ({placeholders})
    )
    SELECT 
        c.province_name,
        ((c.current_value - p.prev_value) / p.prev_value) * 100 as yoy_growth
    FROM CurrentSales c
    JOIN PrevSales p ON c.province_name = p.province_name
    ORDER BY yoy_growth DESC
    """
    # Params: date_limit, industry, *provinces, industry, *provinces
    params = [date_limit, industry] + VALID_PROVINCES + [industry] + VALID_PROVINCES
    return run_query(query, tuple(params))

def get_industry_distribution(province, date_limit):
    """
    Fetches sales data for ALL industries in a province for the latest available date.
    Used for Pie/Donut charts.
    """
    query = """
    WITH LatestDate AS (
        SELECT MAX(d.full_date) as max_date 
        FROM fact_retail_sales f 
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE d.full_date <= %s
    )
    SELECT 
        i.industry_name,
        f.value as sales
    FROM fact_retail_sales f
    JOIN dim_date d ON f.date_id = d.date_id
    JOIN dim_geography g ON f.geo_id = g.geo_id
    JOIN dim_industry i ON f.industry_id = i.industry_id
    WHERE g.province_name = %s
      AND d.full_date = (SELECT max_date FROM LatestDate)
      AND i.industry_name != 'Retail trade [44-45]' -- Exclude the total aggregate
    ORDER BY sales DESC
    """
    return run_query(query, (date_limit, province))

def get_seasonal_data(province, industry, end_year):
    """
    Fetches monthly sales data for the last 3 years to show seasonality/trends.
    """
    start_year = end_year - 2
    query = """
    SELECT 
        d.year,
        d.month,
        f.value as sales
    FROM fact_retail_sales f
    JOIN dim_date d ON f.date_id = d.date_id
    JOIN dim_geography g ON f.geo_id = g.geo_id
    JOIN dim_industry i ON f.industry_id = i.industry_id
    WHERE g.province_name = %s
      AND i.industry_name = %s
      AND d.year BETWEEN %s AND %s
    ORDER BY d.year, d.month
    """
    return run_query(query, (province, industry, start_year, end_year))
