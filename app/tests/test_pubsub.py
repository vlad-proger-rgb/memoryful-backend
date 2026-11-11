"""kombu 5.7.0 sends Pub/Sub an update mask it rejects: the immutable `filter` and the nested
`expiration_policy.ttl`. Our transport repairs the mask so the update applies."""

from typing import Any

import pytest
from google.cloud.pubsub_v1 import SubscriberClient
from google.protobuf.field_mask_pb2 import FieldMask

from app.core.celery_app import celery
from app.core.pubsub import Channel, FilterlessSubscriber, Transport


def test_update_drops_filter_and_flattens_nested_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[dict[str, Any]] = []

    def record(self: SubscriberClient, request: dict[str, Any], **_: Any) -> None:
        sent.append(request)

    monkeypatch.setattr(SubscriberClient, "update_subscription", record)
    subscriber = FilterlessSubscriber.__new__(FilterlessSubscriber)
    mask = FieldMask(paths=["ack_deadline_seconds", "expiration_policy.ttl", "filter"])

    subscriber.update_subscription(request={"subscription": "sub", "update_mask": mask})

    assert sent[0]["subscription"] == "sub"
    assert list(sent[0]["update_mask"].paths) == ["ack_deadline_seconds", "expiration_policy"]


def test_celery_uses_the_patched_transport() -> None:
    assert celery.connection_for_write().transport_cls == "app.core.pubsub:Transport"
    assert isinstance(celery.connection_for_write().transport, Transport)
    assert Transport.Channel is Channel
