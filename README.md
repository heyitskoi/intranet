# Project: Company Intranet

This is an internal-only Flask intranet for multiple departments.
The goal is to have a single shared core that handles:
- Local user authentication (with hashed passwords)
- Basic role-based access control (admin, manager, user)
- Department-level data separation
- Blueprint-based modules for each tool (e.g., standby tool, helpdesk later)

I do NOT want React. The frontend must be classic server-side rendered HTML using Flask templates with Bootstrap 5 (or CoreUI Bootstrap theme) for a consistent, professional UI.

All templates must extend a single `base.html` and reuse `theme.css` for shared branding. No React, no SPA.

I plan to expand the system later with Google SSO, so design the user table and session handling to allow for that switch. But for now, only build local auth.

