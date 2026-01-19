import streamlit as st
import pandas as pd
import altair as alt
import db_utils
from datetime import date, timedelta

# ---- Configuration ----
st.set_page_config(
    page_title="Canadian Inflation Monitor",
    page_icon="🇨🇦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---- Custom CSS ----
st.markdown("""
<style>
    /* Global Styles */
    .stApp {
        background-color: #0e1117;
    }
    .main-header {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        color: #f0f2f6;
        font-size: 3rem;
        margin-bottom: 0px;
    }
    .sub-header {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 400;
        color: #a0a5ab;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    
    /* Metrics Cards */
    div[data-testid="metric-container"] {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #3d3e47;
    }
</style>
""", unsafe_allow_html=True)

# ---- Helper Functions ----
@st.cache_data
def load_metadata():
    provinces = db_utils.get_provinces()['province_name'].tolist()
    industries = db_utils.get_industries()['industry_name'].tolist()
    return provinces, industries

# ---- Sidebar ----
st.sidebar.header("Configuration")

# Load Metadata
provinces_list, industries_list = load_metadata()

# 1. Geography Selection
st.sidebar.subheader("📍 Geography")
geo_filter = st.sidebar.radio(
    "Filter Location Type:",
    ["Provinces", "Cities", "All"],
    index=0,
    horizontal=True,
    help="Filter the geography list below."
)

# Filter logic
# Import valid provinces from db_utils to ensure consistency
from db_utils import VALID_PROVINCES

# For the dropdown, we want to include Canada as a valid "Regional" option usually
provinces_plus_canada = VALID_PROVINCES + ['Canada']

if geo_filter == "Provinces":
    # User likely wants Provinces + Canada in this view
    filtered_geos = [p for p in provinces_list if p in provinces_plus_canada]
elif geo_filter == "Cities":
    filtered_geos = [p for p in provinces_list if p not in provinces_plus_canada]
else:
    filtered_geos = provinces_list

# Use Canada as default if available, else first option
default_geo_index = filtered_geos.index("Canada") if "Canada" in filtered_geos else 0
selected_province = st.sidebar.selectbox("Select Location", filtered_geos, index=default_geo_index)


# 2. Industry Selection
st.sidebar.subheader("🏢 Industry")

# Categorize Industries for better UX
def categorize_industry(name):
    name = name.lower()
    if any(x in name for x in ['motor', 'auto', 'gasoline', 'car']):
        return "Automotive & Fuel"
    elif any(x in name for x in ['food', 'beverage', 'grocery', 'beer', 'wine', 'liquor', 'supermarket', 'convenience']):
        return "Food & Beverage"
    elif any(x in name for x in ['clothing', 'shoe', 'jewelry', 'luggage', 'fashion']):
        return "Clothing & Accessories"
    elif any(x in name for x in ['furniture', 'electronic', 'appliance', 'furnishing']):
        return "Home & Electronics"
    elif any(x in name for x in ['building', 'garden', 'hardware']):
        return "Building & Garden"
    elif any(x in name for x in ['sporting', 'hobby', 'book', 'music']):
        return "Hobbies & Leisure"
    elif any(x in name for x in ['health', 'personal']):
        return "Health & Personal Care"
    elif 'retail trade' in name:
        return "All Retail"
    else:
        return "General & Other"

# Create categories
industry_categories = sorted(list(set([categorize_industry(i) for i in industries_list])))
# Move "All Retail" to top
if "All Retail" in industry_categories:
    industry_categories.insert(0, industry_categories.pop(industry_categories.index("All Retail")))

selected_category = st.sidebar.selectbox("Filter Industry Category", industry_categories)

# Filter industries by category
filtered_inds = [i for i in industries_list if categorize_industry(i) == selected_category]

# Default selection logic
default_ind = filtered_inds[0] if filtered_inds else industries_list[0]
if "Retail trade [44-45]" in filtered_inds:
    default_ind = "Retail trade [44-45]"

selected_industry = st.sidebar.selectbox("Select Sub-Industry", filtered_inds, index=filtered_inds.index(default_ind))

# Date Range
min_date = date(2018, 1, 1) # Focus on recent years by default
max_date = date.today()

st.sidebar.subheader("📅 Time Period")
start_date, end_date = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=date(1990, 1, 1),
    max_value=max_date
)

# ---- Main Content ----
st.markdown('<div class="main-header">Canadian Inflation & Recession Monitor</div>', unsafe_allow_html=True)

# Create tabs for different views
tab1, tab2 = st.tabs(["📉 Deep Dive Analysis", "🇨🇦 National Dashboard"])

with tab1:
    st.markdown(f'<div class="sub-header">Analyzing the impact of inflation on {selected_industry} in {selected_province}</div>', unsafe_allow_html=True)

    # Fetch Data
    with st.spinner("Fetching data from MySQL..."):
        cpi_df = db_utils.get_cpi_data(selected_province, start_date, end_date)
        sales_df = db_utils.get_retail_data(selected_province, selected_industry, start_date, end_date)

    if cpi_df.empty or sales_df.empty:
        st.warning("No data found for the selected combination. Please try expanding the date range or choosing a different industry.")
    else:
        # Merge Data
        cpi_df['date'] = pd.to_datetime(cpi_df['date'])
        sales_df['date'] = pd.to_datetime(sales_df['date'])
        
        merged_df = pd.merge(sales_df, cpi_df, on='date', how='inner')
        
        # Calculate Real Sales
        # Real Sales = Nominal Sales / (CPI / 100)
        merged_df['real_sales'] = merged_df['sales'] / (merged_df['cpi'] / 100.0)
        
        # ---- KPIs ----
        latest_data = merged_df.iloc[-1]
        
        # Calculate YoY for latest month available
        # Find exactly 1 year ago row
        one_year_ago = latest_data['date'] - pd.DateOffset(years=1)
        # Find closest date match
        prev_year_row = merged_df.loc[merged_df['date'] == one_year_ago]
        
        if not prev_year_row.empty:
            prev_year_data = prev_year_row.iloc[0]
            cpi_yoy = ((latest_data['cpi'] - prev_year_data['cpi']) / prev_year_data['cpi']) * 100
            sales_yoy = ((latest_data['sales'] - prev_year_data['sales']) / prev_year_data['sales']) * 100
            real_sales_yoy = ((latest_data['real_sales'] - prev_year_data['real_sales']) / prev_year_data['real_sales']) * 100
        else:
             cpi_yoy = 0
             sales_yoy = 0
             real_sales_yoy = 0
        
        col1, col2, col3 = st.columns(3)
        col1.metric("CPI Inflation (YoY)", f"{cpi_yoy:.2f}%", delta_color="inverse")
        col2.metric("Nominal Sales Growth (YoY)", f"{sales_yoy:.2f}%")
        col3.metric("Real Volume Growth (YoY)", f"{real_sales_yoy:.2f}%", help="Sales adjusted for inflation")

        # ---- Charts ----
        
        # Chart 1: Nominal vs Real Sales
        st.markdown("### Purchasing Power Erosion")
        st.write("Discrepancy between the money spent (Nominal) and the actual volume of goods purchased (Real).")
        
        melted_df = merged_df.melt(id_vars=['date'], value_vars=['sales', 'real_sales'], var_name='Metric', value_name='Amount')
        melted_df['Metric'] = melted_df['Metric'].map({'sales': 'Nominal Sales', 'real_sales': 'Real Sales (Adj)'})
        
        chart_sales = alt.Chart(melted_df).mark_line(point=False).encode(
            x=alt.X('date', title='Date'),
            y=alt.Y('Amount', title='Sales ($ CAD)'),
            color=alt.Color('Metric', scale=alt.Scale(domain=['Nominal Sales', 'Real Sales (Adj)'], range=['#00D4FF', '#FF0055'])),
            tooltip=['date', 'Metric', alt.Tooltip('Amount', format='$,.0f')]
        ).properties(height=400).interactive()
        
        st.altair_chart(chart_sales, use_container_width=True)
        
        # New Row: Seasonality & Wallet Share
        row2_col1, row2_col2 = st.columns(2)
        
        with row2_col1:
            st.markdown("### 🍂 Seasonality Analysis")
            st.write("Comparing monthly sales trends across years.")
            seasonal_df = db_utils.get_seasonal_data(selected_province, selected_industry, end_date.year)
            
            if not seasonal_df.empty:
                chart_seasonal = alt.Chart(seasonal_df).mark_line(point=True).encode(
                    x=alt.X('month:O', title='Month'),
                    y=alt.Y('sales', title='Sales ($)'),
                    color=alt.Color('year:N', title='Year'),
                    tooltip=['year', 'month', alt.Tooltip('sales', format='$,.0f')]
                ).properties(height=350)
                st.altair_chart(chart_seasonal, use_container_width=True)
            else:
                st.info("Insufficient data for seasonality analysis.")

        with row2_col2:
            st.markdown(f"### 🥧 Wallet Share ({selected_province})")
            st.write("Distribution of retail spending by category.")
            dist_df = db_utils.get_industry_distribution(selected_province, end_date)
            
            if not dist_df.empty:
                # Apply categorization
                dist_df['Category'] = dist_df['industry_name'].apply(categorize_industry)
                # Aggregate
                pie_df = dist_df.groupby('Category')['sales'].sum().reset_index()
                # Sort
                pie_df = pie_df.sort_values('sales', ascending=False)
                
                base = alt.Chart(pie_df).encode(
                    theta=alt.Theta("sales", stack=True), 
                    color=alt.Color("Category")
                )
                pie = base.mark_arc(outerRadius=120, innerRadius=50).encode(
                     order=alt.Order("sales", sort="descending"),
                     tooltip=["Category", alt.Tooltip("sales", format="$,.0f"), alt.Tooltip("sales", format=".1%")]
                )
                text = base.mark_text(radius=140).encode(
                    text="sales",
                    order=alt.Order("sales", sort="descending"),
                )
                st.altair_chart(pie, use_container_width=True)
            else:
                st.info("No distribution data available.")

        # Scatter for Elasticity
        st.markdown("### Inflation Elasticity Check")
        st.write("Does higher inflation correlate with lower real spending?")
        
        base = alt.Chart(merged_df).encode(x=alt.X('cpi', title='CPI Index', scale=alt.Scale(zero=False)))
        scatter = base.mark_circle(size=60).encode(
            y=alt.Y('real_sales', title='Real Sales Volume', scale=alt.Scale(zero=False)),
            tooltip=['date', 'cpi', 'real_sales'],
            color=alt.value('#FFAA00')
        )
        line = scatter.transform_regression('cpi', 'real_sales').mark_line(color='white', strokeDash=[5,5])
        
        st.altair_chart(scatter + line, use_container_width=True)

        # Data Table
        with st.expander("View Raw Data"):
            st.dataframe(merged_df.sort_values('date', ascending=False))

with tab2:
    st.markdown("### National Economic Snapshot")
    st.write("Comparing performance across industries and provinces for the latest available period.")
    
    # Snapshot Date
    row1_col1, row1_col2 = st.columns(2)
    
    with row1_col1:
        st.subheader(f"Industry Winners & Losers ({selected_province})")
        ind_growth_df = db_utils.get_latest_yoy_growth_by_industry(selected_province, end_date)
        
        if not ind_growth_df.empty:
             # Sort head/tail
             top_bottom = pd.concat([ind_growth_df.head(5), ind_growth_df.tail(5)])
             
             chart_ind = alt.Chart(top_bottom).mark_bar().encode(
                 x=alt.X('yoy_growth', title='YoY Growth (%)'),
                 y=alt.Y('industry_name', sort='-x', title=None),
                 color=alt.condition(
                     alt.datum.yoy_growth > 0,
                     alt.value('#00FF7F'),  # Green for positive
                     alt.value('#FF4B4B')   # Red for negative
                 ),
                 tooltip=['industry_name', alt.Tooltip('yoy_growth', format='.2f')]
             ).properties(height=400)
             st.altair_chart(chart_ind, use_container_width=True)
        else:
            st.info("No industry data available for this range.")
            
    with row1_col2:
        st.subheader(f"Provincial Heatmap: {selected_industry}")
        prov_growth_df = db_utils.get_provincial_comparison(selected_industry, end_date)
        
        if not prov_growth_df.empty:
             chart_prov = alt.Chart(prov_growth_df).mark_bar().encode(
                 x=alt.X('province_name', sort='-y', title=None),
                 y=alt.Y('yoy_growth', title='YoY Growth (%)'),
                 color=alt.condition(
                     alt.datum.yoy_growth > 0,
                     alt.value('#00D4FF'),
                     alt.value('#FF0055')
                 ),
                 tooltip=['province_name', alt.Tooltip('yoy_growth', format='.2f')]
             ).properties(height=400)
             st.altair_chart(chart_prov, use_container_width=True)
        else:
             st.info("No provincial comparison data available.")
