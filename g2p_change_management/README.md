# OpenG2P Change Management Module

## Overview

The **Change Management Module** (`g2p_change_management`) provides a comprehensive workflow system for managing changes to registrant data in OpenG2P. It integrates with the existing `g2p_draft_publish` module to provide a structured approval process for creating, modifying, and deleting individual and group registrants.

## Features

### 🔄 **Change Request Workflow**
- **Create Requests**: Add new individuals or groups to the registry
- **Modify Requests**: Update existing registrant information
- **Delete Requests**: Remove registrants from the registry
- **State Management**: Draft → Submitted → Approved/Rejected workflow

### 👥 **User Management**
- **Requester**: Users who create change requests
- **Approver**: Users who approve or reject change requests
- **Role-based Access**: Different permissions for different user types

### 📋 **Data Management**
- **Draft Records**: Temporary storage for pending changes
- **Group Members**: Manage individual members within groups
- **Validation**: Comprehensive data validation and constraints
- **Audit Trail**: Complete history of all changes

### 🔐 **Security & Access Control**
- **Access Rights**: Granular permissions for different operations
- **Data Isolation**: Users can only see their own change requests
- **Security Groups**: Configurable user groups with specific permissions

## Installation

### Prerequisites
- OpenG2P Registry Base Module
- OpenG2P Draft Publish Module
- OpenG2P Social Registry Theme
- OpenG2P Registry Group Module
- OpenG2P Registry Individual Module
- OpenG2P Registry Membership Module

### Installation Steps
1. Ensure all prerequisite modules are installed
2. Install the `g2p_change_management` module
3. Configure user groups and permissions
4. Set up approval workflows

## Quick Start

### Creating a Change Request

1. **Navigate** to Change Management → Change Requests
2. **Click** "Create" to start a new change request
3. **Select** the type of change:
   - **Create**: Add a new registrant
   - **Modify**: Update an existing registrant
   - **Delete**: Remove a registrant
4. **Fill** in the required information
5. **Save** and **Submit** for approval

### Managing Group Members

1. **Open** a group registrant
2. **Navigate** to the "Draft Members" tab
3. **Click** "Add Draft Members" to add new members
4. **Select** individuals from the draft records
5. **Save** the changes

### Approval Process

1. **Review** submitted change requests
2. **Validate** the data and changes
3. **Approve** or **Reject** the request
4. **Monitor** the implementation of approved changes

## User Interface

### Change Request Form
- **Basic Information**: Type, description, requester
- **Partner Information**: Related registrant details
- **Draft Record**: Temporary data storage
- **Workflow Status**: Current state and next actions

### Partner View Extensions
- **Change Request History**: All related change requests
- **Draft Members**: For group registrants
- **Active Draft Warning**: Prevents direct modifications

### Dashboard Integration
- **Pending Approvals**: Change requests awaiting review
- **My Requests**: User's own change requests
- **Statistics**: Overview of change request statuses

## Configuration

### User Groups
- **Change User**: Can create and manage change requests
- **Change Approver**: Can approve or reject change requests
- **Change Admin**: Full administrative access

### Workflow Settings
- **Auto-approval**: For certain types of changes
- **Notification Settings**: Email alerts for workflow events
- **Validation Rules**: Custom business rules

## API Reference

### Models

#### Change Request (`change.request`)
```python
# Create a new change request
change_request = env['change.request'].create({
    'type': 'create',
    'is_group': False,
    'description': 'Add new individual registrant',
})

# Submit for approval
change_request.action_submit()

# Approve the request
change_request.action_approve()
```

#### Res Partner Extensions
```python
# Check if partner has active draft
if partner.has_active_draft:
    print("Partner has pending changes")

# Get active change request
active_cr = partner.active_change_request_id

# Create change request from partner
action = partner.action_create_change_request()
```

### Methods

#### Change Request Actions
- `action_submit()`: Submit change request for approval
- `action_approve()`: Approve the change request
- `action_reject()`: Reject the change request
- `action_open_partner()`: Open related partner record
- `action_edit_partner()`: Edit partner through draft record

#### Partner Actions
- `action_create_change_request()`: Create new change request
- `action_add_draft_members()`: Add draft members to group
- `_validate_for_change_request()`: Validate partner for change request

## Troubleshooting

### Common Issues

#### "Cannot modify partner directly"
**Problem**: Trying to edit a partner with an active change request
**Solution**: Use the change request workflow instead of direct editing

#### "Group Kind is required"
**Problem**: Creating a group change request without selecting group kind
**Solution**: Select a group kind from the dropdown

#### "Duplicate active requests"
**Problem**: Multiple active change requests for the same partner
**Solution**: Complete or cancel existing requests before creating new ones

### Debug Mode
Enable debug mode to see additional information:
1. Go to Settings → Developer Tools → Debug Mode
2. Enable debug mode for your user
3. Additional fields and information will be visible

## Development

### Adding New Features
1. **Extend Models**: Add new fields or methods to existing models
2. **Update Views**: Modify XML views for new functionality
3. **Add Tests**: Create comprehensive tests for new features
4. **Update Documentation**: Document new features and changes

### Testing
Run the test suite:
```bash
python -m pytest openg2p-social-registry/g2p_change_management/tests/ -v
```

### Code Style
- Follow Odoo coding standards
- Use proper docstrings for methods
- Add type hints where appropriate
- Maintain backward compatibility

## Contributing

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Add** tests for new functionality
5. **Update** documentation
6. **Submit** a pull request

## License

This module is part of the OpenG2P project and follows the same licensing terms.

## Support

For support and questions:
- **Documentation**: Check this README and inline documentation
- **Issues**: Report bugs and feature requests on the project repository
- **Community**: Join the OpenG2P community discussions

## Changelog

### Version 1.0.0
- Initial release
- Basic change request workflow
- Integration with draft publish module
- Group member management
- Comprehensive test suite
- Security and access control
