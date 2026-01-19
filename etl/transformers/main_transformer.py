import pandas as pd
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

def transform_cpi(input_file="cpi_monthly.csv"):
    print("Transforming CPI data...")
    df = pd.read_csv(os.path.join(DATA_DIR, input_file))
    
    # Select relevant columns
    # We want: REF_DATE (Date), GEO (Geography), Products and product groups (Product), VALUE
    df = df[['REF_DATE', 'GEO', 'Products and product groups', 'VALUE']]
    
    # Rename columns to match our internal naming convention or schema expectations
    df.columns = ['date', 'geography', 'product', 'value']
    
    # Filter out rows with missing values
    df = df.dropna(subset=['value'])
    
    # Normalize Date
    df['date'] = pd.to_datetime(df['date'])
    
    return df

def transform_retail_industry(input_file="retail_sales_industry.csv"):
    print("Transforming Retail Industry data...")
    df = pd.read_csv(os.path.join(DATA_DIR, input_file), dtype={'North American Industry Classification System (NAICS)': str})
    
    # Look for 'Adjustments' column. We usually want 'Seasonally adjusted' for economic analysis, 
    # or 'Unadjusted' depending on user preference. The design doc mentions "Real vs Nominal", 
    # which often implies using Unadjusted + CPI adjustment, or Seasonally adjusted for trend.
    # Let's keep both or specific one? Let's filter for "Seasonally adjusted" as default for trends.
    if 'Adjustments' in df.columns:
        df = df[df['Adjustments'] == 'Seasonally adjusted']
    
    df = df[['REF_DATE', 'GEO', 'North American Industry Classification System (NAICS)', 'VALUE']]
    df.columns = ['date', 'geography', 'industry', 'value']
    
    df = df.dropna(subset=['value'])
    df['date'] = pd.to_datetime(df['date'])
    
    return df

def transform_retail_province(input_file="retail_sales_province.csv"):
    print("Transforming Retail Province data...")
    df = pd.read_csv(os.path.join(DATA_DIR, input_file))
    
    # Columns: REF_DATE, GEO, NAICS, Sales, Adjustments, VALUE
    # Filter for 'Total retail sales' type only to simplify for now
    if 'Sales' in df.columns:
        df = df[df['Sales'] == 'Total retail sales']
        
    if 'Adjustments' in df.columns:
        df = df[df['Adjustments'] == 'Seasonally adjusted']
        
    df = df[['REF_DATE', 'GEO', 'North American Industry Classification System (NAICS)', 'VALUE']]
    df.columns = ['date', 'geography', 'industry', 'value']
    
    df = df.dropna(subset=['value'])
    df['date'] = pd.to_datetime(df['date'])
    
    return df

if __name__ == "__main__":
    # Test transformations
    try:
        cpi_df = transform_cpi()
        print(f"CPI Data: {cpi_df.shape}")
        print(cpi_df.head())
        
        ind_df = transform_retail_industry()
        print(f"Retail Industry Data: {ind_df.shape}")
        print(ind_df.head())
        
        prov_df = transform_retail_province()
        print(f"Retail Province Data: {prov_df.shape}")
        print(prov_df.head())
    except Exception as e:
        print(f"Error during transformation: {e}")
