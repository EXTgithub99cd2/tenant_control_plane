
from datetime import date,datetime
from decimal import Decimal,InvalidOperation
import re
TRUE={'true','yes','y','1'};FALSE={'false','no','n','0'}
def _kind(value):
    if value is None or value=='':return None
    if isinstance(value,bool):return 'boolean'
    if isinstance(value,datetime) or isinstance(value,date):return 'datetime'
    if isinstance(value,int) and not isinstance(value,bool):return 'integer'
    if isinstance(value,float) or isinstance(value,Decimal):return 'decimal'
    text=str(value).strip();lower=text.lower()
    if re.fullmatch(r'[+-]?\d+',text):
        digits=text.lstrip('+-')
        if len(digits)>1 and digits.startswith('0'):return 'string'
        return 'integer'
    try:
        Decimal(text.replace(',','.'))
        if any(c in text for c in '.,'):return 'decimal'
    except InvalidOperation:pass
    if lower in TRUE|FALSE:return 'boolean'
    for fmt in ('%Y-%m-%d','%Y-%m-%d %H:%M:%S','%d-%m-%Y','%d/%m/%Y'):
        try:datetime.strptime(text,fmt);return 'datetime'
        except ValueError:pass
    return 'string'
def infer(values):
    kinds=[_kind(v) for v in values if v is not None and v!=''];unique=set(kinds)
    if not unique:return 'string'
    if unique<={'integer'}:return 'integer'
    if unique<={'integer','decimal'}:return 'decimal'
    if unique<={'boolean'}:return 'boolean'
    if unique<={'datetime'}:return 'datetime'
    return 'string'
