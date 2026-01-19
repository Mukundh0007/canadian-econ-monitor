import os
import sys
import pandas as pd
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Add etl to path to import transformers
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from etl.transformers.main_transformer import transform_cpi, transform_retail_industry, transform_retail_province

load_dotenv()

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "canadian_finance")
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def load_dim_geography(conn, df_list):
    """
    Extracts unique geography names from all dataframes and loads into dim_geography
    """
    print("Loading dim_geography...")
    unique_geos = set()
    for df in df_list:
        unique_geos.update(df['geography'].unique())
    
    cursor = conn.cursor()
    count = 0
    for geo in unique_geos:
        try:
            # Insert ignore to skip duplicates
            cursor.execute("INSERT IGNORE INTO dim_geography (province_name) VALUES (%s)", (geo,))
            count += 1
        except Error as e:
            print(f"Error inserting geo {geo}: {e}")
    conn.commit()
    cursor.close()
    print(f"Processed {count} geographies.")

def load_dim_product(conn, df):
    """
    Extracts unique products from CPI dataframe and loads into dim_product
    """
    print("Loading dim_product...")
    unique_products = df['product'].unique()
    cursor = conn.cursor()
    count = 0
    for prod in unique_products:
        try:
            cursor.execute("INSERT IGNORE INTO dim_product (product_name) VALUES (%s)", (prod,))
            count += 1
        except Error as e:
            print(f"Error inserting product {prod}: {e}")
    conn.commit()
    cursor.close()
    print(f"Processed {count} products.")

def load_dim_industry(conn, df_list):
    """
    Extracts unique industries from retail dataframes and loads into dim_industry
    """
    print("Loading dim_industry...")
    unique_inds = set()
    for df in df_list:
        unique_inds.update(df['industry'].unique())
        
    cursor = conn.cursor()
    count = 0
    for ind in unique_inds:
        try:
            cursor.execute("INSERT IGNORE INTO dim_industry (industry_name) VALUES (%s)", (ind,))
            count += 1
        except Error as e:
            print(f"Error inserting industry {ind}: {e}")
    conn.commit()
    cursor.close()
    print(f"Processed {count} industries.")

def load_dim_date(conn, df_list):
    """
    Extracts unique dates and loads into dim_date
    """
    print("Loading dim_date...")
    unique_dates = set()
    for df in df_list:
        unique_dates.update(df['date'].unique())
    
    cursor = conn.cursor()
    count = 0
    for date_val in unique_dates:
        # date_val is a Timestamp
        d = pd.to_datetime(date_val)
        quarter = (d.month - 1) // 3 + 1
        
        try:
            cursor.execute("""
                INSERT IGNORE INTO dim_date (full_date, year, month, quarter) 
                VALUES (%s, %s, %s, %s)
            """, (d.date(), d.year, d.month, quarter))
            count += 1
        except Error as e:
            print(f"Error inserting date {d}: {e}")
    conn.commit()
    cursor.close()
    print(f"Processed {count} dates.")

def load_fact_cpi(conn, df):
    print("Loading fact_cpi...")
    cursor = conn.cursor()
    
    # Pre-fetch dimensions to memory to speed up lookups (or use SQL joins/subqueries)
    # For bulk loading, it is often faster to map in Python or use LOAD DATA INFILE.
    # We will use simple row-by-row for simplicity/robustness first, or batch insert.
    
    # Let's map IDs first
    print("Fetching dimension maps...")
    cursor.execute("SELECT full_date, date_id FROM dim_date")
    date_map = {str(d): i for d, i in cursor.fetchall()}
    
    cursor.execute("SELECT province_name, geo_id FROM dim_geography")
    geo_map = {n: i for n, i in cursor.fetchall()}
    
    cursor.execute("SELECT product_name, product_id FROM dim_product")
    prod_map = {n: i for n, i in cursor.fetchall()}
    
    # Prepare batch
    data_to_insert = []
    
    # Iterate with limit check? No, let's try to batch.
    # df has: date, geography, product, value
    # We need to map these to IDs.
    
    print("Mapping data to IDs...")
    # Convert date column to string for mapping
    temp_df = df.copy()
    temp_df['date_str'] = temp_df['date'].dt.date.astype(str)
    
    for _, row in temp_df.iterrows():
        d_id = date_map.get(row['date_str'])
        g_id = geo_map.get(row['geography'])
        p_id = prod_map.get(row['product'])
        
        if d_id and g_id and p_id:
            data_to_insert.append((d_id, g_id, p_id, row['value']))
            
    # Bulk Insert
    print(f"Inserting {len(data_to_insert)} rows into fact_cpi...")
    query = "INSERT INTO fact_cpi (date_id, geo_id, product_id, value) VALUES (%s, %s, %s, %s)"
    
    batch_size = 1000
    for i in range(0, len(data_to_insert), batch_size):
        batch = data_to_insert[i:i + batch_size]
        cursor.executemany(query, batch)
        if i % 10000 == 0:
            print(f"Inserted {i} rows...")
            conn.commit()
            
    conn.commit()
    cursor.close()
    print("Done loading fact_cpi.")

def load_fact_retail(conn, df):
    print("Loading fact_retail_sales...")
    cursor = conn.cursor()
    
    print("Fetching dimension maps...")
    cursor.execute("SELECT full_date, date_id FROM dim_date")
    date_map = {str(d): i for d, i in cursor.fetchall()}
    
    cursor.execute("SELECT province_name, geo_id FROM dim_geography")
    geo_map = {n: i for n, i in cursor.fetchall()}
    
    cursor.execute("SELECT industry_name, industry_id FROM dim_industry")
    ind_map = {n: i for n, i in cursor.fetchall()}
    
    data_to_insert = []
    temp_df = df.copy()
    temp_df['date_str'] = temp_df['date'].dt.date.astype(str)
    
    print("Mapping data to IDs...")
    for _, row in temp_df.iterrows():
        d_id = date_map.get(row['date_str'])
        g_id = geo_map.get(row['geography'])
        i_id = ind_map.get(row['industry'])
        
        if d_id and g_id and i_id:
            # We assume 'Dollars' for unit for now based on CSV review
            data_to_insert.append((d_id, g_id, i_id, row['value'], 'Dollars'))
            
    query = "INSERT INTO fact_retail_sales (date_id, geo_id, industry_id, value, unit) VALUES (%s, %s, %s, %s, %s)"
    
    print(f"Inserting {len(data_to_insert)} rows into fact_retail_sales...")
    batch_size = 1000
    for i in range(0, len(data_to_insert), batch_size):
        batch = data_to_insert[i:i + batch_size]
        cursor.executemany(query, batch)
        
    conn.commit()
    cursor.close()
    print("Done loading fact_retail_sales.")


def run_etl():
    conn = get_db_connection()
    if not conn:
        return
        
    try:
        # Get data
        cpi_df = transform_cpi()
        retail_ind_df = transform_retail_industry()
        retail_prov_df = transform_retail_province()
        
        # Load Dimensions
        load_dim_geography(conn, [cpi_df, retail_ind_df, retail_prov_df])
        load_dim_date(conn, [cpi_df, retail_ind_df, retail_prov_df])
        load_dim_product(conn, cpi_df)
        load_dim_industry(conn, [retail_ind_df, retail_prov_df])
        
        # Load Facts
        # Note: This might take a while for large CPI files
        load_fact_cpi(conn, cpi_df)
        load_fact_retail(conn, retail_ind_df) # Industry specific
        load_fact_retail(conn, retail_prov_df) # Province specific aggregates
        
    except Exception as e:
        print(f"ETL Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    run_etl()
