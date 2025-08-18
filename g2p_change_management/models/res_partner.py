import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    change_request_ids = fields.One2many(
        "change.request",
        "partner_id",
        string="Change Requests",
        help="Change requests related to this partner.",
    )
    
    # Computed field to check if group has active draft
    has_active_draft = fields.Boolean(
        compute="_compute_has_active_draft",
        string="Has Active Draft",
        help="True if this group has an active change request with draft",
    )
    
    # Computed field to show active change request
    active_change_request_id = fields.Many2one(
        "change.request",
        compute="_compute_active_change_request",
        store=True,
        search="_search_active_change_request",
        string="Active Change Request",
        help="Active change request for this partner",
    )
    
    # Draft members field - will be managed through the draft record JSON
    draft_member_ids = fields.Many2many(
        "draft.record",
        string="Draft Members",
        help="Draft members from the active change request",
        compute="_compute_draft_members",
        store=False,
    )

    @api.depends("change_request_ids", "change_request_ids.state")
    def _compute_has_active_draft(self):
        """Compute if partner has active change request."""
        for record in self:
            active_crs = record.change_request_ids.filtered(
                lambda cr: cr.state in ['draft', 'submitted']
            )
            record.has_active_draft = bool(active_crs)
    
    @api.depends("change_request_ids", "change_request_ids.state")
    def _compute_active_change_request(self):
        """Compute the active change request for this partner."""
        for record in self:
            active_crs = record.change_request_ids.filtered(
                lambda cr: cr.state in ['draft', 'submitted']
            )
            record.active_change_request_id = active_crs[0] if active_crs else False
    
    def _search_active_change_request(self, operator, value):
        """Search method for active_change_request_id field."""
        if operator == '=' and value:
            # Search for partners that have the specified change request as active
            return [('change_request_ids', '=', value)]
        elif operator == '!=' and value:
            # Search for partners that don't have the specified change request as active
            return [('change_request_ids', '!=', value)]
        elif operator in ('=', '!=') and not value:
            # Search for partners with/without any active change request
            active_crs = self.env['change.request'].search([
                ('state', 'in', ['draft', 'submitted'])
            ])
            if operator == '=':
                return [('change_request_ids', 'in', active_crs.ids)]
            else:
                return [('change_request_ids', 'not in', active_crs.ids)]
        return []
    
    @api.depends("active_change_request_id", "active_change_request_id.draft_record_id")
    def _compute_draft_members(self):
        """Compute draft members from the active change request's draft record."""
        for record in self:
            if record.active_change_request_id and record.active_change_request_id.draft_record_id:
                # Get draft members from the draft record's JSON data
                draft_record = record.active_change_request_id.draft_record_id
                if draft_record.is_group and draft_record.group_member_ids_json:
                    try:
                        import json
                        member_data = json.loads(draft_record.group_member_ids_json)
                        # Get draft individual records from the JSON data
                        draft_member_ids = []
                        for member in member_data:
                            if member.get('draft_id'):
                                # This is a draft individual record ID
                                draft_member_ids.append(member['draft_id'])
                            elif member.get('id'):
                                # This is an existing partner ID, we need to find/create draft record
                                # For now, we'll skip existing partners and only show draft individuals
                                continue
                        record.draft_member_ids = self.env["draft.record"].browse(draft_member_ids)
                    except (json.JSONDecodeError, KeyError):
                        record.draft_member_ids = self.env["draft.record"].browse([])
                else:
                    record.draft_member_ids = self.env["draft.record"].browse([])
            else:
                record.draft_member_ids = self.env["draft.record"].browse([])
    


    def action_create_change_request(self):
        """Create a change request for this partner."""
        self.ensure_one()
        
        # Check if there's already an active change request
        if self.has_active_draft:
            return {
                "type": "ir.actions.act_window",
                "name": _("Active Change Request"),
                "res_model": "change.request",
                "res_id": self.active_change_request_id.id,
                "view_mode": "form",
                "target": "current",
            }
        
        # Create new change request
        change_request = self.env["change.request"].create({
            "type": "modify",
            "partner_id": self.id,
            "description": f"Modify partner: {self.name}",
        })
        
        # Create draft record by copying partner data
        draft_record = self._create_draft_from_partner()
        change_request.write({"draft_record_id": draft_record.id})
        
        return {
            "type": "ir.actions.act_window",
            "name": _("Change Request"),
            "res_model": "change.request",
            "res_id": change_request.id,
            "view_mode": "form",
            "target": "current",
        }

    def _create_draft_from_partner(self):
        """Create a draft record by copying partner data."""
        self.ensure_one()
        
        # Prepare partner data for draft record
        partner_data = {
            "name": self.name,
            "is_group": self.is_group,
            "given_name": getattr(self, "given_name", ""),
            "family_name": getattr(self, "family_name", ""),
            "addl_name": getattr(self, "addl_name", ""),
            "phone": self.phone if hasattr(self, "phone") else "",
            "gender": getattr(self, "gender", ""),
            "region": getattr(self, "region", ""),
        }
        
        # Create draft record
        draft_record = self.env["draft.record"].create(partner_data)
        
        return draft_record

    def write(self, vals):
        """Override write to prevent direct modification if there's an active change request."""
        for partner in self:
            if partner.has_active_draft and not self.env.context.get("force_write"):
                raise ValidationError(
                    _("Cannot modify partner '%s' directly. Please use the Change Request workflow.")
                    % partner.name
                )
        return super().write(vals)


    
