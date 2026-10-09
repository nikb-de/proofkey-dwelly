from test_engine_processing import (EngineFixture, compose, ProcessingSummaryV1,
    RoleAdmissionLimits, make_request, make_auth, CaseStore, CaseResult, asdict,
    EvidenceAccessDenied, make_fixture_campaign, ProcessorIdentity, InvocationRequest,
    AssertionsOutput, EvidenceAssertion, UnknownLocator, ProcessingReceipt, output_digest)
from dataclasses import FrozenInstanceError
from datetime import timedelta, timezone, tzinfo
import json
import unittest
import threading
import sqlite3
from unittest.mock import patch
from proofkey.processing_summary import ProcessingAttemptSummaryV1, ProcessingEntryNoteV1
from proofkey.evidence.processing_contracts import canonical
from support import NOW, make_binding


class PureProcessingProjectionTests(unittest.TestCase):
    def test_as_of_detaches_mutable_timezone_and_preserves_utc_instant(self):
        class MutableTimezone(tzinfo):
            def __init__(self):
                self.offset, self.daylight, self.name = timedelta(0), timedelta(0), 'initial'

            def utcoffset(self, value):
                return self.offset

            def dst(self, value):
                return self.daylight

            def tzname(self, value):
                return self.name

        original_timezone = MutableTimezone()
        original = NOW.replace(tzinfo=original_timezone)
        original_instant = original.timestamp()
        summary = ProcessingSummaryV1(canonical(make_binding().model_dump(mode='json')),
            original, (), ())
        original_timezone.offset = timedelta(hours=3)
        original_timezone.daylight = timedelta(hours=1)
        original_timezone.name = 'mutated'
        self.assertEqual(original.utcoffset(), timedelta(hours=3))
        self.assertEqual(summary.as_of.utcoffset(), timedelta(0))
        self.assertEqual(summary.as_of.timestamp(), original_instant)
        self.assertEqual(summary.as_of.isoformat(), NOW.isoformat())
        self.assertIs(summary.as_of.tzinfo, timezone.utc)
        self.assertEqual(summary.as_of.tzname(), 'UTC')
        self.assertIsNone(summary.as_of.dst())

    def attempt(self, **changes):
        fields = dict(invocation_id='i', role='extraction', reservation_status='consumed',
            receipt_status=None, mode=None, reserved_usage=(('tokens', 2.0),),
            worst_case_cost=1.0, case_debit=1, role_debit=1, campaign_debit=1)
        return ProcessingAttemptSummaryV1(**{**fields, **changes})

    def test_attempt_rejects_nonexact_enums_and_terminal_pairs(self):
        cases = [dict(invocation_id=''), dict(invocation_id='  '), dict(invocation_id=1),
            dict(role='provider'), dict(role=1), dict(reservation_status='reserved'),
            dict(reservation_status='completed'), dict(receipt_status='running'),
            dict(mode='synthetic'), dict(reservation_status='failed', receipt_status='completed', mode='actual'),
            dict(reservation_status='completed', receipt_status='completed'),
            dict(reservation_status='failed', receipt_status='failed', mode='wrong')]
        for number, changes in enumerate(cases):
            with self.subTest(number=number), self.assertRaises((TypeError, ValueError)):
                self.attempt(**changes)

    def test_attempt_rejects_mutable_unsorted_duplicate_and_nonfinite_debt(self):
        cases = [dict(reserved_usage=[('tokens', 2.0)]), dict(reserved_usage=(['tokens', 2.0],)),
            dict(reserved_usage=(('z', 1.0), ('a', 1.0))),
            dict(reserved_usage=(('tokens', 1.0), ('tokens', 2.0))),
            dict(reserved_usage=((' ', 1.0),)), dict(reserved_usage=(('tokens', True),)),
            dict(reserved_usage=(('tokens', 1),)), dict(reserved_usage=(('tokens', -1.0),)),
            dict(reserved_usage=(('tokens', float('nan')),)),
            dict(worst_case_cost=float('inf')), dict(worst_case_cost=-1.0),
            dict(worst_case_cost=True), dict(worst_case_cost=1),
            dict(case_debit=True), dict(role_debit=0), dict(campaign_debit=2)]
        for number, changes in enumerate(cases):
            with self.subTest(number=number), self.assertRaises((TypeError, ValueError)):
                self.attempt(**changes)

    def test_note_rejects_unknown_reason_pairs_and_aliases(self):
        for number, pair in enumerate((('wrong', None), ('unavailable', None),
                ('recorded_replay', 'input_unavailable'), ('unavailable', 'private text'),
                (True, None), ('unavailable', True))):
            with self.subTest(number=number), self.assertRaises((TypeError, ValueError)):
                ProcessingEntryNoteV1(*pair)

    def test_summary_rejects_incomplete_noncanonical_mutable_and_wrong_time(self):
        binding = canonical(make_binding().model_dump(mode='json'))
        raw = json.loads(binding)
        missing = {k: v for k, v in raw.items() if k != 'supersedes_generation'}
        extra = {**raw, 'output': 'secret'}
        cases = [dict(binding_bytes=bytearray(binding)), dict(binding_bytes=binding + b' '),
            dict(binding_bytes=canonical(missing)), dict(binding_bytes=canonical(extra)),
            dict(binding_bytes=b'{"case_id":"C1","case_id":"C2"}'),
            dict(binding_bytes=b'x' * 65537), dict(as_of=NOW.replace(tzinfo=None)),
            dict(as_of=NOW.astimezone(timezone(timedelta(hours=1)))), dict(as_of='2026-10-08'),
            dict(attempts=[self.attempt()]), dict(attempts=(object(),)),
            dict(entry_local=[ProcessingEntryNoteV1('recorded_replay', None)]),
            dict(entry_local=(object(),)),
            dict(entry_local=(ProcessingEntryNoteV1('recorded_replay', None),) * 2)]
        for number, changes in enumerate(cases):
            fields = dict(binding_bytes=binding, as_of=NOW, attempts=(), entry_local=())
            with self.subTest(number=number), self.assertRaises((TypeError, ValueError)):
                ProcessingSummaryV1(**{**fields, **changes})

    def test_frozen_closed_fields_preserve_opaque_identifiers_and_all_rows(self):
        attempts = tuple(self.attempt(invocation_id='long-' + 'x' * 1000 + str(i)) for i in range(30))
        summary = ProcessingSummaryV1(canonical(make_binding().model_dump(mode='json')), NOW,
            attempts, (ProcessingEntryNoteV1('recorded_replay', None),))
        self.assertEqual(len(summary.attempts), 30)
        self.assertEqual(set(asdict(summary)), {'binding_bytes', 'as_of', 'attempts', 'entry_local'})
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            summary.attempts = ()
        with self.assertRaises(TypeError):
            ProcessingSummaryV1(summary.binding_bytes, NOW, (), (), output='secret')

    def test_mutable_subclass_aliases_never_cross_pure_projection_boundary(self):
        class Word(str):
            pass
        class BytesAlias(bytes):
            pass
        class TupleAlias(tuple):
            pass
        class AttemptAlias(ProcessingAttemptSummaryV1):
            pass
        class NoteAlias(ProcessingEntryNoteV1):
            pass
        for changes in (dict(invocation_id=Word('i')), dict(role=Word('extraction')),
                dict(reserved_usage=TupleAlias((('tokens', 1.0),))),
                dict(reserved_usage=((Word('tokens'), 1.0),))):
            with self.subTest(fields=tuple(changes)), self.assertRaises((TypeError, ValueError)):
                self.attempt(**changes)
        binding = canonical(make_binding().model_dump(mode='json'))
        for changes in (dict(binding_bytes=BytesAlias(binding)),
                dict(attempts=TupleAlias((self.attempt(),))),
                dict(attempts=(AttemptAlias(**asdict(self.attempt())),)),
                dict(entry_local=(NoteAlias('recorded_replay', None),))):
            with self.subTest(fields=tuple(changes)), self.assertRaises((TypeError, ValueError)):
                ProcessingSummaryV1(**{**dict(binding_bytes=binding, as_of=NOW, attempts=(), entry_local=()), **changes})

class ProcessingSummaryTests(EngineFixture):
    def assert_denied(self, value, correlation='C1'):
        self.assertIsInstance(value, CaseResult)
        self.assertEqual(value.model_dump(mode='json'),
            CaseResult(status='denied', correlation_id=correlation, reason='denied').model_dump(mode='json'))

    def test_final_checkpoint_read_cannot_outlive_original_host_window(self):
        fx = self.fixture(make_request(narrative='synthetic unavailable input'))
        fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
        ready = [False]
        original_attempts, original_checkpoint = fx.store.processing_attempts, fx.store.checkpoint
        def inventory(binding):
            value = original_attempts(binding)
            ready[0] = True
            return value
        def checkpoint(case_id):
            value = original_checkpoint(case_id)
            if ready[0]:
                fx.clock.advance(31)
            return value
        with patch.object(fx.store, 'processing_attempts', inventory), patch.object(fx.store, 'checkpoint', checkpoint):
            result = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        self.assert_denied(result)

    def test_invalid_inputs_thread_recursion_expiry_and_reversal_do_not_enter_store(self):
        fx = self.fixture(make_request())
        invalid = ['', '  ', None, 1, True, object()]
        with patch.object(fx.store, 'checkpoint', side_effect=AssertionError('store entered')):
            for number, case_id in enumerate(invalid):
                with self.subTest(number=number):
                    self.assert_denied(fx.engine.processing_summary(case_id, fx.auth,
                        execution=self.execution(fx)), 'invalid-request')
            self.assert_denied(fx.engine.processing_summary('C1', object(), execution=self.execution(fx)))
            values = []
            execution = self.execution(fx)
            thread = threading.Thread(target=lambda: values.append(fx.engine.processing_summary('C1', fx.auth,
                execution=execution)))
            thread.start()
            thread.join()
            self.assert_denied(values[0])
            with fx.engine._execution_scope(self.execution(fx)):
                self.assert_denied(fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx)))
            fx.clock.advance(31)
            self.assert_denied(fx.engine.processing_summary('C1', fx.auth, execution=execution))
            execution = self.execution(fx)
            fx.clock.tick -= 1
            self.assert_denied(fx.engine.processing_summary('C1', fx.auth, execution=execution))
        self.assertEqual(fx.world.calls, ())

    def test_stopped_state_is_inspectable_but_source_identity_and_authorization_are_current(self):
        fx = self.fixture(make_request(narrative='synthetic unavailable input'))
        fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
        binding = fx.store.checkpoint('C1').binding
        fx.engine.stop('C1', binding.generation, fx.auth, execution=self.execution(fx))
        stopped = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        self.assertIsInstance(stopped, ProcessingSummaryV1)
        self.assertTrue(fx.store.checkpoint('C1').stop.requested)
        self.assertEqual(fx.store.processing_attempts(binding), ())
        for fact, value in (('case.authorization', 'unverified'), ('case.generation', 'foreign'),
                ('case.request_revision', 'foreign')):
            fresh = self.fixture(make_request(narrative='synthetic unavailable input'))
            fresh.engine.run(fresh.request, fresh.auth, execution=self.execution(fresh))
            fresh.world.mutate(fact, value)
            self.assert_denied(fresh.engine.processing_summary('C1', fresh.auth, execution=self.execution(fresh)))

    def test_inspection_does_not_clear_notes_and_new_denied_workflow_does(self):
        fx = self.fixture(make_request(narrative='synthetic unavailable input'))
        fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
        self.assert_denied(fx.engine.processing_summary('C1', make_auth(proof_reference='wrong'),
            execution=self.execution(fx)))
        present = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        self.assertEqual([(n.kind, n.reason) for n in present.entry_local], [('unavailable', 'input_unavailable')])
        fx.engine.run(fx.request, make_auth(proof_reference='wrong'), execution=self.execution(fx))
        cleared = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        self.assertEqual(cleared.entry_local, ())
        fx.engine.recover('C1', fx.auth, execution=self.execution(fx))
        paused = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        self.assertEqual(paused.entry_local, ())  # wait status does not reconstruct input observation

    def test_real_corrupt_later_row_denies_entire_inventory_without_partial_list(self):
        fx = self.fixture(make_request(narrative='synthetic unavailable input'))
        fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
        cp = fx.store.checkpoint('C1')
        record = fx.catalog.register_saved_narrative(cp.binding, fx.auth)
        grant = make_fixture_campaign(input_hashes=[record.original_hash])
        fx.store.register_campaign(grant)
        identity = ProcessorIdentity(case_id='C1', generation=cp.binding.generation, role='extraction',
            campaign_id=grant.campaign_id, permit_hash=grant.permit_hash, input_hashes=[record.original_hash],
            provider=grant.provider, model=grant.model, endpoint=grant.endpoint, prompt_hash='2' * 64,
            version='v1', profile_version=cp.profile_version, process_version=cp.process_version, deadline=cp.deadline)
        for identifier in ('first', 'later'):
            fx.store.reserve_invocation(InvocationRequest(identity=identity, invocation_id=identifier,
                requested_usage={'tokens': 1.0}, worst_case_cost=1.0), fx.clock.now())
        inventory = fx.store.processing_attempts(cp.binding)
        self.assertEqual([a.invocation_id for a, _ in inventory], ['first', 'later'])
        # Deliberately corrupt a real negative fixture after public producers; never an authority positive.
        broken = inventory[1][0].model_dump(mode='json')
        broken['case_debit'] = 0
        with sqlite3.connect(fx.root / 'journal.sqlite') as connection:
            connection.execute('UPDATE invocations SET reservation_json=? WHERE invocation_id=?',
                (json.dumps(broken), 'later'))
        self.assert_denied(fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx)))

    def test_status_inspection_never_calls_catalog_or_processing_and_preserves_fresh_as_of(self):
        fx = self.fixture(make_request(narrative='synthetic unavailable input'))
        fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
        before = fx.clock.now()
        fx.clock.advance(1)
        with patch.object(fx.catalog, 'get', side_effect=AssertionError('catalog read')), \
                patch.object(fx.catalog, 'read_original', side_effect=AssertionError('catalog read')), \
                patch.object(fx.catalog, 'publish_processing_output', side_effect=AssertionError('publication')), \
                patch.object(fx.processing, 'plan_prepared', side_effect=AssertionError('processor entered')):
            result = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        self.assertIsInstance(result, ProcessingSummaryV1)
        self.assertGreater(result.as_of, before)
        self.assertEqual(result.as_of, fx.clock.now())

    def test_wrong_thread_workflow_denial_cannot_mutate_owner_entry_note(self):
        fx = self.fixture(make_request(narrative='synthetic unavailable input'))
        fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
        execution = self.execution(fx)
        denied = []
        thread = threading.Thread(target=lambda: denied.append(fx.engine.run(fx.request, fx.auth,
            execution=execution)))
        thread.start()
        thread.join()
        self.assert_denied(denied[0])
        summary = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        self.assertEqual([(n.kind, n.reason) for n in summary.entry_local], [('unavailable', 'input_unavailable')])

    def test_all_ordered_durable_status_debt_private_and_local_notes_not_rebuilt(self):
        secret = 'PRIVATE-CONTENT-NOT-FOR-SUMMARY'
        fx = self.fixture(make_request(narrative=secret))
        paused = fx.engine.run(fx.request, fx.auth, execution=self.execution(fx))
        self.assertEqual(paused.status, 'authorized')
        cp = fx.store.checkpoint('C1')
        self.assertEqual(cp.processing_status, 'unavailable')
        record = fx.catalog.register_saved_narrative(cp.binding, fx.auth)
        grant = make_fixture_campaign(input_hashes=[record.original_hash], max_invocations=5,
            max_usage={'tokens': 10.0}, max_cost=5.0)
        fx.store.register_campaign(grant)  # explicit outside engine, not permission inference
        ordered = (('z-complete', 'completed'), ('m-none', None), ('b-failed', 'failed'),
                   ('a-unknown', 'outcome_unknown'), ('q-unavailable', 'unavailable'))
        for identifier, status in ordered:
            identity = ProcessorIdentity(case_id='C1', generation=cp.binding.generation,
                role='extraction', campaign_id=grant.campaign_id, permit_hash=grant.permit_hash,
                input_hashes=[record.original_hash], provider=grant.provider, model=grant.model,
                endpoint=grant.endpoint, prompt_hash='2' * 64, version='v1',
                profile_version=cp.profile_version, process_version=cp.process_version,
                deadline=cp.deadline)
            fx.store.reserve_invocation(InvocationRequest(identity=identity, invocation_id=identifier,
                requested_usage={'tokens': 2.0}, worst_case_cost=1.0), fx.clock.now())
            if status is not None:
                output = None if status != 'completed' else AssertionsOutput(kind='assertions',
                    assertions=[EvidenceAssertion(artifact_id=record.artifact_id,
                        content_hash=record.original_hash, lineage_hash=record.lineage_hash,
                        locator=UnknownLocator(reason='not_measured'), uncertainty='unverified',
                        processing_receipt_id=identifier, claim=secret)])
                fx.store.record_processing(identifier, ProcessingReceipt(invocation_id=identifier,
                    role='extraction', provider=identity.provider, requested_model=identity.model,
                    prompt_hash=identity.prompt_hash, version='v1', input_hashes=identity.input_hashes,
                    mode='synthetic', status=status, latency_seconds=0.0, usage={}, output=output,
                    output_hashes=[] if output is None else [output_digest(output)],
                    processed_at=fx.clock.now(), reason=secret))
        before = fx.store.processing_attempts(cp.binding)
        debt = fx.store.campaign_usage(grant.permit_hash)
        budget = fx.store.checkpoint('C1').budget
        catalog_before = {str(p.relative_to(fx.catalog.root)): p.read_bytes()
                          for p in fx.catalog.root.rglob('*') if p.is_file()}
        summary = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        self.assertIsInstance(summary, ProcessingSummaryV1)
        self.assertEqual(set(asdict(summary)), {'binding_bytes', 'as_of', 'attempts', 'entry_local'})
        allowed = {'invocation_id', 'role', 'reservation_status', 'receipt_status', 'mode',
                   'reserved_usage', 'worst_case_cost', 'case_debit', 'role_debit', 'campaign_debit'}
        self.assertTrue(all(set(asdict(a)) == allowed for a in summary.attempts))
        self.assertEqual([a.invocation_id for a in summary.attempts], [i for i, _ in ordered])
        self.assertEqual([a.reservation_status for a in summary.attempts],
                         ['completed', 'consumed', 'failed', 'outcome_unknown', 'failed'])
        self.assertEqual([a.receipt_status for a in summary.attempts], [s for _, s in ordered])
        self.assertEqual([a.mode for a in summary.attempts],
                         ['synthetic', None, 'synthetic', 'synthetic', 'synthetic'])
        self.assertEqual([(a.case_debit, a.role_debit, a.campaign_debit)
                          for a in summary.attempts], [(1, 1, 1)] * 5)
        self.assertEqual([a.worst_case_cost for a in summary.attempts], [1.0] * 5)
        self.assertEqual([a.reserved_usage for a in summary.attempts], [(('tokens', 2.0),)] * 5)
        self.assertEqual([(n.kind, n.reason) for n in summary.entry_local],
                         [('unavailable', 'input_unavailable')])
        self.assertNotIn(secret, repr(asdict(summary)))
        self.assertEqual(fx.store.processing_attempts(cp.binding), before)
        self.assertEqual(fx.store.campaign_usage(grant.permit_hash), debt)
        self.assertEqual({str(p.relative_to(fx.catalog.root)): p.read_bytes()
                          for p in fx.catalog.root.rglob('*') if p.is_file()}, catalog_before)
        after = fx.store.checkpoint('C1').budget
        self.assertEqual(after.role_allowances, budget.role_allowances)
        self.assertEqual(after.tool_calls, budget.tool_calls + 1)  # real current control read
        fx.revoked.add('saved-scope')
        with self.assertRaises(EvidenceAccessDenied):
            fx.catalog.get(record.artifact_id, fx.auth)
        withheld = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        self.assertEqual(withheld.attempts, summary.attempts)  # no output readability claim
        self.assertNotIn(secret, repr(asdict(withheld)))
        self.assertEqual({str(p.relative_to(fx.catalog.root)): p.read_bytes()
                          for p in fx.catalog.root.rglob('*') if p.is_file()}, catalog_before)
        fx.store.close()
        fx.store = CaseStore(fx.root / 'journal.sqlite')
        compose(fx, (RoleAdmissionLimits('extraction', 5, (('tokens', 10.0),), 5.0),
                     RoleAdmissionLimits('planning', 1, (('tokens', 2.0),), 1.0)))
        reopened = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        self.assertEqual(reopened.attempts, summary.attempts)
        self.assertEqual(reopened.entry_local, ())
        denied = fx.engine.processing_summary('C1', make_auth(proof_reference='wrong'),
                                              execution=self.execution(fx))
        self.assertEqual(denied.model_dump(mode='json'),
                         CaseResult(status='denied', correlation_id='C1', reason='denied').model_dump(mode='json'))
        missing = fx.engine.processing_summary('missing', fx.auth, execution=self.execution(fx))
        self.assertEqual(set(missing.model_dump(mode='json')), {'status', 'correlation_id', 'reason'})
        fx.world.mutate('case.authorization', 'unverified')
        revoked = fx.engine.processing_summary('C1', fx.auth, execution=self.execution(fx))
        self.assertEqual(revoked.model_dump(mode='json'), denied.model_dump(mode='json'))
        self.assertEqual(fx.store.processing_attempts(cp.binding), before)
        self.assertEqual(fx.store.campaign_usage(grant.permit_hash), debt)
