# fix_db.py — أضفه في مجلد civil_registry04copy ثم شغّله مرة واحدة
import sqlite3
import os

DB_PATH = os.path.join('instance', 'civil_registry.db')

columns_to_add = {
    'births': [
        'witness1_name TEXT',
        'witness1_id TEXT',
        'witness1_relation TEXT',
        'witness2_name TEXT',
        'witness2_id TEXT',
        'witness2_relation TEXT',
    ],
    'marriages': [
        'witness1_relation TEXT',
        'witness2_relation TEXT',
    ],
    'deaths': [
        'witness1_name TEXT',
        'witness1_id TEXT',
        'witness1_relation TEXT',
        'witness2_name TEXT',
        'witness2_id TEXT',
        'witness2_relation TEXT',
    ],
    'divorces': [
        'witness1_relation TEXT',
        'witness2_relation TEXT',
        'court_decision_number TEXT',
        'court_name TEXT',
        'custody_decision TEXT',
        'children_count INTEGER DEFAULT 0',
        'marriage_cert_number TEXT',
        'marriage_id INTEGER',
    ],
}

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

for table, columns in columns_to_add.items():
    # اجلب الأعمدة الموجودة حالياً
    cur.execute(f'PRAGMA table_info({table})')
    existing = {row[1] for row in cur.fetchall()}

    for col_def in columns:
        col_name = col_def.split()[0]
        if col_name not in existing:
            cur.execute(f'ALTER TABLE {table} ADD COLUMN {col_def}')
            print(f'✅ أضفت عمود {col_name} إلى جدول {table}')
        else:
            print(f'⏭  {col_name} موجود مسبقاً في {table}')

conn.commit()
conn.close()
print('\n✅ تمت العملية بنجاح')
