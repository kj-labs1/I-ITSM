import React from "react";

export default function IncidentPriorityBadge({ priority }) {
    const priorityClass = {
        P1: "employee-priority-p1",
        P2: "employee-priority-p2",
        P3: "employee-priority-p3",
        P4: "employee-priority-p4",
    };

    return (
        <span
            className={`employee-badge employee-priority ${
                priorityClass[priority] || ""
            }`}
        >
            {priority || "N/A"}
        </span>
    );
}