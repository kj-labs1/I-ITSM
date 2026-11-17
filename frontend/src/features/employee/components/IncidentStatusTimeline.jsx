import React from "react";

import {
    INCIDENT_STATUSES,
} from "../utils/incidentHelpers";

export default function IncidentStatusTimeline({
    currentStatus,
}) {
    const currentIndex = INCIDENT_STATUSES.indexOf(
        currentStatus
    );

    return (
        <div className="employee-timeline">
            {INCIDENT_STATUSES.map((status, index) => {
                const completed =
                    currentIndex >= 0 && index <= currentIndex;

                const current = index === currentIndex;

                return (
                    <div
                        key={status}
                        className={`employee-timeline-step ${
                            completed ? "is-completed" : ""
                        } ${current ? "is-current" : ""}`}
                    >
                        <div className="employee-timeline-marker">
                            {completed ? "✓" : index + 1}
                        </div>

                        <div className="employee-timeline-label">
                            {status.replaceAll("_", " ")}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}