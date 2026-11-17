/**
 * Employee Feature Module
 *
 * Public exports for integration into the shared React application.
 */

import "./styles/employee.css";

export { default as EmployeeDashboard } from "./pages/EmployeeDashboard";

export { default as MyIncidents } from "./pages/MyIncidents";

export { default as ReportIncident } from "./pages/ReportIncident";

export { default as IncidentDetails } from "./pages/IncidentDetails";

export { default as useIncidents } from "./hooks/useIncidents";

export { createIncidentApi } from "./api/incidentApi";