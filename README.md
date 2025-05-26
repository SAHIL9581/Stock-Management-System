# Stock Inventory Management System

A Flask-based web application for managing stock inventory with MySQL database integration. This system allows you to track products across multiple store locations with full CRUD operations and Excel import/export functionality.

## Features

- **Complete Stock Management**: Add, update, view, and delete stock entries
- **Multi-Store Support**: Track inventory across different store locations
- **Excel Integration**: Import data from Excel files and export current inventory
- **Smart Updates**: Automatically updates existing records based on Item Code + Store Name combination
- **Search Functionality**: Real-time search with autocomplete suggestions
- **Product History**: View complete history of any item code across all stores
- **Duplicate Prevention**: Intelligent handling of duplicate entries during imports
- **Date Tracking**: Automatic timestamping with purchase and reservation dates

## Tech Stack

- **Backend**: Python Flask
- **Database**: MySQL
- **Frontend**: HTML templates with Bootstrap styling
- **Data Processing**: Pandas, NumPy
- **File Handling**: Excel (.xlsx, .xls) support

## Prerequisites

- Python 3.7+
- MySQL Server
- Required Python packages (see Installation)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/stock-inventory-system.git
   cd stock-inventory-system
   ```

2. **Install required packages**
   ```bash
   pip install flask mysql-connector-python pandas numpy openpyxl xlsxwriter werkzeug
   ```

3. **Set up MySQL Database**
   ```sql
   CREATE DATABASE stock_nf;
   USE stock_nf;
   
   CREATE TABLE nafla (
       id INT AUTO_INCREMENT PRIMARY KEY,
       item_code VARCHAR(100) NOT NULL,
       particulars TEXT,
       quantity DECIMAL(10,2) DEFAULT 0,
       reserved DECIMAL(10,2) DEFAULT 0,
       net_quantity DECIMAL(10,2) GENERATED ALWAYS AS (quantity - reserved) STORED,
       store_name VARCHAR(100),
       purchase_date DATE,
       reservation_date DATE,
       customer_name VARCHAR(100),
       engineer_name VARCHAR(100),
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
   );
   ```

4. **Configure Database Connection**
   Update the `DB_CONFIG` in the code with your MySQL credentials:
   ```python
   DB_CONFIG = {
       'host': 'localhost',
       'user': 'your_username',
       'password': 'your_password',
       'database': 'stock_nf'
   }
   ```

5. **Create Upload Directory**
   ```bash
   mkdir uploads
   ```

## Usage

1. **Start the application**
   ```bash
   python app.py
   ```

2. **Access the web interface**
   Open your browser and navigate to `http://localhost:5000`

## Key Functionalities

### Stock Management
- **Add New Items**: Use the form to add new stock entries
- **Update Existing**: Click update button to modify quantities and details
- **Delete Entries**: Remove specific stock records
- **View All**: See complete inventory with quantities and store locations

### Excel Operations
- **Import**: Upload Excel files to bulk import/update inventory data
- **Export**: Download complete inventory as Excel file with timestamp
- **Required Excel Columns**: `item_code`, `particulars`, `quantity`, `reserved`, `store_name`, `engineer_name`
- **Optional Columns**: `purchase_date`, `reservation_date`, `customer_name`

### Search & Filter
- **Real-time Search**: Search by item code with instant results
- **Autocomplete**: Get suggestions while typing item codes
- **Product History**: View complete transaction history for any item

### Smart Data Handling
- **Automatic Net Quantity**: Calculated as `quantity - reserved`
- **Duplicate Management**: Updates existing records instead of creating duplicates
- **Data Validation**: Ensures numeric values for quantities
- **Error Handling**: Comprehensive error messages and rollback on failures

## Database Schema

```sql
Table: nafla
├── id (INT, AUTO_INCREMENT, PRIMARY KEY)
├── item_code (VARCHAR(100), NOT NULL)
├── particulars (TEXT)
├── quantity (DECIMAL(10,2))
├── reserved (DECIMAL(10,2))
├── net_quantity (DECIMAL(10,2), COMPUTED)
├── store_name (VARCHAR(100))
├── purchase_date (DATE)
├── reservation_date (DATE)
├── customer_name (VARCHAR(100))
├── engineer_name (VARCHAR(100))
└── created_at (TIMESTAMP, AUTO-UPDATE)
```

## Excel File Format

Your Excel file should contain these columns:

| Column Name | Required | Type | Description |
|-------------|----------|------|-------------|
| item_code | Yes | Text | Unique identifier for the item |
| particulars | Yes | Text | Item description |
| quantity | Yes | Number | Total quantity in stock |
| reserved | Yes | Number | Reserved/allocated quantity |
| store_name | Yes | Text | Store location name |
| engineer_name | Yes | Text | Responsible engineer |
| purchase_date | No | Date | Purchase date (YYYY-MM-DD) |
| reservation_date | No | Date | Reservation date (YYYY-MM-DD) |
| customer_name | No | Text | Customer name if reserved |

## API Endpoints

- `GET /` - Main dashboard with all stock entries
- `POST /add` - Add new stock entry
- `GET /update/<id>` - Get update form for specific entry
- `POST /update/<id>` - Update stock entry (creates new version)
- `GET /delete/<id>` - Delete specific stock entry
- `GET /product_details/<item_code>` - View history for item code
- `GET /autocomplete` - Get autocomplete suggestions
- `GET /download_excel` - Export inventory to Excel

## Security Notes

- Change the `app.secret_key` to a strong, unique value for production
- Use environment variables for database credentials
- Implement proper authentication for production use
- Add input validation and sanitization for user inputs

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions, please open an issue on GitHub or contact the development team.

---

**Made with ❤️ for efficient inventory management**
