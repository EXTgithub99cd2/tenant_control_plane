
import json,sqlite3
from datetime import datetime,timezone
from pathlib import Path
from statement_import.domain.models import StatementStructure,MappingColumn,StatementTemplate

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
class ImportRepository:
    def __init__(self,path:Path):self.path=path;self.init()
    def db(self):c=sqlite3.connect(self.path);c.row_factory=sqlite3.Row;return c
    def init(self):
        with self.db() as c:c.executescript("""
        CREATE TABLE IF NOT EXISTS statement_templates(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,extension TEXT NOT NULL,dataset_pattern TEXT NOT NULL,header_signature TEXT NOT NULL,structure_json TEXT NOT NULL,columns_json TEXT NOT NULL,auto_process_allowed INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS import_jobs(id INTEGER PRIMARY KEY,file_id INTEGER NOT NULL,database_id INTEGER NOT NULL,dataset TEXT NOT NULL,target_table TEXT NOT NULL,template_id INTEGER REFERENCES statement_templates(id),status TEXT NOT NULL,rows_read INTEGER NOT NULL DEFAULT 0,rows_inserted INTEGER NOT NULL DEFAULT 0,failure_message TEXT,created_at TEXT NOT NULL,completed_at TEXT);
        CREATE UNIQUE INDEX IF NOT EXISTS ux_import_source ON import_jobs(file_id,database_id,dataset,target_table) WHERE status='completed';
        """)
    def save_template(self,t):
        structure=json.dumps(t.structure.__dict__);columns=json.dumps([x.__dict__ for x in t.columns])
        with self.db() as c:
            row=c.execute('SELECT id FROM statement_templates WHERE name=?',(t.name,)).fetchone()
            if row:c.execute('UPDATE statement_templates SET extension=?,dataset_pattern=?,header_signature=?,structure_json=?,columns_json=?,auto_process_allowed=?,updated_at=? WHERE id=?',(t.extension,t.dataset_pattern,t.header_signature,structure,columns,int(t.auto_process_allowed),now(),row['id']));return row['id']
            return c.execute('INSERT INTO statement_templates(name,extension,dataset_pattern,header_signature,structure_json,columns_json,auto_process_allowed,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(t.name,t.extension,t.dataset_pattern,t.header_signature,structure,columns,int(t.auto_process_allowed),now(),now())).lastrowid
    def templates(self):
        with self.db() as c:return [dict(x) for x in c.execute('SELECT * FROM statement_templates ORDER BY name')]
    def match(self,extension,dataset,signature):
        with self.db() as c:r=c.execute('SELECT * FROM statement_templates WHERE extension=? AND header_signature=? ORDER BY CASE WHEN dataset_pattern=? THEN 0 ELSE 1 END,id LIMIT 1',(extension,signature,dataset)).fetchone()
        return self._model(r) if r else None
    def template(self,i):
        with self.db() as c:r=c.execute('SELECT * FROM statement_templates WHERE id=?',(i,)).fetchone()
        return self._model(r) if r else None
    def _model(self,r):
        s=json.loads(r['structure_json']);cols=json.loads(r['columns_json']);return StatementTemplate(r['id'],r['name'],r['extension'],r['dataset_pattern'],r['header_signature'],StatementStructure(**s),[MappingColumn(**x) for x in cols],bool(r['auto_process_allowed']))
    def start_job(self,file_id,database_id,dataset,target,template_id):
        with self.db() as c:return c.execute("INSERT INTO import_jobs(file_id,database_id,dataset,target_table,template_id,status,created_at) VALUES(?,?,?,?,?,'importing',?)",(file_id,database_id,dataset,target,template_id,now())).lastrowid
    def complete(self,job_id,read,inserted):
        with self.db() as c:c.execute("UPDATE import_jobs SET status='completed',rows_read=?,rows_inserted=?,completed_at=? WHERE id=?",(read,inserted,now(),job_id))
    def fail(self,job_id,message):
        with self.db() as c:c.execute("UPDATE import_jobs SET status='failed',failure_message=?,completed_at=? WHERE id=?",(message,now(),job_id))
    def jobs(self):
        with self.db() as c:return [dict(x) for x in c.execute('SELECT * FROM import_jobs ORDER BY id DESC LIMIT 100')]
