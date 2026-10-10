"""Replay is original processing evidence, never fresh provider participation."""
from proofkey.contracts import ProcessingReceipt


class ReplayProcessor:
    def __init__(self, receipt):
        self.receipt = ProcessingReceipt.model_validate(receipt)

    def _replay(self, role):
        if self.receipt.role != role:
            raise ValueError("Replay role mismatch")
        return ProcessingReceipt.model_validate({**self.receipt.model_dump(), "mode": "recorded_replay"})

    def extract(self, records, context):
        return self._replay("extraction")

    def transcribe(self, record, context):
        return self._replay("transcription")

    def propose(self, checkpoint, observations):
        return self._replay("planning")
