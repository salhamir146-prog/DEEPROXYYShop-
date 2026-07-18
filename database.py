import sqlite3
import config

DB_NAME = "shop.db"

def get_db():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  price INTEGER NOT NULL,
                  stock INTEGER DEFAULT 0,
                  codes TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  product_id INTEGER NOT NULL,
                  amount INTEGER NOT NULL,
                  receipt_file_id TEXT,
                  status TEXT DEFAULT 'pending',
                  assigned_code TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS admins
                 (user_id INTEGER PRIMARY KEY)''')
    
    for admin_id in config.ADMIN_IDS:
        c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (admin_id,))
    
    conn.commit()
    conn.close()

def get_product(product_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, price, stock, codes FROM products WHERE id = ?", (product_id,))
    result = c.fetchone()
    conn.close()
    return result

def get_all_products():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, price, stock FROM products WHERE stock > 0")
    result = c.fetchall()
    conn.close()
    return result

def create_transaction(user_id, product_id, amount, file_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO transactions 
                 (user_id, product_id, amount, receipt_file_id, status) 
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, product_id, amount, file_id, 'pending'))
    trans_id = c.lastrowid
    conn.commit()
    conn.close()
    return trans_id

def get_transaction(trans_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE id = ?", (trans_id,))
    result = c.fetchone()
    conn.close()
    return result

def update_transaction_status(trans_id, status, assigned_code=None):
    conn = get_db()
    c = conn.cursor()
    if assigned_code:
        c.execute('''UPDATE transactions 
                     SET status = ?, assigned_code = ? 
                     WHERE id = ?''', (status, assigned_code, trans_id))
    else:
        c.execute("UPDATE transactions SET status = ? WHERE id = ?", (status, trans_id))
    conn.commit()
    conn.close()

def get_pending_transactions():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE status = 'pending' ORDER BY created_at DESC")
    result = c.fetchall()
    conn.close()
    return result

def get_user_transactions(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    result = c.fetchall()
    conn.close()
    return result

def use_product_code(product_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT codes FROM products WHERE id = ?", (product_id,))
    row = c.fetchone()
    
    if not row or not row[0]:
        conn.close()
        return None
    
    codes_list = row[0].split(',')
    if not codes_list:
        conn.close()
        return None
    
    assigned_code = codes_list[0].strip()
    remaining_codes = ','.join(codes_list[1:])
    
    c.execute("UPDATE products SET codes = ?, stock = stock - 1 WHERE id = ?", 
              (remaining_codes if remaining_codes else None, product_id))
    conn.commit()
    conn.close()
    
    return assigned_code

def is_admin(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None
