
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class StatementStructure:
    header_row:int
    data_start_row:int
    data_end_row:int|None
    document_header_start:int|None=1
    document_header_end:int|None=None
@dataclass(frozen=True)
class MappingColumn:
    source_index:int
    source_name:str
    target_name:str
    logical_type:str
    nullable:bool=True
@dataclass(frozen=True)
class StatementTemplate:
    id:int|None
    name:str
    extension:str
    dataset_pattern:str
    header_signature:str
    structure:StatementStructure
    columns:list[MappingColumn]
    auto_process_allowed:bool=True
