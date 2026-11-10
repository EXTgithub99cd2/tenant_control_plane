
import re,unicodedata

def normalize_headers(values,empty_prefix='column'):
    names=[];counts={};warnings=[]
    for index,value in enumerate(values,1):
        source='' if value is None else str(value).strip()
        ascii_name=unicodedata.normalize('NFKD',source).encode('ascii','ignore').decode().lower()
        base=re.sub(r'[^a-z0-9]+','_',ascii_name).strip('_')
        if not base:base=f'{empty_prefix}_{index}';warnings.append(f'Column {index} had an empty or unsupported header and was named {base}.')
        if base[0].isdigit():base='column_'+base
        base=base[:55];counts[base]=counts.get(base,0)+1;name=base if counts[base]==1 else f'{base}_{counts[base]}'
        if counts[base]>1:warnings.append(f'Duplicate header {source or base!r} was normalized to {name}.')
        names.append({'source':source or f'(empty column {index})','normalized':name})
    return names,warnings
