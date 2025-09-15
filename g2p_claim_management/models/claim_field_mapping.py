# Part of OpenG2P. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ClaimFieldMapping(models.Model):
    _name = "claim.field.mapping"
    _description = "Claim Field Mapping"
    _order = "config_id, sequence, claim_field_name"

    config_id = fields.Many2one(
        "claim.configuration",
        string="Claim Configuration",
        required=True,
        ondelete="cascade",
        help="The claim configuration this field mapping belongs to"
    )
    claim_field_name = fields.Char(
        "Claim Field Name",
        required=True,
        help="Name of the field in the claim form (e.g., 'education_level', 'phone_number')"
    )
    target_field_name = fields.Char(
        "Target Field Name",
        required=True,
        help="Name of the field in the target model (e.g., 'education_level', 'phone')"
    )
    field_type = fields.Selection(
        [
            ("char", "Text"),
            ("text", "Long Text"),
            ("integer", "Integer"),
            ("float", "Float"),
            ("boolean", "Boolean"),
            ("date", "Date"),
            ("datetime", "DateTime"),
            ("selection", "Selection"),
            ("many2one", "Many2one"),
            ("one2many", "One2many"),
            ("many2many", "Many2many"),
        ],
        string="Field Type",
        required=True,
        default="char",
        help="Data type of the field"
    )
    is_required = fields.Boolean(
        "Required",
        default=False,
        help="If checked, this field must be provided when submitting a claim"
    )
    sequence = fields.Integer(
        "Sequence",
        default=10,
        help="Order in which fields are displayed in the claim form"
    )
    validation_rules = fields.Text(
        "Validation Rules",
        help="Additional validation rules (JSON format) for this field"
    )
    help_text = fields.Text(
        "Help Text",
        help="Help text to display to users when filling this field"
    )
    default_value = fields.Char(
        "Default Value",
        help="Default value for this field (if applicable)"
    )
    selection_options = fields.Text(
        "Selection Options",
        help="Options for selection fields (one per line, format: key|value)"
    )

    # Computed fields
    field_label = fields.Char(
        "Field Label",
        compute="_compute_field_label",
        store=True,
        help="Human-readable label for the field"
    )
    is_valid = fields.Boolean(
        "Valid Mapping",
        compute="_compute_is_valid",
        store=True,
        help="Whether this field mapping is valid"
    )

    @api.depends("claim_field_name")
    def _compute_field_label(self):
        for record in self:
            if record.claim_field_name:
                # Convert snake_case to Title Case
                label = record.claim_field_name.replace("_", " ").title()
                record.field_label = label
            else:
                record.field_label = ""

    @api.depends("claim_field_name", "target_field_name", "field_type")
    def _compute_is_valid(self):
        for record in self:
            record.is_valid = bool(
                record.claim_field_name and
                record.target_field_name and
                record.field_type
            )

    @api.constrains("claim_field_name", "config_id")
    def _check_unique_claim_field_name(self):
        for record in self:
            if record.claim_field_name:
                existing = self.search([
                    ("config_id", "=", record.config_id.id),
                    ("claim_field_name", "=", record.claim_field_name),
                    ("id", "!=", record.id)
                ])
                if existing:
                    raise ValidationError(
                        _("Field name '%s' already exists in this claim configuration.") % record.claim_field_name
                    )

    @api.constrains("target_field_name", "config_id")
    def _check_unique_target_field_name(self):
        for record in self:
            if record.target_field_name:
                existing = self.search([
                    ("config_id", "=", record.config_id.id),
                    ("target_field_name", "=", record.target_field_name),
                    ("id", "!=", record.id)
                ])
                if existing:
                    raise ValidationError(
                        _("Target field '%s' is already mapped in this claim configuration.") % record.target_field_name
                    )

    @api.constrains("field_type", "selection_options")
    def _check_selection_options(self):
        for record in self:
            if record.field_type == "selection" and not record.selection_options:
                raise ValidationError(
                    _("Selection options must be provided for selection field '%s'.") % record.claim_field_name
                )

    @api.constrains("validation_rules")
    def _check_validation_rules(self):
        for record in self:
            if record.validation_rules:
                try:
                    import json
                    json.loads(record.validation_rules)
                except (ValueError, TypeError):
                    raise ValidationError(
                        _("Validation rules must be valid JSON format for field '%s'.") % record.claim_field_name
                    )

    def get_selection_options_list(self):
        """Get selection options as a list of tuples"""
        self.ensure_one()
        if not self.selection_options:
            return []
        
        options = []
        for line in self.selection_options.strip().split('\n'):
            if '|' in line:
                key, value = line.split('|', 1)
                options.append((key.strip(), value.strip()))
        return options

    def validate_field_value(self, value):
        """Validate a field value against the mapping rules"""
        self.ensure_one()
        errors = []

        # Check required field
        if self.is_required and (value is None or value == ""):
            errors.append(_("Field '%s' is required.") % self.field_label)

        # Type-specific validation
        if value is not None and value != "":
            if self.field_type == "integer":
                try:
                    int(value)
                except (ValueError, TypeError):
                    errors.append(_("Field '%s' must be a valid integer.") % self.field_label)
            
            elif self.field_type == "float":
                try:
                    float(value)
                except (ValueError, TypeError):
                    errors.append(_("Field '%s' must be a valid number.") % self.field_label)
            
            elif self.field_type == "boolean":
                if value not in [True, False, "true", "false", "1", "0"]:
                    errors.append(_("Field '%s' must be true or false.") % self.field_label)
            
            elif self.field_type == "selection":
                valid_options = [opt[0] for opt in self.get_selection_options_list()]
                if value not in valid_options:
                    errors.append(_("Field '%s' must be one of: %s") % (self.field_label, ", ".join(valid_options)))

        # Custom validation rules
        if self.validation_rules:
            try:
                import json
                rules = json.loads(self.validation_rules)
                
                # Min/Max length validation
                if "min_length" in rules and len(str(value)) < rules["min_length"]:
                    errors.append(_("Field '%s' must be at least %d characters long.") % (self.field_label, rules["min_length"]))
                
                if "max_length" in rules and len(str(value)) > rules["max_length"]:
                    errors.append(_("Field '%s' must not exceed %d characters.") % (self.field_label, rules["max_length"]))
                
                # Min/Max value validation
                if "min_value" in rules and float(value) < rules["min_value"]:
                    errors.append(_("Field '%s' must be at least %s.") % (self.field_label, rules["min_value"]))
                
                if "max_value" in rules and float(value) > rules["max_value"]:
                    errors.append(_("Field '%s' must not exceed %s.") % (self.field_label, rules["max_value"]))
                
                # Pattern validation
                if "pattern" in rules:
                    import re
                    if not re.match(rules["pattern"], str(value)):
                        errors.append(_("Field '%s' format is invalid.") % self.field_label)
                        
            except (ValueError, TypeError, KeyError):
                pass  # Skip validation if rules are malformed

        return errors

    def get_field_definition(self):
        """Get field definition for dynamic form generation"""
        self.ensure_one()
        field_def = {
            "name": self.claim_field_name,
            "string": self.field_label,
            "type": self.field_type,
            "required": self.is_required,
            "help": self.help_text or "",
            "default": self.default_value or False,
        }

        if self.field_type == "selection":
            field_def["selection"] = self.get_selection_options_list()

        if self.validation_rules:
            try:
                import json
                field_def["validation_rules"] = json.loads(self.validation_rules)
            except (ValueError, TypeError):
                pass

        return field_def

    @api.model
    def get_field_mappings_for_config(self, config_id):
        """Get all field mappings for a claim configuration"""
        return self.search([
            ("config_id", "=", config_id)
        ], order="sequence, claim_field_name")

    def copy(self, default=None):
        """Override copy to handle unique constraints"""
        default = default or {}
        default.update({
            "claim_field_name": _("%s (Copy)") % self.claim_field_name,
        })
        return super().copy(default)