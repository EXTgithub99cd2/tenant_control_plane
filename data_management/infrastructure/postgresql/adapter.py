from sqlalchemy import create_engine,MetaData,Table,Column,BigInteger,Text,Numeric,Boolean,DateTime,LargeBinary,text
from data_management.infrastructure.sqlalchemy_store import SQLAlchemyDataStore
from data_management.domain.models import LogicalType
MAP={LogicalType.STRING:Text,LogicalType.INTEGER:BigInteger,LogicalType.DECIMAL:Numeric,LogicalType.BOOLEAN:Boolean,LogicalType.DATETIME:DateTime,LogicalType.BINARY:LargeBinary}
class PostgreSQLDataStore(SQLAlchemyDataStore):
    engine_name='postgresql'
    def __init__(self): super().__init__(lambda d:create_engine(d.connection_reference))
    def to_logical(self,t):
        n=t.__class__.__name__.lower();return 'integer' if 'int' in n else 'decimal' if 'numeric' in n or 'float' in n else 'boolean' if 'bool' in n else 'datetime' if 'date' in n else 'binary' if 'binary' in n or 'bytea' in n else 'string'
    def create_table(self,d,definition):
        e=self._engine(d);cols=[Column(x.name,MAP[x.logical_type](),primary_key=x.primary_key,autoincrement=x.generated,nullable=x.nullable and not x.primary_key) for x in definition.columns];Table(definition.name,MetaData(),*cols).create(e)
    def add_column(self,d,table,column):
        typ=MAP[column.logical_type]().compile(dialect=self._engine(d).dialect);sql=f'ALTER TABLE "{self._name(table)}" ADD COLUMN "{self._name(column.name)}" {typ}'+(' NOT NULL' if not column.nullable else '')
        with self._engine(d).begin() as c:c.execute(text(sql))
    def alter_column(self,d,table,current,replacement):
        e=self._engine(d);tn=self._name(table);old=self._name(current);new=self._name(replacement.name);typ=MAP[replacement.logical_type]().compile(dialect=e.dialect)
        with e.begin() as c:
            if old!=new:c.execute(text(f'ALTER TABLE "{tn}" RENAME COLUMN "{old}" TO "{new}"'))
            c.execute(text(f'ALTER TABLE "{tn}" ALTER COLUMN "{new}" TYPE {typ} USING "{new}"::{typ}'))
