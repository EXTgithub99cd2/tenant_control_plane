
import csv
from file_inspection.domain.models import DataSetInfo
class CsvReader:
    def __init__(self,encodings,delimiters):self.encodings=encodings;self.delimiters=delimiters
    def supports(self,extension):return extension.lower()=='.csv'
    def list_datasets(self,path):return [DataSetInfo('CSV','csv',True)]
    def _detect(self,path):
        last=None
        for encoding in self.encodings:
            try:
                with path.open('r',encoding=encoding,newline='') as f:sample=f.read(65536)
                dialect=csv.Sniffer().sniff(sample,delimiters=''.join(self.delimiters));return encoding,dialect.delimiter
            except UnicodeDecodeError as exc:last=exc;continue
            except csv.Error as exc:
                last=exc
                counts={delimiter:sample.count(delimiter) for delimiter in self.delimiters}
                delimiter=max(counts,key=counts.get)
                if counts[delimiter]>0:return encoding,delimiter
        raise ValueError(f'Could not detect CSV encoding/delimiter: {last}')
    def physical_rows(self,path,dataset,max_rows=None):
        encoding,delimiter=self._detect(path);out=[]
        with path.open('r',encoding=encoding,newline='') as f:
            for number,row in enumerate(csv.reader(f,delimiter=delimiter),1):
                blank=not any(str(v).strip() for v in row);out.append({'source_row_number':number,'values':row,'is_blank':blank,'is_hidden':False})
                if max_rows and len(out)>=max_rows:break
        return out,{'encoding':encoding,'delimiter':delimiter}
    def iter_rows(self,path,dataset,start,end=None):
        encoding,delimiter=self._detect(path)
        with path.open('r',encoding=encoding,newline='') as f:
            for number,row in enumerate(csv.reader(f,delimiter=delimiter),1):
                if number<start:continue
                if end and number>end:break
                yield number,row
    def read(self,path,dataset,max_rows):
        rows,meta=self.physical_rows(path,dataset,None);header=rows[0]['values'] if rows else [];data=[r['values'] for r in rows[1:] if not r['is_blank']][:max_rows];return {'headers':header,'rows':data,'total_rows':sum(not r['is_blank'] for r in rows[1:]),'metadata':meta,'physical_rows':rows}
