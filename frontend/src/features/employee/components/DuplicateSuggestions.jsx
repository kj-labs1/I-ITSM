import React from "react";

import IncidentPriorityBadge from "./IncidentPriorityBadge";
import IncidentStatusBadge from "./IncidentStatusBadge";

export default function DuplicateSuggestions({
    duplicates = [],
    onOpen,
}) {
    return (
        <section className="employee-section">
            <div className="employee-section-heading">
                <h2>Possible duplicate incidents</h2>

                <span className="employee-muted">
                    {duplicates.length} potential match(es)
                </span>
            </div>

            {duplicates.length === 0 ? (
                <p className="employee-muted">
                    No potential duplicates were identified.
                </p>
            ) : (
                <div className="employee-duplicate-list">
                    {duplicates.map((item) => (
                        <article
                            className="employee-duplicate-card"
                            key={item.incidentId}
                        >
                            <div className="employee-duplicate-header">
                                <strong>
                                    {item.incidentCode}
                                </strong>

                                <span className="employee-similarity">
                                    {(item.similarityScore * 100).toFixed(1)}%
                                    match
                                </span>
                            </div>

                            <div className="employee-inline-badges">
                                <IncidentPriorityBadge
                                    priority={item.priority}
                                />

                                <IncidentStatusBadge
                                    status={item.status}
                                />
                            </div>

                            <p>{item.explanation}</p>

                            <button
                                type="button"
                                className="employee-text-button"
                                onClick={() =>
                                    onOpen?.(item.incidentId)
                                }
                            >
                                View incident
                            </button>
                        </article>
                    ))}
                </div>
            )}
        </section>
    );
}