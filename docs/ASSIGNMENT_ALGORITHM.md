# Technician Assignment Algorithms Specification

The I-ITSM Assignment Engine implements the **Strategy Pattern** via the abstract base class `AssignmentStrategy`. Two concrete strategies are provided out of the box, with support for optional AI-assisted ranking.

---

## 1. Eligibility Filtering Rules (Shared by All Strategies)

Before ranking occurs, candidates must pass three deterministic hard filters:
1. **Availability:** Technician status must be `AVAILABLE`. (Excluded: `BUSY`, `OFFLINE`, `ON_LEAVE`).
2. **Skill Match:** Technician must possess the incident's `requiredSkill` (case-insensitive match).
3. **Capacity Headroom:** Technician's current active incident workload must be strictly less than their `maxCapacity`:
   $$\text{activeIncidentCount} < \text{maxCapacity}$$

If zero technicians meet all three conditions, the strategy raises `NoEligibleTechnicianError`.

---

## 2. Strategy A: Skill-Based Assignment (`SkillBasedAssignmentStrategy`)

### 2.1 Formula & Justification
Calculates a composite suitability score:

$$\text{Score} = (\text{Proficiency Level} \times 20) + (\text{Experience Years} \times 2)$$

- **Proficiency Weight ($20$):** Skill proficiency is an integer from $1$ to $5$. Multiplying by $20$ produces a base score from $20$ to $100$. This places primary importance on technical mastery of the incident domain.
- **Experience Weight ($2$):** Each year of professional experience contributes $+2$ points. This serves as a secondary differentiator between technicians with equal proficiency levels.

### 2.2 Ranking & Ordering
- Candidates are sorted **descending** by $\text{Score}$.
- Any remaining tie is broken deterministically by sorting technician `user_id` string representations alphabetically.
- Generates a transparent explanation string detailing skill level, experience, workload, and computed score.

---

## 3. Strategy B: Least-Loaded Assignment (`LeastLoadedAssignmentStrategy`)

### 3.1 Objective
Distributes operational burden evenly across the IT support engineering team by routing tickets to technicians with the lowest active workload.

### 3.2 Sorting & Deterministic Tie-Breaking
Candidates are sorted using a compound key:
1. **Primary Sort:** `active_incident_count` **ascending** (fewest active open incidents first).
2. **First Tie-Break:** `experience_years` **descending** (if workloads are equal, assign to the more experienced engineer).
3. **Second Tie-Break:** `user_id` string representation **ascending** (ensures deterministic, reproducible order).

---

## 4. Concurrency & Pre-Assignment Re-Validation

A recommendation query is a read-only projection. Between receiving a recommendation and confirming assignment, external state may change (e.g. another incident was assigned, or the technician went on leave).

When `POST /api/v1/incidents/{id}/assign` executes:
1. Re-verifies incident is still in `NEW` or `CLASSIFIED` status.
2. Re-verifies technician exists and is currently `AVAILABLE`.
3. Re-verifies technician possesses the required skill.
4. Queries latest active incident count from Member 2 to guarantee $\text{workload} < \text{maxCapacity}$.
5. Atomic hand-off to Member 2's `assign_technician` lifecycle boundary.
