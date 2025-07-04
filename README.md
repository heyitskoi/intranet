# Company Intranet

This is a minimal Flask-based intranet prototype with local user authentication and role-based access control. It uses server-side rendered HTML templates styled with Bootstrap 5.

## Features
- Local user registration and login with hashed passwords
- Role field for future RBAC (admin, manager, user)
- Department field on the user for data separation
- Designed to extend to other authentication providers (e.g., Google SSO)
- Blueprint structure for modular tools

Run the development server:

```bash
python -m intranet.app
```
