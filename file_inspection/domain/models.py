
from dataclasses import dataclass,field
from typing import Any
@dataclass(frozen=True)
class DataSetInfo:
    name:str
    kind:str
    visible:bool=True
@dataclass(frozen=True)
class ColumnProfile:
    source_name:str
    normalized_name:str
    logical_type:str
    nullable:bool
    non_empty_count:int
    empty_count:int
    warnings:list[str]=field(default_factory=list)
@dataclass(frozen=True)
class InspectionReport:
    file_id:int
    filename:str
    dataset:str
    reader:str
    columns:list[ColumnProfile]
    preview_rows:list[dict[str,Any]]
    rows_sampled:int
    estimated_total_rows:int|None
    valid:bool
    errors:list[str]
    warnings:list[str]
    metadata:dict[str,Any]=field(default_factory=dict)
