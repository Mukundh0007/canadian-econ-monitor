import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """
    Establishes a connection to the MySQL database.
    Retries or manages connection parameters from .env
    """
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "canadian_finance")
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        # If database doesn't exist, try connecting without it to create it
        if "Unknown database" in str(e):
            print("Database does not exist. Attempting to create it...")
            create_database()
            return get_db_connection()
        return None

def create_database():
    """Create the database if it doesn't exist"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "")
        )
        if connection.is_connected():
            cursor = connection.cursor()
            db_name = os.getenv("DB_NAME", "canadian_finance")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            print(f"Database {db_name} created successfully")
            cursor.close()
            connection.close()
    except Error as e:
        print(f"Error creating database: {e}")

def init_schema():
    """Reads the schema.sql and applies it to the database"""
    conn = get_db_connection()
    if conn is None:
        print("Failed to connect to database. Please check your .env credentials and ensure MySQL is running.")
        return

    cursor = conn.cursor()
    
    # Read schema file
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sql", "schema.sql")
    print(f"Applying schema from {schema_path}...")
    
    try:
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        
        # Split by semicolon to execute individual statements
        # This is a simple parser, might need robustness for complex SQL
        statements = schema_sql.split(';')
        for statement in statements:
            if statement.strip():
                try:
                    cursor.execute(statement)
                except Error as err:
                    print(f"Error executing statement: {err}")
                    print(f"Statement: {statement[:50]}...")
        
        conn.commit()
        print("Schema applied successfully.")
    except Exception as e:
        print(f"Error applying schema: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    init_schema()
