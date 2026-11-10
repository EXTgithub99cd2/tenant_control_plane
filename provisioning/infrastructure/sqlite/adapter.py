import re,sqlite3
from datetime import datetime,timezone
from pathlib import Path
from provisioning.domain.models import DatabaseEngine,DatabaseReference,BackupResult
class SQLiteProvisioner:
    engine_name='sqlite'
    def __init__(self,directory:Path): self.directory=directory;directory.mkdir(exist_ok=True)
    def provision(self,r):
        name=re.sub('[^a-z0-9_]','_',f'tenant_{r.tenant_id}_{r.tenant_slug}_{r.database_name}'.lower());path=self.directory/f'{name}.db'
        if path.exists(): raise ValueError('Database already exists')
        with sqlite3.connect(path) as c:c.execute('PRAGMA journal_mode=WAL');c.execute('CREATE TABLE database_metadata(id INTEGER PRIMARY KEY,tenant_id INTEGER,tenant_slug TEXT,database_name TEXT,created_at TEXT)');c.execute('INSERT INTO database_metadata(tenant_id,tenant_slug,database_name,created_at) VALUES(?,?,?,?)',(r.tenant_id,r.tenant_slug,r.database_name,datetime.now(timezone.utc).isoformat()))
        return DatabaseReference(None,r.tenant_id,r.database_name,name,DatabaseEngine.SQLITE,str(path),{})
    def health_check(self,d):
        try:
            with sqlite3.connect(d.connection_reference) as c:return c.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        except:return False
    def backup(self,d,directory):
        directory.mkdir(exist_ok=True);stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');target=directory/f'{d.physical_name}_{stamp}.db'
        with sqlite3.connect(d.connection_reference) as s,sqlite3.connect(target) as t:s.backup(t)
        return BackupResult(str(target),target.stat().st_size,{'type':'sqlite-online'})
    def delete(self,d): Path(d.connection_reference).unlink(missing_ok=True)
