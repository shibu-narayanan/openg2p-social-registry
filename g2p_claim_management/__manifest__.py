# Part of OpenG2P. See LICENSE file for full copyright and licensing details.

{
    "name": "OpenG2P Claim Management",
    "summary": "Claim and Approve Management System for OpenG2P Social Registry",
    "version": "1.0.0",
    "category": "G2P",
    "author": "OpenG2P",
    "website": "https://openg2p.org",
    "license": "Other OSI approved licence",
    "depends": [
        "base",
        "mail",
        "g2p_change_management",  # For CR integration
        "g2p_draft_publish",      # For draft record integration
        "g2p_social_registry_model",  # For registrant attributes
    ],
    "data": [
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "data/claim_configuration_data.xml",
        "views/claim_configuration_views.xml",
        "views/claim_request_views.xml",
        "views/claim_submission_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "assets": {
        "web.assets_backend": [
            "g2p_claim_management/static/src/css/claim_management.css",
            "g2p_claim_management/static/src/js/claim_management.js",
        ],
    },
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": False,
}