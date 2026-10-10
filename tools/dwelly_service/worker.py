"""Single job coordinator. Provider concurrency belongs to the model runner."""
import threading

from tools.dwelly_model.runner import run_experiment


class Worker:
    def __init__(self, store, bundle, config):
        self.store, self.bundle, self.config = store, bundle, config
        self.stopping = threading.Event()
        self.wakeup = threading.Event()
        self.failure = None
        self.thread = threading.Thread(target=self._loop, name="dwelly-job-worker", daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stopping.set()
        self.wakeup.set()
        if self.thread.is_alive():
            self.thread.join()

    def _loop(self):
        try:
            self._run()
        except Exception:
            # Keep unfinished work for restart reconciliation, never replay it.
            self.failure = "worker_unavailable"

    def _run(self):
        while not self.stopping.is_set():
            job = self.store.claim_next()
            if job is None:
                self.wakeup.wait(0.2)
                self.wakeup.clear()
                continue
            job_id, spec = job["job_id"], job["spec"]
            try:
                run_experiment(self.bundle, self.store.output_path(job_id), self.config,
                               live=spec["mode"] == "live", limit=spec["limit"],
                               proposals_only=not spec["evaluate"],
                               max_parallel_requests=spec["max_parallel_requests"],
                               per_provider_limit=spec["per_provider_limit"],
                               shared_budget_path=self.store.root / "budget.jsonl",
                               cancel_requested=lambda: self.stopping.is_set() or self.store.cancelled(job_id))
                try:
                    summary = self.store.summary(job_id)
                except ValueError:
                    self.store.finish(job_id, "failed", "invalid_terminal_summary")
                else:
                    self.store.finish(job_id, summary["status"])
            except Exception:
                self.store.finish(job_id, "failed", "execution_failed")
