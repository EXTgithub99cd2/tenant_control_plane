from provisioning.domain.errors import UnsupportedEngine
class ProvisionerRegistry:
    def __init__(self,adapters): self._items={x.engine_name:x for x in adapters}
    def get(self,engine):
        if engine not in self._items: raise UnsupportedEngine(engine)
        return self._items[engine]
    def engines(self): return sorted(self._items)
