import React from "react";
import { CheckIcon } from "../../../components/Icons";

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
                            {completed ? <CheckIcon size={14} strokeWidth={2.5} /> : index + 1}
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