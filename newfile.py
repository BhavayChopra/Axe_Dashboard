#!/usr/bin/env python3

import mysql.connector
from mysql.connector import Error
import pandas as pd
from tabulate import tabulate
import sys
import time
from datetime import datetime
import argparse

# Database connection details
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "Bjrock_007"
}

def create_connection(database=None):
    """Create a connection to the MySQL database"""
    try:
        config = DB_CONFIG.copy()
        if database:
            config["database"] = database
        
        # Add connection timeout and other parameters for better stability
        config.update({
            "connection_timeout": 60,
            "use_pure": True,
            "raise_on_warnings": True,
            "buffered": True
        })
        
        connection = mysql.connector.connect(**config)
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"Connected to MySQL Server version {db_info}")
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def get_databases(connection):
    """Get a list of all databases"""
    try:
        cursor = connection.cursor()
        cursor.execute("SHOW DATABASES")
        databases = [db[0] for db in cursor.fetchall() if db[0] not in ['information_schema', 'performance_schema', 'mysql', 'sys']]
        cursor.close()
        return databases
    except Error as e:
        print(f"Error retrieving databases: {e}")
        return []

def get_database_summary(connection, database):
    """Get a summary of a database including tables and their sizes"""
    try:
        cursor = connection.cursor()
        cursor.execute(f"USE {database}")
        
        # Get all tables
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        
        # Get table statistics
        table_stats = []
        total_size_mb = 0
        total_rows = 0
        
        for table in tables:
            # Get table size
            cursor.execute(f"""
                SELECT 
                    TABLE_ROWS,
                    ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS SIZE_MB,
                    CREATE_TIME,
                    UPDATE_TIME
                FROM 
                    information_schema.TABLES 
                WHERE 
                    TABLE_SCHEMA = '{database}' 
                    AND TABLE_NAME = '{table}'
            """)
            result = cursor.fetchone()
            
            if result:
                rows = result[0] if result[0] is not None else "Unknown"
                size_mb = result[1] if result[1] is not None else 0
                create_time = result[2]
                update_time = result[3]
                
                # Get column count
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = '{database}' AND TABLE_NAME = '{table}'
                """)
                column_count = cursor.fetchone()[0]
                
                # Get index count
                cursor.execute(f"""
                    SELECT COUNT(DISTINCT INDEX_NAME) 
                    FROM information_schema.STATISTICS 
                    WHERE TABLE_SCHEMA = '{database}' AND TABLE_NAME = '{table}'
                """)
                index_count = cursor.fetchone()[0]
                
                table_stats.append({
                    "name": table,
                    "rows": rows,
                    "size_mb": size_mb,
                    "columns": column_count,
                    "indexes": index_count,
                    "created": create_time,
                    "updated": update_time
                })
                
                if isinstance(rows, int):
                    total_rows += rows
                total_size_mb += size_mb
        
        cursor.close()
        return {
            "tables": table_stats,
            "table_count": len(tables),
            "total_size_mb": total_size_mb,
            "total_rows": total_rows
        }
    except Error as e:
        print(f"Error retrieving summary for {database}: {e}")
        return None

def get_table_details(connection, database, table):
    """Get detailed information about a specific table"""
    try:
        cursor = connection.cursor()
        cursor.execute(f"USE {database}")
        
        # Set larger buffer sizes for better performance
        cursor.execute("SET SESSION sort_buffer_size = 67108864")  # 64MB
        cursor.execute("SET SESSION sql_buffer_result = ON")
        cursor.execute("SET SESSION join_buffer_size = 33554432")  # 32MB
        cursor.execute("SET SESSION tmp_table_size = 268435456")  # 256MB
        cursor.execute("SET SESSION max_heap_table_size = 268435456")  # 256MB
        
        # Get column information
        cursor.execute(f"DESCRIBE {table}")
        columns = cursor.fetchall()
        
        # Get index information
        cursor.execute(f"""
            SELECT 
                index_name, 
                GROUP_CONCAT(column_name ORDER BY seq_in_index) as columns,
                index_type,
                non_unique
            FROM 
                information_schema.statistics
            WHERE 
                table_schema = '{database}' 
                AND table_name = '{table}'
            GROUP BY 
                index_name, index_type, non_unique
        """)
        indexes = cursor.fetchall()
        
        # Get sample data
        try:
            cursor.execute(f"SELECT * FROM {table} LIMIT 5")
            sample_data = cursor.fetchall()
            
            # Get column names for sample data
            cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{database}' AND TABLE_NAME = '{table}'")
            column_names = [col[0] for col in cursor.fetchall()]
        except Error as e:
            print(f"Warning: Could not get sample data for {table}: {e}")
            sample_data = []
            column_names = []
        
        cursor.close()
        return {
            "columns": columns,
            "indexes": indexes,
            "sample_data": sample_data,
            "column_names": column_names
        }
    except Error as e:
        print(f"Error retrieving details for {database}.{table}: {e}")
        return None

def print_database_summary(database_name, summary):
    """Print a summary of a database"""
    if not summary:
        print(f"No summary available for {database_name}")
        return
    
    print(f"\n{'=' * 80}")
    print(f"Database: {database_name}")
    print(f"{'=' * 80}")
    print(f"Total Tables: {summary['table_count']}")
    print(f"Total Size: {summary['total_size_mb']:.2f} MB")
    print(f"Estimated Total Rows: {summary['total_rows']}")
    
    # Print table summary
    print("\nTables:")
    table_data = []
    for table in summary['tables']:
        table_data.append([
            table['name'], 
            table['rows'], 
            f"{table['size_mb']:.2f} MB", 
            table['columns'],
            table['indexes']
        ])
    
    print(tabulate(
        sorted(table_data, key=lambda x: x[0]),  # Sort by table name
        headers=["Table Name", "Rows", "Size", "Columns", "Indexes"],
        tablefmt="grid"
    ))

def print_table_details(database_name, table_name, details, max_columns=10):
    """Print detailed information about a table"""
    if not details:
        print(f"No details available for {database_name}.{table_name}")
        return
    
    print(f"\n{'=' * 80}")
    print(f"Table: {database_name}.{table_name}")
    print(f"{'=' * 80}")
    
    # Print column information
    print("\nColumns:")
    columns_data = []
    for col in details["columns"]:
        columns_data.append([col[0], col[1], "YES" if col[2] == "YES" else "NO", 
                           "YES" if col[3] == "PRI" else "NO", col[4], col[5]])
    
    print(tabulate(columns_data, 
                 headers=["Name", "Type", "Nullable", "Primary Key", "Default", "Extra"], 
                 tablefmt="grid"))
    
    # Print index information
    if details["indexes"]:
        print("\nIndexes:")
        index_data = []
        for idx in details["indexes"]:
            index_data.append([idx[0], idx[1], idx[2], "No" if idx[3] == 1 else "Yes"])
        
        print(tabulate(index_data, 
                     headers=["Name", "Columns", "Type", "Unique"], 
                     tablefmt="grid"))
    
    # Print sample data with limited columns to avoid excessive output
    if details["sample_data"] and details["column_names"]:
        print("\nSample Data (first 5 rows, limited columns):")
        
        # Limit the number of columns to display
        display_columns = min(max_columns, len(details["column_names"]))
        limited_headers = details["column_names"][:display_columns]
        if display_columns < len(details["column_names"]):
            limited_headers.append("...")
        
        # Prepare limited sample data
        limited_data = []
        for row in details["sample_data"]:
            limited_row = list(row[:display_columns])
            if display_columns < len(row):
                limited_row.append("...")
            limited_data.append(limited_row)
        
        print(tabulate(limited_data, headers=limited_headers, tablefmt="grid"))
        print(f"\nNote: Only showing {display_columns} of {len(details['column_names'])} columns")
    else:
        print("\nNo sample data available.")

def main():
    parser = argparse.ArgumentParser(description="MySQL Database Analyzer")
    parser.add_argument("-d", "--database", help="Specific database to analyze")
    parser.add_argument("-t", "--table", help="Specific table to analyze in detail")
    parser.add_argument("-c", "--columns", type=int, default=5, help="Maximum number of columns to display in sample data")
    args = parser.parse_args()
    
    print("MySQL Database Analyzer")
    print("=======================")
    
    # Connect to MySQL server
    connection = create_connection()
    if not connection:
        return
    
    try:
        # Get all databases or use the specified one
        if args.database:
            databases = [args.database]
        else:
            databases = get_databases(connection)
            print(f"\nFound {len(databases)} user databases: {', '.join(databases)}")
        
        # Analyze each database
        for database in databases:
            # Connect to the specific database
            db_connection = create_connection(database)
            if not db_connection:
                continue
            
            try:
                # Get database summary
                summary = get_database_summary(db_connection, database)
                print_database_summary(database, summary)
                
                # If a specific table is requested, show its details
                if args.table and args.database == database:
                    details = get_table_details(db_connection, database, args.table)
                    print_table_details(database, args.table, details, args.columns)
            finally:
                db_connection.close()
    finally:
        connection.close()
        print("\nDatabase connection closed.")

if __name__ == "__main__":
    main()