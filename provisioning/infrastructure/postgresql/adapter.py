import subprocess
from datetime import datetime,timezone
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from provisioning.domain.models import DatabaseEngine,DatabaseReference,BackupResult
class PostgreSQLProvisioner:
    engine_name='postgresql'
    def __init__(self,admin_url,host,port,pg_dump): self.admin_url=admin_url;self.host=host;self.port=port;self.pg_dump=pg_dump
    def provision(self,r):
        name=f'tenant_{r.tenant_id}_{r.tenant_slug}_{r.database_name}'.lower().replace('-','_');owner=f'{name}_owner';password=r.options.get('owner_password')
        if not password: raise ValueError('owner_password is required')
        engine=create_engine(self.admin_url,isolation_level='AUTOCOMMIT')
        with engine.connect() as c:
            if c.execute(text('SELECT 1 FROM pg_database WHERE datname=:n'),{'n':name}).first(): raise ValueError('Database exists')
            if not c.execute(text('SELECT 1 FROM pg_roles WHERE rolname=:n'),{'n':owner}).first(): c.exec_driver_sql(f'CREATE ROLE "{owner}" LOGIN PASSWORD %s',(password,))
            c.exec_driver_sql(f'CREATE DATABASE "{name}" OWNER "{owner}"')
        url=URL.create('postgresql+psycopg',username=owner,password=password,host=self.host,port=self.port,database=name)
        with create_engine(url).begin() as c:c.execute(text('CREATE TABLE database_metadata(id BIGSERIAL PRIMARY KEY,tenant_id BIGINT,tenant_slug TEXT,database_name TEXT,created_at TIMESTAMPTZ DEFAULT NOW())'));c.execute(text('INSERT INTO database_metadata(tenant_id,tenant_slug,database_name) VALUES(:i,:s,:n)'),{'i':r.tenant_id,'s':r.tenant_slug,'n':r.database_name})
        return DatabaseReference(None,r.tenant_id,r.database_name,name,DatabaseEngine.POSTGRESQL,url.render_as_string(hide_password=False),{'owner':owner})
    def health_check(self,d):
        try:
            with create_engine(d.connection_reference).connect() as c:return c.execute(text('SELECT 1')).scalar()==1
        except:return False
    def backup(self,d,directory):
        directory.mkdir(exist_ok=True);stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');target=directory/f'{d.physical_name}_{stamp}.dump';p=subprocess.run([self.pg_dump,'--format=custom','--file',str(target),'--dbname',d.connection_reference],capture_output=True,text=True)
        if p.returncode: raise RuntimeError(p.stderr)
        return BackupResult(str(target),target.stat().st_size,{'type':'postgres-custom'})
    def delete(self,d):
        e=create_engine(self.admin_url,isolation_level='AUTOCOMMIT')
        with e.connect() as c:c.execute(text('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:n AND pid<>pg_backend_pid()'),{'n':d.physical_name});c.exec_driver_sql(f'DROP DATABASE "{d.physical_name}"')
