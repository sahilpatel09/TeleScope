import asyncio
import functools
import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator


def configure_opentelemetry(
    otlp_endpoint: str,
    service_name: str,
    app=None,
    engine=None,
):
    """
    Configures OpenTelemetry for the application.

    Args:
        app: The FastAPI application instance to instrument.
        engine: The SQLAlchemy engine to instrument.
        service_name: The name of the service to appear in traces.
        otlp_endpoint: The OTLP Collector endpoint.
                       Defaults to 'http://otel-collector:4317' for Docker Compose.
                       Use 'http://localhost:4317' or 'http://127.0.0.1:4317' for local host.
    """
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": os.getenv("APP_VERSION", "0.1.0"),
            "environment": os.getenv("APP_ENV", "development"),
            "host.name": os.uname().nodename,
        }
    )

    tracer_provider = TracerProvider(
        resource=resource, id_generator=RandomIdGenerator()
    )
    trace.set_tracer_provider(tracer_provider)

    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)

    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    if app:
        FastAPIInstrumentor.instrument_app(app)
        print(f"FastAPI instrumented for service: {service_name}")
    if engine:
        SQLAlchemyInstrumentor().instrument(engine=engine)
        print(f"SQLAlchemy instrumented for service: {service_name}")

    return trace.get_tracer(service_name)


def traced(span_name: Optional[str] = None, attributes: Optional[dict] = None):
    """
    A decorator to create a custom OpenTelemetry span around a function's execution.

    Args:
        span_name: The name of the span. If None, the function's name will be used.
        attributes: A dictionary of attributes to add to the span.
    """

    def decorator(func):
        tracer_instance = trace.get_tracer(func.__module__)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_span_name = span_name if span_name else func.__name__
            with tracer_instance.start_as_current_span(current_span_name) as span:
                if attributes:
                    span.set_attributes(attributes)
                span.set_attribute(f"{func.__name__}.args", str(args))
                span.set_attribute(f"{func.__name__}.kwargs", str(kwargs))
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.StatusCode.ERROR, description=str(e))
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_span_name = span_name if span_name else func.__name__
            with tracer_instance.start_as_current_span(current_span_name) as span:
                if attributes:
                    span.set_attributes(attributes)
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.StatusCode.ERROR, description=str(e))
                    raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
