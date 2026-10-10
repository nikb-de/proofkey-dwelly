"""Keep live work off managed Cloud Run until durable cloud admission exists."""
import os


def reject_live_cloud(live: bool) -> None:
    """Fail before local artifacts or reservations can admit a live cloud run."""
    if live and any(marker in os.environ for marker in ("K_SERVICE", "CLOUD_RUN_JOB")):
        raise ValueError("live_cloud_unavailable")
