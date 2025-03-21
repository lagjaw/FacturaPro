import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('invoices.db')
cursor = conn.cursor()

# Execute insert statements
try:
    cursor.executescript("""
    INSERT INTO clients (id, name, email, phone, address, status, revenue, created_at, updated_at) VALUES
    ('client1', 'Example Company', 'contact@example.com', '+1234567890', '123 Business Street', 'active', 1000.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('client2', 'Another Company', 'info@another.com', '+0987654321', '456 Corporate Ave', 'key_account', 5000.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('client3', 'Inactive Company', 'contact@inactive.com', '+1122334455', '789 Old St', 'inactive', 0.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

    INSERT INTO products (id, name, stock_quantity, unit_price, expiration_date, stock_alert_threshold, expiration_alert_threshold, description, category_id, supplier_id, created_at, updated_at) VALUES
    ('product1', 'Product A', 100, 19.99, NULL, 10, 30, 'Description for Product A', 'category1', 'supplier1', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('product2', 'Product B', 50, 29.99, NULL, 5, 15, 'Description for Product B', 'category1', 'supplier2', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

    INSERT INTO invoices (id, invoice_number, client_id, date, due_date, bill_to, total, subtotal, tax, status, created_at, updated_at) VALUES
    ('invoice1', 'INV-001', 'client1', CURRENT_TIMESTAMP, '2025-03-15 00:00:00', 'Example Company', 199.99, 199.99, 0.00, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('invoice2', 'INV-002', 'client2', CURRENT_TIMESTAMP, '2025-04-15 00:00:00', 'Another Company', 299.99, 299.99, 0.00, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

    INSERT INTO payment_transactions (id, client_id, invoice_id, amount, transaction_date, payment_method, status, created_at, updated_at) VALUES
    ('transaction1', 'client1', 'invoice1', 199.99, CURRENT_TIMESTAMP, 'credit_card', 'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('transaction2', 'client2', 'invoice2', 299.99, CURRENT_TIMESTAMP, 'bank_transfer', 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

    INSERT INTO categories (id, name, created_at) VALUES
    ('category1', 'Electronics', CURRENT_TIMESTAMP),
    ('category2', 'Furniture', CURRENT_TIMESTAMP);

    INSERT INTO suppliers (id, name, contact_info, created_at) VALUES
    ('supplier1', 'Supplier A', 'contact@supplierA.com', CURRENT_TIMESTAMP),
    ('supplier2', 'Supplier B', 'contact@supplierB.com', CURRENT_TIMESTAMP);

    INSERT INTO alerts (id, type, message, related_id, related_type, status, created_at, updated_at) VALUES
    ('alert1', 'client_status_change', 'Client client1 is now a key account', 'client1', 'client', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
    """)
    conn.commit()
    print("Data inserted successfully.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    conn.close()