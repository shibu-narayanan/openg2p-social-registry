# Part of OpenG2P. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import json


class ClaimSubmissionWizard(models.TransientModel):
    _name = "claim.submission.wizard"
    _description = "Claim Submission Wizard"

    claim_config_id = fields.Many2one(
        "claim.configuration",
        string="Claim Type",
        required=True,
        help="Type of claim to submit"
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Registrant",
        required=True,
        help="The registrant for whom the claim is being made"
    )
    requester_id = fields.Many2one(
        "res.users",
        string="Requester",
        required=True,
        default=lambda self: self.env.user,
        help="User submitting the claim"
    )

    # Dynamic field values
    field_values = fields.Json(
        "Field Values",
        help="JSON field containing the new values for the claim"
    )

    # Document uploads
    document_uploads = fields.Json(
        "Document Uploads",
        help="JSON field containing uploaded document data"
    )

    # Computed fields
    field_mappings = fields.Many2many(
        "claim.field.mapping",
        string="Field Mappings",
        compute="_compute_field_mappings",
        help="Field mappings for the selected claim type"
    )
    document_requirements = fields.Many2many(
        "claim.document.requirement",
        string="Document Requirements",
        compute="_compute_document_requirements",
        help="Document requirements for the selected claim type"
    )
    mandatory_documents = fields.Many2many(
        "claim.document.requirement",
        string="Mandatory Documents",
        compute="_compute_mandatory_documents",
        help="Mandatory document requirements"
    )
    optional_documents = fields.Many2many(
        "claim.document.requirement",
        string="Optional Documents",
        compute="_compute_optional_documents",
        help="Optional document requirements"
    )

    @api.depends("claim_config_id")
    def _compute_field_mappings(self):
        for record in self:
            if record.claim_config_id:
                record.field_mappings = record.claim_config_id.field_mappings
            else:
                record.field_mappings = False

    @api.depends("claim_config_id")
    def _compute_document_requirements(self):
        for record in self:
            if record.claim_config_id:
                record.document_requirements = record.claim_config_id.document_requirements
            else:
                record.document_requirements = False

    @api.depends("document_requirements")
    def _compute_mandatory_documents(self):
        for record in self:
            record.mandatory_documents = record.document_requirements.filtered("is_mandatory")

    @api.depends("document_requirements")
    def _compute_optional_documents(self):
        for record in self:
            record.optional_documents = record.document_requirements.filtered(lambda r: not r.is_mandatory)

    @api.onchange("claim_config_id")
    def _onchange_claim_config_id(self):
        """Reset field values when claim type changes"""
        self.field_values = {}
        self.document_uploads = {}

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        """Load current field values when partner changes"""
        if self.partner_id and self.claim_config_id:
            self._load_current_field_values()

    def _load_current_field_values(self):
        """Load current field values from the partner"""
        self.ensure_one()
        if not self.partner_id or not self.claim_config_id:
            return

        current_values = {}
        for field_mapping in self.field_mappings:
            try:
                current_value = getattr(self.partner_id, field_mapping.target_field_name, "")
                current_values[field_mapping.claim_field_name] = current_value
            except Exception:
                current_values[field_mapping.claim_field_name] = ""

        self.field_values = current_values

    def action_load_current_values(self):
        """Action to load current field values"""
        self._load_current_field_values()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("Current field values have been loaded."),
                "type": "success",
            }
        }

    def action_validate_claim(self):
        """Validate the claim data before submission"""
        self.ensure_one()
        errors = []

        # Validate field values
        if not self.field_values:
            errors.append(_("No field values provided."))

        # Validate required fields
        for field_mapping in self.field_mappings.filtered("is_required"):
            if field_mapping.claim_field_name not in self.field_values or not self.field_values[field_mapping.claim_field_name]:
                errors.append(_("Field '%s' is required.") % field_mapping.field_label)

        # Validate field values against mapping rules
        for field_name, value in self.field_values.items():
            field_mapping = self.field_mappings.filtered(lambda r: r.claim_field_name == field_name)
            if field_mapping:
                field_errors = field_mapping.validate_field_value(value)
                errors.extend(field_errors)

        # Validate mandatory documents
        if not self.document_uploads:
            self.document_uploads = {}

        uploaded_doc_types = list(self.document_uploads.keys())
        for doc_req in self.mandatory_documents:
            if doc_req.document_type not in uploaded_doc_types:
                errors.append(_("Mandatory document '%s' is required.") % doc_req.document_type)

        if errors:
            raise ValidationError("\n".join(errors))

        return True

    def action_submit_claim(self):
        """Submit the claim"""
        self.ensure_one()

        # Validate claim data
        self.action_validate_claim()

        # Create claim request
        claim_vals = {
            "claim_config_id": self.claim_config_id.id,
            "partner_id": self.partner_id.id,
            "requester_id": self.requester_id.id,
            "field_values": self.field_values,
        }

        claim_request = self.env["claim.request"].create(claim_vals)

        # Create documents
        if self.document_uploads:
            for doc_type, doc_data in self.document_uploads.items():
                if doc_data.get("file_content"):
                    self.env["claim.document"].create({
                        "claim_id": claim_request.id,
                        "document_type": doc_type,
                        "file_name": doc_data.get("file_name", "Unknown"),
                        "file_content": doc_data.get("file_content"),
                        "file_size": doc_data.get("file_size", 0),
                        "mimetype": doc_data.get("mimetype", "application/octet-stream"),
                    })

        # Submit the claim
        claim_request.action_submit_claim()

        return {
            "type": "ir.actions.act_window",
            "res_model": "claim.request",
            "res_id": claim_request.id,
            "view_mode": "form",
            "target": "current",
            "context": {"form_view_initial_mode": "readonly"},
        }

    def get_field_definitions(self):
        """Get field definitions for dynamic form generation"""
        self.ensure_one()
        field_defs = []
        
        for field_mapping in self.field_mappings.sorted("sequence"):
            field_def = field_mapping.get_field_definition()
            
            # Add current value
            if self.field_values and field_mapping.claim_field_name in self.field_values:
                field_def["value"] = self.field_values[field_mapping.claim_field_name]
            else:
                field_def["value"] = field_mapping.default_value or ""
            
            field_defs.append(field_def)
        
        return field_defs

    def get_document_requirements_info(self):
        """Get document requirements information"""
        self.ensure_one()
        requirements = []
        
        for doc_req in self.document_requirements.sorted("sequence"):
            req_info = doc_req.get_document_requirement_dict()
            
            # Add upload status
            req_info["uploaded"] = doc_req.document_type in (self.document_uploads or {})
            if req_info["uploaded"]:
                req_info["upload_info"] = self.document_uploads[doc_req.document_type]
            
            requirements.append(req_info)
        
        return requirements

    def get_claim_summary(self):
        """Get claim summary for preview"""
        self.ensure_one()
        summary = {
            "claim_type": self.claim_config_id.name,
            "registrant": self.partner_id.name,
            "requester": self.requester_id.name,
            "field_count": len(self.field_values or {}),
            "document_count": len(self.document_uploads or {}),
            "mandatory_docs_uploaded": True,
        }

        # Check mandatory documents
        if self.mandatory_documents:
            uploaded_doc_types = list(self.document_uploads.keys()) if self.document_uploads else []
            missing_docs = []
            for doc_req in self.mandatory_documents:
                if doc_req.document_type not in uploaded_doc_types:
                    missing_docs.append(doc_req.document_type)
            
            summary["mandatory_docs_uploaded"] = len(missing_docs) == 0
            summary["missing_docs"] = missing_docs

        return summary

    def action_preview_claim(self):
        """Preview the claim before submission"""
        self.ensure_one()
        
        summary = self.get_claim_summary()
        
        return {
            "type": "ir.actions.client",
            "tag": "claim_preview_dialog",
            "params": {
                "title": _("Claim Preview"),
                "summary": summary,
                "field_definitions": self.get_field_definitions(),
                "document_requirements": self.get_document_requirements_info(),
            }
        }