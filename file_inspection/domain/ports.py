
from abc import ABC,abstractmethod
from pathlib import Path
class TabularFileReader(ABC):
    @abstractmethod
    def supports(self,extension:str)->bool: ...
    @abstractmethod
    def list_datasets(self,path:Path): ...
    @abstractmethod
    def read(self,path:Path,dataset:str|None,max_rows:int): ...
