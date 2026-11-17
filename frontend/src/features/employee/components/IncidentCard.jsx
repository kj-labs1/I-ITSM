import React from "react";

import IncidentPriorityBadge from "./IncidentPriorityBadge";
import IncidentStatusBadge from "./IncidentStatusBadge";

import {
    formatDate,
} from "../utils/incidentHelpers";

export default function IncidentCard({
    incident,
    onOpen,
}) {
    if (!incident) return null;

    return (
        <article className="employee-incident-card">
            <div className="employee-incident-card-top">
                <span className="employee-incident-code">
                    {incident.incidentCode}
                </span>

                <IncidentPriorityBadge
                    priority={incident.priority}
                />
            </div>

            <h3>{incident.description}</h3>

            <div className="employee-incident-card-meta">
                <span>{incident.category}</span>
                <span>{formatDate(incident.createdAt)}</span>
            </div>

            <div className="employee-incident-card-bottom">
                <IncidentStatusBadge
                    status={incident.status}
                />

                <button
                    type="button"
                    className="employee-text-button"
                    onClick={() => onOpen?.(incident.id)}
                >
                    View details →
                </button>
            </div>
        </article>
    );
}