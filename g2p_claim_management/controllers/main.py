# Part of OpenG2P. See LICENSE file for full copyright and licensing details.

import json
import base64
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import ValidationError, AccessError


class ClaimManagementController(http.Controller):

    @http.route('/claim/configuration/list', type='json', auth='user', methods=['POST'])
    def get_claim_configurations(self, **kwargs):
        """Get list of active claim configurations"""
        try:
            configurations = request.env['claim.configuration'].search([
                ('is_active', '=', True)
            ])
            
            result = []
            for config in configurations:
                result.append({
                    'id': config.id,
                    'name': config.name,
                    'description': config.description,
                    'target_model': config.target_model,
                    'approval_workflow': config.approval_workflow,
                    'field_count': config.field_count,
                    'document_count': config.document_count,
                    'mandatory_document_count': config.mandatory_document_count,
                })
            
            return {
                'success': True,
                'data': result,
                'message': _('Claim configurations retrieved successfully')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': _('Error retrieving claim configurations')
            }

    @http.route('/claim/configuration/<int:config_id>/fields', type='json', auth='user', methods=['POST'])
    def get_claim_configuration_fields(self, config_id, **kwargs):
        """Get field definitions for a claim configuration"""
        try:
            config = request.env['claim.configuration'].browse(config_id)
            if not config.exists():
                return {
                    'success': False,
                    'error': 'Configuration not found',
                    'message': _('Claim configuration not found')
                }
            
            field_definitions = []
            for field_mapping in config.field_mappings.sorted('sequence'):
                field_definitions.append(field_mapping.get_field_definition())
            
            return {
                'success': True,
                'data': field_definitions,
                'message': _('Field definitions retrieved successfully')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': _('Error retrieving field definitions')
            }

    @http.route('/claim/configuration/<int:config_id>/documents', type='json', auth='user', methods=['POST'])
    def get_claim_configuration_documents(self, config_id, **kwargs):
        """Get document requirements for a claim configuration"""
        try:
            config = request.env['claim.configuration'].browse(config_id)
            if not config.exists():
                return {
                    'success': False,
                    'error': 'Configuration not found',
                    'message': _('Claim configuration not found')
                }
            
            document_requirements = []
            for doc_req in config.document_requirements.sorted('sequence'):
                document_requirements.append(doc_req.get_document_requirement_dict())
            
            return {
                'success': True,
                'data': document_requirements,
                'message': _('Document requirements retrieved successfully')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': _('Error retrieving document requirements')
            }

    @http.route('/claim/submit', type='json', auth='user', methods=['POST'])
    def submit_claim(self, **kwargs):
        """Submit a new claim"""
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            
            # Validate required fields
            required_fields = ['claim_config_id', 'partner_id', 'field_values']
            for field in required_fields:
                if field not in data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}',
                        'message': _('Missing required field: %s') % field
                    }
            
            # Create claim request
            claim_vals = {
                'claim_config_id': data['claim_config_id'],
                'partner_id': data['partner_id'],
                'requester_id': request.env.user.id,
                'field_values': data['field_values'],
            }
            
            claim_request = request.env['claim.request'].create(claim_vals)
            
            # Create documents if provided
            if 'documents' in data:
                for doc_data in data['documents']:
                    if doc_data.get('file_content'):
                        request.env['claim.document'].create({
                            'claim_id': claim_request.id,
                            'document_type': doc_data.get('document_type'),
                            'file_name': doc_data.get('file_name', 'Unknown'),
                            'file_content': doc_data.get('file_content'),
                            'file_size': doc_data.get('file_size', 0),
                            'mimetype': doc_data.get('mimetype', 'application/octet-stream'),
                        })
            
            # Submit the claim
            claim_request.action_submit_claim()
            
            return {
                'success': True,
                'data': {
                    'claim_id': claim_request.id,
                    'claim_number': claim_request.name,
                    'state': claim_request.state,
                },
                'message': _('Claim submitted successfully')
            }
        except ValidationError as e:
            return {
                'success': False,
                'error': str(e),
                'message': _('Validation error: %s') % str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': _('Error submitting claim')
            }

    @http.route('/claim/<int:claim_id>/status', type='json', auth='user', methods=['POST'])
    def get_claim_status(self, claim_id, **kwargs):
        """Get claim status and details"""
        try:
            claim = request.env['claim.request'].browse(claim_id)
            if not claim.exists():
                return {
                    'success': False,
                    'error': 'Claim not found',
                    'message': _('Claim not found')
                }
            
            # Check access rights
            if not self._can_access_claim(claim):
                return {
                    'success': False,
                    'error': 'Access denied',
                    'message': _('You do not have access to this claim')
                }
            
            return {
                'success': True,
                'data': {
                    'id': claim.id,
                    'name': claim.name,
                    'claim_type': claim.claim_type_name,
                    'registrant': claim.registrant_name,
                    'requester': claim.requester_name,
                    'state': claim.state,
                    'create_date': claim.create_date.isoformat() if claim.create_date else None,
                    'write_date': claim.write_date.isoformat() if claim.write_date else None,
                    'approver': claim.approver_id.name if claim.approver_id else None,
                    'description': claim.description,
                    'rejection_reason': claim.rejection_reason,
                    'field_count': claim.field_count,
                    'document_count': claim.document_count,
                    'mandatory_documents_uploaded': claim.mandatory_documents_uploaded,
                },
                'message': _('Claim status retrieved successfully')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': _('Error retrieving claim status')
            }

    @http.route('/claim/my-claims', type='json', auth='user', methods=['POST'])
    def get_my_claims(self, **kwargs):
        """Get user's claims"""
        try:
            data = json.loads(request.httprequest.data.decode('utf-8')) if request.httprequest.data else {}
            limit = data.get('limit', 50)
            offset = data.get('offset', 0)
            
            claims = request.env['claim.request'].search([
                ('requester_id', '=', request.env.user.id)
            ], limit=limit, offset=offset, order='create_date desc')
            
            result = []
            for claim in claims:
                result.append({
                    'id': claim.id,
                    'name': claim.name,
                    'claim_type': claim.claim_type_name,
                    'registrant': claim.registrant_name,
                    'state': claim.state,
                    'create_date': claim.create_date.isoformat() if claim.create_date else None,
                    'field_count': claim.field_count,
                    'document_count': claim.document_count,
                })
            
            return {
                'success': True,
                'data': result,
                'message': _('Claims retrieved successfully')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': _('Error retrieving claims')
            }

    @http.route('/claim/upload-document', type='json', auth='user', methods=['POST'])
    def upload_document(self, **kwargs):
        """Upload document for a claim"""
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            
            # Validate required fields
            required_fields = ['claim_id', 'document_type', 'file_content']
            for field in required_fields:
                if field not in data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}',
                        'message': _('Missing required field: %s') % field
                    }
            
            claim = request.env['claim.request'].browse(data['claim_id'])
            if not claim.exists():
                return {
                    'success': False,
                    'error': 'Claim not found',
                    'message': _('Claim not found')
                }
            
            # Check access rights
            if not self._can_access_claim(claim):
                return {
                    'success': False,
                    'error': 'Access denied',
                    'message': _('You do not have access to this claim')
                }
            
            # Create document
            document = request.env['claim.document'].create_from_upload(
                claim_id=data['claim_id'],
                document_type=data['document_type'],
                file_name=data.get('file_name', 'Unknown'),
                file_content=data['file_content'],
                file_size=data.get('file_size', 0),
                mimetype=data.get('mimetype', 'application/octet-stream'),
            )
            
            return {
                'success': True,
                'data': {
                    'document_id': document.id,
                    'file_name': document.file_name,
                    'file_size': document.file_size_mb,
                    'document_type': document.document_type,
                },
                'message': _('Document uploaded successfully')
            }
        except ValidationError as e:
            return {
                'success': False,
                'error': str(e),
                'message': _('Validation error: %s') % str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': _('Error uploading document')
            }

    @http.route('/claim/<int:claim_id>/documents', type='json', auth='user', methods=['POST'])
    def get_claim_documents(self, claim_id, **kwargs):
        """Get documents for a claim"""
        try:
            claim = request.env['claim.request'].browse(claim_id)
            if not claim.exists():
                return {
                    'success': False,
                    'error': 'Claim not found',
                    'message': _('Claim not found')
                }
            
            # Check access rights
            if not self._can_access_claim(claim):
                return {
                    'success': False,
                    'error': 'Access denied',
                    'message': _('You do not have access to this claim')
                }
            
            documents = []
            for doc in claim.documents:
                documents.append(doc.get_file_info())
            
            return {
                'success': True,
                'data': documents,
                'message': _('Documents retrieved successfully')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': _('Error retrieving documents')
            }

    def _can_access_claim(self, claim):
        """Check if current user can access the claim"""
        user = request.env.user
        
        # User can access their own claims
        if claim.requester_id == user:
            return True
        
        # Approver can access claims assigned to them
        if claim.approver_id == user:
            return True
        
        # Manager can access all claims
        if user.has_group('g2p_claim_management.group_claim_manager'):
            return True
        
        return False

    @http.route('/claim/partner/<int:partner_id>/current-values', type='json', auth='user', methods=['POST'])
    def get_partner_current_values(self, partner_id, **kwargs):
        """Get current field values for a partner"""
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            config_id = data.get('config_id')
            
            if not config_id:
                return {
                    'success': False,
                    'error': 'Missing config_id',
                    'message': _('Configuration ID is required')
                }
            
            partner = request.env['res.partner'].browse(partner_id)
            if not partner.exists():
                return {
                    'success': False,
                    'error': 'Partner not found',
                    'message': _('Partner not found')
                }
            
            config = request.env['claim.configuration'].browse(config_id)
            if not config.exists():
                return {
                    'success': False,
                    'error': 'Configuration not found',
                    'message': _('Configuration not found')
                }
            
            current_values = {}
            for field_mapping in config.field_mappings:
                try:
                    current_value = getattr(partner, field_mapping.target_field_name, "")
                    current_values[field_mapping.claim_field_name] = current_value
                except Exception:
                    current_values[field_mapping.claim_field_name] = ""
            
            return {
                'success': True,
                'data': current_values,
                'message': _('Current values retrieved successfully')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': _('Error retrieving current values')
            }