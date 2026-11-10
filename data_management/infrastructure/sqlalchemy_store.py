import re
from sqlalchemy import MetaData,Table,select,func,insert,update,delete,inspect,text
from data_management.domain.models import Capabilities
SAFE=re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,62}$')
class SQLAlchemyDataStore:
    capabilities=Capabilities()
    def __init__(self,engine_factory): self.engine_factory=engine_factory
    def _engine(self,d): return self.engine_factory(d)
    def _name(self,x):
        if not SAFE.fullmatch(x): raise ValueError('Invalid identifier')
        return x
    def _table(self,e,name): return Table(self._name(name),MetaData(),autoload_with=e)
    def list_tables(self,d):
        e=self._engine(d);ins=inspect(e);return [{'name':n,'row_count':self._count(e,n)} for n in ins.get_table_names()]
    def _count(self,e,n):
        t=self._table(e,n)
        with e.connect() as c:return c.execute(select(func.count()).select_from(t)).scalar_one()
    def describe_table(self,d,table):
        e=self._engine(d);t=self._table(e,table);return [{'name':c.name,'logical_type':self.to_logical(c.type),'nullable':c.nullable,'primary_key':c.primary_key} for c in t.columns]
    def read_rows(self,d,table,page,page_size):
        e=self._engine(d);t=self._table(e,table);page=max(1,page);page_size=max(1,min(100,page_size));pk=list(t.primary_key.columns)
        order=pk[0] if pk else list(t.columns)[0]
        with e.connect() as c: total=c.execute(select(func.count()).select_from(t)).scalar_one();rows=[dict(x) for x in c.execute(select(t).order_by(order).limit(page_size).offset((page-1)*page_size)).mappings()]
        return {'table':table,'columns':self.describe_table(d,table),'rows':rows,'total':total,'page':page,'page_size':page_size,'primary_key':order.name}
    def insert_row(self,d,table,values):
        e=self._engine(d);t=self._table(e,table);allowed={c.name for c in t.columns};clean={k:v for k,v in values.items() if k in allowed and v!=''}
        with e.begin() as c:return c.execute(insert(t).values(**clean)).inserted_primary_key
    def update_row(self,d,table,key,values):
        e=self._engine(d);t=self._table(e,table);pk=list(t.primary_key.columns)[0];clean={k:v for k,v in values.items() if k in t.c and k!=pk.name}
        with e.begin() as c:c.execute(update(t).where(pk==key).values(**clean))
    def delete_row(self,d,table,key):
        e=self._engine(d);t=self._table(e,table);pk=list(t.primary_key.columns)[0]
        with e.begin() as c:c.execute(delete(t).where(pk==key))

    def create_table_and_insert_atomic(self,database,definition,rows):
        from uuid import uuid4
        engine=self._engine(database);final=self._name(definition.name);staging=self._name('__staging_'+uuid4().hex[:16])
        staging_definition=type(definition)(staging,definition.columns)
        self.create_table(database,staging_definition)
        stage=self._table(engine,staging);count=0
        try:
            with engine.begin() as connection:
                for batch in rows:
                    if batch:connection.execute(insert(stage),batch);count+=len(batch)
                if inspect(connection).has_table(final):raise ValueError(f'Table already exists: {final}')
                connection.execute(text(f'ALTER TABLE "{staging}" RENAME TO "{final}"'))
            return count
        except Exception:
            try:
                with engine.begin() as connection:connection.execute(text(f'DROP TABLE IF EXISTS "{staging}"'))
            except Exception:pass
            raise
