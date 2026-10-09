"""Cooperative built-in ownership only; no hostile-writer or activation claim."""
from datetime import timedelta
from pathlib import Path
import tempfile
import os
import copy
import pickle
import stat
import threading
from unittest.mock import patch
import unittest
from proofkey.clock import SyntheticReplayClock
from proofkey.execution import ExecutionContext
from proofkey.host import AuthResolver, HostDispatcher, ProfileRegistry, RuntimeFactory, RuntimeResources
from proofkey.contracts import AuthContext
from proofkey.host_contracts import HostLimitsV1
from proofkey.journal import CaseStore
import proofkey.host as host_module
from proofkey.host_writer import RuntimeWriterLease, RuntimeWriterFailure


class RuntimeWriterTests(unittest.TestCase):
    def directory(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name).resolve()

    def scope_failure(self, operation):
        unexpected = None
        try:
            with self.assertRaises(RuntimeWriterFailure) as caught:
                unexpected = operation()
        finally:
            if type(unexpected) is RuntimeWriterLease:
                unexpected.close()
        self.assertEqual(caught.exception.code, 'writer_scope')
        self.assertEqual(str(caught.exception), 'writer_scope')

    def setup_release(self, base):
        clock = SyntheticReplayClock()
        release = ProfileRegistry.builtin(base / "resources").resolve("host-window-replay-v1")
        return release, clock

    def images(self, runtime, clock):
        execution = ExecutionContext.capture(clock.now() + timedelta(seconds=5), clock)
        journal = runtime.store.capture_retained_state(execution=execution, clock=clock)
        execution = ExecutionContext.capture(clock.now() + timedelta(seconds=5), clock)
        source = runtime.world.capture_retained_state(execution=execution, clock=clock)
        return journal.payload, source.payload

    def test_second_builtin_owner_denied_before_database_entry(self):
        with tempfile.TemporaryDirectory() as folder:
            release, clock = self.setup_release(Path(folder).resolve())
            first = RuntimeFactory().create(release, clock)
            second = None
            try:
                before = self.images(first, clock)
                try:
                    with self.assertRaisesRegex(ValueError, "^writer_busy$"):
                        second = RuntimeFactory().create(release, clock)
                finally:
                    if second is not None:
                        second.close()
                self.assertEqual(self.images(first, clock), before)
                self.assertEqual(first.world.effect_count("reschedule"), 0)
            finally:
                first.close()

    def test_clean_close_retains_lock_identity_and_permits_new_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            release, clock = self.setup_release(Path(folder).resolve())
            first = RuntimeFactory().create(release, clock)
            lock = release.resource_root / ".proofkey-resource-writer.lock"
            try:
                self.assertTrue(lock.is_file())
                before = lock.stat()
                images = self.images(first, clock)
            finally:
                first.close()
            first.close()
            after = lock.stat()
            self.assertEqual((before.st_dev, before.st_ino), (after.st_dev, after.st_ino))
            next_owner = RuntimeFactory().create(release, clock)
            try:
                self.assertEqual(self.images(next_owner, clock), images)
                again = lock.stat()
                self.assertEqual((before.st_dev, before.st_ino), (again.st_dev, again.st_ino))
                self.assertEqual(next_owner.world.effect_count("reschedule"), 0)
            finally:
                next_owner.close()

    def test_prohibited_roots_rejected_before_open(self):
        # No negative fixture may create a lock in a real root/home/workspace.
        for root in (Path('/'), Path.home(), Path.cwd()):
            with self.subTest(root=root):
                entered = []
                def deny_open(*args, **kwargs):
                    entered.append(args)
                    raise RuntimeWriterFailure('writer_scope')
                with patch('proofkey.host_writer.os.open', deny_open):
                    self.scope_failure(lambda: RuntimeWriterLease(root))
                self.assertEqual(entered, [])

    def test_ancestor_symlink_and_dotdot_are_rejected_without_lock(self):
        base = self.directory()
        real = base / 'real'
        real.mkdir()
        child = real / 'child'
        child.mkdir()
        alias = base / 'alias'
        alias.symlink_to(real, target_is_directory=True)
        for root in (alias / 'child', child / '..'):
            with self.subTest(root=root):
                self.scope_failure(lambda: RuntimeWriterLease(root))
                self.assertFalse((child / '.proofkey-resource-writer.lock').exists())
                self.assertFalse((real / '.proofkey-resource-writer.lock').exists())

    def test_invalid_lock_targets_are_not_repaired(self):
        for kind in ('symlink', 'hardlink', 'directory', 'fifo', 'nonempty', 'permissions'):
            with self.subTest(kind=kind):
                base = self.directory()
                target = base / '.proofkey-resource-writer.lock'
                original = base / 'original'
                if kind in ('symlink', 'hardlink'):
                    original.touch(mode=0o600)
                    if kind == 'symlink':
                        target.symlink_to(original)
                    else:
                        os.link(original, target)
                elif kind == 'directory':
                    target.mkdir()
                elif kind == 'fifo':
                    os.mkfifo(target, 0o600)
                else:
                    target.touch(mode=0o600)
                    if kind == 'nonempty':
                        target.write_bytes(b'retained foreign content')
                    else:
                        target.chmod(0o640)
                before = target.lstat()
                self.scope_failure(lambda: RuntimeWriterLease(base))
                after = target.lstat()
                self.assertEqual((after.st_ino, after.st_mode, after.st_size, after.st_nlink),
                                 (before.st_ino, before.st_mode, before.st_size, before.st_nlink))

    def test_foreign_root_owner_denies_before_lock_creation(self):
        base = self.directory()
        with patch('proofkey.host_writer.os.geteuid', return_value=os.geteuid() + 1):
            self.scope_failure(lambda: RuntimeWriterLease(base))
        self.assertFalse((base / '.proofkey-resource-writer.lock').exists())

    def test_held_identity_changes_deny_and_close_original_only(self):
        for change in ('root', 'lock', 'hardlink', 'permissions', 'content'):
            with self.subTest(change=change):
                base = self.directory()
                root = base / 'resource'
                root.mkdir()
                lease = RuntimeWriterLease(root)
                target = root / '.proofkey-resource-writer.lock'
                try:
                    if change == 'root':
                        root.rename(base / 'old-root')
                        root.mkdir()
                    elif change == 'lock':
                        target.rename(root / 'old-lock')
                        target.touch(mode=0o600)
                    elif change == 'hardlink':
                        os.link(target, root / 'alias-lock')
                    elif change == 'permissions':
                        target.chmod(0o640)
                    else:
                        target.write_bytes(b'changed')
                    self.scope_failure(lease.check)
                finally:
                    lease.close()
                if change in ('root', 'lock'):
                    successor = RuntimeWriterLease(root)
                    successor.close()

    def test_foreign_thread_cannot_check_or_release_creator_lease(self):
        root = self.directory()
        lease = RuntimeWriterLease(root)
        errors = []
        def foreign():
            for operation in (lease.check, lease.close):
                try:
                    operation()
                except RuntimeWriterFailure as error:
                    errors.append(error.code)
        thread = threading.Thread(target=foreign)
        thread.start()
        thread.join(2)
        try:
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, ['writer_scope', 'writer_scope'])
            with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_busy$'):
                RuntimeWriterLease(root)
            lease.check()
        finally:
            lease.close()
        lease.close()
        self.scope_failure(lease.check)

    def test_path_grammar_and_operational_error_are_finite(self):
        root = self.directory()
        for bad in (str(root), Path('relative'), root / '..', root / ('x' * 1025),
                    root.joinpath(*(['x'] * 65))):
            with self.subTest(bad=bad):
                self.scope_failure(lambda: RuntimeWriterLease(bad))
        with patch('proofkey.host_writer.os.open', side_effect=OSError('private-path-canary')):
            with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_storage$') as caught:
                RuntimeWriterLease(root)
        self.assertEqual(caught.exception.code, 'writer_storage')

    def test_independent_real_builtin_roots_and_busy_constructor_boundary(self):
        base = self.directory()
        registry = ProfileRegistry.builtin(base / 'resources')
        clock = SyntheticReplayClock()
        first = RuntimeFactory().create(registry.resolve('host-window-replay-v1'), clock)
        second = RuntimeFactory().create(registry.resolve('host-goods-replay-v1'), clock)
        try:
            before = (self.images(first, clock), self.images(second, clock))
            entered = []
            def forbidden(*args, **kwargs):
                entered.append((args, kwargs))
                raise AssertionError('database constructor entered while busy')
            with patch('proofkey.host.SimulatedWorld', forbidden), patch('proofkey.host.CaseStore', forbidden):
                with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_busy$'):
                    RuntimeFactory().create(registry.resolve('host-window-replay-v1'), clock)
            self.assertEqual(entered, [])
            self.assertEqual((self.images(first, clock), self.images(second, clock)), before)
        finally:
            first.close()
            second.close()

    def test_ordinary_constructor_failures_release_lease_preserving_error(self):
        for stage in ('world', 'store', 'final-validation'):
            with self.subTest(stage=stage):
                release, clock = self.setup_release(self.directory())
                failure = ValueError('setup failure')
                actual_validate = host_module.ApprovedProfileRelease.validate
                validations = []
                def validate(value):
                    validations.append(value)
                    if len(validations) == 2:
                        raise failure
                    return actual_validate(value)
                target = {'world': 'SimulatedWorld', 'store': 'CaseStore'}.get(stage)
                context = (patch.object(host_module, target, side_effect=failure) if target
                           else patch.object(host_module.ApprovedProfileRelease, 'validate', validate))
                with context:
                    with self.assertRaises(ValueError) as caught:
                        RuntimeFactory().create(release, clock)
                self.assertIs(caught.exception, failure)
                lease = RuntimeWriterLease(release.resource_root)
                lease.close()

    def test_real_store_close_failure_keeps_lease_for_owner_retry(self):
        release, clock = self.setup_release(self.directory())
        runtime = RuntimeFactory().create(release, clock)
        actual_close = CaseStore.close
        failure = OSError('store close failed')
        try:
            with patch.object(CaseStore, 'close', side_effect=failure):
                with self.assertRaises(OSError) as caught:
                    runtime.close()
            self.assertIs(caught.exception, failure)
            self.assertFalse(runtime.closed)
            with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_busy$'):
                RuntimeWriterLease(release.resource_root)
            runtime.close()
            self.assertTrue(runtime.closed)
            successor = RuntimeWriterLease(release.resource_root)
            successor.close()
        finally:
            actual_close(runtime.store)
            runtime.close()

    def test_double_failure_returns_cleanup_only_creator_retry_handle(self):
        release, clock = self.setup_release(self.directory())
        stores, leases = [], []
        setup = ValueError('original setup error')
        cleanup = OSError('original cleanup error')
        actual_close = CaseStore.close
        actual_lease = RuntimeWriterLease
        def store(*args, **kwargs):
            value = CaseStore(*args, **kwargs)
            stores.append(value)
            return value
        def lease(*args, **kwargs):
            value = actual_lease(*args, **kwargs)
            leases.append(value)
            return value
        try:
            with patch.object(host_module, 'CaseStore', store), patch.object(host_module, 'RuntimeWriterLease', lease), \
                    patch.object(host_module, 'WorkflowEngine', side_effect=setup), \
                    patch.object(CaseStore, 'close', side_effect=cleanup):
                with self.assertRaises(ValueError) as caught:
                    RuntimeFactory().create(release, clock)
            failure = caught.exception
            self.assertEqual(type(failure).__name__, 'RuntimeConstructionFailure')
            self.assertEqual(failure.code, 'writer_storage')
            self.assertEqual(str(failure), 'writer_storage')
            self.assertFalse(failure.closed)
            self.assertIs(failure.__cause__, cleanup)
            self.assertIs(cleanup.__context__, setup)
            self.assertFalse(any(hasattr(failure, name) for name in ('engine', 'world', 'store', 'profile')))
            for operation in (copy.copy, copy.deepcopy, pickle.dumps):
                with self.subTest(operation=operation.__name__):
                    with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_scope$'):
                        operation(failure)
            errors = []
            def foreign():
                try:
                    failure.close()
                except RuntimeWriterFailure as error:
                    errors.append(error.code)
            thread = threading.Thread(target=foreign)
            thread.start()
            thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, ['writer_scope'])
            with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_busy$'):
                actual_lease(release.resource_root)
            failure.close()
            failure.close()
            self.assertTrue(failure.closed)
            successor = actual_lease(release.resource_root)
            successor.close()
        finally:
            for value in stores:
                actual_close(value)
            for value in leases:
                value.close()

    def test_resource_optional_lease_requires_exact_type_and_legacy_still_works(self):
        release, clock = self.setup_release(self.directory())
        resource = RuntimeFactory().create(release, clock)
        try:
            with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_scope$'):
                RuntimeResources(resource.profile, resource.world, resource.store, resource.engine, writer_lease=object())
            legacy = RuntimeResources(resource.profile, resource.world, resource.store, resource.engine)
            self.assertFalse(legacy.closed)
        finally:
            resource.close()

    def test_descriptor_close_uncertainty_never_retries_reused_number(self):
        root = self.directory()
        opened = []
        actual_open, actual_close = os.open, os.close
        def observe_open(*args, **kwargs):
            fd = actual_open(*args, **kwargs)
            opened.append((fd, os.fstat(fd)))
            return fd
        with patch('proofkey.host_writer.os.open', observe_open):
            lease = RuntimeWriterLease(root)
        attempts, replacements = [], []
        def close_then_raise(fd):
            regular = stat.S_ISREG(os.fstat(fd).st_mode)
            attempts.append(fd)
            actual_close(fd)
            if regular:
                raise OSError('close reported uncertain after closing actual fd')
        try:
            with patch('proofkey.host_writer.os.close', close_then_raise):
                with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_storage$'):
                    lease.close()
            replacement = actual_open(root, os.O_RDONLY | os.O_DIRECTORY)
            replacements.append(replacement)
            identity = os.fstat(replacement)
            with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_storage$'):
                lease.close()
            self.assertEqual(os.fstat(replacement), identity)
            with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_storage$'):
                lease.check()
            self.assertEqual(len(attempts), 2)
        finally:
            for fd in replacements:
                actual_close(fd)
            # Only close still-live ORIGINAL test-owned identities after a RED;
            # do not touch a reused number. No private lease attributes involved.
            for fd, identity in opened:
                try:
                    current = os.fstat(fd)
                except OSError:
                    continue
                if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                    actual_close(fd)

    def dispatcher(self, factory):
        base = self.directory()
        clock = SyntheticReplayClock()
        resolver = AuthResolver({'local': AuthContext(caller_id='U1', proof_reference='synthetic-proof')})
        dispatcher = HostDispatcher(factory, resolver, ProfileRegistry.builtin(base / 'resources'), clock,
                                    base / 'inventory', HostLimitsV1(), release_id='host-window-replay-v1')
        return dispatcher, resolver.handle('local'), clock

    def recover_command(self, dispatcher, proof, clock):
        return dispatcher.submit({'tag': 'recover', 'release_id': 'host-window-replay-v1', 'case_id': 'C1'},
            proof, ExecutionContext.capture(clock.now() + timedelta(seconds=5), clock))

    def test_host_retains_construction_failure_denies_reentry_and_cleans_on_owner(self):
        class ObservedFactory(RuntimeFactory):
            def __init__(self):
                self.calls = 0
                self.failures = []
            def create(inner, release, clock):
                inner.calls += 1
                # If the buggy host re-enters, safely clean the prior test-owned
                # failure on its creator before proving the unexpected entry.
                if inner.failures:
                    inner.failures[-1].close()
                try:
                    return super().create(release, clock)
                except host_module.RuntimeConstructionFailure as error:
                    inner.failures.append(error)
                    raise
        factory = ObservedFactory()
        actual_close = CaseStore.close
        closes = []
        def fail_first_close(store):
            closes.append(threading.get_ident())
            if len(closes) == 1:
                raise OSError('first cleanup fails')
            return actual_close(store)
        dispatcher, proof, clock = self.dispatcher(factory)
        try:
            with patch.object(host_module, 'WorkflowEngine', side_effect=ValueError('setup failure')), \
                    patch.object(CaseStore, 'close', fail_first_close):
                first = self.recover_command(dispatcher, proof, clock)
                second = self.recover_command(dispatcher, proof, clock)
                shutdown = dispatcher.close(clock.now() + timedelta(seconds=2))
            self.assertEqual(factory.calls, 1)
            self.assertIsNone(first.result)
            self.assertIsNone(second.result)
            self.assertTrue(shutdown.owner_closed)
            self.assertTrue(factory.failures[0].closed)
            self.assertEqual(len(set(closes)), 1)
            self.assertNotEqual(closes[0], threading.get_ident())
        finally:
            dispatcher.close(clock.now() + timedelta(seconds=2))

    def test_host_resource_cleanup_error_cannot_report_clean_shutdown(self):
        class CloseFailsFactory(RuntimeFactory):
            def create(inner, release, clock):
                resource = super().create(release, clock)
                actual_close = resource.close
                def close_then_fail():
                    actual_close()
                    raise OSError('reported cleanup uncertainty after real cleanup')
                resource.close = close_then_fail
                return resource
        dispatcher, proof, clock = self.dispatcher(CloseFailsFactory())
        try:
            self.recover_command(dispatcher, proof, clock)
            shutdown = dispatcher.close(clock.now() + timedelta(seconds=2))
            self.assertFalse(shutdown.owner_closed)
        finally:
            dispatcher.close(clock.now() + timedelta(seconds=2))

    def test_lease_authority_cannot_be_copied_or_serialized(self):
        lease = RuntimeWriterLease(self.directory())
        try:
            for operation in (copy.copy, copy.deepcopy, pickle.dumps):
                with self.subTest(operation=operation.__name__):
                    clone = None
                    try:
                        with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_scope$'):
                            clone = operation(lease)
                    finally:
                        # Pre-fix clones share owned descriptor integers: never
                        # invoke their close; original creator closes once.
                        clone = None
            lease.check()
        finally:
            lease.close()

    def test_directory_walk_close_error_is_finite_and_never_retries_fd(self):
        root = self.directory()
        actual_close = os.close
        attempts = []
        failed = []
        def close_then_raise(fd):
            attempts.append(fd)
            actual_close(fd)
            if not failed:
                failed.append(fd)
                raise OSError('directory close uncertainty')
        with patch('proofkey.host_writer.os.close', close_then_raise):
            with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_storage$'):
                RuntimeWriterLease(root)
        self.assertEqual(len(attempts), len(set(attempts)))
        self.assertFalse((root / '.proofkey-resource-writer.lock').exists())

    def test_check_temporary_descriptor_cleanup_error_is_finite(self):
        root = self.directory()
        lease = RuntimeWriterLease(root)
        identity = root.stat()
        actual_close = os.close
        def close_then_raise(fd):
            current = os.fstat(fd)
            actual_close(fd)
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                raise OSError('check directory close uncertainty')
        try:
            with patch('proofkey.host_writer.os.close', close_then_raise):
                with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_storage$'):
                    lease.check()
        finally:
            with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_storage$'):
                lease.close()

    def test_unlock_error_still_closes_both_owned_descriptors(self):
        root = self.directory()
        lease = RuntimeWriterLease(root)
        import fcntl
        actual_flock = fcntl.flock
        actual_close = os.close
        closed = []
        def unlock_then_raise(fd, operation):
            actual_flock(fd, operation)
            if operation == fcntl.LOCK_UN:
                raise OSError('unlock reported uncertainty')
        def close(fd):
            closed.append(fd)
            actual_close(fd)
        with patch('proofkey.host_writer.fcntl.flock', unlock_then_raise), \
                patch('proofkey.host_writer.os.close', close):
            with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_storage$'):
                lease.close()
        self.assertEqual(len(set(closed)), 2)
        with self.assertRaisesRegex(RuntimeWriterFailure, '^writer_storage$'):
            lease.close()
        errors = []
        def foreign():
            try:
                lease.check()
            except RuntimeWriterFailure as error:
                errors.append(error.code)
        thread = threading.Thread(target=foreign)
        thread.start()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, ['writer_scope'])
        successor = RuntimeWriterLease(root)
        successor.close()

    def test_host_unresolved_construction_cleanup_never_reports_clean(self):
        actual_close, actual_os_close = CaseStore.close, os.close
        failures, closes = [], []
        class ObservedFactory(RuntimeFactory):
            def create(inner, release, clock):
                try:
                    return super().create(release, clock)
                except host_module.RuntimeConstructionFailure as error:
                    failures.append(error)
                    raise
        dispatcher, proof, clock = self.dispatcher(ObservedFactory())
        def store_close(store):
            actual_close(store)
            closes.append(1)
            if len(closes) == 1:
                raise OSError('first store close reported failure after close')
        def descriptor_close(fd):
            value = os.fstat(fd)
            target = dispatcher.release.resource_root / '.proofkey-resource-writer.lock'
            expected = target.stat() if target.exists() else None
            actual_os_close(fd)
            if expected and (value.st_dev, value.st_ino) == (expected.st_dev, expected.st_ino):
                raise OSError('lock close uncertainty after actual close')
        try:
            with patch.object(host_module, 'WorkflowEngine', side_effect=ValueError('setup failure')), \
                    patch.object(CaseStore, 'close', store_close), \
                    patch('proofkey.host_writer.os.close', descriptor_close):
                result = self.recover_command(dispatcher, proof, clock)
                shutdown = dispatcher.close(clock.now() + timedelta(seconds=2))
            self.assertIsNone(result.result)
            self.assertEqual(len(failures), 1)
            self.assertFalse(failures[0].closed)
            self.assertFalse(shutdown.owner_closed)
            # Actual lock+root FDs were closed; uncertainty is not a live leak.
            successor = RuntimeWriterLease(dispatcher.release.resource_root)
            successor.close()
        finally:
            dispatcher.close(clock.now() + timedelta(seconds=2))

    def test_interrupted_constructor_closes_owned_lock_and_preserves_interrupt(self):
        import fcntl
        root = self.directory()
        actual_flock, actual_open, actual_close = fcntl.flock, os.open, os.close
        opened = []
        interruption = KeyboardInterrupt('constructor interrupted')
        def observe_open(*args, **kwargs):
            descriptor = actual_open(*args, **kwargs)
            opened.append((descriptor, os.fstat(descriptor)))
            return descriptor
        def interrupt(fd, operation):
            actual_flock(fd, operation)
            if operation & fcntl.LOCK_EX:
                raise interruption
        successor = None
        try:
            with patch('proofkey.host_writer.fcntl.flock', interrupt), \
                    patch('proofkey.host_writer.os.open', observe_open):
                with self.assertRaises(KeyboardInterrupt) as caught:
                    RuntimeWriterLease(root)
            self.assertIs(caught.exception, interruption)
            successor = RuntimeWriterLease(root)
        finally:
            if successor is not None:
                successor.close()
            for descriptor, identity in opened:
                try:
                    value = os.fstat(descriptor)
                except OSError:
                    continue
                if (value.st_dev, value.st_ino) == (identity.st_dev, identity.st_ino):
                    actual_close(descriptor)
