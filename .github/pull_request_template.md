## Description
Briefly describe what this PR does and which module it belongs to.

## Module Ownership
- [ ] Member 1: Platform, Authentication, Users, Services, Categories
- [ ] Member 2: Incident Management, Priority, State Machine, Comments, Duplicates
- [ ] Member 3: Technicians, Skills, Assignment Strategies, Recommendations
- [ ] Member 4: SLA Tracking, Notifications, Audit Trail, Automation

## Checklist
- [ ] Branch is created from `develop` and targets `develop` (no direct PRs to `main`)
- [ ] Changes stay strictly within module ownership or have cross-member agreement
- [ ] All unit, integration, and API tests pass (`pytest`)
- [ ] Code passes linting and formatting (`ruff check .`, `ruff format --check .`)
- [ ] Any API, schema, or database contract modifications are documented in `PROJECT_CONTRACT.md`
- [ ] No passwords, API keys, tokens, or local secrets are committed
- [ ] Database migrations tested against a clean database
