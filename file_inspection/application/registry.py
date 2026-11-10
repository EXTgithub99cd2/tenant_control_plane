
class ReaderRegistry:
    def __init__(self,readers):self.readers=readers
    def get(self,extension):
        for reader in self.readers:
            if reader.supports(extension):return reader
        raise ValueError(f'No reader for {extension}')
