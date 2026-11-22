# I-ITSM — Automated Testing & Quality Assurance

## 1. Test Architecture & Harness

The I-ITSM automated test suite is built on **pytest** and **pytest-asyncio**, engineered to execute completely offline with zero external network or database dependencies:
- **Database Isolation:** Integration and API tests execute against an in-memory SQLite async engine (`sqlite+aiosqlite:///:memory:`) dynamically created per test session.
- **AI Mocking:** Recommendation tests utilize a deterministic `MockLLMProvider` returning reproducible ranking scores without invoking external network endpoints.
- **Speed & Reliability:** All **273 automated tests** execute in under 4 seconds with 100% pass rates and zero warnings.

---

## 2. Test Suite Organization

```text
backend/tests/
├── api/                                        # API End-to-End Tests (11 files)
│   ├── test_api_incident_search_validation.py  # Search, filters, validation
│   ├── test_assignment_api.py                 # Manual & smart assignment
│   ├── test_auth_and_platform_api.py          # Register, login, me, services
│   ├── test_auth_hardening.py                 # JWT tampering, expired tokens
│   ├── test_incident_id_archive_merge.py      # Canonical IDs, archiving, merging
│   ├── test_incidents_api.py                  # Incident CRUD, priority scoring
│   ├── test_notifications_sla_audit_api.py    # Unread counter, SLA, audit logs
│   ├── test_promoted_technicians_workflow.py  # User promotion & profile creation modal (6 tests)
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

## 3. Running Automated Tests & Quality Checks

### 3.1 Backend Tests
```bash
cd backend
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run all 273 tests
pytest -v

# Run with quick summary
pytest tests/ -q
```

### 3.2 Code Quality & Linting
```bash
cd backend
source .venv/bin/activate

# Execute Ruff linter
ruff check app tests

# Execute Ruff format check
ruff format --check app tests
```

### 3.3 Frontend Production Build
```bash
cd frontend

# Verify production build compilation
npm run build
```

---

## 4. Continuous Integration (GitHub Actions)

Cross-platform automated verification is enforced via `.github/workflows/ci.yml`:
- **Backend Matrix:** Python 3.12 running on `ubuntu-latest`, `macos-latest`, and `windows-latest` (runs `pytest` and `ruff check`).
- **Frontend Matrix:** Node 20 running on `ubuntu-latest`, `macos-latest`, and `windows-latest` (runs `npm run build`).
