# Technician Operations Guide

## 1. Overview
The **Technician Portal** is designed for support engineers to manage their assigned incident queue, acknowledge tickets, track active workloads, log resolutions, and manage their availability status.

---

## 2. Managing Your Availability

- In the top navigation header, technicians have an instant **Availability Status Toggle**.
- Switch between **Available** (eligible to receive new incident assignments) and **Busy** (paused from receiving automatic ticket allocations).

---

## 3. Working an Incident Queue

1. Navigate to **My Incidents** or **Assigned Queue**.
2. Click on any assigned incident ticket.
3. **Step 1 — Acknowledge:**
   - When an incident is assigned, its status is `ASSIGNED`.
   - In the **Incident Resolution** panel, click **Acknowledge Ticket**. Status transitions to `ACKNOWLEDGED`.
4. **Step 2 — Begin Work:**
   - Once troubleshooting starts, click **Start Work**. Status transitions to `IN_PROGRESS`.
5. **Step 3 — Collaborate:**
   - Use the **Comments** thread to ask the reporter for logs, screenshots, or reproduction steps.
6. **Step 4 — Resolve:**
   - Once the issue is fixed, enter comprehensive text in the **Resolution Details** field (e.g. *"Replaced faulty RAM module in node B4 and verified system stability"*).
   - Click **Submit Resolution**. Status transitions to `RESOLVED` and stops the SLA timer.
