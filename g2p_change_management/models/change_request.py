import json
import logging
from datetime import date, datetime, timedelta

from odoo import api, fields, models
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
        default=lambda self: "New",
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
        if vals.get("name", "New") == "New":
            vals["name"] = self.env["ir.sequence"].next_by_code("change.request") or "New"
        
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
                    "Partner must be specified for modify and delete change requests."
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
        
        # Validate state
        if self.state != "draft":
            raise UserError("Only draft change requests can be submitted.")
        
        # Validate required fields
        if not self.description:
            raise UserError("Description is required before submitting.")
        
        # Validate that draft record exists for create and modify requests
        if self.type in ["create", "modify"] and not self.draft_record_id:
            raise UserError("Draft record must be created before submitting.")
        
        # Validate approvers exist
        approvers = self.env["res.users"].search([
            ("groups_id", "in", self.env.ref("g2p_change_management.group_change_approver").id)
        ])
        if not approvers:
            raise UserError("No approvers found. Please contact your administrator.")
        
        # Update state
        self.write({"state": "submitted"})
        
        # Log the submission
        self.message_post(
            body="Change request submitted for approval by %s." % self.env.user.name,
            subject="Change Request Submitted: %s" % self.name,
        )
        
        # Sync draft record state if it exists
        if self.draft_record_id:
            self._sync_draft_record_state()
        
        # Create activity for approvers
        self._create_approval_activity()
        
        _logger.info("Change request %s submitted for approval by %s", self.name, self.env.user.name)
        return True

    def action_approve(self):
        """Approve the change request."""
        self.ensure_one()
        
        # Validate state
        if self.state != "submitted":
            raise UserError("Only submitted change requests can be approved.")
        
        # Validate permissions
        if not self.env.user.has_group("g2p_change_management.group_change_approver"):
            raise UserError("You don't have permission to approve change requests.")
        
        # Update state
        self.write({
            "state": "approved",
            "approver_id": self.env.user.id,
        })
        
        # Log the approval
        self.message_post(
            body="Change request approved by %s." % self.env.user.name,
            subject="Change Request Approved: %s" % self.name,
        )
        
        # Sync draft record state if it exists
        if self.draft_record_id:
            self._sync_draft_record_state()
        
        # Implement the changes based on type
        try:
            self._implement_changes()
            _logger.info("Changes implemented successfully for change request %s", self.name)
        except Exception as e:
            _logger.error("Failed to implement changes for change request %s: %s", self.name, str(e))
            raise UserError("Failed to implement changes: %s" % str(e))
        
        # Send notification to requester
        self._send_approval_result_notification("approved")
        
        # Close related activities
        self._close_related_activities()
        
        _logger.info("Change request %s approved by %s", self.name, self.env.user.name)
        return True

    def action_reject(self):
        """Reject the change request."""
        self.ensure_one()
        
        # Validate state
        if self.state != "submitted":
            raise UserError("Only submitted change requests can be rejected.")
        
        # Validate permissions
        if not self.env.user.has_group("g2p_change_management.group_change_approver"):
            raise UserError("You don't have permission to reject change requests.")
        
        # For now, we'll handle rejection directly without a wizard
        # TODO: Implement rejection wizard in future task
        self.write({
            "state": "rejected",
            "approver_id": self.env.user.id,
        })
        
        # Log the rejection
        self.message_post(
            body="Change request rejected by %s." % self.env.user.name,
            subject="Change Request Rejected: %s" % self.name,
        )
        
        # Sync draft record state if it exists
        if self.draft_record_id:
            self._sync_draft_record_state()
        
        # Send notification to requester
        self._send_approval_result_notification("rejected")
        
        # Close related activities
        self._close_related_activities()
        
        _logger.info("Change request %s rejected by %s", self.name, self.env.user.name)
        return True
    
    def _validate_workflow_transition(self, from_state, to_state):
        """Validate if the state transition is allowed."""
        allowed_transitions = {
            "draft": ["submitted"],
            "submitted": ["approved", "rejected"],
            "approved": [],  # No further transitions
            "rejected": ["draft"],  # Can be reset to draft
        }
        
        if to_state not in allowed_transitions.get(from_state, []):
            raise UserError("Invalid state transition from '%s' to '%s'." % (from_state, to_state))
        
        return True
    
    def _check_workflow_permissions(self, action):
        """Check if user has permissions for the workflow action."""
        user = self.env.user
        
        if action in ["approve", "reject"]:
            if not user.has_group("g2p_change_management.group_change_approver"):
                raise UserError("You don't have permission to %s change requests." % action)
        
        elif action == "submit":
            # Any user can submit their own requests
            if self.requester_id != user:
                raise UserError("You can only submit your own change requests.")
        
        return True
    
    def get_workflow_summary(self):
        """Get a summary of the workflow status."""
        return {
            "name": self.name,
            "type": dict(self._fields['type'].selection).get(self.type, self.type),
            "state": dict(self._fields['state'].selection).get(self.state, self.state),
            "requester": self.requester_id.name,
            "approver": self.approver_id.name if self.approver_id else None,
            "created_date": self.create_date,
            "last_update": self.write_date,
            "has_draft_record": bool(self.draft_record_id),
            "can_submit": self.state == "draft" and self.requester_id == self.env.user,
            "can_approve": self.state == "submitted" and self.env.user.has_group("g2p_change_management.group_change_approver"),
            "can_reject": self.state == "submitted" and self.env.user.has_group("g2p_change_management.group_change_approver"),
        }

    def action_reset_to_draft(self):
        """Reset the change request to draft state."""
        self.ensure_one()
        if self.state not in ["submitted", "rejected"]:
            raise UserError("Only submitted or rejected change requests can be reset to draft.")
        
        self.write({
            "state": "draft",
            "rejection_reason": False,
        })
        self.message_post(body="Change request reset to draft.")
        
        return True

    def _create_approval_activity(self):
        """Create approval activity for approvers."""
        approvers = self.env["res.users"].search([
            ("groups_id", "in", self.env.ref("g2p_change_management.group_change_approver").id)
        ])
        
        if not approvers:
            _logger.warning("No approvers found for change request %s", self.name)
            return
        
        # Calculate deadline (3 business days from now)
        deadline = fields.Date.today()
        for _ in range(3):
            deadline = deadline + timedelta(days=1)
            # Skip weekends (simple implementation)
            while deadline.weekday() >= 5:  # Saturday = 5, Sunday = 6
                deadline = deadline + timedelta(days=1)
        
        for approver in approvers:
            # Create activity
            activity = self.env["mail.activity"].create({
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "note": "Change request '%s' requires your approval.\n\nType: %s\nRequester: %s\nDescription: %s" % (
                    self.name, 
                    dict(self._fields['type'].selection).get(self.type, self.type),
                    self.requester_id.name,
                    self.description or "No description provided"
                ),
                "res_id": self.id,
                "res_model_id": self.env["ir.model"]._get("change.request").id,
                "user_id": approver.id,
                "date_deadline": deadline,
            })
            
            # Send email notification
            self._send_approval_notification(approver, activity)
    
    def _send_approval_notification(self, approver, activity):
        """Send email notification to approver."""
        try:
            template = self.env.ref('g2p_change_management.mail_template_change_request_approval', raise_if_not_found=False)
            if template:
                template.with_context(activity_id=activity.id).send_mail(self.id, force_send=True)
            else:
                # Fallback: send simple notification
                self.message_post(
                    body="Approval notification sent to %s" % approver.name,
                    partner_ids=[approver.partner_id.id] if approver.partner_id else [],
                    subject="Change Request Approval Required: %s" % self.name,
                )
        except Exception as e:
            _logger.error("Failed to send approval notification to %s: %s", approver.name, str(e))
    
    def _send_approval_result_notification(self, result):
        """Send notification to requester about approval result."""
        try:
            if result == "approved":
                subject = "Change Request Approved: %s" % self.name
                body = "Your change request '%s' has been approved by %s." % (self.name, self.approver_id.name)
            else:  # rejected
                subject = "Change Request Rejected: %s" % self.name
                body = "Your change request '%s' has been rejected by %s." % (self.name, self.approver_id.name)
            
            self.message_post(
                body=body,
                subject=subject,
                partner_ids=[self.requester_id.partner_id.id] if self.requester_id.partner_id else [],
            )
        except Exception as e:
            _logger.error("Failed to send approval result notification: %s", str(e))
    
    def _close_related_activities(self):
        """Close all activities related to this change request."""
        try:
            activities = self.env["mail.activity"].search([
                ("res_id", "=", self.id),
                ("res_model", "=", "change.request"),
                ("state", "=", "planned"),
            ])
            activities.write({"state": "done"})
            _logger.info("Closed %s activities for change request %s", len(activities), self.name)
        except Exception as e:
            _logger.error("Failed to close activities for change request %s: %s", self.name, str(e))

    def _implement_changes(self):
        """Implement the changes based on the change request type."""
        self.ensure_one()
        
        if self.type == "create":
            if self.draft_record_id:
                # Publish the draft record to create a new partner
                created_partner = self.draft_record_id.action_publish()
                if created_partner:
                    # Link the created partner to this change request
                    self.write({"partner_id": created_partner.id})
                    self.message_post(
                        body="New partner '%s' has been created and published to the registry." % created_partner.name,
                        subject="Partner Created: %s" % created_partner.name,
                    )
                    _logger.info("Partner created successfully: %s (ID: %s)", created_partner.name, created_partner.id)
        
        elif self.type == "modify":
            if self.draft_record_id:
                # For modify requests, we need to update the existing partner
                # The draft record's action_publish will handle the modification
                modified_partner = self.draft_record_id.action_publish()
                if modified_partner:
                    self.message_post(
                        body="Partner '%s' has been updated in the registry." % modified_partner.name,
                        subject="Partner Updated: %s" % modified_partner.name,
                    )
                    _logger.info("Partner updated successfully: %s (ID: %s)", modified_partner.name, modified_partner.id)
        
        elif self.type == "delete":
            if self.partner_id:
                self.partner_id.write({"active": False})
                self.message_post(body="Partner '%s' has been deactivated." % self.partner_id.name)



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
                raise UserError("Partner must be specified for modify requests.")
            
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
            raise UserError("Draft records are not needed for delete requests.")
        
        else:
            raise UserError("Invalid change request type.")
        
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
            raise UserError("No draft record to open.")
        
        # Use the draft record's existing action methods
        if self.draft_record_id.is_group:
            return self.draft_record_id.action_open_group_wizard_view_only()
        else:
            return self.draft_record_id.action_open_individual_wizard_view_only()

    def action_edit_draft_record(self):
        """Open the draft record in edit mode using existing draft record methods."""
        self.ensure_one()
        
        if not self.draft_record_id:
            raise UserError("No draft record to edit.")
        
        # Use the draft record's existing action methods with proper context
        if self.draft_record_id.is_group:
            action = self.draft_record_id.action_open_group_wizard()
        else:
            action = self.draft_record_id.action_open_individual_wizard()
        
        # Update the context to point to the draft record instead of change request
        if action and 'context' in action:
            action['context'].update({
                'active_model': 'draft.record',
                'active_id': self.draft_record_id.id,
            })
        
        return action

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
            raise UserError("No partner to open.")
        
        # Open partner form with change management context
        return {
            "type": "ir.actions.act_window",
            "name": "Partner",
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
            raise UserError("No partner to edit.")
        
        # Check if there's an active change request for this partner
        if self.partner_id.has_active_draft:
            raise UserError("Cannot edit partner directly. Please use the Change Request workflow.")
        
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
            "approved": "published",  # draft.record uses 'published' instead of 'approved'
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
            raise UserError("No partner data available.")

        try:
            json_data = json.loads(self.partner_data)
        except json.JSONDecodeError as err:
            raise UserError("Invalid JSON data in partner_data.") from err

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
