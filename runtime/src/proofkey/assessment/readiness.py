"""Host-owned preliminary role ledger, not authentication or final acceptance audit.

Input class readiness needs catalog/class joins and development needs Task13 agent
receipts. ProcessingReceipt alone cannot establish either, so these remain missing.
"""
from proofkey.contracts import ProcessingReceipt
from proofkey.providers.invocations import output_digest

INPUT_CLASSES = frozenset({"structured_no_text", "free_text", "supplied_transcript", "images_photos", "documents", "raw_audio"})
ROLE_DIMENSIONS = {"evidence_extraction": "extraction", "audio_asr": "transcription", "runtime_ai_plan": "planning",
                   "extraction": "extraction", "transcription": "transcription", "planning": "planning"}
DEFAULT_REQUIRED = INPUT_CLASSES | {"evidence_extraction", "audio_asr", "runtime_ai_plan", "development_adaptation"}


class ReadinessLedger:
    def __init__(self, required=None):
        self.required = frozenset(DEFAULT_REQUIRED if required is None else required)
        if not self.required or not self.required <= INPUT_CLASSES | set(ROLE_DIMENSIONS) | {"development_adaptation"}:
            raise ValueError("Known nonempty readiness dimensions required")
        self._receipts = {dimension: [] for dimension in self.required}

    def record(self, dimension, receipt):
        if dimension not in self.required:
            raise ValueError("Dimension outside declared requirements")
        if not isinstance(receipt, ProcessingReceipt):
            raise TypeError("Typed processing evidence required")
        self._receipts[dimension].append(ProcessingReceipt.model_validate(receipt))

    def _ready(self, dimension):
        role = ROLE_DIMENSIONS.get(dimension)
        if role is None:
            return False
        for receipt in self._receipts[dimension]:
            if (receipt.mode == "actual" and receipt.status == "completed" and receipt.role == role
                    and receipt.observed_model and receipt.provider_request_id and receipt.usage and receipt.input_hashes
                    and receipt.output is not None and receipt.output.kind == {
                        "extraction": "assertions", "transcription": "transcript", "planning": "proposal"}[role]
                    and receipt.output_hashes == [output_digest(receipt.output)]):
                return True
        return False

    def missing(self):
        return tuple(sorted(dimension for dimension in self.required if not self._ready(dimension)))

    def complete(self):
        return not self.missing()
