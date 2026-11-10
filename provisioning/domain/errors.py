class ProvisioningError(Exception): pass
class UnsupportedEngine(ProvisioningError): pass
class DatabaseAlreadyExists(ProvisioningError): pass
class DatabaseNotFound(ProvisioningError): pass
