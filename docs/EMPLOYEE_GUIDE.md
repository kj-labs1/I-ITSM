# Employee Incident Guide

## 1. Overview
The **Employee Portal** allows enterprise personnel to report technical incidents, track ticket progress in real-time, view SLA deadlines, and collaborate with assigned technicians.

---

## 2. Reporting an Incident

1. From the navigation bar, click **Report Incident**.
2. Fill out the report form:
   - **Service:** Select the affected enterprise IT service (e.g. PostgreSQL Database, ERP, Email).
   - **Category:** Choose the domain category (e.g. `HARDWARE`, `SOFTWARE`, `NETWORK`, `DATABASE`, `CLOUD`, `SECURITY`, `AUTHENTICATION`, `APPLICATION`, `STORAGE`).
   - **Impact (1–5):** How many users or teams are affected.
   - **Urgency (1–5):** How quickly the business requires resolution.
   - **Description:** Provide a detailed description of the failure.
3. **Live Duplicate Warnings:**
   - As you type your description, the system automatically checks for similar active incidents.
   - If an existing ticket reports the same outage, a duplicate suggestion box appears displaying matching tickets and their status.
4. Click **Submit Incident**.
5. The system generates a canonical incident code (e.g. `INC-3F82A1B9`) and redirects you to the incident details view.

---

## 3. Tracking Your Incidents

1. Click **My Incidents** in the navigation bar.
2. View your incidents filterable by priority ($P1$ to $P4$) and lifecycle status.
3. Click any incident to open the **Incident Details** view:
   - **Lifecycle Timeline:** Visual progress bar highlighting whether the ticket is `NEW`, `ASSIGNED`, `IN_PROGRESS`, or `RESOLVED`.
   - **SLA Tracking:** Shows response and resolution deadlines.
   - **Comments Thread:** Post follow-up details or answer questions from the assigned technician.
4. **Notifications & Alerts:**
   - The bell icon in the top right displays unread notifications (e.g. when a technician is assigned, or when your ticket is resolved).
   - Real-time popup toast alerts appear when key lifecycle events occur.
