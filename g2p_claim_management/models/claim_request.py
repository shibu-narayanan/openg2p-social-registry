# Part of OpenG2P. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import json
import logging

_logger = logging.getLogger(__name__)


class ClaimRequest(models.Model):
    _name = "claim.request"
    _description = "Claim Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        "Claim Number",
        required=True,
        default="New",
        tracking=True,
        help="Unique identifier for the claim request"
    )
    claim_config_id = fields.Many2one(
        "claim.configuration",
        string="Claim Type",
        required=True,
        tracking=True,
        help="Type of claim being requested"
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Registrant",
        required=True,
        tracking=True,
        help="The registrant for whom the claim is being made"
    )
    requester_id = fields.Many2one(
        "res.users",
        string="Requester",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        help="User who submitted the claim"
    )

    # CR Integration - No separate state management
    change_request_id = fields.Many2one(
        "change.request",
        string="Change Request",
        required=True,
        readonly=True,
        tracking=True,
        help="Associated Change Request for approval workflow (auto-created)"
    )

    # Claim data
    field_values = fields.Json(
        "Field Values",
        help="JSON field containing the new values for the claim"
    )
    documents = fields.One2many(
        "claim.document",
        "claim_id",
        string="Documents",
        help="Documents uploaded with this claim"
    )

    # Computed fields from CR
    state = fields.Selection(
        related="change_request_id.state",
        store=True,
        tracking=True,
        help="Current state of the claim (inherited from Change Request)"
    )
    approver_id = fields.Many2one(
        related="change_request_id.approver_id",
        store=True,
        tracking=True,
        help="User responsible for approving this claim"
    )
    rejection_reason = fields.Text(
        related="change_request_id.rejection_reason",
        store=True,
        help="Reason for rejection if claim was rejected"
    )
    description = fields.Text(
        related="change_request_id.description",
        store=True,
        help="Description of the claim from the Change Request"
    )

    # Computed fields
    claim_type_name = fields.Char(
        "Claim Type",
        related="claim_config_id.name",
        store=True,
        help="Name of the claim type"
    )
    registrant_name = fields.Char(
        "Registrant Name",
        related="partner_id.name",
        store=True,
        help="Name of the registrant"
    )
    requester_name = fields.Char(
        "Requester Name",
        related="requester_id.name",
        store=True,
        help="Name of the requester"
    )
    document_count = fields.Integer(
        "Document Count",
        compute="_compute_document_count",
        store=True,
        help="Number of documents uploaded with this claim"
    )
    mandatory_documents_uploaded = fields.Boolean(
        "Mandatory Documents Uploaded",
        compute="_compute_mandatory_documents_uploaded",
        store=True,
        help="Whether all mandatory documents have been uploaded"
    )
    field_count = fields.Integer(
        "Field Count",
        compute="_compute_field_count",
        store=True,
        help="Number of fields being updated in this claim"
    )

    @api.depends("documents")
    def _compute_document_count(self):
        for record in self:
            record.document_count = len(record.documents)

    @api.depends("documents.document_type", "claim_config_id.document_requirements")
    def _compute_mandatory_documents_uploaded(self):
        for record in self:
            if not record.claim_config_id:
                record.mandatory_documents_uploaded = False
                continue

            mandatory_doc_types = record.claim_config_id.get_mandatory_documents().mapped("document_type")
            uploaded_doc_types = record.documents.mapped("document_type")
            
            record.mandatory_documents_uploaded = all(
                doc_type in uploaded_doc_types for doc_type in mandatory_doc_types
            )

    @api.depends("field_values")
    def _compute_field_count(self):
        for record in self:
            if record.field_values:
                record.field_count = len(record.field_values)
            else:
                record.field_count = 0

    @api.model
    def create(self, vals):
        """Override create to generate claim number and create Change Request"""
        if vals.get("name", "New") == "New":
            vals["name"] = self.env["ir.sequence"].next_by_code("claim.request") or "New"

        # Create Change Request first
        cr_vals = {
            "name": vals["name"],
            "type": "modify",
            "partner_id": vals.get("partner_id"),
            "requester_id": vals.get("requester_id", self.env.user.id),
            "state": "draft",
            "description": _("Claim: %s") % (vals.get("claim_config_id") and self.env["claim.configuration"].browse(vals["claim_config_id"]).name or "Unknown"),
        }
        change_request = self.env["change.request"].create(cr_vals)
        vals["change_request_id"] = change_request.id

        return super().create(vals)

    @api.constrains("field_values")
    def _check_field_values(self):
        for record in self:
            if record.field_values and record.claim_config_id:
                # Validate field values against configuration
                errors = []
                for field_name, value in record.field_values.items():
                    field_mapping = record.claim_config_id.get_field_mapping_by_name(field_name)
                    if field_mapping:
                        field_errors = field_mapping.validate_field_value(value)
                        errors.extend(field_errors)
                    else:
                        errors.append(_("Unknown field '%s' in claim data.") % field_name)

                if errors:
                    raise ValidationError("\n".join(errors))

    @api.constrains("documents")
    def _check_documents(self):
        for record in self:
            if record.documents and record.claim_config_id:
                # Validate documents against requirements
                doc_requirements = record.claim_config_id.document_requirements
                for doc in record.documents:
                    doc_req = doc_requirements.filtered(lambda r: r.document_type == doc.document_type)
                    if doc_req:
                        validation_errors = doc_req.validate_document_upload(doc)
                        if validation_errors:
                            raise ValidationError(
                                _("Document validation error: %s") % "\n".join(validation_errors)
                            )

    def action_submit_claim(self):
        """Submit the claim for approval"""
        self.ensure_one()
        
        if self.state != "draft":
            raise UserError(_("Only draft claims can be submitted."))

        # Validate claim data
        self._validate_claim_submission()

        # Update Change Request with claim data
        self._update_change_request_with_claim_data()

        # Submit the Change Request
        self.change_request_id.action_submit()

        # Log activity
        self.message_post(
            body=_("Claim submitted for approval."),
            message_type="notification"
        )

        return True

    def _validate_claim_submission(self):
        """Validate claim before submission"""
        self.ensure_one()
        errors = []

        # Check if claim configuration is active
        if not self.claim_config_id.is_active:
            errors.append(_("Claim type '%s' is no longer active.") % self.claim_config_id.name)

        # Validate field values
        if not self.field_values:
            errors.append(_("No field values provided for the claim."))

        # Validate mandatory documents
        if not self.mandatory_documents_uploaded:
            missing_docs = []
            mandatory_doc_types = self.claim_config_id.get_mandatory_documents().mapped("document_type")
            uploaded_doc_types = self.documents.mapped("document_type")
            
            for doc_type in mandatory_doc_types:
                if doc_type not in uploaded_doc_types:
                    missing_docs.append(doc_type)
            
            if missing_docs:
                errors.append(_("Missing mandatory documents: %s") % ", ".join(missing_docs))

        if errors:
            raise ValidationError("\n".join(errors))

    def _update_change_request_with_claim_data(self):
        """Update the Change Request with claim-specific data"""
        self.ensure_one()
        
        # Prepare change data for the CR
        change_data = {}
        for field_name, value in self.field_values.items():
            field_mapping = self.claim_config_id.get_field_mapping_by_name(field_name)
            if field_mapping:
                change_data[field_mapping.target_field_name] = value

        # Update the Change Request
        self.change_request_id.write({
            "description": _("Claim: %s for %s") % (self.claim_config_id.name, self.partner_id.name),
        })

        # Attach documents to Change Request
        for doc in self.documents:
            if doc.file_content:
                attachment = self.env["ir.attachment"].create({
                    "name": doc.file_name,
                    "type": "binary",
                    "datas": doc.file_content,
                    "res_model": "change.request",
                    "res_id": self.change_request_id.id,
                    "mimetype": doc.mimetype or "application/octet-stream",
                })

    def action_approve_claim(self):
        """Approve the claim (called from Change Request)"""
        self.ensure_one()
        
        if self.state != "submitted":
            raise UserError(_("Only submitted claims can be approved."))

        # Apply changes to the registrant
        self._apply_claim_changes()

        # Log activity
        self.message_post(
            body=_("Claim approved and changes applied to registrant."),
            message_type="notification"
        )

        return True

    def action_reject_claim(self):
        """Reject the claim (called from Change Request)"""
        self.ensure_one()
        
        if self.state not in ["submitted", "draft"]:
            raise UserError(_("Only submitted or draft claims can be rejected."))

        # Log activity
        self.message_post(
            body=_("Claim rejected. Reason: %s") % (self.rejection_reason or _("No reason provided")),
            message_type="notification"
        )

        return True

    def action_view_change_request(self):
        """Open the related Change Request"""
        self.ensure_one()
        
        return {
            "type": "ir.actions.act_window",
            "name": _("Change Request"),
            "res_model": "change.request",
            "res_id": self.change_request_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def _apply_claim_changes(self):
        """Apply the claim changes to the target registrant"""
        self.ensure_one()
        
        if not self.field_values:
            return

        # Prepare update data
        update_data = {}
        for field_name, value in self.field_values.items():
            field_mapping = self.claim_config_id.get_field_mapping_by_name(field_name)
            if field_mapping:
                update_data[field_mapping.target_field_name] = value

        # Update the registrant
        if update_data:
            self.partner_id.write(update_data)
            _logger.info(
                "Applied claim changes to registrant %s: %s",
                self.partner_id.name,
                update_data
            )

    def get_field_comparison_data(self):
        """Get field comparison data for display"""
        self.ensure_one()
        comparison_data = {}
        
        if not self.field_values:
            return comparison_data

        for field_name, new_value in self.field_values.items():
            field_mapping = self.claim_config_id.get_field_mapping_by_name(field_name)
            if field_mapping:
                current_value = getattr(self.partner_id, field_mapping.target_field_name, "")
                comparison_data[field_name] = {
                    "label": field_mapping.field_label,
                    "current": current_value,
                    "proposed": new_value,
                    "changed": str(current_value) != str(new_value),
                }

        return comparison_data

    def get_document_summary(self):
        """Get document summary for display"""
        self.ensure_one()
        summary = {
            "total": len(self.documents),
            "mandatory": 0,
            "optional": 0,
            "uploaded": [],
            "missing": [],
        }

        # Count uploaded documents
        for doc in self.documents:
            summary["uploaded"].append({
                "type": doc.document_type,
                "name": doc.file_name,
                "size": doc.file_size_mb,
                "is_mandatory": doc.is_mandatory,
            })
            if doc.is_mandatory:
                summary["mandatory"] += 1
            else:
                summary["optional"] += 1

        # Check for missing mandatory documents
        if self.claim_config_id:
            mandatory_doc_types = self.claim_config_id.get_mandatory_documents().mapped("document_type")
            uploaded_doc_types = [doc["type"] for doc in summary["uploaded"]]
            
            for doc_type in mandatory_doc_types:
                if doc_type not in uploaded_doc_types:
                    summary["missing"].append(doc_type)

        return summary

    def copy(self, default=None):
        """Override copy to create new Change Request"""
        default = default or {}
        default.update({
            "name": "New",
            "state": "draft",
            "change_request_id": False,  # Will be created in create method
        })
        return super().copy(default)

    def unlink(self):
        """Override unlink to also delete associated Change Request"""
        for record in self:
            if record.change_request_id:
                record.change_request_id.unlink()
        return super().unlink()

    @api.model
    def get_my_claims(self, user_id=None):
        """Get claims for a specific user"""
        if not user_id:
            user_id = self.env.user.id
        
        return self.search([
            ("requester_id", "=", user_id)
        ], order="create_date desc")

    @api.model
    def get_claims_for_approval(self, user_id=None):
        """Get claims pending approval for a specific user"""
        if not user_id:
            user_id = self.env.user.id
        
        return self.search([
            ("state", "=", "submitted"),
            ("approver_id", "=", user_id)
        ], order="create_date desc")