# Part of OpenG2P. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import base64
import mimetypes


class ClaimDocument(models.Model):
    _name = "claim.document"
    _description = "Claim Document"
    _order = "upload_date desc"

    claim_id = fields.Many2one(
        "claim.request",
        string="Claim Request",
        required=True,
        ondelete="cascade",
        help="The claim request this document belongs to"
    )
    document_type = fields.Char(
        "Document Type",
        required=True,
        help="Type of document (e.g., 'Education Certificate', 'Identity Proof')"
    )
    file_name = fields.Char(
        "File Name",
        required=True,
        help="Original name of the uploaded file"
    )
    file_content = fields.Binary(
        "File Content",
        required=True,
        help="Binary content of the uploaded file"
    )
    file_size = fields.Integer(
        "File Size (Bytes)",
        help="Size of the file in bytes"
    )
    mimetype = fields.Char(
        "MIME Type",
        help="MIME type of the file"
    )
    upload_date = fields.Datetime(
        "Upload Date",
        default=fields.Datetime.now,
        required=True,
        help="Date and time when the document was uploaded"
    )
    uploaded_by = fields.Many2one(
        "res.users",
        string="Uploaded By",
        default=lambda self: self.env.user,
        required=True,
        help="User who uploaded the document"
    )

    # Computed fields
    file_size_mb = fields.Float(
        "File Size (MB)",
        compute="_compute_file_size_mb",
        store=True,
        help="Size of the file in megabytes"
    )
    file_extension = fields.Char(
        "File Extension",
        compute="_compute_file_extension",
        store=True,
        help="File extension (e.g., 'pdf', 'jpg')"
    )
    is_mandatory = fields.Boolean(
        "Is Mandatory",
        compute="_compute_is_mandatory",
        store=True,
        help="Whether this document type is mandatory for the claim"
    )
    display_name = fields.Char(
        "Display Name",
        compute="_compute_display_name",
        store=True,
        help="Display name for the document"
    )

    @api.depends("file_size")
    def _compute_file_size_mb(self):
        for record in self:
            if record.file_size:
                record.file_size_mb = round(record.file_size / (1024 * 1024), 2)
            else:
                record.file_size_mb = 0.0

    @api.depends("file_name")
    def _compute_file_extension(self):
        for record in self:
            if record.file_name and '.' in record.file_name:
                record.file_extension = record.file_name.split('.')[-1].lower()
            else:
                record.file_extension = ""

    @api.depends("document_type", "claim_id.claim_config_id")
    def _compute_is_mandatory(self):
        for record in self:
            if record.claim_id and record.claim_id.claim_config_id:
                doc_requirements = record.claim_id.claim_config_id.document_requirements
                matching_req = doc_requirements.filtered(
                    lambda r: r.document_type == record.document_type
                )
                record.is_mandatory = matching_req.is_mandatory if matching_req else False
            else:
                record.is_mandatory = False

    @api.depends("file_name", "document_type", "is_mandatory")
    def _compute_display_name(self):
        for record in self:
            name_parts = [record.file_name or "Unknown"]
            if record.document_type:
                name_parts.append("(%s)" % record.document_type)
            if record.is_mandatory:
                name_parts.append("[Required]")
            record.display_name = " ".join(name_parts)

    @api.constrains("file_size")
    def _check_file_size(self):
        for record in self:
            if record.file_size and record.file_size <= 0:
                raise ValidationError(_("File size must be greater than 0."))

    @api.constrains("file_content")
    def _check_file_content(self):
        for record in self:
            if not record.file_content:
                raise ValidationError(_("File content is required."))

    @api.constrains("document_type", "claim_id")
    def _check_unique_document_type_per_claim(self):
        for record in self:
            if record.document_type and record.claim_id:
                existing = self.search([
                    ("claim_id", "=", record.claim_id.id),
                    ("document_type", "=", record.document_type),
                    ("id", "!=", record.id)
                ])
                if existing:
                    raise ValidationError(
                        _("Document type '%s' already exists for this claim.") % record.document_type
                    )

    @api.model
    def create(self, vals):
        """Override create to set file properties"""
        if vals.get("file_content"):
            # Set file size
            if not vals.get("file_size"):
                try:
                    file_data = base64.b64decode(vals["file_content"])
                    vals["file_size"] = len(file_data)
                except Exception:
                    vals["file_size"] = 0

            # Set MIME type
            if not vals.get("mimetype") and vals.get("file_name"):
                mimetype, _ = mimetypes.guess_type(vals["file_name"])
                vals["mimetype"] = mimetype or "application/octet-stream"

        return super().create(vals)

    def write(self, vals):
        """Override write to update file properties if file content changes"""
        if vals.get("file_content"):
            # Update file size
            try:
                file_data = base64.b64decode(vals["file_content"])
                vals["file_size"] = len(file_data)
            except Exception:
                pass

            # Update MIME type if file name changes
            if vals.get("file_name") and not vals.get("mimetype"):
                mimetype, _ = mimetypes.guess_type(vals["file_name"])
                vals["mimetype"] = mimetype or "application/octet-stream"

        return super().write(vals)

    def action_download(self):
        """Action to download the document"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content?model=claim.document&id=%d&field=file_content&filename_field=file_name&download=true" % self.id,
            "target": "new",
        }

    def action_view_file(self):
        """Action to view the document in browser"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content?model=claim.document&id=%d&field=file_content&filename_field=file_name" % self.id,
            "target": "new",
        }

    def get_file_info(self):
        """Get file information for display"""
        self.ensure_one()
        return {
            "name": self.file_name,
            "size": self.file_size_mb,
            "size_bytes": self.file_size,
            "extension": self.file_extension,
            "mimetype": self.mimetype,
            "type": self.document_type,
            "is_mandatory": self.is_mandatory,
            "upload_date": self.upload_date,
            "uploaded_by": self.uploaded_by.name,
        }

    def validate_against_requirements(self):
        """Validate document against claim configuration requirements"""
        self.ensure_one()
        errors = []

        if not self.claim_id or not self.claim_id.claim_config_id:
            return errors

        # Find matching document requirement
        doc_requirements = self.claim_id.claim_config_id.document_requirements
        matching_req = doc_requirements.filtered(
            lambda r: r.document_type == self.document_type
        )

        if not matching_req:
            errors.append(_("Document type '%s' is not configured for this claim type.") % self.document_type)
            return errors

        doc_req = matching_req[0]

        # Validate file size
        if self.file_size > doc_req.max_file_size_bytes:
            errors.append(
                _("File size (%s MB) exceeds maximum allowed size (%s MB) for document type '%s'.") % (
                    self.file_size_mb, doc_req.max_file_size, self.document_type
                )
            )

        # Validate file format
        allowed_formats = doc_req.get_allowed_formats_list()
        if allowed_formats and self.file_extension not in allowed_formats:
            errors.append(
                _("File format '%s' is not allowed for document type '%s'. Allowed formats: %s") % (
                    self.file_extension.upper(), self.document_type, ", ".join(allowed_formats).upper()
                )
            )

        return errors

    def copy(self, default=None):
        """Override copy to handle file content"""
        default = default or {}
        default.update({
            "file_name": _("%s (Copy)") % self.file_name,
            "file_content": False,  # Don't copy file content
            "file_size": 0,
        })
        return super().copy(default)

    def unlink(self):
        """Override unlink to log activity"""
        for record in self:
            if record.claim_id:
                record.claim_id.message_post(
                    body=_("Document '%s' was deleted.") % record.file_name,
                    message_type="notification"
                )
        return super().unlink()

    @api.model
    def create_from_upload(self, claim_id, document_type, file_name, file_content, **kwargs):
        """Create document from uploaded file data"""
        vals = {
            "claim_id": claim_id,
            "document_type": document_type,
            "file_name": file_name,
            "file_content": file_content,
            "uploaded_by": self.env.user.id,
        }
        vals.update(kwargs)
        
        document = self.create(vals)
        
        # Validate against requirements
        validation_errors = document.validate_against_requirements()
        if validation_errors:
            document.unlink()
            raise ValidationError("\n".join(validation_errors))
        
        return document

    def name_get(self):
        """Custom name_get to show file name and type"""
        result = []
        for record in self:
            name = record.file_name or "Unknown"
            if record.document_type:
                name += " (%s)" % record.document_type
            result.append((record.id, name))
        return result