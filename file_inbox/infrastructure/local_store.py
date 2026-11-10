
import os
from pathlib import Path
from uuid import uuid4
class LocalInboxObjectStore:
    def __init__(self,root:Path):
        self.root=root.resolve();self.objects=self.root/'objects';self.staging=self.root/'staging';self.quarantine=self.root/'quarantine'
        for p in (self.objects,self.staging,self.quarantine):p.mkdir(parents=True,exist_ok=True)
    def staging_path(self): return self.staging/f'{uuid4()}.upload'
    def commit(self,staged,sha256):
        target=self.objects/sha256[:2]/sha256[2:4]/sha256;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():staged.unlink(missing_ok=True)
        else:os.replace(staged,target)
        return str(target.relative_to(self.root))
    def discard(self,staged): staged.unlink(missing_ok=True)
    def resolve(self,reference):
        path=(self.root/reference).resolve()
        if self.root not in path.parents:raise ValueError('Unsafe storage reference')
        return path
