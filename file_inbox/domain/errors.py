class InboxError(Exception): pass
class UploadTooLarge(InboxError): pass
class InvalidFilename(InboxError): pass
class ApprovalNotFound(InboxError): pass
