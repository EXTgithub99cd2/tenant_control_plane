from dataclasses import dataclass
from enum import Enum
from typing import Any

class LogicalType(str,Enum):
    STRING='string';INTEGER='integer';DECIMAL='decimal';BOOLEAN='boolean';DATETIME='datetime';BINARY='binary'
@dataclass(frozen=True)
class ColumnDefinition:
    name:str
    logical_type:LogicalType
    nullable:bool=True
    primary_key:bool=False
    generated:bool=False
    default:Any|None=None
@dataclass(frozen=True)
class TableDefinition:
    name:str
    columns:list[ColumnDefinition]
@dataclass(frozen=True)
class Capabilities:
    browse_rows:bool=True;insert_rows:bool=True;update_rows:bool=True;delete_rows:bool=True;create_tables:bool=True;add_columns:bool=True;rename_columns:bool=True;change_column_types:bool=True
