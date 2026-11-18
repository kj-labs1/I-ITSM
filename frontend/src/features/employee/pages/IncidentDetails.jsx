import React, { useEffect, useState } from "react";

import useIncidents from "../hooks/useIncidents";

import IncidentPriorityBadge from "../components/IncidentPriorityBadge";
import IncidentStatusBadge from "../components/IncidentStatusBadge";
import IncidentStatusTimeline from "../components/IncidentStatusTimeline";
import CommentSection from "../components/CommentSection";
import DuplicateSuggestions from "../components/DuplicateSuggestions";
import ResolutionPanel from "../components/ResolutionPanel";

import { formatDate } from "../utils/incidentHelpers";

export default function IncidentDetails({
    apiClient,
    incidentId,
    currentUser,
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

    const [sla, setSla] = useState(null);
    const [recommendations, setRecommendations] = useState(null);
    const [recLoading, setRecLoading] = useState(false);
    const [assigning, setAssigning] = useState(false);
    const [assignSuccess, setAssignSuccess] = useState("");
    const [assignError, setAssignError] = useState("");
    const [techniciansList, setTechniciansList] = useState([]);
    const [selectedTechId, setSelectedTechId] = useState("");

    const isAdmin = currentUser?.role === "ADMIN";

    useEffect(() => {
        if (!incidentId) return;

        loadIncident(incidentId)
            .then(() => loadDuplicates(incidentId))
            .catch(() => {});

        // Fetch SLA status
        if (apiClient?.get) {
            apiClient
                .get(`/incidents/${incidentId}/sla`)
                .then((res) => setSla(res.data))
                .catch(() => setSla(null));
        }

        // If admin, load technicians list for manual assignment dropdown
        if (isAdmin && apiClient?.get) {
            apiClient
                .get("/technicians")
                .then((res) => {
                    const list = Array.isArray(res.data) ? res.data : [];
                    setTechniciansList(list);
                    if (list.length > 0) setSelectedTechId(list[0].id);
                })
                .catch(() => {});
        }
    }, [incidentId, isAdmin, apiClient, loadIncident, loadDuplicates]);

    const handleComment = async (content) => {
        await addComment(incidentId, { content });
    };

    const handleStatusChange = async (newStatus, extraPayload = {}) => {
        await updateIncidentStatus(incidentId, {
            status: newStatus,
            ...extraPayload,
        });
        await loadIncident(incidentId);
    };

    const openAnotherIncident = (id) => {
        if (onOpenIncident) {
            onOpenIncident(id);
        } else if (onBack) {
            onBack();
        }
    };

    const fetchRecommendations = async () => {
        setRecLoading(true);
        setAssignError("");
        try {
            const res = await apiClient.get(
                `/technicians/recommendations?incidentId=${incidentId}&strategy=SKILL_BASED&useLlm=true`
            );
            setRecommendations(res.data);
        } catch (err) {
            setAssignError(err.message || "Failed to fetch technician recommendations.");
        } finally {
            setRecLoading(false);
        }
    };

    const handleAssignTechnician = async (techIdToAssign) => {
        const targetTechId = techIdToAssign || selectedTechId;
        if (!targetTechId) return;

        setAssigning(true);
        setAssignError("");
        setAssignSuccess("");
        try {
            await apiClient.post(`/incidents/${incidentId}/assign`, {
                technicianId: targetTechId,
            });
            setAssignSuccess("Technician successfully assigned!");
            setRecommendations(null);
            await loadIncident(incidentId);
        } catch (err) {
            setAssignError(err.message || "Failed to assign technician.");
        } finally {
            setAssigning(false);
        }
    };

    if (loading && !incident) {
        return (
            <main className="employee-page">
                <div className="employee-message">Loading incident details...</div>
            </main>
        );
    }

    if (error && !incident) {
        return (
            <main className="employee-page">
                <div className="employee-alert employee-alert-error">{error}</div>
            </main>
        );
    }

    if (!incident) {
        return (
            <main className="employee-page">
                <div className="employee-empty-state">
                    <h2>Incident not found</h2>
                    <p>The requested incident could not be loaded.</p>
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
                        onClick={() => (onBack ? onBack() : null)}
                    >
                        ← Back to Incidents
                    </button>

                    <p className="employee-eyebrow">INCIDENT DETAILS</p>
                    <h1>{incident.incidentCode}</h1>
                    <p>{incident.description}</p>
                </div>

                <div className="employee-inline-badges">
                    <IncidentPriorityBadge priority={incident.priority} />
                    <IncidentStatusBadge status={incident.status} />
                </div>
            </div>

            {error && <div className="employee-alert employee-alert-error">{error}</div>}

            {/* INCIDENT INFORMATION */}
            <section className="employee-section">
                <h2>Incident Information</h2>
                <div className="employee-details-grid">
                    <DetailItem label="Incident code" value={incident.incidentCode} />
                    <DetailItem label="Category" value={incident.category} />
                    <DetailItem label="Required Skill" value={incident.requiredSkill || "None"} />
                    <DetailItem label="Affected service" value={incident.serviceId} />
                    <DetailItem label="Priority" value={incident.priority} />
                    <DetailItem label="Impact" value={`${incident.impact}/5`} />
                    <DetailItem label="Urgency" value={`${incident.urgency}/5`} />
                    <DetailItem label="Business Criticality" value={`${incident.businessCriticality}/5`} />
                    <DetailItem label="Created" value={formatDate(incident.createdAt)} />
                    <DetailItem label="Last updated" value={formatDate(incident.updatedAt)} />
                    <DetailItem
                        label="Assigned Technician"
                        value={incident.assignedTechnicianId || "Unassigned"}
                    />
                </div>
            </section>

            {/* SLA TRACKING STATUS */}
            {sla && (
                <section className="employee-section">
                    <h2>SLA Tracking & Deadlines</h2>
                    <div className="employee-details-grid">
                        <DetailItem label="Policy Priority" value={sla.priority} />
                        <DetailItem label="SLA Status" value={sla.status} />
                        <DetailItem
                            label="Response Deadline"
                            value={formatDate(sla.responseDueAt)}
                        />
                        <DetailItem
                            label="Resolution Deadline"
                            value={formatDate(sla.resolutionDueAt)}
                        />
                        <DetailItem
                            label="Breached?"
                            value={sla.isBreached ? "YES (Breached)" : "No (Within SLA)"}
                        />
                        <DetailItem
                            label="Warning Sent?"
                            value={sla.warningSent ? "Yes" : "No"}
                        />
                    </div>
                </section>
            )}

            {/* ADMIN SMART RECOMMENDATION & ASSIGNMENT PANEL */}
            {isAdmin && ["NEW", "CLASSIFIED"].includes(incident.status) && (
                <section className="employee-section" style={{ borderLeft: "4px solid #0969da" }}>
                    <h2>Technician Recommendation & Assignment</h2>
                    <p className="employee-muted">
                        AI-assisted matching ranks technicians by skill proficiency, availability, and active workload.
                    </p>

                    {assignSuccess && (
                        <div className="employee-alert employee-alert-success" style={{ margin: "12px 0" }}>
                            {assignSuccess}
                        </div>
                    )}
                    {assignError && (
                        <div className="employee-alert employee-alert-error" style={{ margin: "12px 0" }}>
                            {assignError}
                        </div>
                    )}

                    <div style={{ display: "flex", gap: "12px", margin: "16px 0", flexWrap: "wrap" }}>
                        <button
                            type="button"
                            className="employee-button employee-button-primary"
                            disabled={recLoading || assigning}
                            onClick={fetchRecommendations}
                        >
                            {recLoading ? "Analyzing candidates..." : "⚡ Get Smart Recommendations"}
                        </button>
                    </div>

                    {/* Recommendations table */}
                    {recommendations?.recommendations && (
                        <div style={{ marginTop: "16px" }}>
                            <h3>Ranked Candidates ({recommendations.strategyUsed})</h3>
                            <div style={{ overflowX: "auto" }}>
                                <table className="employee-table" style={{ width: "100%", marginTop: "8px" }}>
                                    <thead>
                                        <tr>
                                            <th>Rank</th>
                                            <th>Technician Profile ID</th>
                                            <th>Match Score</th>
                                            <th>Skill Match</th>
                                            <th>LLM Enhanced</th>
                                            <th>Reasoning</th>
                                            <th>Action</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {recommendations.recommendations.map((rec) => (
                                            <tr key={rec.technicianId}>
                                                <td><strong>#{rec.rank}</strong></td>
                                                <td style={{ fontFamily: "monospace", fontSize: "12px" }}>{rec.technicianId}</td>
                                                <td>{rec.score?.toFixed(2)}</td>
                                                <td>{rec.skillMatch ? "✓ Yes" : "✗ No"}</td>
                                                <td>{rec.isLlmEnhanced ? "✨ Yes" : "No"}</td>
                                                <td style={{ fontSize: "13px" }}>{rec.explanation}</td>
                                                <td>
                                                    <button
                                                        type="button"
                                                        className="employee-button employee-button-primary"
                                                        style={{ padding: "4px 10px", fontSize: "12px" }}
                                                        disabled={assigning}
                                                        onClick={() => handleAssignTechnician(rec.technicianId)}
                                                    >
                                                        {assigning ? "Assigning..." : "Assign"}
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Manual Assignment Fallback */}
                    <div style={{ marginTop: "20px", paddingTop: "16px", borderTop: "1px solid #e6eaf0" }}>
                        <h4>Manual Assignment</h4>
                        <div style={{ display: "flex", gap: "12px", alignItems: "center", marginTop: "8px" }}>
                            <select
                                value={selectedTechId}
                                onChange={(e) => setSelectedTechId(e.target.value)}
                                style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #d0d7de", minWidth: "300px" }}
                            >
                                {techniciansList.map((t) => (
                                    <option key={t.id} value={t.id}>
                                        {t.id} — Status: {t.availability} (Active: {t.activeIncidentCount}/{t.maxCapacity})
                                    </option>
                                ))}
                            </select>
                            <button
                                type="button"
                                className="employee-button employee-button-secondary"
                                disabled={assigning || !selectedTechId}
                                onClick={() => handleAssignTechnician(selectedTechId)}
                            >
                                {assigning ? "Assigning..." : "Assign Selected"}
                            </button>
                        </div>
                    </div>
                </section>
            )}

            {/* LIFECYCLE TIMELINE */}
            <section className="employee-section">
                <h2>Incident Lifecycle</h2>
                <IncidentStatusTimeline currentStatus={incident.status} />
            </section>

            {/* RESOLUTION & ACTIONS */}
            <ResolutionPanel
                incident={incident}
                currentUser={currentUser}
                onStatusChange={handleStatusChange}
                saving={saving}
            />

            {/* COMMENTS */}
            <CommentSection
                comments={incident.comments || []}
                onSubmit={handleComment}
                saving={saving}
            />

            {/* DUPLICATE SUGGESTIONS */}
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
