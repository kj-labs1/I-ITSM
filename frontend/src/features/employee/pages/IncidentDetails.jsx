import React, { useEffect } from "react";

import useIncidents from "../hooks/useIncidents";

import IncidentPriorityBadge from "../components/IncidentPriorityBadge";
import IncidentStatusBadge from "../components/IncidentStatusBadge";
import IncidentStatusTimeline from "../components/IncidentStatusTimeline";
import CommentSection from "../components/CommentSection";
import DuplicateSuggestions from "../components/DuplicateSuggestions";
import ResolutionPanel from "../components/ResolutionPanel";

import {
    formatDate,
} from "../utils/incidentHelpers";

export default function IncidentDetails({
    apiClient,
    incidentId,
    onBack,
    onOpenIncident,
}) {
    const {
        incident,
        duplicates,
        loading,
        saving,
        error,
        loadIncident,
        loadDuplicates,
        addComment,
        updateIncidentStatus,
    } = useIncidents(apiClient);

    useEffect(() => {
        if (!incidentId) return;

        loadIncident(incidentId)
            .then(() => {
                return loadDuplicates(incidentId);
            })
            .catch(() => {
                // The hook stores errors for display.
            });

        // The current incident is fetched when the route ID changes.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [incidentId]);

    const handleComment = async (content) => {
        await addComment(incidentId, { content });
    };

    const handleStatusChange = async (status) => {
        try {
            await updateIncidentStatus(
                incidentId,
                { status }
            );

            await loadIncident(incidentId);
        } catch {
            // API error is displayed through the hook.
        }
    };

    const openAnotherIncident = (id) => {
        if (onOpenIncident) {
            onOpenIncident(id);
        } else {
            window.location.assign(
                `/employee/incidents/${id}`
            );
        }
    };

    if (loading && !incident) {
        return (
            <main className="employee-page">
                <div className="employee-message">
                    Loading incident details...
                </div>
            </main>
        );
    }

    if (error && !incident) {
        return (
            <main className="employee-page">
                <div className="employee-alert employee-alert-error">
                    {error}
                </div>
            </main>
        );
    }

    if (!incident) {
        return (
            <main className="employee-page">
                <div className="employee-empty-state">
                    <h2>Incident not found</h2>
                    <p>
                        The requested incident could not be loaded.
                    </p>
                </div>
            </main>
        );
    }

    return (
        <main className="employee-page">
            <div className="employee-page-header">
                <div>
                    <button
                        type="button"
                        className="employee-text-button"
                        onClick={() =>
                            onBack
                                ? onBack()
                                : window.location.assign("/employee/incidents")
                        }
                    >
                        ← Back to My Incidents
                    </button>

                    <p className="employee-eyebrow">
                        INCIDENT DETAILS
                    </p>

                    <h1>{incident.incidentCode}</h1>

                    <p>{incident.description}</p>
                </div>

                <div className="employee-inline-badges">
                    <IncidentPriorityBadge
                        priority={incident.priority}
                    />

                    <IncidentStatusBadge
                        status={incident.status}
                    />
                </div>
            </div>

            {error && (
                <div className="employee-alert employee-alert-error">
                    {error}
                </div>
            )}

            <section className="employee-section">
                <h2>Incident information</h2>

                <div className="employee-details-grid">
                    <DetailItem
                        label="Incident code"
                        value={incident.incidentCode}
                    />

                    <DetailItem
                        label="Category"
                        value={incident.category}
                    />

                    <DetailItem
                        label="Affected service"
                        value={incident.serviceId}
                    />

                    <DetailItem
                        label="Priority"
                        value={incident.priority}
                    />

                    <DetailItem
                        label="Impact"
                        value={`${incident.impact}/5`}
                    />

                    <DetailItem
                        label="Urgency"
                        value={`${incident.urgency}/5`}
                    />

                    <DetailItem
                        label="Created"
                        value={formatDate(incident.createdAt)}
                    />

                    <DetailItem
                        label="Last updated"
                        value={formatDate(incident.updatedAt)}
                    />

                    <DetailItem
                        label="Assigned technician"
                        value={
                            incident.assignedTechnicianId ||
                            "Not assigned yet"
                        }
                    />
                </div>
            </section>

            <section className="employee-section">
                <h2>Incident lifecycle</h2>

                <IncidentStatusTimeline
                    currentStatus={incident.status}
                />
            </section>

            <ResolutionPanel
                incident={incident}
                onStatusChange={handleStatusChange}
                saving={saving}
            />

            <CommentSection
                comments={incident.comments || []}
                onSubmit={handleComment}
                saving={saving}
            />

            <DuplicateSuggestions
                duplicates={duplicates}
                onOpen={openAnotherIncident}
            />
        </main>
    );
}

function DetailItem({ label, value }) {
    return (
        <div className="employee-detail-item">
            <span>{label}</span>
            <strong>{value ?? "Not available"}</strong>
        </div>
    );
}