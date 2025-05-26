import pandas as pd
import mysql.connector
from datetime import datetime

def import_excel_to_mysql(excel_file_path, host, user, password, database):
    """
    Imports data from an Excel file into a MySQL database, with error handling,
    data validation, and efficient insertion, including date conversion.

    Args:
        excel_file_path (str): Path to the Excel file.
        host (str): MySQL host.
        user (str): MySQL user.
        password (str): MySQL password.
        database (str): MySQL database name.
    """
    conn = None
    cursor = None
    try:
        # 1. Load Excel file
        df = pd.read_excel(excel_file_path)
        if df.empty:
            print("❌ Error: Excel file is empty.")
            return
        print("✅ Excel file loaded.")

        # 2. Clean NaN values in 'reserved' column
        df['reserved'] = df['reserved'].fillna(0)

        # 3. Connect to MySQL
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()
        print("✅ Connected to MySQL database.")

        # 4. Validate data and prepare for insertion
        data_to_insert = []
        for index, row in df.iterrows():
            item_code = str(row['item_code']).strip()
            particulars = str(row['particulars']).strip()
            quantity = row['quantity']
            reserved = row.get('reserved', 0)
            store_name = str(row.get('store_name', 'AL NAHLA SOLUTIONS LLC')).strip()
            purchase_date = row.get('purchase_date')
            reservation_date = row.get('reservation_date')
            customer_name = row.get('customer_name')
            engineer_name = str(row.get('engineer_name', '')).strip()

            if not isinstance(quantity, (int, float)) or not isinstance(reserved, (int, float)):
                print(f"❌ Error: Invalid data type in row {index + 1}. 'quantity' and 'reserved' must be numeric.")
                continue
            net_quantity = quantity - reserved

            # Convert dates to MySQL format if they are datetime objects
            if isinstance(purchase_date, pd.Timestamp):
                purchase_date = purchase_date.strftime('%Y-%m-%d')  # Or '%Y-%m-%d %H:%M:%S'
            if isinstance(reservation_date, pd.Timestamp):
                reservation_date = reservation_date.strftime('%Y-%m-%d')

            data_to_insert.append(
                (item_code, particulars, quantity, reserved, net_quantity, store_name, purchase_date, reservation_date,
                 customer_name, engineer_name))

        # 5. Use executemany for efficient insertion
        cursor.executemany(
            """
            INSERT INTO nafla (item_code, particulars, quantity, reserved, net_quantity, store_name, purchase_date, reservation_date, customer_name, engineer_name) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            data_to_insert
        )
        conn.commit()
        print("✅ All data inserted successfully!")

    except FileNotFoundError:
        print("❌ Error: Excel file not found.")
    except pd.errors.EmptyDataError:
        print("❌ Error: No data in Excel file.")
    except pd.errors.ParserError as e:
        print(f"❌ Error parsing Excel file: {e}")
    except mysql.connector.Error as err:
        print(f"❌ MySQL error: {err}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    excel_file_path = "uploads/Al_Nahla_Store.xlsx"
    mysql_host = "localhost"
    mysql_user = "root"
    mysql_password = "SAHIL9581"
    mysql_database = "stock_nf"

    import_excel_to_mysql(excel_file_path, mysql_host, mysql_user, mysql_password, mysql_database)
