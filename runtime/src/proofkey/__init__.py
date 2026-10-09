"""ProofKey offline runtime. No providers or adapters are imported at startup."""

__version__ = "0.1.0"

# Finite lazy library exports: importing the package alone constructs nothing.
_CONTRACT_EXPORTS = ("InterfaceLimitsV1", "PublicationWindowV1", "BatchInputV1", "BatchPositionInventoryV1",
    "CommandInputInventoryV1", "RunReferenceV1", "ConsumedExportV1", "BatchPositionReceiptV1",
    "BatchManifestV1", "CommandManifestV1", "BatchRunReceiptV1", "CommandRunReceiptV1", "RunReadbackV1")
__all__ = ("run_command", "run_batch", "read_run_inventory", "RunPublisher", *_CONTRACT_EXPORTS)


def __getattr__(name):
    if name in _CONTRACT_EXPORTS:
        module = "host_contracts"
    elif name in ("run_command", "run_batch"):
        module = "batch"
    elif name in ("read_run_inventory", "RunPublisher"):
        module = "batch_files"
    else:
        raise AttributeError(name)
    from importlib import import_module
    return getattr(import_module("." + module, __name__), name)
