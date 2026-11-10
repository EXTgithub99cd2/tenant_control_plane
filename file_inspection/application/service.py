
from file_inspection.domain.models import ColumnProfile,InspectionReport
from file_inspection.application.normalization import normalize_headers
from file_inspection.application.inference import infer
class FileInspectionService:
    def __init__(self,inbox,registry,settings,observability):self.inbox=inbox;self.registry=registry;self.settings=settings;self.obs=observability
    def datasets(self,file_id):
        item=self.inbox.get_file(file_id)
        if not item:raise ValueError('Inbox file not found')
        reader=self.registry.get(item['extension']);sets=reader.list_datasets(self.inbox.store.resolve(item['storage_reference']))
        return item,sets
    def inspect(self,file_id,dataset=None):
        item=self.inbox.get_file(file_id)
        if not item:raise ValueError('Inbox file not found')
        verification=self.inbox.verify_file(file_id)
        if not verification['ok']:raise ValueError('Stored file failed SHA-256 verification')
        reader=self.registry.get(item['extension']);path=self.inbox.store.resolve(item['storage_reference']);raw=reader.read(path,dataset,self.settings.type_inference_sample_rows)
        headers=raw['headers'];errors=[];warnings=[]
        if not headers:errors.append('No header row was found.')
        if len(headers)>self.settings.maximum_columns:errors.append(f'File has {len(headers)} columns; maximum is {self.settings.maximum_columns}.')
        normalized,header_warnings=normalize_headers(headers,self.settings.empty_header_prefix);warnings.extend(header_warnings)
        width=len(headers);samples=[[] for _ in range(width)]
        for row_no,row in enumerate(raw['rows'],2):
            if len(row)>width:warnings.append(f'Row {row_no} has {len(row)} values but the header has {width}; extra values are ignored.')
            for i in range(width):samples[i].append(row[i] if i<len(row) else None)
        columns=[]
        for i,h in enumerate(normalized):
            values=samples[i];empty=sum(v is None or v=='' for v in values);logical=infer(values);cw=[]
            if empty:cw.append(f'{empty} empty values in the sampled rows.')
            columns.append(ColumnProfile(h['source'],h['normalized'],logical,empty>0,len(values)-empty,empty,cw))
        preview=[]
        for row in raw['rows'][:self.settings.preview_rows]:preview.append({normalized[i]['normalized']:(row[i] if i<len(row) else None) for i in range(width)})
        report=InspectionReport(file_id,item['original_filename'],dataset or raw['metadata'].get('worksheet','CSV'),reader.__class__.__name__,columns,preview,len(raw['rows']),raw['total_rows'],not errors,errors,warnings,raw['metadata'])
        self.obs.event('audit.inbox.file.inspected',file_id=file_id,filename=item['normalized_filename'],dataset=report.dataset,reader=report.reader,valid=report.valid,columns=len(columns),preview_rows=len(preview));self.obs.count('controlplane_file_inspections_total',{'extension':item['extension'],'result':'valid' if report.valid else 'invalid'})
        return report
