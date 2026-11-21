# Automated Testing & Verification Specification

## 1. Test Architecture & Harness

The I-ITSM automated test suite is built on **pytest** and **pytest-asyncio**, engineered to execute completely offline with zero external network or database dependencies:
- **Database Isolation:** Integration and API tests use an in-memory SQLite async engine (`sqlite+aiosqlite:///:memory:`) dynamically created per test.
- **AI Isolation:** Recommendation tests utilize a deterministic `MockLLMProvider` returning reproducible ranking scores without invoking external APIs.
- **Fast Execution:** All 267 test cases execute in under 10 seconds.

---

## 2. Test Organization & Coverage

```text
backend/tests/
├── api/                                        # API End-to-End Tests (10 files)
│   ├── test_api_incident_search_validation.py  # Search, filters, validation
│   ├── test_assignment_api.py                 # Manual & smart assignment
│   ├── test_auth_and_platform_api.py          # Register, login, me, services
│   ├── test_auth_hardening.py                 # JWT tampering, expired tokens
│   ├── test_incident_id_archive_merge.py      # Canonical IDs, archiving, merging
│   ├── test_incidents_api.py                  # Incident CRUD, priority scoring
│   ├── test_notifications_sla_audit_api.py    # Unread counter, SLA, audit logs
│   ├── test_role_permissions_and_visibility.py# Multi-role access control
│   ├── test_sla_api.py                        # SLA policy creation & violations
│   └── test_technicians_api.py                # Profiles, availability, skills
├── integration/                                # Service & Repository Tests (5 files)
│   ├── test_assignment_concurrency.py         # Concurrency locking & capacity CAS
│   ├── test_assignment_service.py             # Recommendation orchestration
│   ├── test_incident_repository.py            # Persistence & complex queries
│   ├── test_sla_service.py                    # Deadline checks & breach flags
│   └── test_technician_service.py             # Capacity limits & domain methods
└── unit/                                       # Pure Domain & Algorithm Tests (12 files)
    ├── test_assignment_strategies.py          # Skill-based & least-loaded math
    ├── test_domain_technician.py              # Encapsulation & aggregate root
    ├── test_duplicate_detector.py             # Trigram tokenization & similarity
    ├── test_incident_domain.py                # Pure incident entity logic
    ├── test_incident_lifecycle.py             # State machine transition rules
    ├── test_incident_search_validation.py     # Domain search criteria
    ├── test_incident_service.py               # Incident service mock tests
    ├── test_llm_integration.py                # Adapter pattern & fallback
    ├── test_priority_calculator.py            # Priority matrix calculations
    ├── test_sla_domain.py                     # SLA entity properties
    └── test_sla_listeners.py                 # Event bus subscriber reactions
```

---

## 3. Verified Test Results

### Pytest Execution Summary
```text
============================= test session starts ==============================
platform darwin -- Python 3.14.7, pytest-9.2.0, pluggy-1.7.0
rootdir: /Users/wonderer/Desktop/I-ITSM/backend
plugins: anyio-4.16.0, asyncio-1.4.1.post1
collected 267 items

tests/api/test_api_incident_search_validation.py ....                    [  1%]
tests/api/test_assignment_api.py .....                                   [  3%]
tests/api/test_auth_and_platform_api.py .....                            [  5%]
tests/api/test_auth_hardening.py ...                                     [  6%]
tests/api/test_incident_id_archive_merge.py ....                         [  7%]
tests/api/test_incidents_api.py ............                             [ 12%]
tests/api/test_notifications_sla_audit_api.py ...                        [ 13%]
tests/api/test_role_permissions_and_visibility.py ......                 [ 15%]
tests/api/test_sla_api.py ..                                             [ 16%]
tests/api/test_technicians_api.py ........                               [ 19%]
tests/integration/test_assignment_concurrency.py ..                      [ 20%]
tests/integration/test_assignment_service.py ....                        [ 21%]
tests/integration/test_incident_repository.py .....                      [ 23%]
tests/integration/test_sla_service.py ...                                [ 24%]
tests/integration/test_technician_service.py ................            [ 30%]
tests/unit/test_assignment_strategies.py .........                       [ 34%]
tests/unit/test_domain_technician.py ....................                [ 41%]
tests/unit/test_duplicate_detector.py ................                   [ 47%]
tests/unit/test_incident_domain.py ...................                   [ 54%]
tests/unit/test_incident_lifecycle.py ..............................     [ 65%]
tests/unit/test_incident_search_validation.py .........                  [ 69%]
tests/unit/test_incident_service.py ...........                          [ 73%]
tests/unit/test_llm_integration.py ......                                [ 75%]
tests/unit/test_priority_calculator.py ................................. [ 88%]
..................                                                       [ 94%]
tests/unit/test_sla_domain.py ............                               [ 99%]
tests/unit/test_sla_listeners.py ..                                      [100%]

============================= 267 passed in 8.76s ==============================
```

### Static Analysis & Linter Verification
```text
$ ruff check app tests
All checks passed!
```

### Frontend Production Build
```text
$ npm run build
✓ 35 modules transformed.
dist/index.html                   0.46 kB │ gzip:  0.30 kB
dist/assets/index-Bi2bkYGU.css   22.39 kB │ gzip:  5.20 kB
dist/assets/index-DAMENB5S.js   316.37 kB │ gzip: 89.60 kB
✓ built in 387ms
```

---

## 4. Running Tests Locally

```bash
cd backend
source .venv/bin/activate

# Run the complete test suite
pytest -v

# Run a specific test module
pytest tests/api/test_incidents_api.py

# Run with test coverage
pytest --cov=app tests/

# Execute Ruff checks
ruff check app tests
```
