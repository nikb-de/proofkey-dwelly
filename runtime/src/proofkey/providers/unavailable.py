"""Absent routes do not invent provider invocations, model identity or usable output."""
from datetime import datetime, timezone
from uuid import uuid4
from proofkey.contracts import ProcessingReceipt, ProcessorIdentity


class UnavailableProcessor:
    def __init__(self, identity, clock=None):
        self.identity = ProcessorIdentity.model_validate(identity)
        self.clock = clock

    def _receipt(self, role):
        identity = self.identity
        if identity.role != role:
            raise ValueError("Unavailable role mismatch")
        return ProcessingReceipt(invocation_id="unavailable-" + uuid4().hex, role=role,
            provider=identity.provider, requested_model=identity.model, prompt_hash=identity.prompt_hash,
            version=identity.version, input_hashes=identity.input_hashes, mode="unavailable", status="unavailable",
            latency_seconds=0.0, usage={}, processed_at=self.clock.now() if self.clock else datetime.now(timezone.utc),
            reason="No enabled content-processing route")

    def extract(self, records, context):
        return self._receipt("extraction")

    def transcribe(self, record, context):
        return self._receipt("transcription")

    def propose(self, checkpoint, observations):
        return self._receipt("planning")
