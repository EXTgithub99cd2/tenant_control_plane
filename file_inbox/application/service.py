
import hashlib,re
from pathlib import Path,PurePath
from file_inbox.domain.models import UploadDecision,UploadResult
from file_inbox.domain.errors import UploadTooLarge,InvalidFilename,ApprovalNotFound
class InboxService:
    def __init__(self,repository,store,observability,max_bytes=100*1024*1024,chunk_size=1024*1024,allowed_extensions=None):
        self.repo=repository;self.store=store;self.obs=observability;self.max_bytes=max_bytes;self.chunk_size=chunk_size;self.allowed_extensions=allowed_extensions or {'.csv','.xlsx'}
    def sanitize(self,filename):
        raw=PurePath(filename or '').name.strip();stem=Path(raw).stem;ext=Path(raw).suffix.lower()
        stem=re.sub(r'[^A-Za-z0-9._-]+','_',stem).strip('._-');normalized=(stem+ext)[:180]
        if not stem or ext not in self.allowed_extensions:raise InvalidFilename(f'Only {", ".join(sorted(self.allowed_extensions))} files are allowed')
        return raw,normalized,ext
    async def upload(self,upload):
        original,normalized,ext=self.sanitize(upload.filename);staged=self.store.staging_path();digest=hashlib.sha256();size=0
        try:
            with staged.open('wb') as out:
                while True:
                    chunk=await upload.read(self.chunk_size)
                    if not chunk:break
                    size+=len(chunk)
                    if size>self.max_bytes:raise UploadTooLarge(f'File exceeds {self.max_bytes} bytes')
                    digest.update(chunk);out.write(chunk)
            sha=digest.hexdigest();same_name=self.repo.file_by_name(normalized);same_content=self.repo.object_by_hash(sha)
            if same_name and same_name['sha256']==sha:
                self.store.discard(staged);self.obs.event('audit.inbox.file.already_present',file_id=same_name['id'],filename=normalized,sha256=sha);self.obs.count('controlplane_inbox_uploads_total',{'decision':'already_present'});return UploadResult(UploadDecision.ALREADY_PRESENT,same_name['id'],message='This exact file is already in the inbox.')
            if same_name and same_name['sha256']!=sha:
                self.store.discard(staged);self.obs.event('inbox.file.name_conflict',severity='warning',filename=normalized,existing_file_id=same_name['id']);self.obs.count('controlplane_inbox_uploads_total',{'decision':'name_conflict'});return UploadResult(UploadDecision.NAME_CONFLICT,existing_file_id=same_name['id'],message='The filename already exists with different contents. Rename the incoming file.')
            if same_content:
                existing=self.repo.first_file_for_object(same_content['id']);token=self.repo.create_approval(same_content['id'],original,normalized,existing['id']);self.store.discard(staged);self.obs.event('audit.inbox.file.alias_approval_required',approval_token=token,existing_file_id=existing['id'],incoming_filename=normalized,sha256=sha);self.obs.count('controlplane_inbox_uploads_total',{'decision':'approval_required'});return UploadResult(UploadDecision.APPROVAL_REQUIRED,approval_token=token,existing_file_id=existing['id'],message='The same contents already exist under another filename.')
            ref=self.store.commit(staged,sha);fid=self.repo.create_object_and_file(sha,size,ref,upload.content_type,original,normalized,ext);self.obs.event('audit.inbox.file.accepted',file_id=fid,filename=normalized,size_bytes=size,sha256=sha);self.obs.count('controlplane_inbox_uploads_total',{'decision':'accepted'});return UploadResult(UploadDecision.ACCEPTED,fid,message='File accepted.')
        except Exception:
            self.store.discard(staged);raise
        finally:await upload.close()
    def approve_alias(self,token):
        approval=self.repo.approval(token)
        if not approval:raise ApprovalNotFound(token)
        fid=self.repo.approve(token);self.obs.event('audit.inbox.file.alias_approved',file_id=fid,existing_file_id=approval['existing_file_id'],filename=approval['normalized_filename']);self.obs.count('controlplane_inbox_alias_approvals_total',{'decision':'approved'});return fid
    def reject_alias(self,token):
        approval=self.repo.approval(token)
        if not approval:raise ApprovalNotFound(token)
        self.repo.reject(token);self.obs.event('audit.inbox.file.alias_rejected',existing_file_id=approval['existing_file_id'],filename=approval['normalized_filename']);self.obs.count('controlplane_inbox_alias_approvals_total',{'decision':'rejected'})
    def list_files(self):return self.repo.files()
    def get_file(self,file_id):
        item=self.repo.file(file_id)
        if item:
            path=self.store.resolve(item['storage_reference']);item['stored']=path.is_file();item['absolute_storage_path']=str(path)
        return item
    def verify_file(self,file_id):
        item=self.get_file(file_id)
        if not item:return None
        path=Path(item['absolute_storage_path'])
        if not path.is_file():return {'ok':False,'reason':'stored object is missing','actual_sha256':None}
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            while True:
                chunk=stream.read(self.chunk_size)
                if not chunk:break
                digest.update(chunk)
        actual=digest.hexdigest();ok=actual==item['sha256']
        self.obs.event('audit.inbox.file.verified' if ok else 'inbox.file.verification_failed',severity='info' if ok else 'error',file_id=file_id,expected_sha256=item['sha256'],actual_sha256=actual)
        self.obs.count('controlplane_inbox_verifications_total',{'result':'success' if ok else 'failed'})
        return {'ok':ok,'reason':'hash matches stored metadata' if ok else 'hash mismatch','actual_sha256':actual}

    def get_approval(self,token):return self.repo.approval(token)
