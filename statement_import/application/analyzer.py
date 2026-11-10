
import hashlib,json
from file_inspection.application.normalization import normalize_headers
class StatementAnalyzer:
    def __init__(self,empty_prefix='column'):self.empty_prefix=empty_prefix
    def suggest(self,physical_rows):
        nonblank=[r for r in physical_rows if not r['is_blank']]
        if not nonblank:return {'header_row':1,'data_start_row':2,'data_end_row':None,'document_header_end':None,'confidence':0}
        best=None
        for row in nonblank[:50]:
            values=row['values'];filled=[v for v in values if v is not None and str(v).strip()!=''];text=sum(1 for v in filled if isinstance(v,str) and v.strip());unique=len({str(v).strip().lower() for v in filled})
            score=len(filled)*2+text+unique-(5 if len(filled)<2 else 0)
            if best is None or score>best[0]:best=(score,row['source_row_number'])
        header=best[1];following=[r['source_row_number'] for r in nonblank if r['source_row_number']>header]
        return {'header_row':header,'data_start_row':following[0] if following else header+1,'data_end_row':following[-1] if following else None,'document_header_end':header-1 if header>1 else None,'confidence':min(100,max(10,best[0]*5))}
    def signature(self,headers):
        normalized,_=normalize_headers(headers,self.empty_prefix);names=[x['normalized'] for x in normalized];return hashlib.sha256(json.dumps(names,separators=(',',':')).encode()).hexdigest(),normalized
