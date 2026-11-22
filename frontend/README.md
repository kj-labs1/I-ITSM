# I-ITSM — Frontend Application Documentation

The I-ITSM Frontend is a Single Page Application (SPA) built using **React 18** and bundled with **Vite 5**. It provides role-based portals for **Employees**, **Technicians**, and **Administrators** to interact with the I-ITSM backend via asynchronous REST API calls.

---

## 1. Architecture & Technology Stack

- **Framework:** React 18
- **Build Tool:** Vite 5
- **Design System:** Custom CSS design system located in `src/index.css` (fast, lightweight, zero heavy external UI framework overhead)
- **State Management:** Native React Hooks (`useState`, `useEffect`, `useMemo`, `useRef`)
- **API Communication:** Browser Native `fetch` with centralized JWT Authorization injection and error formatting
- **Routing:** Session-backed and hash-based navigation (`#incident-{id}` deep-linking, automatic history state synchronization)
- **Environment Binding:** Configured via `import.meta.env.VITE_API_URL` with automatic development fallback to `http://127.0.0.1:8000/api/v1`

---

## 2. Directory Structure

```text
frontend/
├── dist/                          # Production build output
├── public/                        # Static web assets
├── src/
│   ├── features/
│   │   └── employee/              # Modular Employee & Incident feature pack
│   │       ├── api/
│   │       │   └── incidentApi.js # API communication layer for incidents
│   │       ├── components/        # Reusable UI components
│   │       │   ├── DuplicateSuggestions.jsx  # Real-time duplicate alerts
│   │       │   ├── IncidentCard.jsx          # Grid card presentation
│   │       │   ├── IncidentStatusBadge.jsx   # Lifecycle state badge
│   │       │   ├── IncidentPriorityBadge.jsx # Priority level badge
│   │       │   ├── IncidentTable.jsx         # Tabular incident listing
│   │       │   ├── IncidentStatusTimeline.jsx# Lifecycle progress tracker
│   │       │   └── ResolutionPanel.jsx       # Technician resolution interface
│   │       ├── hooks/
│   │       │   └── useIncidents.js           # Incidents state and operations hook
│   │       ├── pages/
│   │       │   ├── EmployeeDashboard.jsx     # Employee overview metrics
│   │       │   ├── MyIncidents.jsx           # Filterable incident list
│   │       │   ├── ReportIncident.jsx        # Submission form with duplicate check
│   │       │   └── IncidentDetails.jsx       # Comprehensive ticket view
│   │       └── utils/
│   │           └── incidentHelpers.js        # Formatting and date boundary helpers
│   ├── utils/
│   │   └── errorHandler.js        # Centralized error extraction utility
│   ├── App.jsx                    # Root component, router, role portals & modals
│   ├── main.jsx                   # React DOM entry point
│   └── index.css                  # Enterprise design tokens and styles
├── index.html                     # HTML5 shell
├── package.json                   # NPM dependencies and scripts
└── vite.config.js                 # Vite build settings and proxy configurations
```

---

## 3. Implemented Role Portals & Features

### 3.1 Employee Portal
- **Dashboard:** Summary metrics showing personal incident counts (Total, Active, In-Progress, Resolved, Critical $P1/P2$).
- **Report Incident (`ReportIncident.jsx`):**
  - Incident category and service selection.
  - Interactive urgency and impact selectors ($1$ to $5$) calculating real-time priority.
  - **Live Duplicate Detection:** Automatically queries `/api/v1/incidents/search` as descriptions are typed; displays potential duplicate matches with similarity scores.
- **My Incidents (`MyIncidents.jsx`):** Searchable, filterable list by status, category, and priority.
- **Incident Details (`IncidentDetails.jsx`):** Real-time lifecycle timeline, SLA tracking countdowns, and collaborative comment thread.

### 3.2 Technician Portal
- **Assigned Queue:** Filtered view displaying incidents assigned to the logged-in technician's user UUID.
- **Incident Acknowledgment & Resolution (`ResolutionPanel.jsx`):**
  - Step-by-step state machine progression: `ASSIGNED` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `RESOLVED`.
  - Detailed resolution text entry required prior to closing.
- **Availability Toggle:** Direct toggle on the navigation bar to switch between `AVAILABLE` and `BUSY` operational modes.

### 3.3 Administrator Portal
- **Executive Metrics Dashboard:** Overview of total incidents, SLA compliance rates, breached incidents, active technician count, and category distributions.
- **Incident Management:** Full visibility across enterprise incidents, smart candidate recommendations, manual assignment, soft-archiving, and duplicate merging.
- **Technician Roster & Workload (`TechniciansPage`):**
  - Displays technician **Username**, **Full Name**, **Skills** (as proficiency badges `Skill (X/5)`), **Availability**, **Experience**, and **Workload / Max Capacity**.
  - **Zero User-Facing UUIDs:** Internal database IDs are kept under the hood and never rendered in table cells or headers.
  - **Promoted User Profile Configuration Modal:** Displays newly promoted technicians with **Profile Not Configured** status and allows administrators to open an **Add Technician Profile** modal to configure experience, capacity, availability, and skills.
- **Service Catalogue & Incident Categories:** Dynamic forms to create, edit, activate, or deactivate services and category mappings.
- **SLA Monitoring (`SLAPage`):** Real-time summary grid showing total tracked, compliant, breached, and approaching-breach tickets.
- **Audit Logs (`AuditPage`):** Filterable chronological audit log table with actor, action, timestamp, and metadata search.

---

## 4. Real-Time Notifications & Popup Alerts

- **Polling Engine:** Background polling every 15 seconds querying `/api/v1/notifications/unread/count` and `/api/v1/notifications?limit=20`.
- **Unread Badge & Dropdown:** Bell icon with counter badge displaying recent notifications with event icons (🚨 SLA Breach, ⚠️ SLA Warning, 🛠️ Assignment, 📝 Created, 🔄 Status Changed, 💬 Comment).
- **Popup Toast Alerts:** New unread notifications trigger temporary popup toast alerts in the bottom-right corner that automatically dismiss after 6 seconds.
- **Single-Click Navigation:** Clicking any notification marks it as read and deep-links directly to the relevant incident.

---

## 5. Centralized Error Handling (`src/utils/errorHandler.js`)

The frontend implements a centralized error extraction utility:
- **FastAPI / Domain Envelope Extraction:** Extracts meaningful error messages from `data.message`, `data.detail`, and `data.error`.
- **Validation Array Parsing:** Formats Pydantic HTTP 422 validation error arrays into clean strings instead of `[object Object]`.
- **Status Code Mapping:** Provides human-readable fallback messages for HTTP 400, 401, 403, 404, 409, 422, 429, 500, 502, 503, and 504.
- **Network Resilience:** Catches fetch and network errors (`Network error: Unable to connect to server`).

---

## 6. Running the Frontend

### Development Server
```bash
npm install
npm run dev
```
Application accessible at [http://localhost:5173](http://localhost:5173).

### Production Build
```bash
npm run build
```
Generates optimized static assets in `dist/`.
