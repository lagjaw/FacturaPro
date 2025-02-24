import sqlite3

# Connexion à la base de données (ou création si elle n'existe pas)
conn = sqlite3.connect("invoices.db")
cursor = conn.cursor()

# Création de la nouvelle table PaymentTransaction
cursor.execute("""
    CREATE TABLE IF NOT EXISTS payment_transactions (
        id TEXT PRIMARY KEY,
        client_id TEXT,
        invoice_id TEXT,
        amount NUMERIC NOT NULL DEFAULT 0,
        transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        payment_method TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        due_date DATETIME,
        paid_amount NUMERIC DEFAULT 0,
        remaining_amount NUMERIC DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
""")

# Sauvegarde et fermeture de la connexion
conn.commit()
conn.close()

print("✅ Table 'payment_transactions' créée avec succès !")
