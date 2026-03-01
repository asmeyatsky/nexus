"""
Project Nexus - Salesforce Replacement CRM
Architectural Intent:
- CRM system following DDD principles with Twenty CRM as the reference
- Bounded contexts: Sales, Accounts, Contacts, Marketing, Support
- All state changes go through domain methods to enforce invariants
- External integrations abstracted behind ports

MCP Integration:
- Exposed as 'nexus-crm' MCP server
- Tools for write operations, Resources for read operations

Parallelization Notes:
- Independent validation and enrichment run concurrently
- Email notifications and event publishing are sequential after core operations
"""

__version__ = "1.0.0"
