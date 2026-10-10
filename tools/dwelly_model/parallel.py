"""Bounded canonical batches; only provider completions run off the coordinator."""
from concurrent.futures import ThreadPoolExecutor

from . import providers


def dispatch(tasks, *, admit, settle, cancelled, max_parallel_requests,
             per_provider_limit, max_output_tokens, timeout):
    """Admit and settle in input order, independent of response arrival order.

    A batch is drained before admitting the next canonical prefix. This favors
    reproducible admission over maximum throughput. Callbacks run on the caller;
    workers neither reserve budget nor write artifacts.
    """
    position = 0
    with ThreadPoolExecutor(max_workers=max_parallel_requests) as pool:
        while position < len(tasks) and not cancelled():
            batch, counts = [], {}
            while position < len(tasks) and len(batch) < max_parallel_requests:
                seat, system, prompt, key = task = tasks[position]
                provider = seat["provider"]
                if counts.get(provider, 0) >= per_provider_limit or cancelled():
                    break
                position += 1
                if not admit(task):
                    continue
                future = pool.submit(providers.complete, dict(seat), system, prompt,
                                     max_output_tokens=max_output_tokens, timeout=timeout)
                batch.append((task, future))
                counts[provider] = counts.get(provider, 0) + 1
            for task, future in batch:
                try:
                    response = future.result()
                except Exception as error:
                    settle(task, None, error)
                else:
                    settle(task, response, None)
            cancelled()
