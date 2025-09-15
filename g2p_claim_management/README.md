# OpenG2P Claim Management Module

## Overview

The **Claim Management Module** (`g2p_claim_management`) provides a comprehensive system for managing partial data updates in OpenG2P Social Registry. It extends the existing Change Request (CR) functionality to enable users to raise targeted update requests for specific registrant attributes through a configurable, document-driven approval workflow.

## Features

### 🎯 **Configurable Claim Types**
- Define different claim types for various attribute groups
- Examples: Education Details, Contact Information, Economic Status, Social Status
- Flexible field mapping to registrant attributes

### 📄 **Document Management**
- Configurable document requirements per claim type
- Mandatory and optional document settings
- File format and size validation
- Document upload and storage

### 🔄 **CR Integration**
- Seamless integration with existing Change Request workflow
- No separate status management - inherits CR states
- Automatic CR creation from claim submissions
- Unified approval process

### ✅ **Approval Workflow**
- Reuses existing CR approval infrastructure
- Enhanced CR interface for claim-specific information
- Field-by-field comparison views
- Document review capabilities

### 🔒 **Security & Access Control**
- Role-based permissions (User, Approver, Manager)
- Data isolation between users
- Comprehensive audit trail
- Secure document handling

## Installation

### Prerequisites
- OpenG2P Registry Base Module
- OpenG2P Change Management Module
- OpenG2P Draft Publish Module
- OpenG2P Social Registry Model Module

### Installation Steps
1. Ensure all prerequisite modules are installed
2. Install the `g2p_claim_management` module
3. Configure claim types and document requirements
4. Set up user groups and permissions

## Quick Start

### Creating a Claim Type

1. **Navigate** to Claim Management → Claim Configurations
2. **Click** "Create" to start a new claim configuration
3. **Configure** the claim type:
   - Set name and description
   - Define field mappings
   - Set document requirements
   - Configure approval workflow

### Submitting a Claim

1. **Navigate** to Claim Management → Claim Requests
2. **Click** "Create" to start a new claim
3. **Select** claim type and target registrant
4. **Fill** in the required fields
5. **Upload** mandatory documents
6. **Submit** for approval

### Approving Claims

1. **Navigate** to Change Management → Change Requests
2. **Review** claim-specific information
3. **Compare** current vs. proposed values
4. **Review** uploaded documents
5. **Approve** or reject with comments

## Architecture

### CR-Driven Design
- Claims automatically create Change Requests
- State management inherited from CR system
- Unified approval workflow
- Consistent user experience

### Data Models
- `claim.configuration`: Claim type definitions
- `claim.field.mapping`: Field mapping configurations
- `claim.document.requirement`: Document requirements
- `claim.request`: Individual claim requests
- `claim.document`: Uploaded documents
- Extended `change.request`: CR integration

## Configuration Examples

### Education Update Claim
```
Claim Type: "Education Update"
Fields: education_level, course, board, year_of_passing, marks
Required Documents: Education certificate
Optional Documents: Transcript, ID proof
```

### Contact Information Update
```
Claim Type: "Contact Information Update"
Fields: phone, email, address
Required Documents: Identity proof
Optional Documents: Address proof, Phone bill
```

## API Endpoints

- `GET /claim/configuration/list` - List active claim configurations
- `GET /claim/configuration/{id}/fields` - Get field definitions
- `GET /claim/configuration/{id}/documents` - Get document requirements
- `POST /claim/submit` - Submit a new claim
- `GET /claim/{id}/status` - Get claim status
- `GET /claim/my-claims` - Get user's claims

## Security

### User Groups
- **Claim User**: Can create and submit claims
- **Claim Approver**: Can approve or reject claims
- **Claim Manager**: Can manage configurations and all claims

### Access Control
- Users can only see their own claims
- Approvers can see all claims for approval
- Managers have full access to all functionality

## Testing

Run the test suite:
```bash
odoo-bin -d your_database -i g2p_claim_management --test-enable
```

## Support

For issues and questions:
- Check the documentation
- Review the test cases
- Contact the OpenG2P community

## License

This module is part of OpenG2P and follows the same licensing terms.
