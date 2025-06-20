import random
import time
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

resource = Resource.create({"service.name": "my-test-service"})

exporter = OTLPMetricExporter(endpoint="127.0.0.1:4317", insecure=True)
reader = PeriodicExportingMetricReader(exporter)
provider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(provider)

meter = metrics.get_meter(__name__)

my_counter = meter.create_counter(
    name="my_test_counter",
    description="A simple test counter",
    unit="1",
)

labels_options = [
    {"key1": "valueA", "key2": "valueB"},
    {"key1": "valueC", "key2": "valueD"},
    {"key1": "valueE", "key2": "valueF"},
]

print("Sending metrics to OTLP collector at 127.0.0.1:4317.")

try:
    while True:
        labels = random.choice(labels_options)
        increment = random.randint(1, 5)
        my_counter.add(increment, labels)
        print(f"Added {increment} with labels {labels}")
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopped sending metrics.")
