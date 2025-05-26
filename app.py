import os
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
import io
from datetime import datetime # Import datetime to get the current date

app = Flask(__name__)
app.secret_key = 'your_secret_key' # Replace with a strong secret key for production

# Database configuration (replace with your MySQL credentials)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'SAHIL9581', # Make sure this password is correct
    'database': 'stock_nf'
}

# Upload folder configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    """Checks if a given filename has an allowed Excel extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        flash("Database connection error. Please try again later.", 'error')
        return None

def close_db_connection(conn):
    """Closes the database connection if it exists."""
    if conn:
        conn.close()

# --- Core Data Fetching Functions ---

def fetch_products():
    """
    Fetches ALL entries for the main stock table, ordered by their database ID (as they were inserted).
    Includes the 'created_at' (last updated) timestamp.
    Returns products, total_count, and error.
    """
    products = []
    total_count = 0 # Initialize total_count
    error = None
    conn = get_db_connection()
    if conn:
        # Use a buffered cursor for general fetching to avoid unread result issues
        cursor = conn.cursor(buffered=True)
        try:
            cursor.execute("SELECT id, item_code, particulars, quantity, reserved, net_quantity, store_name, created_at FROM nafla ORDER BY id ASC")
            result = cursor.fetchall()

            products = [(id, code, part, float(q) if q is not None else 0.0, float(r) if r is not None else 0.0, float(nq) if nq is not None else 0.0, store_name, created_at)
                        for id, code, part, q, r, nq, store_name, created_at in result]
            
            total_count = len(products) # Calculate total count of products fetched
        except mysql.connector.Error as err:
            error = f"Error fetching products: {err}"
            print(error)
            flash(error, 'error')
        finally:
            cursor.close()
            close_db_connection(conn)
    else:
        error = "Database connection not available."
        print(error)
        flash(error, 'error')
    return products, total_count, error # Return total_count as well

def fetch_product_details(item_code):
    """
    Fetches all records for a given item_code, ordered by ID.
    This shows the exact history of that item_code across all store names,
    but remember that updates now overwrite previous data for matching item_code + store_name.
    Includes the 'created_at' timestamp.
    """
    details = []
    error = None
    conn = get_db_connection()

    if conn:
        # Use a buffered cursor
        cursor = conn.cursor(buffered=True)
        try:
            cursor.execute(
                """SELECT id, item_code, particulars, quantity, reserved, net_quantity, store_name, purchase_date, reservation_date, customer_name, engineer_name, created_at
                   FROM nafla
                   WHERE item_code = %s ORDER BY id ASC""", (item_code,)
            )
            result = cursor.fetchall()

            details = [(id, code, part, float(q) if q is not None else 0.0, float(r) if r is not None else 0.0, float(nq) if nq is not None else 0.0, store_name, purchase_date, reservation_date, customer_name, engineer_name, created_at)
                       for id, code, part, q, r, nq, store_name, purchase_date, reservation_date, customer_name, engineer_name, created_at in result]

            print(f"Details fetched for {item_code}: {details}") # Debug print

            if not details:
                return [], None # No product found
        except mysql.connector.Error as err:
            error = f"Error fetching product details: {err}"
            print(error)
            flash(error, 'error')
        finally:
            cursor.close()
            close_db_connection(conn)
    else:
        error = "Database connection not available."
        print(error)
        flash(error, 'error')
    return details, error

# --- Excel Import Function ---

def import_excel_data(filepath):
    """
    Imports data from an Excel file. If an item_code and store_name combination
    already exists, that record is updated. Otherwise, a new record is inserted.
    The 'created_at' timestamp will be handled automatically by the database.
    """
    error = None
    imported_count = 0
    updated_count = 0
    new_inserted_count = 0

    conn = get_db_connection() # Get a new connection for the import process
    if not conn:
        return "Database connection not available for import."

    try:
        # Crucial fix: Use a buffered cursor for the import process
        # This allows multiple SELECTs and INSERT/UPDATEs without "Unread result found"
        cursor = conn.cursor(buffered=True)

        df = pd.read_excel(filepath)
        
        # Ensure required columns are present
        required_columns = ['item_code', 'particulars', 'quantity', 'reserved', 'store_name', 'engineer_name']
        for col in required_columns:
            if col not in df.columns:
                return f"Error: Excel file is missing required column: '{col}'"

        # Add optional columns if they don't exist in DataFrame (to avoid KeyError)
        for col_opt in ['purchase_date', 'reservation_date', 'customer_name']:
            if col_opt not in df.columns:
                df[col_opt] = None  

        for index, row in df.iterrows():
            try:
                item_code = str(row['item_code'])
                particulars = str(row['particulars']) if pd.notna(row['particulars']) else None
                quantity = float(row['quantity'])
                reserved = float(row['reserved'])
                net_quantity = quantity - reserved
                store_name = str(row['store_name']) if pd.notna(row['store_name']) else None

                # Handle pandas NaT (Not a Time) for dates and NaN/NaT for strings/objects
                # Ensure date format is 'YYYY-MM-DD'
                purchase_date = row['purchase_date'].strftime('%Y-%m-%d') if pd.notna(row['purchase_date']) else None
                reservation_date = row['reservation_date'].strftime('%Y-%m-%d') if pd.notna(row['reservation_date']) else None
                customer_name = str(row['customer_name']) if pd.notna(row['customer_name']) else None
                engineer_name = str(row['engineer_name']) if pd.notna(row['engineer_name']) else None

                # Check if a record with the same item_code AND store_name already exists
                cursor.execute(
                    "SELECT id FROM nafla WHERE item_code = %s AND store_name = %s",
                    (item_code, store_name)
                )
                existing_record = cursor.fetchone() # Fetch the result to clear the cursor

                if existing_record:
                    # Update existing record
                    record_id = existing_record[0]
                    cursor.execute(
                        """
                        UPDATE nafla
                        SET particulars = %s, quantity = %s, reserved = %s, net_quantity = %s,
                            purchase_date = %s, reservation_date = %s, customer_name = %s, engineer_name = %s
                        WHERE id = %s
                        """,
                        (particulars, quantity, reserved, net_quantity, purchase_date,
                         reservation_date, customer_name, engineer_name, record_id)
                    )
                    conn.commit()
                    updated_count += 1
                    print(f"Updated record (ID: {record_id}) from Excel for item_code: {item_code}, store: {store_name} (Row {index + 2})")
                else:
                    # Insert new record if no match found
                    cursor.execute(
                        """
                        INSERT INTO nafla (item_code, particulars, quantity, reserved, net_quantity, store_name, purchase_date, reservation_date, customer_name, engineer_name)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (item_code, particulars, quantity, reserved, net_quantity, store_name, purchase_date,
                         reservation_date, customer_name, engineer_name)
                    )
                    conn.commit()
                    new_inserted_count += 1
                    print(f"Inserted new record from Excel for item_code: {item_code}, store: {store_name} (Row {index + 2})")
                imported_count += 1
            except ValueError as ve:
                conn.rollback()
                error = f"Error: Invalid data type in Excel file. Please ensure 'quantity' and 'reserved' are numeric. Row {index + 2}: {ve}"
                print(error)
                return error
            except mysql.connector.Error as e:
                conn.rollback()
                error = f"Database error during Excel import for row {index + 2}: {e}"
                print(error)
                return error
        
        flash_message = f"Excel import complete. {imported_count} rows processed: {updated_count} updated, {new_inserted_count} new records inserted."
        flash(flash_message, 'success')
        return None
    except Exception as e:
        error = f"Error reading Excel file or general error during import: {e}"
        print(error)
        return error
    finally:
        cursor.close()
        close_db_connection(conn) # Close the connection used for import

# --- Flask Routes ---

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Main page route. Displays all stock entries.
    Handles search, Excel upload, and provides links to add/update/view history.
    """
    products = []
    error = None
    total_products_count = 0 # Initialize total_products_count
    conn = get_db_connection()
    if conn:
        # Use a buffered cursor for the main page search
        cursor = conn.cursor(buffered=True)
        try:
            if request.method == 'POST' and 'search' in request.form:
                search_term = request.form.get('search')
                if search_term:
                    try:
                        cursor.execute(
                            "SELECT id, item_code, particulars, quantity, reserved, net_quantity, store_name, created_at FROM nafla WHERE item_code LIKE %s ORDER BY id ASC",
                            (f"%{search_term}%",)
                        )
                        result = cursor.fetchall()
                        products = [(id, code, part, float(q) if q is not None else 0.0, float(r) if r is not None else 0.0, float(nq) if nq is not None else 0.0, store_name, created_at)
                                    for id, code, part, q, r, nq, store_name, created_at in result]
                        total_products_count = len(products) # Count for search results
                    except mysql.connector.Error as err:
                        error = f"Error searching products: {err}"
                        print(error)
                        flash(error, 'error')
                else: # If search term is empty, show all products
                    products, total_products_count, error = fetch_products() 
            elif request.method == 'POST' and 'remove_duplicates' in request.form:
                flash("The Excel import and 'Add' functionality now update existing records based on Item Code and Store Name if a match is found, treating each row as a unique item in a specific store. No explicit 'duplicate removal' is needed in the same way as before.", 'info')
                products, total_products_count, error = fetch_products() # Re-fetch to show latest data
            elif request.method == 'POST' and 'upload_excel' in request.files:
                excel_file = request.files['upload_excel']
                if excel_file and allowed_file(excel_file.filename):
                    filename = secure_filename(excel_file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    excel_file.save(filepath)
                    error = import_excel_data(filepath) 
                    if error:
                        flash(error, 'error')
                    products, total_products_count, error = fetch_products() # Re-fetch to show updated data
                else:
                    error = "Invalid file. Please upload an Excel file (xlsx, xls)."
                    flash(error, 'error')
                    products, total_products_count, error = fetch_products() # Re-fetch even on error to show current data
            else:
                products, total_products_count, error = fetch_products() # Default fetch all products (current stock)

        finally:
            cursor.close()
            close_db_connection(conn)
    else:
        flash("Database connection not available. Cannot display stock.", 'error')
        return render_template('index.html', products=[], error="Database connection not available.", total_products_count=0)
    return render_template('index.html', products=products, error=error, total_products_count=total_products_count)

@app.route('/autocomplete')
def autocomplete():
    """Provides autocomplete suggestions for item codes."""
    conn = get_db_connection()
    if conn:
        # Use a buffered cursor
        cursor = conn.cursor(buffered=True)
        try:
            term = request.args.get('term', '')
            cursor.execute("SELECT DISTINCT item_code FROM nafla WHERE item_code LIKE %s LIMIT 10", (f"%{term}%",))
            suggestions = [row[0] for row in cursor.fetchall()]
            return jsonify(suggestions)
        except mysql.connector.Error as err:
            print(f"Autocomplete error: {err}")
            return jsonify([])
        finally:
            cursor.close()
            close_db_connection(conn)
    return jsonify([])

@app.route('/add', methods=['POST'])
def add():
    """
    Adds a new product or updates an existing one if item_code and store_name match.
    The 'created_at' timestamp will be handled automatically by the database.
    """
    conn = get_db_connection()
    if conn:
        # Use a buffered cursor for add/update logic
        cursor = conn.cursor(buffered=True)
        item_code = request.form['item_code']
        particulars = request.form['particulars']
        store_name = request.form['store_name']
        purchase_date = request.form.get('purchase_date')
        reservation_date = request.form.get('reservation_date')
        customer_name = request.form.get('customer_name')
        engineer_name = request.form.get('engineer_name')

        try:
            quantity = float(request.form['quantity'])
            reserved = float(request.form.get('reserved', 0))
            net_quantity = quantity - reserved
            
            # Check if item_code and store_name exist to either update or insert
            cursor.execute(
                "SELECT id FROM nafla WHERE item_code = %s AND store_name = %s",
                (item_code, store_name)
            )
            existing_record = cursor.fetchone() # Fetch the result to clear the cursor

            if existing_record:
                # Update existing record
                record_id = existing_record[0]
                cursor.execute(
                    """
                    UPDATE nafla
                    SET particulars = %s, quantity = %s, reserved = %s, net_quantity = %s,
                        purchase_date = %s, reservation_date = %s, customer_name = %s, engineer_name = %s
                    WHERE id = %s
                    """,
                    (particulars, quantity, reserved, net_quantity, purchase_date,
                     reservation_date, customer_name, engineer_name, record_id)
                )
                conn.commit()
                flash('Product updated successfully (existing record patched)!', 'success')
            else:
                # Insert new record
                cursor.execute(
                    """INSERT INTO nafla (item_code, particulars, quantity, reserved, net_quantity, store_name, purchase_date, reservation_date, customer_name, engineer_name)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (item_code, particulars, quantity, reserved, net_quantity, store_name, purchase_date, reservation_date,
                     customer_name, engineer_name))
                conn.commit()
                flash('New product added successfully!', 'success')
            return redirect('/')
        except ValueError:
            flash('Invalid data for quantity or reserved', 'error')
            return redirect('/')
        except mysql.connector.Error as err:
            print(f"Error adding/updating product: {err}")
            flash(f"Error adding/updating product to the database: {err}", 'error')
            return redirect('/')
        finally:
            cursor.close()
            close_db_connection(conn)
    else:
        flash("Database connection not available. Cannot add product.", 'error')
        return redirect('/')

@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    """
    Handles product update. When a POST request is received, a new record is inserted
    with the updated details, preserving the old record.
    The 'created_at' timestamp will be handled automatically by the database for the new record.
    """
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(buffered=True)
        try:
            if request.method == 'GET':
                try:
                    cursor.execute(
                        """SELECT id, item_code, particulars, quantity, reserved, store_name, purchase_date, reservation_date, customer_name, engineer_name, created_at
                           FROM nafla WHERE id=%s""",
                        (id,))
                    product = cursor.fetchone()
                    if product:
                        product = list(product)
                        # Safely convert to float, defaulting to 0.0 if None
                        product[3] = float(product[3]) if product[3] is not None else 0.0 # quantity
                        product[4] = float(product[4]) if product[4] is not None else 0.0 # reserved
                        if product[6]: # purchase_date
                            product[6] = product[6].strftime('%Y-%m-%d')
                        if product[7]: # reservation_date
                            product[7] = product[7].strftime('%Y-%m-%d')
                        return render_template('update.html', product=product)
                    else:
                        flash("Product not found.", 'error')
                        return redirect('/')
                except mysql.connector.Error as err:
                    print(f"Error fetching product for update: {err}")
                    flash(f"Error fetching product with ID {id} for update: {err}", 'error')
                    return redirect('/')
            elif request.method == 'POST':
                item_code = request.form['item_code']
                particulars = request.form['particulars']
                store_name = request.form['store_name']
                purchase_date = request.form.get('purchase_date')
                reservation_date = request.form.get('reservation_date')
                customer_name = request.form.get('customer_name')
                engineer_name = request.form.get('engineer_name')

                try:
                    quantity = float(request.form['quantity'])
                    reserved = float(request.form['reserved'])
                    net_quantity = quantity - reserved
                    
                    # Instead of UPDATE, INSERT a new record to preserve history
                    cursor.execute(
                        """INSERT INTO nafla (item_code, particulars, quantity, reserved, net_quantity, store_name, purchase_date, reservation_date, customer_name, engineer_name)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (item_code, particulars, quantity, reserved, net_quantity, store_name, purchase_date, reservation_date,
                         customer_name, engineer_name))
                    conn.commit()
                    flash(f'Stock entry for {item_code} updated (new version added) successfully!', 'success')
                    return redirect('/')
                except ValueError:
                    flash("Invalid data for quantity or reserved", 'error')
                    return redirect(url_for('update', id=id))
                except mysql.connector.Error as err:
                    print(f"Error updating product (inserting new record): {err}")
                    flash(f"Error updating product (inserting new record) for ID {id}: {err}", 'error')
                    return redirect(url_for('update', id=id))
        finally:
            cursor.close()
            close_db_connection(conn)
    else:
        flash("Database connection not available. Cannot update product.", 'error')
        return redirect('/')

@app.route('/delete/<int:id>', methods=['GET'])
def delete(id):
    """
    Deletes a specific product record by its ID.
    This deletes only one entry from the current stock.
    """
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(buffered=True) # Use buffered cursor
        try:
            cursor.execute("DELETE FROM nafla WHERE id = %s", (id,))
            # Check if any row was actually deleted
            if cursor.rowcount > 0:
                conn.commit()
                flash(f'Stock entry with ID {id} deleted successfully.', 'success')
            else:
                conn.rollback() # Rollback if no row was affected (good practice)
                flash(f'Product with ID {id} not found or already deleted.', 'info')
            return redirect('/')
        except mysql.connector.Error as err:
            conn.rollback() # Ensure rollback on error
            flash(f"Error deleting stock entry: {err}", 'error')
            print(f"Error deleting stock entry: {err}")
            return redirect('/')
        finally:
            cursor.close()
            close_db_connection(conn)
    else:
        flash("Database connection not available. Cannot delete product.", 'error')
        return redirect('/')

@app.route('/product_details/<string:item_code>')
def product_details(item_code):
    """
    Displays all records for a given item_code, ordered by ID.
    This will show all entries for that item_code across different store names,
    including their 'created_at' (last updated) timestamp.
    """
    details, error = fetch_product_details(item_code)
    if error:
        flash(error, 'error')
        return redirect('/')
    elif not details:
        flash("No product details found for that item code.", 'info')
        return redirect('/')
    return render_template('product_details.html', details=details, item_code=item_code, error=error)


@app.route('/download_excel')
def download_excel():
    """
    Downloads the entire database table as an Excel file.
    The data will be ordered by its database ID, including 'created_at'.
    """
    conn = get_db_connection()
    if conn:
        try:
            # When using pd.read_sql_query, pandas internally handles fetching
            # all results, so you don't typically need buffered=True here directly.
            df = pd.read_sql_query("SELECT id, item_code, particulars, quantity, reserved, net_quantity, store_name, purchase_date, reservation_date, customer_name, engineer_name, created_at FROM nafla ORDER BY id ASC", conn)

            # Rename columns
            df = df.rename(columns={
                'purchase_date': 'entry_date',
                'created_at': 'updated_at'
            })

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='AllStockData')
            output.seek(0)

            # Generate dynamic filename with current date
            current_date = datetime.now().strftime("%Y-%m-%d")
            filename = f"Stock inventory {current_date}.xlsx"

            # Flash a success message before sending the file
            flash(f"Excel file '{filename}' download initiated!", 'success')

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                download_name=filename, # Use the dynamically generated filename
                as_attachment=True
            )
        except Exception as e:
            flash(f"Error downloading Excel file: {e}", 'error')
            print(f"Error generating Excel file: {e}")
            return redirect('/')
        finally:
            close_db_connection(conn)
    else:
        flash("Database connection not available.", 'error')
        return redirect('/')
    
if __name__ == '__main__':
    app.run(debug=True)
