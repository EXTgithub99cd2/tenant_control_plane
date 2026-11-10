class DataManagementService:
    def __init__(self,registry,catalog): self.registry=registry;self.catalog=catalog
    def _pair(self,database_id):
        db=self.catalog.get_database(database_id);return db,self.registry.get(db.engine.value)
    def capabilities(self,database_id): db,s=self._pair(database_id);return s.capabilities
    def list_tables(self,database_id): db,s=self._pair(database_id);return s.list_tables(db)
    def describe_table(self,database_id,table): db,s=self._pair(database_id);return s.describe_table(db,table)
    def read_rows(self,database_id,table,page=1,page_size=50): db,s=self._pair(database_id);return s.read_rows(db,table,page,page_size)
    def insert_row(self,database_id,table,values): db,s=self._pair(database_id);return s.insert_row(db,table,values)
    def update_row(self,database_id,table,key,values): db,s=self._pair(database_id);return s.update_row(db,table,key,values)
    def delete_row(self,database_id,table,key): db,s=self._pair(database_id);return s.delete_row(db,table,key)
    def create_table(self,database_id,definition): db,s=self._pair(database_id);return s.create_table(db,definition)
    def add_column(self,database_id,table,column): db,s=self._pair(database_id);return s.add_column(db,table,column)
    def alter_column(self,database_id,table,current,replacement): db,s=self._pair(database_id);return s.alter_column(db,table,current,replacement)
