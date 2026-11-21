import React from "react";

import IncidentPriorityBadge from "./IncidentPriorityBadge";
import IncidentStatusBadge from "./IncidentStatusBadge";

import {
    formatDate,
} from "../utils/incidentHelpers";

export default function IncidentTable({
    incidents = [],
    loading = false,
    onOpen,
}) {
    if (loading) {
        return (
            <div className="employee-message">
                Loading incidents...
            </div>
        );
    }

    if (incidents.length === 0) {
        return (
            <div className="employee-empty-state">
                <h3>No incidents found</h3>
                <p>
                    There are no incidents matching your search criteria.
                </p>
            </div>
        );
    }

    return (
        <div className="employee-table-wrapper">
            <table className="employee-table">
                <thead>
                    <tr>
                        <th>Incident</th>
                        <th>Description</th>
                        <th>Category</th>
                        <th>Priority</th>
                        <th>Status</th>
                        <th>Created</th>
                        <th>Action</th>
                    </tr>
                </thead>

                <tbody>
                    {incidents.map((incident) => (
                        <tr key={incident.id}>
                            <td>
                                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                                    <strong>
                                        {incident.incidentCode}
                                    </strong>
                                    {incident.isArchived && (
                                        <span style={{ backgroundColor: "#eaeef2", color: "#57606a", fontSize: "10px", fontWeight: "600", padding: "2px 6px", borderRadius: "10px", border: "1px solid #d0d7de" }}>
                                            ARCHIVED
                                        </span>
                                    )}
                                    {incident.mergedIntoIncidentId && (
                                        <span style={{ backgroundColor: "#fbefff", color: "#8250df", fontSize: "10px", fontWeight: "600", padding: "2px 6px", borderRadius: "10px", border: "1px solid #d8b9ff" }}>
                                            MERGED
                                        </span>
                                    )}
                                </div>
                                <span style={{ display: "block", fontSize: "11px", color: "#656d76", fontFamily: "monospace" }}>
                                    ID: {incident.id}
                                </span>
                            </td>

                            <td className="employee-description-cell">
                                {incident.description}
                            </td>

                            <td>{incident.category}</td>

                            <td>
                                <IncidentPriorityBadge
                                    priority={incident.priority}
                                />
                            </td>

                            <td>
                                <IncidentStatusBadge
                                    status={incident.status}
                                />
                            </td>

                            <td>
                                {formatDate(incident.createdAt)}
                            </td>

                            <td>
                                <button
                                    type="button"
                                    className="employee-text-button"
                                    onClick={() =>
                                        onOpen?.(incident.id)
                                    }
                                >
                                    View
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}