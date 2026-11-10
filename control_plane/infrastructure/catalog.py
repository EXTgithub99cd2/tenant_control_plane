import json,sqlite3
from datetime import datetime,timezone
from pathlib import Path
from provisioning.domain.models import DatabaseEngine,DatabaseReference

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
class Catalog:
    def __init__(self,path:Path): self.path=path;self.init()
    def db(self): c=sqlite3.connect(self.path);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
    def init(self):
        with self.db() as c:c.executescript("""CREATE TABLE IF NOT EXISTS tenants(id INTEGER PRIMARY KEY,name TEXT NOT NULL,slug TEXT UNIQUE NOT NULL,created_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS databases(id INTEGER PRIMARY KEY,tenant_id INTEGER NOT NULL REFERENCES tenants(id),requested_name TEXT NOT NULL,physical_name TEXT NOT NULL,engine TEXT NOT NULL,status TEXT NOT NULL,connection_reference TEXT NOT NULL,metadata_json TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(tenant_id,requested_name));CREATE TABLE IF NOT EXISTS backups(id INTEGER PRIMARY KEY,database_id INTEGER REFERENCES databases(id),reference TEXT,size_bytes INTEGER,metadata_json TEXT,created_at TEXT);""")
    def create_tenant(self,name,slug):
        with self.db() as c:return c.execute('INSERT INTO tenants(name,slug,created_at) VALUES(?,?,?)',(name,slug,now())).lastrowid
    def tenant(self,i):
        with self.db() as c:return c.execute('SELECT * FROM tenants WHERE id=?',(i,)).fetchone()
    def tenants(self):
        with self.db() as c:return [dict(x) for x in c.execute('SELECT * FROM tenants ORDER BY id DESC')]
    def save_database(self,d):
        with self.db() as c:return c.execute('INSERT INTO databases(tenant_id,requested_name,physical_name,engine,status,connection_reference,metadata_json,created_at) VALUES(?,?,?,?,?,?,?,?)',(d.tenant_id,d.requested_name,d.physical_name,d.engine.value,'available',d.connection_reference,json.dumps(d.metadata),now())).lastrowid
    def get_database(self,i):
        with self.db() as c:r=c.execute("SELECT * FROM databases WHERE id=? AND status='available'",(i,)).fetchone()
        if not r: raise ValueError('Database not found')
        return DatabaseReference(r['id'],r['tenant_id'],r['requested_name'],r['physical_name'],DatabaseEngine(r['engine']),r['connection_reference'],json.loads(r['metadata_json']))
    def databases(self):
        with self.db() as c:return [dict(x) for x in c.execute("SELECT d.*,t.name tenant_name FROM databases d JOIN tenants t ON t.id=d.tenant_id WHERE d.status='available' ORDER BY d.id DESC")]
    def save_backup(self,i,r):
        with self.db() as c:c.execute('INSERT INTO backups(database_id,reference,size_bytes,metadata_json,created_at) VALUES(?,?,?,?,?)',(i,r.reference,r.size_bytes,json.dumps(r.metadata),now()))
    def mark_deleted(self,i):
        with self.db() as c:c.execute("UPDATE databases SET status='deleted' WHERE id=?",(i,))
