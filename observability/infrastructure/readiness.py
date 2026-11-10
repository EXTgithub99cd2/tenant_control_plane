
class ReadinessChecker:
    def __init__(self,catalog,provisioner_registry,data_store_registry): self.catalog=catalog;self.provisioners=provisioner_registry;self.stores=data_store_registry
    def check(self):
        checks={}
        try:
            with self.catalog.db() as c:c.execute('SELECT 1').fetchone()
            checks['catalog']='ok'
        except Exception as exc: checks['catalog']=f'error: {exc}'
        checks['provisioning_engines']=','.join(self.provisioners.engines()) or 'none'
        checks['data_stores']=','.join(sorted(self.stores._items)) or 'none'
        return {'status':'ready' if checks['catalog']=='ok' and checks['provisioning_engines']!='none' and checks['data_stores']!='none' else 'not_ready','checks':checks}
