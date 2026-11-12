# Object-Oriented Design & Design Patterns Specification

This backend foundation was engineered specifically for **CS F213 / MAC F212 (Object-Oriented Programming)**. The system is intentionally built around robust OOP principles, avoiding procedural scripting or flat CRUD structures.

---

## 1. The Six Core OOP Pillars in I-ITSM

### 1.1 Encapsulation
- **Technician Domain Model (`app/domain/technician/technician.py`):**
  - Internal state variables (`_availability`, `_skills`, `_active_incident_count`) are protected with leading underscores.
  - State changes can only be initiated through explicit domain methods (`set_available()`, `set_busy()`, `add_skill()`, `update_active_incident_count()`).
  - Read access to collections is guarded: `Technician.skills` returns a shallow copy (`list(self._skills)`), preventing callers from mutating the list outside the aggregate root.
- **TechnicianSkill Entity (`app/domain/technician/skill.py`):**
  - Proficiency level ($1$–$5$) invariant is validated during construction in `__post_init__` and during updates in `update_proficiency()`.

### 1.2 Abstraction
- **AssignmentStrategy ABC (`app/domain/assignment/strategy.py`):**
  - Declares the abstract methods `strategy_name` and `evaluate(context)` that hide ranking algorithms from consumers.
- **LLMProvider ABC (`app/integrations/llm/provider.py`):**
  - Abstract interface defining `get_recommendation(request)` and `health_check()`. The application does not know whether a call routes to an HTTP REST API, a local subprocess, or an in-memory mock.
- **Repositories and Boundaries (`app/application/interfaces/`):**
  - `TechnicianRepository`, `IncidentServiceBoundary`, and `EventPublisher` provide abstract contracts separating business logic from PostgreSQL, external modules, and message dispatchers.

### 1.3 Inheritance (Genuine "Is-A" Relationships)
- **Assignment Strategies (`app/domain/assignment/strategies.py`):**
  - `SkillBasedAssignmentStrategy` **is an** `AssignmentStrategy`.
  - `LeastLoadedAssignmentStrategy` **is an** `AssignmentStrategy`.
  - Both inherit common filtering logic (`_filter_eligible()`) while providing specialized evaluation logic.
- **LLM Provider Adapters (`app/integrations/llm/`):**
  - `MockLLMProvider` and `OpenAICompatibleProvider` inherit from `LLMProvider`.
- **Exception Hierarchy (`app/core/exceptions.py`):**
  - `IITSMException` $\rightarrow$ `BusinessRuleError` $\rightarrow$ `SkillMismatchError`, `TechnicianUnavailableError`, `CapacityExceededError`, `NoEligibleTechnicianError`.
  - Enables polymorphic exception handling in FastAPI middlewares.

### 1.4 Polymorphism
- **Interchangeable Strategy Execution:**
  - `SmartTechnicianRecommendationService` executes any `AssignmentStrategy` polymorphically through the abstract `evaluate()` method without inspecting the underlying concrete class.
- **Interchangeable LLM Adapters:**
  - Recommendation services interact with `LLMProvider` regardless of whether the mock adapter or OpenAI adapter is active.
- **Exception Handling:**
  - The API exception handler in `app/main.py` catches the base class `IITSMException` and formats uniform JSON responses polymorphically for over 15 specific error subclasses.

### 1.5 Composition
- **Technician Aggregate (`app/domain/technician/technician.py`):**
  - Technician **has a** collection of `TechnicianSkill` instances. Skills do not exist independently; their lifecycle is bound to the parent Technician aggregate root.
- **Application Services (`app/application/assignment/service.py`):**
  - Built by composing `TechnicianRepository`, `IncidentServiceBoundary`, `LLMProvider`, and `EventPublisher`. Favors composition over complex inheritance graphs.

### 1.6 Interface Segregation Principle
- **`IncidentRef` vs Full Incident Entity:**
  - Member 3 defines `IncidentRef` (`app/domain/incident/incident_ref.py`) which holds only the fields needed for recommendation and assignment, shielding M3 from internal changes in Member 2's Incident entity.
- **`UserIdentity` Value Object (`app/domain/identity/user.py`):**
  - Represents the minimal user identity needed by technicians without exposing Member 1's full User table or password hashing logic.

---

## 2. Design Patterns Implemented

| Design Pattern | Implementation Classes | Location | Real Architectural Purpose |
|---|---|---|---|
| **Strategy Pattern** | `AssignmentStrategy`, `SkillBasedAssignmentStrategy`, `LeastLoadedAssignmentStrategy` | `app/domain/assignment/` | Allows switching between skill-based and workload-based ranking algorithms at runtime per request. |
| **Repository Pattern** | `TechnicianRepository`, `SQLAlchemyTechnicianRepository` | `app/application/interfaces/repositories.py`, `app/infrastructure/repositories/` | Decouples business logic from SQLAlchemy queries, allowing in-memory testing and seamless database migrations. |
| **Factory Pattern** | `AssignmentStrategyFactory`, `LLMProviderFactory` | `app/application/assignment/factory.py`, `app/integrations/llm/factory.py` | Centralizes object creation and decouples callers from concrete strategy and provider implementations. |
| **Adapter Pattern** | `OpenAICompatibleProvider`, `MockLLMProvider`, `StubIncidentService` | `app/integrations/llm/`, `app/integrations/incidents/` | Adapts external third-party protocols (OpenAI HTTP REST, Member 2 boundary) to internal domain interfaces. |
| **Observer Pattern** | `EventPublisher`, `InProcessEventBus`, `IncidentAssignedEvent` | `app/application/interfaces/event_publisher.py`, `app/infrastructure/events/event_bus.py` | Decouples assignment engine from Member 4's audit and notification handlers. |

---

## 3. SOLID Principles Compliance

1. **Single Responsibility Principle (SRP):**
   - `TechnicianProfileService` handles profiles and skills.
   - `SmartTechnicianRecommendationService` handles candidate scoring.
   - `TechnicianAssignmentService` coordinates assignment confirmation.
2. **Open/Closed Principle (OCP):**
   - New assignment algorithms can be added by creating a new `AssignmentStrategy` subclass and registering it with `AssignmentStrategyFactory` without altering existing code.
3. **Liskov Substitution Principle (LSP):**
   - Any `AssignmentStrategy` subclass can substitute for the base class without breaking the recommendation service.
4. **Interface Segregation Principle (ISP):**
   - Interfaces define minimal role-specific contracts (`IncidentServiceBoundary`, `EventPublisher`).
5. **Dependency Inversion Principle (DIP):**
   - High-level modules (application services) depend on abstractions, not concrete database or HTTP implementations.
