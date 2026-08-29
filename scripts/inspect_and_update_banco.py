import os
import re
import sqlite3

DB = 'banco.db'
BACKUP = 'banco.db.bak'

if not os.path.exists(DB):
    print('ERROR: banco.db not found')
    raise SystemExit(1)

# show current schema
con = sqlite3.connect(DB)
cur = con.cursor()
create_row = cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='armarios'").fetchone()
create = create_row[0] if create_row else None
print('CREATE TABLE for armarios:')
print(create if create else 'Table not found')
cols = cur.execute("PRAGMA table_info(armarios)").fetchall()
print('\nColumns (PRAGMA):')
for c in cols:
    print(c)

# Detect UNIQUE(...) clause and check whether it already includes localizacao
needs_update = False
m = None
if create:
    m = re.search(r'UNIQUE\s*\(([^)]+)\)', create, flags=re.IGNORECASE)
    if m:
        unique_cols = [s.strip().strip('"\'') for s in m.group(1).split(',')]
        if 'localizacao' not in [c.lower() for c in unique_cols]:
            needs_update = True
    else:
        # no UNIQUE clause found — if there is a single-column unique index elsewhere, update
        if 'UNIQUE' in create.upper():
            needs_update = True

if needs_update:
    print('\nFound UNIQUE on numero without localizacao. Will update table after backup.')
    # backup
    if not os.path.exists(BACKUP):
        import shutil
        shutil.copyfile(DB, BACKUP)
        print('Backup created:', BACKUP)
    else:
        print('Backup already exists:', BACKUP)

    # build new create statement: replace the UNIQUE(...) clause or append composite unique
    if m:
        new_unique = 'UNIQUE(numero, localizacao)'
        new_create = re.sub(r'UNIQUE\s*\([^)]+\)', new_unique, create, flags=re.IGNORECASE)
    else:
        # append UNIQUE at end before closing paren
        new_create = create.rstrip().rstrip(')') + ',\n    UNIQUE(numero, localizacao)\n)'

    # create new table
    new_create = new_create.replace('CREATE TABLE armarios', 'CREATE TABLE armarios_new')
    print('\nNew CREATE TABLE (armarios_new):')
    print(new_create)

    cur.execute(new_create)

    # columns list
    cols_names = [c[1] for c in cols]
    col_list = ', '.join(cols_names)

    ins = f"INSERT INTO armarios_new ({col_list}) SELECT {col_list} FROM armarios"
    print('\nCopying data:')
    print(ins)
    cur.execute(ins)

    # drop old, rename
    cur.execute('DROP TABLE armarios')
    cur.execute('ALTER TABLE armarios_new RENAME TO armarios')

    # recreate simple index on id if missing
    cur.execute("CREATE INDEX IF NOT EXISTS ix_armarios_id ON armarios(id)")

    con.commit()
    print('\nUpdate complete.')
else:
    print('\nNo change needed: UNIQUE already contains localizacao or table missing.')

con.close()
print('\nDone')
