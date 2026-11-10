
import sqlite3
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
class InboxRepository:
    def __init__(self,path:Path):self.path=path;self.init()
    def db(self):c=sqlite3.connect(self.path);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
    def init(self):
        with self.db() as c:c.executescript("""
        CREATE TABLE IF NOT EXISTS inbox_objects(id INTEGER PRIMARY KEY,sha256 TEXT UNIQUE NOT NULL,size_bytes INTEGER NOT NULL,storage_reference TEXT UNIQUE NOT NULL,media_type TEXT,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS inbox_files(id INTEGER PRIMARY KEY,object_id INTEGER NOT NULL REFERENCES inbox_objects(id),original_filename TEXT NOT NULL,normalized_filename TEXT NOT NULL,extension TEXT,status TEXT NOT NULL,uploaded_at TEXT NOT NULL,UNIQUE(normalized_filename));
        CREATE TABLE IF NOT EXISTS inbox_approvals(token TEXT PRIMARY KEY,object_id INTEGER NOT NULL REFERENCES inbox_objects(id),incoming_filename TEXT NOT NULL,normalized_filename TEXT NOT NULL,existing_file_id INTEGER NOT NULL REFERENCES inbox_files(id),status TEXT NOT NULL,created_at TEXT NOT NULL,resolved_at TEXT);
        """)
    def object_by_hash(self,sha):
        with self.db() as c:return c.execute('SELECT * FROM inbox_objects WHERE sha256=?',(sha,)).fetchone()
    def file_by_name(self,name):
        with self.db() as c:return c.execute('SELECT f.*,o.sha256,o.size_bytes,o.media_type,o.storage_reference FROM inbox_files f JOIN inbox_objects o ON o.id=f.object_id WHERE f.normalized_filename=?',(name,)).fetchone()
    def first_file_for_object(self,object_id):
        with self.db() as c:return c.execute('SELECT * FROM inbox_files WHERE object_id=? ORDER BY id LIMIT 1',(object_id,)).fetchone()
    def create_object_and_file(self,sha,size,ref,media,original,normalized,extension):
        with self.db() as c:
            cur=c.execute('INSERT INTO inbox_objects(sha256,size_bytes,storage_reference,media_type,created_at) VALUES(?,?,?,?,?)',(sha,size,ref,media,now()));oid=cur.lastrowid
            return c.execute("INSERT INTO inbox_files(object_id,original_filename,normalized_filename,extension,status,uploaded_at) VALUES(?,?,?,?, 'available',?)",(oid,original,normalized,extension,now())).lastrowid
    def create_approval(self,object_id,incoming,normalized,existing_id):
        token=str(uuid4())
        with self.db() as c:c.execute("INSERT INTO inbox_approvals VALUES(?,?,?,?,?,'pending',?,NULL)",(token,object_id,incoming,normalized,existing_id,now()))
        return token
    def approval(self,token):
        with self.db() as c:return c.execute("SELECT a.*,f.original_filename existing_filename FROM inbox_approvals a JOIN inbox_files f ON f.id=a.existing_file_id WHERE a.token=? AND a.status='pending'",(token,)).fetchone()
    def approve(self,token):
        with self.db() as c:
            a=c.execute("SELECT * FROM inbox_approvals WHERE token=? AND status='pending'",(token,)).fetchone()
            if not a:return None
            ext=Path(a['normalized_filename']).suffix.lower();fid=c.execute("INSERT INTO inbox_files(object_id,original_filename,normalized_filename,extension,status,uploaded_at) VALUES(?,?,?,?, 'available',?)",(a['object_id'],a['incoming_filename'],a['normalized_filename'],ext,now())).lastrowid
            c.execute("UPDATE inbox_approvals SET status='approved',resolved_at=? WHERE token=?",(now(),token));return fid
    def reject(self,token):
        with self.db() as c:c.execute("UPDATE inbox_approvals SET status='rejected',resolved_at=? WHERE token=? AND status='pending'",(now(),token))
    def files(self):
        with self.db() as c:return [dict(x) for x in c.execute('SELECT f.*,o.sha256,o.size_bytes,o.media_type FROM inbox_files f JOIN inbox_objects o ON o.id=f.object_id ORDER BY f.uploaded_at DESC')]
    def file(self,file_id):
        with self.db() as c:r=c.execute('SELECT f.*,o.sha256,o.size_bytes,o.media_type,o.storage_reference,o.created_at object_created_at FROM inbox_files f JOIN inbox_objects o ON o.id=f.object_id WHERE f.id=?',(file_id,)).fetchone();return dict(r) if r else None
