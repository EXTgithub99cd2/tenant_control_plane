class DataStoreRegistry:
    def __init__(self,stores): self._items={x.engine_name:x for x in stores}
    def get(self,engine):
        if engine not in self._items: raise ValueError(f'No data-store adapter for {engine}')
        return self._items[engine]
