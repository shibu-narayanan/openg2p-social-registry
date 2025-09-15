# Part of OpenG2P. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ClaimDocumentRequirement(models.Model):
    _name = "claim.document.requirement"
    _description = "Document Requirements for Claims"
    _order = "config_id, sequence, document_type"

    config_id = fields.Many2one(
        "claim.configuration",
        string="Claim Configuration",
        required=True,
        ondelete="cascade",
        help="The claim configuration this document requirement belongs to"
    )
    document_type = fields.Char(
        "Document Type",
        required=True,
        help="Type of document (e.g., 'Education Certificate', 'Identity Proof', 'Income Certificate')"
    )
    is_mandatory = fields.Boolean(
        "Mandatory",
        default=True,
        help="If True, this document must be provided for the claim to be submitted"
    )
    file_formats = fields.Char(
        "Allowed File Formats",
        default="pdf,jpg,jpeg,png,doc,docx",
        help="Comma-separated list of allowed formats (e.g., 'pdf,jpg,png')"
    )
    max_file_size = fields.Integer(
        "Max File Size (MB)",
        default=10,
        help="Maximum file size allowed in megabytes"
    )
    description = fields.Text(
        "Description/Instructions",
        help="Instructions for users on what document to upload"
    )
    sequence = fields.Integer(
        "Sequence",
        default=10,
        help="Order in which documents are displayed to users"
    )

    # Computed fields
    file_formats_list = fields.Char(
        "File Formats List",
        compute="_compute_file_formats_list",
        store=True,
        help="List of allowed file formats"
    )
    max_file_size_bytes = fields.Integer(
        "Max File Size (Bytes)",
        compute="_compute_max_file_size_bytes",
        store=True,
        help="Maximum file size in bytes"
    )

    @api.depends("file_formats")
    def _compute_file_formats_list(self):
        for record in self:
            if record.file_formats:
                # Clean and normalize file formats
                formats = [fmt.strip().lower() for fmt in record.file_formats.split(",")]
                record.file_formats_list = ",".join(formats)
            else:
                record.file_formats_list = ""

    @api.depends("max_file_size")
    def _compute_max_file_size_bytes(self):
        for record in self:
            record.max_file_size_bytes = record.max_file_size * 1024 * 1024  # Convert MB to bytes

    @api.constrains("document_type", "config_id")
    def _check_unique_document_type(self):
        for record in self:
            if record.document_type:
                existing = self.search([
                    ("config_id", "=", record.config_id.id),
                    ("document_type", "=", record.document_type),
                    ("id", "!=", record.id)
                ])
                if existing:
                    raise ValidationError(
                        _("Document type '%s' already exists in this claim configuration.") % record.document_type
                    )

    @api.constrains("max_file_size")
    def _check_max_file_size(self):
        for record in self:
            if record.max_file_size <= 0:
                raise ValidationError(
                    _("Maximum file size must be greater than 0 for document type '%s'.") % record.document_type
                )
            if record.max_file_size > 100:  # 100MB limit
                raise ValidationError(
                    _("Maximum file size cannot exceed 100MB for document type '%s'.") % record.document_type
                )

    @api.constrains("file_formats")
    def _check_file_formats(self):
        for record in self:
            if record.file_formats:
                # Validate file formats
                allowed_formats = {
                    "pdf", "jpg", "jpeg", "png", "gif", "bmp", "tiff",
                    "doc", "docx", "xls", "xlsx", "ppt", "pptx",
                    "txt", "rtf", "odt", "ods", "odp"
                }
                
                formats = [fmt.strip().lower() for fmt in record.file_formats.split(",")]
                invalid_formats = [fmt for fmt in formats if fmt not in allowed_formats]
                
                if invalid_formats:
                    raise ValidationError(
                        _("Invalid file formats for document type '%s': %s. Allowed formats: %s") % (
                            record.document_type,
                            ", ".join(invalid_formats),
                            ", ".join(sorted(allowed_formats))
                        )
                    )

    def get_allowed_formats_list(self):
        """Get list of allowed file formats"""
        self.ensure_one()
        if not self.file_formats_list:
            return []
        return [fmt.strip() for fmt in self.file_formats_list.split(",")]

    def validate_document_upload(self, file_data):
        """Validate uploaded document against requirements"""
        self.ensure_one()
        errors = []

        if not file_data:
            if self.is_mandatory:
                errors.append(_("Document '%s' is required.") % self.document_type)
            return errors

        # Check file size
        if hasattr(file_data, 'size') and file_data.size > self.max_file_size_bytes:
            errors.append(
                _("File size for '%s' exceeds maximum allowed size of %d MB.") % (
                    self.document_type, self.max_file_size
                )
            )

        # Check file format
        if hasattr(file_data, 'filename'):
            file_extension = file_data.filename.split('.')[-1].lower() if '.' in file_data.filename else ''
            allowed_formats = self.get_allowed_formats_list()
            
            if file_extension not in allowed_formats:
                errors.append(
                    _("File format for '%s' is not allowed. Allowed formats: %s") % (
                        self.document_type, ", ".join(allowed_formats)
                    )
                )

        return errors

    def get_upload_instructions(self):
        """Get formatted upload instructions for users"""
        self.ensure_one()
        instructions = []
        
        if self.description:
            instructions.append(self.description)
        
        # Add format information
        allowed_formats = self.get_allowed_formats_list()
        if allowed_formats:
            instructions.append(_("Allowed formats: %s") % ", ".join(allowed_formats).upper())
        
        # Add size information
        instructions.append(_("Maximum file size: %d MB") % self.max_file_size)
        
        # Add mandatory/optional information
        if self.is_mandatory:
            instructions.append(_("This document is required."))
        else:
            instructions.append(_("This document is optional."))

        return "\n".join(instructions)

    def get_document_requirement_dict(self):
        """Get document requirement as dictionary for API/form usage"""
        self.ensure_one()
        return {
            "id": self.id,
            "document_type": self.document_type,
            "is_mandatory": self.is_mandatory,
            "file_formats": self.get_allowed_formats_list(),
            "max_file_size": self.max_file_size,
            "max_file_size_bytes": self.max_file_size_bytes,
            "description": self.description,
            "instructions": self.get_upload_instructions(),
            "sequence": self.sequence,
        }

    @api.model
    def get_document_requirements_for_config(self, config_id):
        """Get all document requirements for a claim configuration"""
        return self.search([
            ("config_id", "=", config_id)
        ], order="sequence, document_type")

    def get_mandatory_requirements(self):
        """Get mandatory document requirements"""
        return self.filtered("is_mandatory")

    def get_optional_requirements(self):
        """Get optional document requirements"""
        return self.filtered(lambda r: not r.is_mandatory)

    def copy(self, default=None):
        """Override copy to handle unique constraints"""
        default = default or {}
        default.update({
            "document_type": _("%s (Copy)") % self.document_type,
        })
        return super().copy(default)

    def name_get(self):
        """Custom name_get to show document type and mandatory status"""
        result = []
        for record in self:
            name = record.document_type
            if record.is_mandatory:
                name += " (Required)"
            else:
                name += " (Optional)"
            result.append((record.id, name))
        return result