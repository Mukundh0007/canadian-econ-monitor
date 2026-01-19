import os
import requests
import zipfile
import io
import pandas as pd

# Define the data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_stats_can_data(table_id, output_filename):
    """
    Fetches data from Statistics Canada using direct CSV URL
    and saves it to a CSV file.
    """
    url = f"https://www150.statcan.gc.ca/n1/tbl/csv/{table_id}-eng.zip"
    print(f"Fetching {table_id} from {url}...")
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        # Open the zip file
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            # The zip usually contains {table_id}.csv and metadata
            csv_name = f"{table_id}.csv"
            if csv_name in z.namelist():
                print(f"Extracting {csv_name}...")
                # Extract to specific path, but we want to rename it
                with z.open(csv_name) as source_file:
                    df = pd.read_csv(source_file)
                    
                output_path = os.path.join(DATA_DIR, output_filename)
                df.to_csv(output_path, index=False)
                print(f"Saved {table_id} to {output_path}")
                return df
            else:
                print(f"Could not find {csv_name} in zip file. Available: {z.namelist()}")
                return None
                
    except Exception as e:
        print(f"Error fetching {table_id}: {e}")
        return None

if __name__ == "__main__":
    # Table IDs from the design document
    
    tasks = [
        ("18100004", "cpi_monthly.csv"),           # Consumer Price Index
        ("20100008", "retail_sales_industry.csv"), # Retail trade sales by industry
        ("20100056", "retail_sales_province.csv")  # Monthly retail trade sales by province
    ]
    
    for table_id, filename in tasks:
        fetch_stats_can_data(table_id, filename)
