CREATE DATABASE IF NOT EXISTS stock_nf;
USE stock_nf;

CREATE TABLE nafla (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_code VARCHAR(100),
    particulars TEXT,
    quantity INT,
    reserved INT,
    store_name VARCHAR(255),
    purchase_date DATE,
    reservation_date DATE,
    customer_name VARCHAR(255),
    engineer_name VARCHAR(255)
);
