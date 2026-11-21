# Administrator Operations Guide

## 1. Overview
The **Administrator Dashboard** provides full operational control across the enterprise IT ecosystem: executive KPI metrics, incident triage, technician management, SLA policy administration, IT service catalogue curation, user access control, and audit trails.

---

## 2. Managing Incidents

### Viewing and Filtering Incidents
- Navigate to **Incidents**.
- Filter by status (`NEW`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`), priority level ($P1$–$P4$), or search by incident code (`INC-xxxxxxxx`) or description.

### Technician Assignment & AI Recommendations
1. Open an unassigned incident in `NEW` or `CLASSIFIED` status.
2. Under **Technician Recommendation & Assignment**, click **⚡ Get Smart Recommendations**.
3. Review the ranked candidate table:
   - Rank and Technician name.
   - Matched skills and proficiency scores.
   - Composite match score.
   - Explainable justification text.
4. Click **Assign** next to the desired technician.
5. Alternatively, use the **Manual Assignment** dropdown to assign any eligible technician directly.

### Duplicate Incident Merging
1. In the Incident Details panel, if potential duplicates are detected, click **View Duplicates**.
2. Click **Merge into this Incident**. The secondary incident will be automatically closed, linked, and recorded in the audit trail.

### Incident Archiving
1. Open any incident in `CLOSED` status.
2. Click **Archive Incident**.
3. The incident will be marked as archived, preserving all historical timestamps, comments, SLA records, and audit entries in read-only compliance storage.
4. View all archived records by navigating to **Archived Incidents**.

---

## 3. Managing Technicians

Navigate to **Technicians**:
- **Zero Technical UUIDs:** The table displays **Username**, **Full Name**, **Skills** (as proficiency badges), **Availability**, **Experience**, and **Workload / Max Capacity**.
- **Toggle Availability:** Click **Toggle Busy / Available** to change a technician's real-time operational status.
- **View & Edit Profile:**
  - Click **View & Edit** on any technician row.
  - In the modal, adjust **Experience (Years)** and **Max Incident Capacity**.
  - Add new skills with a $1$ to $5$ proficiency rating.
  - Remove existing skills.

---

## 4. Managing SLA Policies

Navigate to **SLA Policies**:
- Review the response and resolution target hours for $P1$, $P2$, $P3$, and $P4$.
- View the SLA Summary grid: Total Tracked, In Compliance, Breached Incidents, Approaching Breach, and Overall Compliance Percentage.
- Click **Trigger SLA Check Sweep** to execute an immediate evaluation of active timers.

---

## 5. Audit Log Inspection

Navigate to **Audit Logs**:
- Query historical audit logs across all system events.
- Filter by action (`INCIDENT_CREATED`, `INCIDENT_ASSIGNED`, `STATUS_CHANGED`, `SLA_BREACHED`, `INCIDENT_ARCHIVED`, `INCIDENT_MERGED`, etc.) or date range.
