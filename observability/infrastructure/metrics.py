from collections import defaultdict
from threading import RLock

class InMemoryPrometheusMetrics:
    def __init__(self):
        self.counters=defaultdict(float);self.sums=defaultdict(float);self.counts=defaultdict(int);self.lock=RLock()
    def _key(self,name,labels): return name,tuple(sorted((str(k),str(v)) for k,v in (labels or {}).items()))
    def increment(self,name,labels=None,value=1):
        with self.lock:self.counters[self._key(name,labels)]+=value
    def observe(self,name,value,labels=None):
        key=self._key(name,labels)
        with self.lock:self.sums[key]+=float(value);self.counts[key]+=1
    @staticmethod
    def _escape(value): return str(value).replace('\\','\\\\').replace('\n','\\n').replace('"','\\"')
    def _line(self,name,label_items,value):
        labels=''
        if label_items: labels='{'+','.join(f'{k}="{self._escape(v)}"' for k,v in label_items)+'}'
        return f'{name}{labels} {value}'
    def render_prometheus(self):
        with self.lock:
            counters=list(self.counters.items());sums=list(self.sums.items());counts=dict(self.counts)
        lines=[]
        for (name,labels),value in sorted(counters): lines.append(self._line(name,labels,value))
        for (name,labels),value in sorted(sums):
            lines.append(self._line(name+'_sum',labels,value));lines.append(self._line(name+'_count',labels,counts[(name,labels)]))
        return '\n'.join(lines)+'\n'
