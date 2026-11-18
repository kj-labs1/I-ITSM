import React from "react";

import { humanizeEnum } from "../utils/incidentHelpers";

export default function IncidentStatusBadge({ status }) {
    const statusClass = {
        NEW: "employee-status-new",
        CLASSIFIED: "employee-status-classified",
        ASSIGNED: "employee-status-assigned",
        ACKNOWLEDGED: "employee-status-acknowledged",
        IN_PROGRESS: "employee-status-progress",
        RESOLVED: "employee-status-resolved",
        VERIFIED: "employee-status-verified",
        CLOSED: "employee-status-closed",
    };

    return (
        <span
            className={`employee-badge employee-status ${
                statusClass[status] || ""
            }`}
        >
            {humanizeEnum(status)}
        </span>
    );
}