"""J05-era current-source comparison; never historical execution evidence."""
import unittest

from proofkey.factory import AdaptationFactory, FactoryDenied
from support_factory_lanes import current_v1_context, current_v1_registration
from test_adaptation_factory import current_registration, factory_for, material, reviewed, supported_candidate


class CurrentSourceV1ComparisonTests(unittest.TestCase):
    def test_fixed_current_lane_executes_supported_v1(self):
        registration = current_v1_registration()
        mat = material(supported_candidate())
        factory = AdaptationFactory(current_v1_context(mat, registration=registration))
        self.assertEqual(factory.context.implementation_registration.registration_id,
                         'synthetic-factory-j05-current-v1')
        factory, proposal, regression, approval, packet = reviewed(
            implementation_registration=registration)
        self.assertEqual(factory.release_profile(packet, approval, []).status, 'staged_simulation')

    def test_historical_registration_rejects_current_source(self):
        with self.assertRaises(FactoryDenied) as caught:
            factory_for(material(supported_candidate()), implementation_registration=current_registration())
        self.assertEqual(caught.exception.reason, 'unsupported_adapter_implementation')

    def test_default_registration_rejects_current_source(self):
        with self.assertRaises(FactoryDenied) as caught:
            factory_for(material(supported_candidate()), implementation_registration=None)
        self.assertEqual(caught.exception.reason, 'unsupported_adapter_implementation')

    def test_comparison_identity_does_not_claim_historical_source(self):
        current = current_v1_registration()
        self.assertEqual(current.registration_id, 'synthetic-factory-j05-current-v1')
        self.assertNotEqual(current.registration_id, current_registration().registration_id)
        self.assertNotEqual(current.implementations, current_registration().implementations)
