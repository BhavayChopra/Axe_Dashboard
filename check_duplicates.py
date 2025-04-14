#!/usr/bin/env python3

import mysql.connector
from mysql.connector import Error
import pandas as pd
from tabulate import tabulate
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

def check_table_exists(connection, database, table):
    """Check if a specific table exists in the database"""
    try:
        cursor = connection.cursor()
        cursor.execute(f"USE {database}")
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        cursor.close()
        return table in tables
    except Error as e:
        print(f"Error checking if table exists: {e}")
        return False

def get_table_columns(connection, database, table):
    """Get column names for a specific table"""
    try:
        cursor = connection.cursor()
        cursor.execute(f"USE {database}")
        cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{database}' AND TABLE_NAME = '{table}'")
        columns = [col[0] for col in cursor.fetchall()]
        cursor.close()
        return columns
    except Error as e:
        print(f"Error retrieving columns for {database}.{table}: {e}")
        return []

def find_duplicates(connection, database, table, columns=None):
    """Find duplicate records in a table based on specified columns"""
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(f"USE {database}")
        
        # Set larger buffer sizes for better performance
        cursor.execute("SET SESSION sort_buffer_size = 67108864")  # 64MB
        cursor.execute("SET SESSION sql_buffer_result = ON")
        cursor.execute("SET SESSION join_buffer_size = 33554432")  # 32MB
        cursor.execute("SET SESSION tmp_table_size = 268435456")  # 256MB
        cursor.execute("SET SESSION max_heap_table_size = 268435456")  # 256MB
        cursor.execute("SET SESSION group_concat_max_len = 1048576")  # 1MB
        
        # If no columns specified, get all columns
        if not columns:
            columns = get_table_columns(connection, database, table)
        
        # Exclude BLOB/TEXT columns as they can't be used in GROUP BY
        cursor.execute(f"""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = '{database}' 
            AND TABLE_NAME = '{table}'
            AND DATA_TYPE IN ('blob', 'text', 'mediumtext', 'longtext', 'mediumblob', 'longblob')
        """)
        blob_text_columns = [col['COLUMN_NAME'] for col in cursor.fetchall()]
        
        # Remove BLOB/TEXT columns from the columns list
        columns = [col for col in columns if col not in blob_text_columns]
        
        # Get primary key columns
        cursor.execute(f"""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
            WHERE TABLE_SCHEMA = '{database}' 
            AND TABLE_NAME = '{table}' 
            AND CONSTRAINT_NAME = 'PRIMARY'
        """)
        primary_key_columns = [col['COLUMN_NAME'] for col in cursor.fetchall()]
        
        # Get total row count
        cursor.execute(f"SELECT COUNT(*) as total FROM {table}")
        total_rows = cursor.fetchone()['total']
        print(f"\nTotal rows in {table}: {total_rows}")
        
        # Find duplicates based on all columns (except BLOB/TEXT)
        if columns:
            # Create a comma-separated list of columns for the GROUP BY clause
            group_by_columns = ", ".join(columns)
            
            # Create a SELECT clause that includes all columns
            select_columns = ", ".join([f"`{col}`" for col in columns])
            
            # Query to find duplicates
            query = f"""
                SELECT {select_columns}, COUNT(*) as duplicate_count
                FROM {table}
                GROUP BY {group_by_columns}
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC
                LIMIT 100
            """
            
            cursor.execute(query)
            duplicates = cursor.fetchall()
            
            if duplicates:
                print(f"\nFound {len(duplicates)} groups of duplicate records (showing up to 100):")
                
                # Prepare data for tabulate
                headers = list(duplicates[0].keys())
                table_data = []
                for dup in duplicates:
                    row = [dup[col] if col in dup else "N/A" for col in headers]
                    table_data.append(row)
                
                print(tabulate(table_data, headers=headers, tablefmt="grid"))
                
                # For the first duplicate group, show the actual duplicate records
                if duplicates and len(duplicates) > 0:
                    first_dup = duplicates[0]
                    conditions = []
                    for col in columns:
                        if col in first_dup and first_dup[col] is not None:
                            if isinstance(first_dup[col], str):
                                conditions.append(f"`{col}` = '{first_dup[col].replace("'", "''")}'")
                            else:
                                conditions.append(f"`{col}` = {first_dup[col]}")
                    
                    if conditions:
                        where_clause = " AND ".join(conditions)
                        detail_query = f"SELECT * FROM {table} WHERE {where_clause} LIMIT 10"
                        
                        try:
                            cursor.execute(detail_query)
                            detail_records = cursor.fetchall()
                            
                            if detail_records:
                                print(f"\nSample of duplicate records for first group (up to 10):")
                                
                                # Limit the columns to display to avoid excessive output
                                display_columns = min(10, len(detail_records[0].keys()))
                                headers = list(detail_records[0].keys())[:display_columns]
                                if display_columns < len(detail_records[0].keys()):
                                    headers.append("...")
                                
                                table_data = []
                                for rec in detail_records:
                                    row = [rec[col] if col in rec else "N/A" for col in headers[:display_columns]]
                                    if display_columns < len(rec.keys()):
                                        row.append("...")
                                    table_data.append(row)
                                
                                print(tabulate(table_data, headers=headers, tablefmt="grid"))
                                print(f"Note: Only showing {display_columns} of {len(detail_records[0].keys())} columns")
                        except Error as e:
                            print(f"Error retrieving detail records: {e}")
            else:
                print("No duplicates found based on all columns.")
            
            # If primary keys exist, check for duplicates based on specific important columns
            if primary_key_columns:
                print(f"\nPrimary key columns: {', '.join(primary_key_columns)}")
            else:
                print("\nNo primary key defined for this table.")
                
                # Suggest potential duplicate checks based on common column names
                potential_id_columns = [col for col in columns if 'id' in col.lower() or 'key' in col.lower()]
                potential_content_columns = [col for col in columns if 'content' in col.lower() or 'text' in col.lower() or 'message' in col.lower()]
                potential_user_columns = [col for col in columns if 'user' in col.lower()]
                potential_time_columns = [col for col in columns if 'time' in col.lower() or 'date' in col.lower() or 'created' in col.lower()]
                
                suggested_columns = []
                if potential_id_columns:
                    suggested_columns.extend(potential_id_columns[:2])  # Limit to 2 ID columns
                if potential_content_columns:
                    suggested_columns.extend(potential_content_columns[:1])  # Limit to 1 content column
                if potential_user_columns:
                    suggested_columns.extend(potential_user_columns[:1])  # Limit to 1 user column
                
                if suggested_columns:
                    print(f"\nSuggested columns for duplicate check: {', '.join(suggested_columns)}")
                    print("Run this script with the --columns parameter to check these specific columns.")
        else:
            print("No valid columns found for duplicate checking.")
        
        cursor.close()
    except Error as e:
        print(f"Error finding duplicates in {database}.{table}: {e}")

def main():
    parser = argparse.ArgumentParser(description="MySQL Duplicate Record Finder")
    parser.add_argument("-d", "--database", default="axe_assistant", help="Database to analyze (default: axe_assistant)")
    parser.add_argument("-t", "--table", default="axe_assistant_prompts_responses", help="Table to check for duplicates (default: axe_assistant_prompts_responses)")
    parser.add_argument("-c", "--columns", help="Comma-separated list of columns to check for duplicates")
    args = parser.parse_args()
    
    print("MySQL Duplicate Record Finder")
    print("============================")
    
    # Connect to MySQL server
    connection = create_connection(args.database)
    if not connection:
        return
    
    try:
        # Check if table exists
        if not check_table_exists(connection, args.database, args.table):
            print(f"Table '{args.table}' does not exist in database '{args.database}'")
            return
        
        # Parse columns if provided
        columns = None
        if args.columns:
            columns = [col.strip() for col in args.columns.split(',')]
        
        # Find duplicates
        find_duplicates(connection, args.database, args.table, columns)
    finally:
        connection.close()
        print("\nDatabase connection closed.")

if __name__ == "__main__":
    main()