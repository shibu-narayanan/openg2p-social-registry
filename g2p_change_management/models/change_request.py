import json
import logging
from datetime import date, datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ChangeRequest(models.Model):
    _name = "change.request"
    _description = "Change Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="Change Request Name",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    
    type = fields.Selection(
        selection=[
            ("create", "Create"),
            ("modify", "Modify"),
            ("delete", "Delete"),
        ],
        required=True,
        default="create",
        tracking=True,
    )
    
    is_group = fields.Boolean(
        string="Is Group",
        default=False,
        tracking=True,
        help="Indicates if this change request is for a group (True) or individual (False).",
    )
    
    group_kind_id = fields.Many2one(
        "g2p.group.kind",
        string="Group Kind",
        tracking=True,
        help="Type of group for group change requests.",
    )
    
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        tracking=True,
        copy=False,
    )
    
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        tracking=True,
        help="The partner record this change request relates to. Empty for create requests.",
    )
    
    draft_record_id = fields.Many2one(
        "draft.record",
        string="Draft Record",
        tracking=True,
        help="The draft record containing the proposed changes.",
    )
    
    partner_data = fields.Json(
        string="Partner Data (JSON)",
        help="JSON data for partner form wizard",
    )
    
    requester_id = fields.Many2one(
        "res.users",
        string="Requester",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    
    approver_id = fields.Many2one(
        "res.users",
        string="Approver",
        tracking=True,
        help="User who approved or rejected this change request.",
    )
    
    description = fields.Text(
        string="Description",
        tracking=True,
        help="Description of the changes being requested.",
    )
    
    rejection_reason = fields.Text(
        string="Rejection Reason",
        tracking=True,
        help="Reason for rejection if the change request was rejected.",
    )
    
    # Computed fields
    partner_name = fields.Char(
        string="Partner Name",
        compute="_compute_partner_name",
        store=True,
    )
    
    is_group = fields.Boolean(
        string="Is Group",
        default=False,
        tracking=True,
        help="Indicates if this change request is for a group (True) or individual (False).",
    )
    
    # Draft record computed fields for display
    draft_name = fields.Char(
        string="Draft Name",
        compute="_compute_draft_fields",
        store=True,
    )
    
    draft_is_group = fields.Boolean(
        string="Draft Is Group",
        compute="_compute_draft_fields",
        store=True,
    )
    
    draft_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("published", "Published"),
            ("rejected", "Rejected"),
        ],
        string="Draft State",
        compute="_compute_draft_fields",
        store=True,
    )
    
    draft_given_name = fields.Char(
        string="Draft Given Name",
        compute="_compute_draft_fields",
        store=True,
    )
    
    draft_family_name = fields.Char(
        string="Draft Family Name",
        compute="_compute_draft_fields",
        store=True,
    )
    
    draft_phone = fields.Char(
        string="Draft Phone",
        compute="_compute_draft_fields",
        store=True,
    )
    
    draft_region = fields.Char(
        string="Draft Region",
        compute="_compute_draft_fields",
        store=True,
    )
    
    # Partner computed fields for display
    partner_given_name = fields.Char(
        string="Partner Given Name",
        compute="_compute_partner_fields",
        store=True,
    )
    
    partner_family_name = fields.Char(
        string="Partner Family Name",
        compute="_compute_partner_fields",
        store=True,
    )
    
    partner_phone = fields.Char(
        string="Partner Phone",
        compute="_compute_partner_fields",
        store=True,
    )
    
    partner_region = fields.Char(
        string="Partner Region",
        compute="_compute_partner_fields",
        store=True,
    )

    @api.model
    def create(self, vals):
        """Override create to generate sequence for name field and create draft record."""
        if vals.get("name", _("New")) == _("New"):
            vals["name"] = self.env["ir.sequence"].next_by_code("change.request") or _("New")
        
        # Set default values
        if "type" not in vals:
            vals["type"] = "create"
        if "state" not in vals:
            vals["state"] = "draft"
        if "requester_id" not in vals:
            vals["requester_id"] = self.env.user.id
        
        # Create the change request
        change_request = super().create(vals)
        
        # Create draft record after change request is created
        draft_record = change_request._create_draft_record()
        change_request.write({"draft_record_id": draft_record.id})
        
        return change_request

    @api.depends("partner_id")
    def _compute_partner_name(self):
        """Compute partner name for display purposes."""
        for record in self:
            if record.partner_id:
                record.partner_name = record.partner_id.name
            else:
                record.partner_name = ""



    @api.depends("draft_record_id")
    def _compute_draft_fields(self):
        """Compute draft record fields for display."""
        for record in self:
            if record.draft_record_id:
                record.draft_name = record.draft_record_id.name
                record.draft_is_group = record.draft_record_id.is_group
                record.draft_state = record.draft_record_id.state
                record.draft_given_name = record.draft_record_id.given_name
                record.draft_family_name = record.draft_record_id.family_name
                record.draft_phone = record.draft_record_id.phone
                record.draft_region = record.draft_record_id.region
            else:
                record.draft_name = ""
                record.draft_is_group = False
                record.draft_state = False
                record.draft_given_name = ""
                record.draft_family_name = ""
                record.draft_phone = ""
                record.draft_region = ""

    @api.depends("partner_id")
    def _compute_partner_fields(self):
        """Compute partner fields for display."""
        for record in self:
            if record.partner_id:
                record.partner_given_name = getattr(record.partner_id, "given_name", "")
                record.partner_family_name = getattr(record.partner_id, "family_name", "")
                record.partner_phone = record.partner_id.phone if hasattr(record.partner_id, "phone") else ""
                record.partner_region = getattr(record.partner_id, "region", "")
            else:
                record.partner_given_name = ""
                record.partner_family_name = ""
                record.partner_phone = ""
                record.partner_region = ""

    @api.constrains("type", "partner_id")
    def _check_partner_required_for_modify_delete(self):
        """Ensure partner_id is set for modify and delete requests."""
        for record in self:
            if record.type in ["modify", "delete"] and not record.partner_id:
                raise ValidationError(
                    _("Partner must be specified for modify and delete change requests.")
                )

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        """Update is_group field when partner is selected for modify requests."""
        if self.partner_id and self.type == "modify":
            self.is_group = self.partner_id.is_group

    @api.onchange("is_group")
    def _onchange_is_group(self):
        """Auto-select group_kind if only one exists when is_group is True."""
        if self.is_group and self.type == "create":
            group_kinds = self.env["g2p.group.kind"].search([])
            if len(group_kinds) == 1:
                self.group_kind_id = group_kinds.id

    def action_submit(self):
        """Submit the change request for approval."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Only draft change requests can be submitted."))
        
        # Validate that draft record exists for create and modify requests
        if self.type in ["create", "modify"] and not self.draft_record_id:
            raise UserError(_("Draft record must be created before submitting."))
        
        self.write({"state": "submitted"})
        self.message_post(body=_("Change request submitted for approval."))
        
        # Sync draft record state if it exists
        if self.draft_record_id:
            self._sync_draft_record_state()
        
        # Create activity for approvers
        self._create_approval_activity()
        
        return True

    def action_approve(self):
        """Approve the change request."""
        self.ensure_one()
        if self.state != "submitted":
            raise UserError(_("Only submitted change requests can be approved."))
        
        if not self.env.user.has_group("g2p_change_management.group_change_approver"):
            raise UserError(_("You don't have permission to approve change requests."))
        
        self.write({
            "state": "approved",
            "approver_id": self.env.user.id,
        })
        self.message_post(body=_("Change request approved by %s.") % self.env.user.name)
        
        # Sync draft record state if it exists
        if self.draft_record_id:
            self._sync_draft_record_state()
        
        # Implement the changes based on type
        self._implement_changes()
        
        return True

    def action_reject(self):
        """Reject the change request."""
        self.ensure_one()
        if self.state != "submitted":
            raise UserError(_("Only submitted change requests can be rejected."))
        
        if not self.env.user.has_group("g2p_change_management.group_change_approver"):
            raise UserError(_("You don't have permission to reject change requests."))
        
        # For now, we'll handle rejection directly without a wizard
        # TODO: Implement rejection wizard in future task
        self.write({
            "state": "rejected",
            "approver_id": self.env.user.id,
        })
        self.message_post(body=_("Change request rejected by %s.") % self.env.user.name)
        
        # Sync draft record state if it exists
        if self.draft_record_id:
            self._sync_draft_record_state()
        
        return True

    def action_reset_to_draft(self):
        """Reset the change request to draft state."""
        self.ensure_one()
        if self.state not in ["submitted", "rejected"]:
            raise UserError(_("Only submitted or rejected change requests can be reset to draft."))
        
        self.write({
            "state": "draft",
            "rejection_reason": False,
        })
        self.message_post(body=_("Change request reset to draft."))
        
        return True

    def _create_approval_activity(self):
        """Create approval activity for approvers."""
        approvers = self.env["res.users"].search([
            ("groups_id", "in", self.env.ref("g2p_change_management.group_change_approver").id)
        ])
        
        for approver in approvers:
            self.env["mail.activity"].create({
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "note": _("Change request '%s' requires your approval.") % self.name,
                "res_id": self.id,
                "res_model_id": self.env["ir.model"]._get("change.request").id,
                "user_id": approver.id,
                "date_deadline": fields.Date.today(),
            })

    def _implement_changes(self):
        """Implement the changes based on the change request type."""
        self.ensure_one()
        
        if self.type == "create":
            if self.draft_record_id:
                self.draft_record_id.action_publish()
        
        elif self.type == "modify":
            if self.draft_record_id:
                self.draft_record_id.action_publish()
        
        elif self.type == "delete":
            if self.partner_id:
                self.partner_id.write({"active": False})
                self.message_post(body=_("Partner '%s' has been deactivated.") % self.partner_id.name)



    def _create_draft_record(self):
        """Create a draft record based on the change request type."""
        self.ensure_one()
        
        _logger.info(f"Creating draft record for type: {self.type}")
        
        if self.type == "create":
            # For create requests, use the is_group field from change request
            draft_data = {
                "name": f"New {self.type.title()} Request",
                "is_group": self.is_group,  # Use the user's selection
            }
            
            # For groups, we need to handle group_kind_id in the JSON data
            if self.is_group:
                # Create the draft record first, then update its JSON data
                draft_record = self.env["draft.record"].create(draft_data)
                
                # Update the JSON data to include group_kind_id if set
                partner_data = json.loads(draft_record.partner_data or "{}")
                if self.group_kind_id:
                    partner_data["kind"] = self.group_kind_id.id
                draft_record.write({"partner_data": json.dumps(partner_data)})
                
                return draft_record
            
            _logger.info(f"Create request draft data: {draft_data}")
        
        elif self.type == "modify":
            # For modify requests, copy partner data to draft
            if not self.partner_id:
                raise UserError(_("Partner must be specified for modify requests."))
            
            draft_data = {
                "name": self.partner_id.name,
                "is_group": self.partner_id.is_group,
                "given_name": getattr(self.partner_id, "given_name", ""),
                "family_name": getattr(self.partner_id, "family_name", ""),
                "addl_name": getattr(self.partner_id, "addl_name", ""),
                "phone": self.partner_id.phone if hasattr(self.partner_id, "phone") else "",
                "gender": getattr(self.partner_id, "gender", ""),
                "region": getattr(self.partner_id, "region", ""),
            }
            _logger.info(f"Modify request draft data: {draft_data}")
        
        elif self.type == "delete":
            # For delete requests, no draft record needed
            raise UserError(_("Draft records are not needed for delete requests."))
        
        else:
            raise UserError(_("Invalid change request type."))
        
        try:
            # Create the draft record
            _logger.info(f"Attempting to create draft record with data: {draft_data}")
            draft_record = self.env["draft.record"].create(draft_data)
            _logger.info(f"Draft record created successfully: {draft_record.name}")
            return draft_record
        except Exception as e:
            _logger.error(f"Error in _create_draft_record: {str(e)}")
            raise

    def action_open_draft_record(self):
        """Open the draft record in read-only mode using existing draft record methods."""
        self.ensure_one()
        
        if not self.draft_record_id:
            raise UserError(_("No draft record to open."))
        
        # Use the draft record's existing action methods
        if self.draft_record_id.is_group:
            return self.draft_record_id.action_open_group_wizard_view_only()
        else:
            return self.draft_record_id.action_open_individual_wizard_view_only()

    def action_edit_draft_record(self):
        """Open the draft record in edit mode using existing draft record methods."""
        self.ensure_one()
        
        if not self.draft_record_id:
            raise UserError(_("No draft record to edit."))
        
        # Use the draft record's existing action methods
        if self.draft_record_id.is_group:
            return self.draft_record_id.action_open_group_wizard()
        else:
            return self.draft_record_id.action_open_individual_wizard()

    def _draft_to_json(self, draft_record):
        """Convert draft record data to JSON format for wizard."""
        draft_data = {}
        
        # Basic fields
        draft_data["name"] = draft_record.name
        draft_data["is_group"] = draft_record.is_group
        draft_data["phone"] = draft_record.phone
        
        # Individual fields
        if not draft_record.is_group:
            draft_data["given_name"] = draft_record.given_name
            draft_data["family_name"] = draft_record.family_name
            draft_data["addl_name"] = draft_record.addl_name
            draft_data["gender"] = draft_record.gender
            draft_data["region"] = draft_record.region
        
        # Parse partner_data if it exists
        if draft_record.partner_data:
            try:
                parsed_data = json.loads(draft_record.partner_data)
                draft_data.update(parsed_data)
            except json.JSONDecodeError:
                pass
        
        return draft_data

    def action_open_partner(self):
        """Open the partner record in read-only mode using enhanced partner view."""
        self.ensure_one()
        
        if not self.partner_id:
            raise UserError(_("No partner to open."))
        
        # Open partner form with change management context
        return {
            "type": "ir.actions.act_window",
            "name": _("Partner"),
            "res_model": "res.partner",
            "res_id": self.partner_id.id,
            "view_mode": "form",
            "view_id": self.env.ref("g2p_change_management.view_partner_form_change_management").id,
            "target": "current",
            "context": {"change_management_context": True},
        }

    def action_edit_partner(self):
        """Open the partner record in edit mode using existing draft record."""
        self.ensure_one()
        
        if not self.partner_id:
            raise UserError(_("No partner to edit."))
        
        # Check if there's an active change request for this partner
        if self.partner_id.has_active_draft:
            raise UserError(_("Cannot edit partner directly. Please use the Change Request workflow."))
        
        # Use the existing draft record if it exists, otherwise create one
        if not self.draft_record_id:
            # Create draft record from partner data
            draft_record = self._create_draft_record()
            self.write({"draft_record_id": draft_record.id})
        
        # Use the draft record's existing action methods
        if self.partner_id.is_group:
            return self.draft_record_id.action_open_group_wizard()
        else:
            return self.draft_record_id.action_open_individual_wizard()



    def _sync_draft_record_state(self):
        """Synchronize draft record state with change request state."""
        self.ensure_one()
        
        if not self.draft_record_id:
            return
        
        # Map change request states to draft record states
        state_mapping = {
            "draft": "draft",
            "submitted": "submitted", 
            "approved": "approved",
            "rejected": "rejected",
        }
        
        target_state = state_mapping.get(self.state)
        if target_state and self.draft_record_id.state != target_state:
            self.draft_record_id.write({"state": target_state})
            _logger.info(f"Draft record {self.draft_record_id.name} state synced to {target_state}")

    def _return_wizard_with_context(self, view_id):
        """Return wizard action with proper context for partner form."""
        self.ensure_one()
        active_id = self.id

        if not self.partner_data:
            raise UserError(_("No partner data available."))

        try:
            json_data = json.loads(self.partner_data)
        except json.JSONDecodeError as err:
            raise UserError(_("Invalid JSON data in partner_data.")) from err

        context_data, additional_g2p_info = self._process_json_data(json_data)

        context_data["active_id"] = active_id

        _logger.info("Additional info")
        _logger.info(additional_g2p_info)
        return {
            "type": "ir.actions.act_window",
            "name": "Record Data",
            "view_mode": "form",
            "res_model": "res.partner",
            "view_id": view_id,
            "target": "new",
            "context": {
                **context_data,
                "default_additional_g2p_info": json.dumps(additional_g2p_info),
                "draft": "yes",
                "default_phone_number_ids": json_data.get("phone_number_ids", []),
                "default_individual_membership_ids": json_data.get("individual_membership_ids", []),
                "default_reg_ids": json_data.get("reg_ids", []),
                "default_is_group": json_data.get("is_group", False),
            },
        }

    def _process_json_data(self, json_data):
        """Process JSON data for partner form context."""
        partner_model_fields = self.env["res.partner"]._fields
        additional_g2p_info = {}
        context_data = {}

        for field_name, field_value in json_data.items():
            if field_name not in partner_model_fields:
                continue
                
            field = partner_model_fields[field_name]

            if field.type == "datetime" and isinstance(field_value, str):
                field_value = datetime.fromisoformat(field_value)
                context_data[f"default_{field_name}"] = field_value

            elif field.type == "date" and isinstance(field_value, str):
                field_value = date.fromisoformat(field_value)
                context_data[f"default_{field_name}"] = field_value

            elif (field.type == "char" or field.type == "text") and isinstance(field_value, str):
                context_data[f"default_{field_name}"] = field_value

            elif field.type == "many2one":
                if isinstance(field_value, int):
                    field_value = int(field_value)
                    context_data[f"default_{field_name}"] = json_data[field_name]
                else:
                    if field_name in self._fields and field_value is not None:
                        additional_g2p_info[field_name] = field_value

            elif field.type == "many2many":
                _logger.info(field_value)
                if isinstance(field_value, list):
                    if all(isinstance(val, list) for val in field_value):
                        items = []
                        for item in field_value:
                            items.append(item[1])

                        context_data[f"default_{field_name}"] = [(6, 0, items)]

            elif field.type == "selection":
                selection_values = field.get_values(env=self.env)

                if field_value in selection_values:
                    context_data[f"default_{field_name}"] = field_value

                if field_value not in selection_values:
                    if field_name in self._fields and field_value is not None:
                        additional_g2p_info[field_name] = field_value

            else:
                context_data[f"default_{field_name}"] = field_value

        return context_data, additional_g2p_info
