
from dataclasses import dataclass
from pathlib import Path
import tomllib

@dataclass(frozen=True)
class ServerSettings:
    host:str
    port:int
    log_level:str
    reload:bool
@dataclass(frozen=True)
class InboxSettings:
    root:Path
    metadata_database:Path
    max_upload_bytes:int
    chunk_size_bytes:int
    allowed_extensions:set[str]
    show_storage_reference:bool

def _read(path:Path):
    if not path.exists(): raise RuntimeError(f'Missing configuration file: {path}')
    with path.open('rb') as stream:return tomllib.load(stream)
def _resolve(base:Path,value:str)->Path:
    path=Path(value);return path if path.is_absolute() else (base/path).resolve()
def load_server_settings(base:Path)->ServerSettings:
    raw=_read(base/'config/system.toml')['server']
    host=str(raw.get('host','127.0.0.1'));port=int(raw.get('port',8000))
    if not 1<=port<=65535:raise RuntimeError('server.port must be between 1 and 65535')
    return ServerSettings(host,port,str(raw.get('log_level','info')),bool(raw.get('reload',False)))
def load_inbox_settings(base:Path)->InboxSettings:
    raw=_read(base/'config/inbox.toml')['inbox'];extensions={str(x).lower() for x in raw.get('allowed_extensions',[])}
    if not extensions or any(not x.startswith('.') for x in extensions):raise RuntimeError('inbox.allowed_extensions must contain extensions beginning with a dot')
    maximum=int(raw.get('max_upload_bytes',104857600));chunk=int(raw.get('chunk_size_bytes',1048576))
    if maximum<1 or chunk<1 or chunk>maximum:raise RuntimeError('Inbox size settings are invalid')
    return InboxSettings(_resolve(base,str(raw.get('root','inbox'))),_resolve(base,str(raw.get('metadata_database','inbox.db'))),maximum,chunk,extensions,bool(raw.get('show_storage_reference',True)))


@dataclass(frozen=True)
class InspectionSettings:
    preview_rows:int
    type_inference_sample_rows:int
    maximum_columns:int
    maximum_worksheets:int
    csv_encoding_candidates:list[str]
    csv_delimiters:list[str]
    empty_header_prefix:str

def load_inspection_settings(base:Path)->InspectionSettings:
    raw=_read(base/'config/inspection.toml')['inspection']
    preview=int(raw.get('preview_rows',100));sample=int(raw.get('type_inference_sample_rows',1000));columns=int(raw.get('maximum_columns',500));worksheets=int(raw.get('maximum_worksheets',50))
    if not 1<=preview<=500:raise RuntimeError('inspection.preview_rows must be 1..500')
    if sample<preview:raise RuntimeError('inspection.type_inference_sample_rows must be >= preview_rows')
    if columns<1 or worksheets<1:raise RuntimeError('Inspection limits must be positive')
    return InspectionSettings(preview,sample,columns,worksheets,list(raw.get('csv_encoding_candidates',['utf-8-sig','utf-8'])),list(raw.get('csv_delimiters',[',',';','\t','|'])),str(raw.get('empty_header_prefix','column')))
