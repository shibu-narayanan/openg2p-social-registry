# Part of OpenG2P. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


class TestClaimManagement(TransactionCase):

    def setUp(self):
        super().setUp()
        
        # Create test data
        self.test_partner = self.env['res.partner'].create({
            'name': 'Test Registrant',
            'email': 'test@example.com',
            'phone': '+1234567890',
        })
        
        self.test_user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'testuser',
            'email': 'testuser@example.com',
        })
        
        # Create claim configuration
        self.claim_config = self.env['claim.configuration'].create({
            'name': 'Test Claim Type',
            'description': 'Test claim configuration',
            'target_model': 'res.partner',
            'is_active': True,
            'approval_workflow': 'single_approver',
        })
        
        # Create field mappings
        self.field_mapping1 = self.env['claim.field.mapping'].create({
            'config_id': self.claim_config.id,
            'claim_field_name': 'email',
            'target_field_name': 'email',
            'field_type': 'char',
            'is_required': True,
            'sequence': 10,
        })
        
        self.field_mapping2 = self.env['claim.field.mapping'].create({
            'config_id': self.claim_config.id,
            'claim_field_name': 'phone',
            'target_field_name': 'phone',
            'field_type': 'char',
            'is_required': False,
            'sequence': 20,
        })
        
        # Create document requirements
        self.doc_requirement = self.env['claim.document.requirement'].create({
            'config_id': self.claim_config.id,
            'document_type': 'Identity Proof',
            'is_mandatory': True,
            'file_formats': 'pdf,jpg,png',
            'max_file_size': 5,
            'description': 'Please upload a valid identity proof',
            'sequence': 10,
        })

    def test_claim_configuration_creation(self):
        """Test claim configuration creation"""
        self.assertEqual(self.claim_config.name, 'Test Claim Type')
        self.assertEqual(self.claim_config.field_count, 2)
        self.assertEqual(self.claim_config.document_count, 1)
        self.assertEqual(self.claim_config.mandatory_document_count, 1)

    def test_field_mapping_validation(self):
        """Test field mapping validation"""
        # Test required field validation
        with self.assertRaises(ValidationError):
            self.env['claim.field.mapping'].create({
                'config_id': self.claim_config.id,
                'claim_field_name': '',  # Empty field name
                'target_field_name': 'test_field',
                'field_type': 'char',
            })

    def test_document_requirement_validation(self):
        """Test document requirement validation"""
        # Test unique document type
        with self.assertRaises(ValidationError):
            self.env['claim.document.requirement'].create({
                'config_id': self.claim_config.id,
                'document_type': 'Identity Proof',  # Duplicate
                'is_mandatory': False,
            })

    def test_claim_request_creation(self):
        """Test claim request creation"""
        claim_request = self.env['claim.request'].create({
            'claim_config_id': self.claim_config.id,
            'partner_id': self.test_partner.id,
            'requester_id': self.test_user.id,
            'field_values': {
                'email': 'newemail@example.com',
                'phone': '+0987654321',
            },
        })
        
        self.assertEqual(claim_request.name, 'New')  # Will be set by sequence
        self.assertEqual(claim_request.state, 'draft')
        self.assertEqual(claim_request.field_count, 2)
        self.assertTrue(claim_request.change_request_id)

    def test_claim_submission(self):
        """Test claim submission"""
        claim_request = self.env['claim.request'].create({
            'claim_config_id': self.claim_config.id,
            'partner_id': self.test_partner.id,
            'requester_id': self.test_user.id,
            'field_values': {
                'email': 'newemail@example.com',
                'phone': '+0987654321',
            },
        })
        
        # Create a document to satisfy mandatory requirement
        self.env['claim.document'].create({
            'claim_id': claim_request.id,
            'document_type': 'Identity Proof',
            'file_name': 'test.pdf',
            'file_content': 'dGVzdCBmaWxlIGNvbnRlbnQ=',  # base64 encoded
            'file_size': 1000,
        })
        
        # Submit the claim
        claim_request.action_submit_claim()
        
        self.assertEqual(claim_request.state, 'submitted')
        self.assertEqual(claim_request.change_request_id.state, 'submitted')

    def test_claim_approval(self):
        """Test claim approval"""
        claim_request = self.env['claim.request'].create({
            'claim_config_id': self.claim_config.id,
            'partner_id': self.test_partner.id,
            'requester_id': self.test_user.id,
            'field_values': {
                'email': 'newemail@example.com',
            },
        })
        
        # Create a document
        self.env['claim.document'].create({
            'claim_id': claim_request.id,
            'document_type': 'Identity Proof',
            'file_name': 'test.pdf',
            'file_content': 'dGVzdCBmaWxlIGNvbnRlbnQ=',
            'file_size': 1000,
        })
        
        # Submit and approve
        claim_request.action_submit_claim()
        claim_request.action_approve_claim()
        
        self.assertEqual(claim_request.state, 'approved')
        self.assertEqual(self.test_partner.email, 'newemail@example.com')

    def test_claim_rejection(self):
        """Test claim rejection"""
        claim_request = self.env['claim.request'].create({
            'claim_config_id': self.claim_config.id,
            'partner_id': self.test_partner.id,
            'requester_id': self.test_user.id,
            'field_values': {
                'email': 'newemail@example.com',
            },
        })
        
        # Create a document
        self.env['claim.document'].create({
            'claim_id': claim_request.id,
            'document_type': 'Identity Proof',
            'file_name': 'test.pdf',
            'file_content': 'dGVzdCBmaWxlIGNvbnRlbnQ=',
            'file_size': 1000,
        })
        
        # Submit and reject
        claim_request.action_submit_claim()
        claim_request.change_request_id.write({
            'rejection_reason': 'Invalid document provided'
        })
        claim_request.action_reject_claim()
        
        self.assertEqual(claim_request.state, 'rejected')
        self.assertEqual(self.test_partner.email, 'test@example.com')  # Original value unchanged

    def test_field_validation(self):
        """Test field validation"""
        field_mapping = self.env['claim.field.mapping'].create({
            'config_id': self.claim_config.id,
            'claim_field_name': 'age',
            'target_field_name': 'age',
            'field_type': 'integer',
            'is_required': True,
            'validation_rules': '{"min_value": 0, "max_value": 120}',
        })
        
        # Test valid value
        errors = field_mapping.validate_field_value(25)
        self.assertEqual(len(errors), 0)
        
        # Test invalid value (negative)
        errors = field_mapping.validate_field_value(-5)
        self.assertGreater(len(errors), 0)
        
        # Test invalid value (too high)
        errors = field_mapping.validate_field_value(150)
        self.assertGreater(len(errors), 0)

    def test_document_validation(self):
        """Test document validation"""
        # Test file size validation
        doc_req = self.env['claim.document.requirement'].create({
            'config_id': self.claim_config.id,
            'document_type': 'Test Document',
            'is_mandatory': True,
            'file_formats': 'pdf',
            'max_file_size': 1,  # 1MB
        })
        
        # Mock file data
        class MockFile:
            def __init__(self, size, filename):
                self.size = size
                self.filename = filename
        
        # Test valid file
        valid_file = MockFile(500000, 'test.pdf')  # 500KB
        errors = doc_req.validate_document_upload(valid_file)
        self.assertEqual(len(errors), 0)
        
        # Test file too large
        large_file = MockFile(2000000, 'test.pdf')  # 2MB
        errors = doc_req.validate_document_upload(large_file)
        self.assertGreater(len(errors), 0)
        
        # Test invalid format
        invalid_file = MockFile(500000, 'test.txt')
        errors = doc_req.validate_document_upload(invalid_file)
        self.assertGreater(len(errors), 0)

    def test_claim_configuration_copy(self):
        """Test claim configuration copy functionality"""
        # Create a copy
        copied_config = self.claim_config.copy()
        
        self.assertNotEqual(copied_config.id, self.claim_config.id)
        self.assertEqual(copied_config.name, 'Test Claim Type (Copy)')
        self.assertFalse(copied_config.is_active)  # Should be inactive by default
        self.assertEqual(copied_config.field_count, 2)
        self.assertEqual(copied_config.document_count, 1)

    def test_claim_request_field_comparison(self):
        """Test field comparison functionality"""
        claim_request = self.env['claim.request'].create({
            'claim_config_id': self.claim_config.id,
            'partner_id': self.test_partner.id,
            'requester_id': self.test_user.id,
            'field_values': {
                'email': 'newemail@example.com',
                'phone': '+0987654321',
            },
        })
        
        comparison_data = claim_request.get_field_comparison_data()
        
        self.assertIn('email', comparison_data)
        self.assertIn('phone', comparison_data)
        self.assertEqual(comparison_data['email']['current'], 'test@example.com')
        self.assertEqual(comparison_data['email']['proposed'], 'newemail@example.com')
        self.assertTrue(comparison_data['email']['changed'])

    def test_claim_document_creation(self):
        """Test claim document creation"""
        claim_request = self.env['claim.request'].create({
            'claim_config_id': self.claim_config.id,
            'partner_id': self.test_partner.id,
            'requester_id': self.test_user.id,
            'field_values': {'email': 'test@example.com'},
        })
        
        document = self.env['claim.document'].create({
            'claim_id': claim_request.id,
            'document_type': 'Identity Proof',
            'file_name': 'test.pdf',
            'file_content': 'dGVzdCBmaWxlIGNvbnRlbnQ=',
            'file_size': 1000,
        })
        
        self.assertEqual(document.file_size_mb, 0.0)  # 1000 bytes = ~0.001 MB
        self.assertEqual(document.file_extension, 'pdf')
        self.assertTrue(document.is_mandatory)
        self.assertIn('Identity Proof', document.display_name)

    def test_change_request_extension(self):
        """Test change request extension for claims"""
        claim_request = self.env['claim.request'].create({
            'claim_config_id': self.claim_config.id,
            'partner_id': self.test_partner.id,
            'requester_id': self.test_user.id,
            'field_values': {'email': 'test@example.com'},
        })
        
        change_request = claim_request.change_request_id
        
        self.assertTrue(change_request.is_claim_based)
        self.assertEqual(change_request.claim_type_name, 'Test Claim Type')
        self.assertEqual(change_request.claim_field_count, 1)
        self.assertEqual(change_request.claim_document_count, 0)
