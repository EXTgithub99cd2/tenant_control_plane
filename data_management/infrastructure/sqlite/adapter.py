from sqlalchemy import create_engine,MetaData,Table,Column,Integer,String,Numeric,Boolean,DateTime,LargeBinary,text
from data_management.infrastructure.sqlalchemy_store import SQLAlchemyDataStore
from data_management.domain.models import LogicalType
MAP={LogicalType.STRING:String,LogicalType.INTEGER:Integer,LogicalType.DECIMAL:Numeric,LogicalType.BOOLEAN:Boolean,LogicalType.DATETIME:DateTime,LogicalType.BINARY:LargeBinary}
class SQLiteDataStore(SQLAlchemyDataStore):
    engine_name='sqlite'
    def __init__(self): super().__init__(lambda d:create_engine('sqlite:///'+d.connection_reference))
    def to_logical(self,t):
        n=t.__class__.__name__.lower();return 'integer' if 'integer' in n else 'decimal' if 'numeric' in n or 'float' in n else 'boolean' if 'bool' in n else 'datetime' if 'date' in n else 'binary' if 'binary' in n or 'blob' in n else 'string'
    def create_table(self,d,definition):
        e=self._engine(d);cols=[]
        for x in definition.columns: cols.append(Column(x.name,MAP[x.logical_type](),primary_key=x.primary_key,autoincrement=x.generated,nullable=x.nullable and not x.primary_key))
        Table(definition.name,MetaData(),*cols).create(e)
    def add_column(self,d,table,column):
        typ=MAP[column.logical_type]().compile(dialect=self._engine(d).dialect);sql=f'ALTER TABLE "{self._name(table)}" ADD COLUMN "{self._name(column.name)}" {typ}'+(' NOT NULL' if not column.nullable else '')
        with self._engine(d).begin() as c:c.execute(text(sql))
    def alter_column(self,d,table,current,replacement):
        e=self._engine(d);old=Table(self._name(table),MetaData(),autoload_with=e);tmp='__rebuild_'+table;md=MetaData();newcols=[]
        for c in old.columns:
            if c.name==current:newcols.append(Column(replacement.name,MAP[replacement.logical_type](),nullable=replacement.nullable))
            else:newcols.append(Column(c.name,c.type,primary_key=c.primary_key,nullable=c.nullable))
        new=Table(tmp,md,*newcols)
        with e.begin() as conn:
            new.create(conn);targets=', '.join(f'"{c.name}"' for c in new.columns);sources=[]
            for c in old.columns:sources.append(f'CAST("{c.name}" AS {MAP[replacement.logical_type]().compile(dialect=e.dialect)})' if c.name==current else f'"{c.name}"')
            conn.execute(text(f'INSERT INTO "{tmp}" ({targets}) SELECT {", ".join(sources)} FROM "{table}"'));conn.execute(text(f'DROP TABLE "{table}"'));conn.execute(text(f'ALTER TABLE "{tmp}" RENAME TO "{table}"'))
