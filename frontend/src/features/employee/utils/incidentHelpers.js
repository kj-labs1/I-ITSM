/**
 * Common helper functions for Employee Incident Management.
 */

export const INCIDENT_STATUSES = [
    "NEW",
    "CLASSIFIED",
    "ASSIGNED",
    "ACKNOWLEDGED",
    "IN_PROGRESS",
    "RESOLVED",
    "VERIFIED",
    "CLOSED",
];

export const INCIDENT_CATEGORIES = [
    "HARDWARE",
    "SOFTWARE",
    "NETWORK",
    "DATABASE",
    "CLOUD",
    "SECURITY",
    "AUTHENTICATION",
    "APPLICATION",
    "STORAGE",
];

export const PRIORITIES = ["P1", "P2", "P3", "P4"];

export function formatDate(dateValue) {
    if (!dateValue) return "Not available";

    const date = new Date(dateValue);

    if (Number.isNaN(date.getTime())) {
        return "Invalid date";
    }

    return date.toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

export function formatDateOnly(dateValue) {
    if (!dateValue) return "Not available";

    const date = new Date(dateValue);

    if (Number.isNaN(date.getTime())) {
        return "Invalid date";
    }

    return date.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

export function getErrorMessage(error) {
    return (
        error?.response?.data?.message ||
        error?.response?.data?.detail ||
        error?.message ||
        "Something went wrong. Please try again."
    );
}

export function getIncidentStats(incidents = []) {
    return {
        total: incidents.length,

        open: incidents.filter(
            (incident) =>
                !["RESOLVED", "VERIFIED", "CLOSED"].includes(
                    incident.status
                )
        ).length,

        resolved: incidents.filter(
            (incident) =>
                ["RESOLVED", "VERIFIED", "CLOSED"].includes(
                    incident.status
                )
        ).length,

        critical: incidents.filter(
            (incident) =>
                ["P1", "P2"].includes(incident.priority)
        ).length,
    };
}

/**
 * Converts a local date input into an ISO-8601 UTC timestamp.
 * This avoids sending timezone-naive dates to the backend.
 */
export function localDateBoundary(dateString, endOfDay = false) {
    if (!dateString) return undefined;

    const date = new Date(
        `${dateString}T${endOfDay ? "23:59:59.999" : "00:00:00"}`
    );

    if (Number.isNaN(date.getTime())) {
        return undefined;
    }

    return date.toISOString();
}

export function humanizeEnum(value) {
    if (!value) return "Unknown";

    return value
        .toLowerCase()
        .replaceAll("_", " ")
        .replace(/\b\w/g, (character) => character.toUpperCase());
}