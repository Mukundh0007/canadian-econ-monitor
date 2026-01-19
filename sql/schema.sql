-- Create tables for the Canadian Financial Data Project

CREATE TABLE IF NOT EXISTS dim_date (
    date_id INT AUTO_INCREMENT PRIMARY KEY,
    full_date DATE NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    quarter INT NOT NULL,
    UNIQUE(full_date)
);

CREATE TABLE IF NOT EXISTS dim_geography (
    geo_id INT AUTO_INCREMENT PRIMARY KEY,
    province_name VARCHAR(100) NOT NULL,
    UNIQUE(province_name)
);

CREATE TABLE IF NOT EXISTS dim_industry (
    industry_id INT AUTO_INCREMENT PRIMARY KEY,
    industry_name VARCHAR(255) NOT NULL,
    naics_code VARCHAR(50),
    UNIQUE(industry_name)
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    UNIQUE(product_name)
);

-- Fact Table: CPI Data
CREATE TABLE IF NOT EXISTS fact_cpi (
    cpi_id INT AUTO_INCREMENT PRIMARY KEY,
    date_id INT,
    geo_id INT,
    product_id INT,
    value DECIMAL(10, 2),
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
    FOREIGN KEY (geo_id) REFERENCES dim_geography(geo_id),
    FOREIGN KEY (product_id) REFERENCES dim_product(product_id)
);

-- Fact Table: Retail Sales
CREATE TABLE IF NOT EXISTS fact_retail_sales (
    sales_id INT AUTO_INCREMENT PRIMARY KEY,
    date_id INT,
    geo_id INT,
    industry_id INT,
    value DECIMAL(15, 2), -- Large numbers for sales
    unit VARCHAR(50), -- e.g., 'Dollars', 'Percentage'
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
    FOREIGN KEY (geo_id) REFERENCES dim_geography(geo_id),
    FOREIGN KEY (industry_id) REFERENCES dim_industry(industry_id)
);
