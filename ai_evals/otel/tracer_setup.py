from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter

def setup_tracer(service_name="ai-evals"): 
    provider = TracerProvider(resource=Resource.create({"service.name": service_name})) 
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter())) 
    trace.set_tracer_provider(provider) 
    return trace.get_tracer(service_name)

