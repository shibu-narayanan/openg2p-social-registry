from odoo import api, fields, models


class DraftGroupAddMembersWizard(models.TransientModel):
    _name = "draft.group.add.members.wizard"
    _description = "Add Group Members Wizard"

    group_id = fields.Many2one(
        "draft.record", string="Group", required=True, domain=[("is_group", "=", True)]
    )
    selected_member_ids = fields.Many2many(
        "draft.record", 
        string="Selected Members",
        domain=[("is_group", "=", False)]
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        group_id = self._context.get("default_group_id")
        if group_id:
            group = self.env["draft.record"].browse(group_id)
            res["group_id"] = group_id
            if group and group.group_member_ids_json:
                member_ids = group.group_member_ids_json
                members = self.env["draft.record"].browse(member_ids)
                res["selected_member_ids"] = [(6, 0, members.ids)]
        return res

    def action_save_members(self):
        self.ensure_one()
        self.group_id.group_member_ids_json = self.selected_member_ids.ids
        return {"type": "ir.actions.act_window_close"}



    

    

    

