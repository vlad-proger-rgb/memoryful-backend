from functools import cached_property
from typing import Any

from google.cloud.pubsub_v1 import SubscriberClient
from google.protobuf.field_mask_pb2 import FieldMask
from kombu.transport import gcpubsub


class FilterlessSubscriber(SubscriberClient):
    # kombu 5.7.0 masks `filter`, which Pub/Sub treats as immutable, and the nested path
    # `expiration_policy.ttl`, which it does not know. Either one fails the whole update.
    def update_subscription(self, request: Any = None, **kwargs: Any) -> Any:
        fields = [path.split(".")[0] for path in request["update_mask"].paths]
        paths = [field for field in dict.fromkeys(fields) if field != "filter"]
        request = {**request, "update_mask": FieldMask(paths=paths)}
        return super().update_subscription(request=request, **kwargs)


class Channel(gcpubsub.Channel):
    @cached_property
    def subscriber(self) -> SubscriberClient:
        return FilterlessSubscriber()


class Transport(gcpubsub.Transport):
    Channel = Channel
