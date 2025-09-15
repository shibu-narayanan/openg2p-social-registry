# Part of OpenG2P. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ClaimConfiguration(models.Model):
    _name = "claim.configuration"
    _description = "Claim Configuration"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"

    name = fields.Char(
        "Claim Type Name",
        required=True,
        tracking=True,
        help="Name of the claim type (e.g., 'Education Update', 'Contact Information Update')"
    )
    description = fields.Text(
        "Description",
        tracking=True,
        help="Detailed description of what this claim type covers"
    )
    target_model = fields.Selection(
        [
            ("res.partner", "Registrant"),
        ],
        string="Target Model",
        required=True,
        default="res.partner",
        tracking=True,
        help="The model that this claim type targets for updates"
    )
    is_active = fields.Boolean(
        "Active",
        default=True,
        tracking=True,
        help="If unchecked, this claim type will not be available for new claims"
    )
    sequence = fields.Integer(
        "Sequence",
        default=10,
        help="Order in which claim types are displayed to users"
    )
    approval_workflow = fields.Selection(
        [
            ("single_approver", "Single Approver"),
            ("multi_approver", "Multiple Approvers"),
            ("auto_approve", "Auto Approve"),
        ],
        string="Approval Workflow",
        required=True,
        default="single_approver",
        tracking=True,
        help="Type of approval workflow for this claim type"
    )

    # Related fields
    field_mappings = fields.One2many(
        "claim.field.mapping",
        "config_id",
        string="Field Mappings",
        help="Field mappings that define which fields can be updated in this claim type"
    )
    document_requirements = fields.One2many(
        "claim.document.requirement",
        "config_id",
        string="Document Requirements",
        help="Document requirements for this claim type"
    )
    claim_requests = fields.One2many(
        "claim.request",
        "claim_config_id",
        string="Claim Requests",
        help="All claim requests of this type"
    )

    # Computed fields
    field_count = fields.Integer(
        "Field Count",
        compute="_compute_field_count",
        store=True,
        help="Number of field mappings configured"
    )
    document_count = fields.Integer(
        "Document Count",
        compute="_compute_document_count",
        store=True,
        help="Number of document requirements configured"
    )
    mandatory_document_count = fields.Integer(
        "Mandatory Documents",
        compute="_compute_mandatory_document_count",
        store=True,
        help="Number of mandatory document requirements"
    )
    claim_request_count = fields.Integer(
        "Claim Requests",
        compute="_compute_claim_request_count",
        help="Number of claim requests of this type"
    )
    active_claim_count = fields.Integer(
        "Active Claims",
        compute="_compute_active_claim_count",
        help="Number of active (pending/submitted) claim requests"
    )

    @api.depends("field_mappings")
    def _compute_field_count(self):
        for record in self:
            record.field_count = len(record.field_mappings)

    @api.depends("document_requirements")
    def _compute_document_count(self):
        for record in self:
            record.document_count = len(record.document_requirements)

    @api.depends("document_requirements.is_mandatory")
    def _compute_mandatory_document_count(self):
        for record in self:
            record.mandatory_document_count = len(record.document_requirements.filtered("is_mandatory"))

    @api.depends("claim_requests")
    def _compute_claim_request_count(self):
        for record in self:
            record.claim_request_count = len(record.claim_requests)

    @api.depends("claim_requests.state")
    def _compute_active_claim_count(self):
        for record in self:
            active_states = ["draft", "submitted"]
            record.active_claim_count = len(record.claim_requests.filtered(
                lambda r: r.state in active_states
            ))

    @api.constrains("field_mappings")
    def _check_field_mappings(self):
        for record in self:
            if not record.field_mappings:
                raise ValidationError(
                    _("At least one field mapping must be configured for claim type '%s'.") % record.name
                )

    @api.constrains("document_requirements")
    def _check_document_requirements(self):
        for record in self:
            # Check for duplicate document types
            doc_types = record.document_requirements.mapped("document_type")
            if len(doc_types) != len(set(doc_types)):
                raise ValidationError(
                    _("Duplicate document types found in claim type '%s'. Each document type must be unique.") % record.name
                )

    def action_view_field_mappings(self):
        """Action to view field mappings for this claim configuration"""
        self.ensure_one()
        return {
            "name": _("Field Mappings - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "claim.field.mapping",
            "view_mode": "tree,form",
            "domain": [("config_id", "=", self.id)],
            "context": {
                "default_config_id": self.id,
                "search_default_config_id": self.id,
            },
        }

    def action_view_document_requirements(self):
        """Action to view document requirements for this claim configuration"""
        self.ensure_one()
        return {
            "name": _("Document Requirements - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "claim.document.requirement",
            "view_mode": "tree,form",
            "domain": [("config_id", "=", self.id)],
            "context": {
                "default_config_id": self.id,
                "search_default_config_id": self.id,
            },
        }

    def action_view_claim_requests(self):
        """Action to view claim requests for this claim configuration"""
        self.ensure_one()
        return {
            "name": _("Claim Requests - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "claim.request",
            "view_mode": "tree,form",
            "domain": [("claim_config_id", "=", self.id)],
            "context": {
                "default_claim_config_id": self.id,
                "search_default_claim_config_id": self.id,
            },
        }

    def action_view_active_claims(self):
        """Action to view active claim requests for this claim configuration"""
        self.ensure_one()
        active_states = ["draft", "submitted"]
        return {
            "name": _("Active Claims - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "claim.request",
            "view_mode": "tree,form",
            "domain": [
                ("claim_config_id", "=", self.id),
                ("state", "in", active_states)
            ],
            "context": {
                "default_claim_config_id": self.id,
                "search_default_claim_config_id": self.id,
                "search_default_active_claims": True,
            },
        }

    def get_field_mapping_by_name(self, field_name):
        """Get field mapping by claim field name"""
        self.ensure_one()
        return self.field_mappings.filtered(lambda r: r.claim_field_name == field_name)

    def get_mandatory_documents(self):
        """Get list of mandatory document requirements"""
        self.ensure_one()
        return self.document_requirements.filtered("is_mandatory")

    def get_optional_documents(self):
        """Get list of optional document requirements"""
        self.ensure_one()
        return self.document_requirements.filtered(lambda r: not r.is_mandatory)

    def validate_claim_data(self, field_values, documents):
        """Validate claim data against configuration"""
        self.ensure_one()
        errors = []

        # Validate required fields
        required_fields = self.field_mappings.filtered("is_required")
        for field_mapping in required_fields:
            if field_mapping.claim_field_name not in field_values or not field_values[field_mapping.claim_field_name]:
                errors.append(_("Field '%s' is required.") % field_mapping.claim_field_name)

        # Validate mandatory documents
        mandatory_docs = self.get_mandatory_documents()
        uploaded_doc_types = [doc.get("document_type") for doc in documents]
        for doc_req in mandatory_docs:
            if doc_req.document_type not in uploaded_doc_types:
                errors.append(_("Mandatory document '%s' is required.") % doc_req.document_type)

        if errors:
            raise ValidationError("\n".join(errors))

        return True

    def copy(self, default=None):
        """Override copy to handle related records"""
        default = default or {}
        default.update({
            "name": _("%s (Copy)") % self.name,
            "is_active": False,  # Inactive by default for copies
        })
        new_config = super().copy(default)
        
        # Copy field mappings
        for field_mapping in self.field_mappings:
            field_mapping.copy({"config_id": new_config.id})
        
        # Copy document requirements
        for doc_req in self.document_requirements:
            doc_req.copy({"config_id": new_config.id})
        
        return new_config