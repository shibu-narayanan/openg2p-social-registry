# Part of OpenG2P. See LICENSE file for full copyright and licensing details.

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """Post-installation hook to assign admin user to claim manager group."""
    try:
        # Get the admin user
        cr.execute("SELECT id FROM res_users WHERE login = 'admin'")
        admin_user_id = cr.fetchone()
        
        if admin_user_id:
            admin_user_id = admin_user_id[0]
            
            # Get the claim manager group
            cr.execute("SELECT id FROM res_groups WHERE name = 'Claim Manager'")
            claim_manager_group_id = cr.fetchone()
            
            if claim_manager_group_id:
                claim_manager_group_id = claim_manager_group_id[0]
                
                # Check if admin user is already in the group
                cr.execute("""
                    SELECT 1 FROM res_groups_users_rel 
                    WHERE uid = %s AND gid = %s
                """, (admin_user_id, claim_manager_group_id))
                
                if not cr.fetchone():
                    # Add admin user to claim manager group
                    cr.execute("""
                        INSERT INTO res_groups_users_rel (uid, gid) 
                        VALUES (%s, %s)
                    """, (admin_user_id, claim_manager_group_id))
                    
                    _logger.info("Admin user assigned to Claim Manager group")
                else:
                    _logger.info("Admin user already in Claim Manager group")
            else:
                _logger.warning("Claim Manager group not found")
        else:
            _logger.warning("Admin user not found")
            
    except Exception as e:
        _logger.error("Error in post_init_hook: %s", str(e))
