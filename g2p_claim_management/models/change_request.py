# Part of OpenG2P. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ChangeRequest(models.Model):
    _inherit = "change.request"

    # Claim-specific fields
    claim_request_id = fields.One2many(
        "claim.request",
        "change_request_id",
        string="Claim Request",
        help="Associated claim request (if this CR was created from a claim)"
    )
    is_claim_based = fields.Boolean(
        "Is Claim Based",
        compute="_compute_is_claim_based",
        store=True,
        help="Whether this Change Request was created from a claim"
    )
    claim_type_name = fields.Char(
        "Claim Type",
        related="claim_request_id.claim_config_id.name",
        store=True,
        help="Type of claim that created this Change Request"
    )
    claim_requester_name = fields.Char(
        "Claim Requester",
        related="claim_request_id.requester_id.name",
        store=True,
        help="User who submitted the claim"
    )

    # Computed fields for claim information
    claim_field_count = fields.Integer(
        "Claim Fields",
        compute="_compute_claim_info",
        store=True,
        help="Number of fields being updated in the claim"
    )
    claim_document_count = fields.Integer(
        "Claim Documents",
        compute="_compute_claim_info",
        store=True,
        help="Number of documents uploaded with the claim"
    )
    claim_mandatory_docs_uploaded = fields.Boolean(
        "Mandatory Docs Uploaded",
        compute="_compute_claim_info",
        store=True,
        help="Whether all mandatory documents have been uploaded"
    )

    @api.depends("claim_request_id")
    def _compute_is_claim_based(self):
        for record in self:
            record.is_claim_based = bool(record.claim_request_id)

    @api.depends("claim_request_id.field_count", "claim_request_id.document_count", "claim_request_id.mandatory_documents_uploaded")
    def _compute_claim_info(self):
        for record in self:
            if record.claim_request_id:
                claim = record.claim_request_id[0]  # Should only be one
                record.claim_field_count = claim.field_count
                record.claim_document_count = claim.document_count
                record.claim_mandatory_docs_uploaded = claim.mandatory_documents_uploaded
            else:
                record.claim_field_count = 0
                record.claim_document_count = 0
                record.claim_mandatory_docs_uploaded = False

    def action_approve(self):
        """Override approve to handle claim-specific logic"""
        result = super().action_approve()
        
        # If this is a claim-based CR, approve the associated claim
        for record in self:
            if record.is_claim_based and record.claim_request_id:
                record.claim_request_id.action_approve_claim()
        
        return result

    def action_reject(self):
        """Override reject to handle claim-specific logic"""
        result = super().action_reject()
        
        # If this is a claim-based CR, reject the associated claim
        for record in self:
            if record.is_claim_based and record.claim_request_id:
                record.claim_request_id.action_reject_claim()
        
        return result

    def get_claim_field_comparison(self):
        """Get field comparison data for claim-based CRs"""
        self.ensure_one()
        if not self.is_claim_based or not self.claim_request_id:
            return {}
        
        return self.claim_request_id[0].get_field_comparison_data()

    def get_claim_document_summary(self):
        """Get document summary for claim-based CRs"""
        self.ensure_one()
        if not self.is_claim_based or not self.claim_request_id:
            return {}
        
        return self.claim_request_id[0].get_document_summary()

    def action_view_claim_request(self):
        """Action to view the associated claim request"""
        self.ensure_one()
        if not self.is_claim_based or not self.claim_request_id:
            return False
        
        claim = self.claim_request_id[0]
        return {
            "name": _("Claim Request - %s") % claim.name,
            "type": "ir.actions.act_window",
            "res_model": "claim.request",
            "res_id": claim.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_claim_documents(self):
        """Action to view claim documents"""
        self.ensure_one()
        if not self.is_claim_based or not self.claim_request_id:
            return False
        
        claim = self.claim_request_id[0]
        return {
            "name": _("Claim Documents - %s") % claim.name,
            "type": "ir.actions.act_window",
            "res_model": "claim.document",
            "view_mode": "tree,form",
            "domain": [("claim_id", "=", claim.id)],
            "context": {
                "default_claim_id": claim.id,
                "search_default_claim_id": claim.id,
            },
        }

    def get_claim_approval_context(self):
        """Get context information for claim approval"""
        self.ensure_one()
        if not self.is_claim_based or not self.claim_request_id:
            return {}
        
        claim = self.claim_request_id[0]
        return {
            "claim_type": claim.claim_type_name,
            "registrant": claim.registrant_name,
            "requester": claim.requester_name,
            "field_comparison": self.get_claim_field_comparison(),
            "document_summary": self.get_claim_document_summary(),
            "create_date": claim.create_date,
            "description": claim.claim_config_id.description,
        }

    @api.model
    def get_claim_based_crs(self, user_id=None):
        """Get claim-based Change Requests for a specific user"""
        if not user_id:
            user_id = self.env.user.id
        
        return self.search([
            ("is_claim_based", "=", True),
            ("approver_id", "=", user_id),
            ("state", "=", "submitted")
        ], order="create_date desc")

    def _get_claim_approval_buttons(self):
        """Get additional buttons for claim approval interface"""
        self.ensure_one()
        buttons = []
        
        if self.is_claim_based:
            buttons.extend([
                {
                    "name": "view_claim_request",
                    "string": _("View Claim"),
                    "type": "object",
                    "class": "btn-primary",
                },
                {
                    "name": "view_claim_documents",
                    "string": _("View Documents"),
                    "type": "object",
                    "class": "btn-info",
                }
            ])
        
        return buttons