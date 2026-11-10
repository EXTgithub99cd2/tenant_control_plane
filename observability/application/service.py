
class ObservabilityService:
    def __init__(self,events,metrics): self.events=events;self.metrics=metrics
    def event(self,name,severity='info',**attributes): self.events.record(name,severity=severity,attributes=attributes)
    def count(self,name,labels=None,value=1): self.metrics.increment(name,labels,value)
    def duration(self,name,seconds,labels=None): self.metrics.observe(name,seconds,labels)
