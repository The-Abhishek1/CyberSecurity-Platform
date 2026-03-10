from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager
from datetime import datetime
import asyncio
import json

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AIOHttpClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from src.core.config import get_settings
from src.utils.logging import logger

settings = get_settings()


class TelemetryManager:
    """
    Enterprise Telemetry Manager
    
    Integrates:
    - OpenTelemetry for traces, metrics, logs
    - Distributed tracing
    - Performance monitoring
    - Resource tracking
    """
    
    def __init__(self):
        self.tracer_provider = None
        self.meter_provider = None
        self.logger_provider = None
        self.is_initialized = False
        
        # Active spans
        self.active_spans: Dict[str, Any] = {}
        
        # Custom metrics
        self.meters: Dict[str, Any] = {}
        
        logger.info("Telemetry Manager initialized")
    
    async def initialize(self):
        """Initialize OpenTelemetry components"""
        
        # Create resource
        resource = Resource.create({
            SERVICE_NAME: settings.observability.service_name,
            "environment": settings.environment.value,
            "version": settings.version,
            "deployment.region": settings.region
        })
        
        # Initialize tracing
        if settings.observability.traces_enabled:
            await self._init_tracing(resource)
        
        # Initialize metrics
        if settings.observability.metrics_enabled:
            await self._init_metrics(resource)
        
        # Initialize logging
        if settings.observability.logging_enabled:
            await self._init_logging(resource)
        
        self.is_initialized = True
        logger.info("Telemetry initialized successfully")
    
    async def _init_tracing(self, resource: Resource):
        """Initialize distributed tracing"""
        
        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)
        
        # Add span processor
        if settings.observability.otlp_endpoint:
            span_exporter = OTLPSpanExporter(
                endpoint=settings.observability.otlp_endpoint,
                insecure=True
            )
            span_processor = BatchSpanProcessor(span_exporter)
            self.tracer_provider.add_span_processor(span_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)
        
        # Instrument libraries
        FastAPIInstrumentor.instrument()
        AIOHttpClientInstrumentor.instrument()
        RedisInstrumentor.instrument()
        
        logger.info("Tracing initialized")
    
    async def _init_metrics(self, resource: Resource):
        """Initialize metrics collection"""
        
        # Create metric reader
        if settings.observability.otlp_endpoint:
            metric_exporter = OTLPMetricExporter(
                endpoint=settings.observability.otlp_endpoint,
                insecure=True
            )
            metric_reader = PeriodicExportingMetricReader(
                metric_exporter,
                export_interval_millis=60000  # 1 minute
            )
        else:
            # Use in-memory reader for development
            from opentelemetry.sdk.metrics.export import InMemoryMetricReader
            metric_reader = InMemoryMetricReader()
        
        # Create meter provider
        self.meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader]
        )
        
        # Set global meter provider
        metrics.set_meter_provider(self.meter_provider)
        
        logger.info("Metrics initialized")
    
    async def _init_logging(self, resource: Resource):
        """Initialize structured logging"""
        
        # Create logger provider
        self.logger_provider = LoggerProvider(resource=resource)
        
        # Add log processor
        if settings.observability.otlp_endpoint:
            log_exporter = OTLPLogExporter(
                endpoint=settings.observability.otlp_endpoint,
                insecure=True
            )
            log_processor = BatchLogRecordProcessor(log_exporter)
            self.logger_provider.add_log_processor(log_processor)
        
        # Set global logger provider
        from opentelemetry._logs import set_logger_provider
        set_logger_provider(self.logger_provider)
        
        # Create logging handler
        handler = LoggingHandler(level=settings.observability.log_level, logger_provider=self.logger_provider)
        
        # Add handler to root logger
        import logging
        logging.getLogger().addHandler(handler)
        
        logger.info("Logging initialized")
    
    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict] = None,
        kind: Optional[str] = None
    ):
        """Start a new trace span"""
        
        if not self.is_initialized:
            yield None
            return
        
        tracer = trace.get_tracer(__name__)
        
        with tracer.start_as_current_span(
            name,
            kind=kind,
            attributes=attributes
        ) as span:
            span_id = format(span.get_span_context().span_id, '016x')
            trace_id = format(span.get_span_context().trace_id, '032x')
            
            self.active_spans[span_id] = {
                "span": span,
                "name": name,
                "start_time": datetime.utcnow()
            }
            
            yield {
                "span": span,
                "span_id": span_id,
                "trace_id": trace_id
            }
    
    async def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "1",
        attributes: Optional[Dict] = None
    ):
        """Record a metric value"""
        
        if not self.is_initialized:
            return
        
        meter = metrics.get_meter(__name__)
        
        # Create or get counter
        if name not in self.meters:
            counter = meter.create_counter(
                name=name,
                unit=unit,
                description=f"Counter for {name}"
            )
            self.meters[name] = counter
        else:
            counter = self.meters[name]
        
        # Add to counter
        counter.add(value, attributes or {})
    
    async def record_histogram(
        self,
        name: str,
        value: float,
        unit: str = "ms",
        attributes: Optional[Dict] = None
    ):
        """Record a histogram value"""
        
        if not self.is_initialized:
            return
        
        meter = metrics.get_meter(__name__)
        
        # Create or get histogram
        histogram_key = f"histogram:{name}"
        if histogram_key not in self.meters:
            histogram = meter.create_histogram(
                name=name,
                unit=unit,
                description=f"Histogram for {name}"
            )
            self.meters[histogram_key] = histogram
        else:
            histogram = self.meters[histogram_key]
        
        # Record value
        histogram.record(value, attributes or {})
    
    async def record_gauge(
        self,
        name: str,
        value: float,
        unit: str = "1",
        attributes: Optional[Dict] = None
    ):
        """Record a gauge value"""
        
        if not self.is_initialized:
            return
        
        meter = metrics.get_meter(__name__)
        
        # Create or get gauge
        gauge_key = f"gauge:{name}"
        if gauge_key not in self.meters:
            gauge = meter.create_up_down_counter(
                name=name,
                unit=unit,
                description=f"Gauge for {name}"
            )
            self.meters[gauge_key] = gauge
        else:
            gauge = self.meters[gauge_key]
        
        # Set value
        gauge.add(value - gauge.last_value if hasattr(gauge, 'last_value') else value, attributes or {})
        gauge.last_value = value
    
    def get_trace_context(self) -> Dict[str, str]:
        """Get current trace context for propagation"""
        
        span = trace.get_current_span()
        if not span:
            return {}
        
        span_context = span.get_span_context()
        if span_context == trace.INVALID_SPAN_CONTEXT:
            return {}
        
        return {
            "trace_id": format(span_context.trace_id, '032x'),
            "span_id": format(span_context.span_id, '016x'),
            "trace_flags": format(span_context.trace_flags, '02x')
        }
    
    async def shutdown(self):
        """Shutdown telemetry components"""
        
        if self.tracer_provider:
            self.tracer_provider.shutdown()
        
        if self.meter_provider:
            self.meter_provider.shutdown()
        
        if self.logger_provider:
            self.logger_provider.shutdown()
        
        logger.info("Telemetry shutdown complete")