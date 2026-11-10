
from data_management.domain.models import ColumnDefinition,TableDefinition,LogicalType
from statement_import.domain.models import StatementStructure,MappingColumn,StatementTemplate
from datetime import datetime
def convert(value,logical_type):
    if value is None or value=='':return None
    if logical_type=='integer':return int(value)
    if logical_type=='decimal':return float(str(value).replace(',','.'))
    if logical_type=='boolean':return str(value).strip().lower() in {'true','yes','y','1'}
    if logical_type=='datetime':
        if isinstance(value,datetime):return value
        for fmt in ('%Y-%m-%d','%Y-%m-%d %H:%M:%S','%d-%m-%Y','%d/%m/%Y'):
            try:return datetime.strptime(str(value).strip(),fmt)
            except ValueError:pass
        raise ValueError(f'Invalid datetime: {value}')
    return str(value)

class StatementImportService:
    def __init__(self,inbox,inspection,reader_registry,data_registry,catalog,repository,analyzer,observability,batch_size=500):self.inbox=inbox;self.inspection=inspection;self.readers=reader_registry;self.data_registry=data_registry;self.catalog=catalog;self.repo=repository;self.analyzer=analyzer;self.obs=observability;self.batch_size=batch_size
    def analyze(self,file_id,dataset):
        item=self.inbox.get_file(file_id);reader=self.readers.get(item['extension']);path=self.inbox.store.resolve(item['storage_reference']);rows,metadata=reader.physical_rows(path,dataset,200)
        for row in rows:row['values_display']=' | '.join('' if v is None else str(v) for v in row['values'])
        suggestion=self.analyzer.suggest(rows)
        header=next((r['values'] for r in rows if r['source_row_number']==suggestion['header_row']),[]);signature,normalized=self.analyzer.signature(header);template=self.repo.match(item['extension'],dataset,signature)
        return {'file':item,'dataset':dataset,'physical_rows':rows,'metadata':metadata,'suggestion':suggestion,'header_signature':signature,'normalized_headers':normalized,'matched_template':template}
    def preview_mapping(self,file_id,dataset,structure):
        item=self.inbox.get_file(file_id);reader=self.readers.get(item['extension']);path=self.inbox.store.resolve(item['storage_reference']);rows,_=reader.physical_rows(path,dataset,structure.header_row);header=next(r['values'] for r in rows if r['source_row_number']==structure.header_row);signature,normalized=self.analyzer.signature(header);all_rows=list(reader.iter_rows(path,dataset,structure.data_start_row,structure.data_end_row));samples=[]
        for i,h in enumerate(normalized):
            vals=[r[1][i] if i<len(r[1]) else None for r in all_rows[:1000]];samples.append(vals)
        from file_inspection.application.inference import infer
        columns=[MappingColumn(i,h['source'],h['normalized'],infer(samples[i]),any(v is None or v=='' for v in samples[i])) for i,h in enumerate(normalized)]
        return signature,columns,all_rows[:100]
    def save_template(self,name,file_id,dataset,structure,columns,auto):
        item=self.inbox.get_file(file_id);signature,_,_=self.preview_mapping(file_id,dataset,structure);return self.repo.save_template(StatementTemplate(None,name,item['extension'],dataset,signature,structure,columns,auto))
    def import_new_table(self,file_id,database_id,dataset,target_table,structure,columns,template_id=None):
        item=self.inbox.get_file(file_id);database=self.catalog.get_database(database_id);reader=self.readers.get(item['extension']);path=self.inbox.store.resolve(item['storage_reference']);adapter=self.data_registry.get(database.engine.value);job=self.repo.start_job(file_id,database_id,dataset,target_table,template_id)
        definition=TableDefinition(target_table,[ColumnDefinition('id',LogicalType.INTEGER,False,True,True)]+[ColumnDefinition(c.target_name,LogicalType(c.logical_type),c.nullable) for c in columns])
        read=0
        def batches():
            nonlocal read
            batch=[]
            for source_row,values in reader.iter_rows(path,dataset,structure.data_start_row,structure.data_end_row):
                if not any(v is not None and str(v).strip()!='' for v in values):continue
                row={c.target_name:convert(values[c.source_index] if c.source_index<len(values) else None,c.logical_type) for c in columns};read+=1;batch.append(row)
                if len(batch)>=self.batch_size:yield batch;batch=[]
            if batch:yield batch
        try:
            inserted=adapter.create_table_and_insert_atomic(database,definition,batches());self.repo.complete(job,read,inserted);self.obs.event('audit.import.completed',import_job_id=job,file_id=file_id,database_id=database_id,target_table=target_table,rows_inserted=inserted);self.obs.count('controlplane_import_jobs_total',{'operation':'create_table','result':'completed'});return job,inserted
        except Exception as exc:self.repo.fail(job,str(exc));self.obs.event('import.failed',severity='error',import_job_id=job,error_type=type(exc).__name__);self.obs.count('controlplane_import_jobs_total',{'operation':'create_table','result':'failed'});raise
