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
        archiveIncident,
        mergeIncidents,
    } = useIncidents(apiClient);

    const [sla, setSla] = useState(null);
    const [recommendations, setRecommendations] = useState(null);
    const [recLoading, setRecLoading] = useState(false);
    const [assigning, setAssigning] = useState(false);
    const [assignSuccess, setAssignSuccess] = useState("");
    const [assignError, setAssignError] = useState("");
    const [techniciansList, setTechniciansList] = useState([]);
    const [selectedTechId, setSelectedTechId] = useState("");

    // Archiving & Merging states
    const [showArchiveModal, setShowArchiveModal] = useState(false);
    const [archiving, setArchiving] = useState(false);
    const [archiveSuccess, setArchiveSuccess] = useState("");
    const [archiveError, setArchiveError] = useState("");

    const [mergeCandidate, setMergeCandidate] = useState(null);
    const [merging, setMerging] = useState(false);
    const [mergeSuccess, setMergeSuccess] = useState("");
    const [mergeError, setMergeError] = useState("");

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
                    if (list.length > 0) setSelectedTechId(list[0].userId || list[0].id);
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

    const handleAssignTechnician = async (techUserIdToAssign) => {
        const targetUserId = techUserIdToAssign || selectedTechId;
        if (!targetUserId) return;

        setAssigning(true);
        setAssignError("");
        setAssignSuccess("");
        try {
            await apiClient.post(`/incidents/${incidentId}/assign`, {
                technicianUserId: targetUserId,
                technicianId: targetUserId,
            });
            setAssignSuccess("Technician successfully assigned using User ID!");
            setRecommendations(null);
            await loadIncident(incidentId);
        } catch (err) {
            setAssignError(err.message || "Failed to assign technician.");
        } finally {
            setAssigning(false);
        }
    };

    const handleArchive = async () => {
        setArchiving(true);
        setArchiveError("");
        setArchiveSuccess("");
        try {
            await archiveIncident(incidentId);
            setArchiveSuccess("Incident successfully archived.");
            setShowArchiveModal(false);
            await loadIncident(incidentId);
        } catch (err) {
            setArchiveError(err.message || "Failed to archive incident.");
        } finally {
            setArchiving(false);
        }
    };

    const handlePromptMerge = (candidate) => {
        setMergeCandidate(candidate);
        setMergeError("");
        setMergeSuccess("");
    };

    const handleConfirmMerge = async () => {
        if (!mergeCandidate) return;
        setMerging(true);
        setMergeError("");
        setMergeSuccess("");
        try {
            await mergeIncidents(incidentId, [mergeCandidate.incidentId]);
            setMergeSuccess(`Successfully merged incident ${mergeCandidate.incidentCode} into this primary incident.`);
            setMergeCandidate(null);
            await loadIncident(incidentId);
            await loadDuplicates(incidentId);
        } catch (err) {
            setMergeError(err.message || "Failed to merge duplicate incident.");
        } finally {
            setMerging(false);
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
                    <p style={{ fontFamily: "monospace", fontSize: "12px", color: "#656d76", margin: "4px 0" }}>
                        Database ID: <strong>{incident.id}</strong>
                    </p>
                    <p>{incident.description}</p>
                </div>

                <div className="employee-inline-badges">
                    <IncidentPriorityBadge priority={incident.priority} />
                    <IncidentStatusBadge status={incident.status} />
                </div>
            </div>

            {error && <div className="employee-alert employee-alert-error">{error}</div>}
            {archiveError && <div className="employee-alert employee-alert-error">{archiveError}</div>}
            {archiveSuccess && <div className="employee-alert employee-alert-success">{archiveSuccess}</div>}
            {mergeError && <div className="employee-alert employee-alert-error">{mergeError}</div>}
            {mergeSuccess && <div className="employee-alert employee-alert-success">{mergeSuccess}</div>}

            {incident.isArchived && (
                <div style={{ padding: "14px 18px", backgroundColor: "#fff8c5", border: "1px solid #d4a72c", borderRadius: "6px", margin: "16px 0", color: "#594200" }}>
                    <strong>This incident is ARCHIVED.</strong> It was archived on {formatDate(incident.archivedAt)}. Archived incidents are preserved in read-only mode for audit compliance.
                </div>
            )}

            {incident.mergedIntoIncidentId && (
                <div style={{ padding: "14px 18px", backgroundColor: "#fbefff", border: "1px solid #d8b9ff", borderRadius: "6px", margin: "16px 0", color: "#54249a", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                        <strong>🔗 This incident was MERGED into primary incident:</strong> <code>{incident.mergedIntoIncidentId}</code>
                    </div>
                    <button
                        type="button"
                        className="employee-button employee-button-secondary"
                        style={{ fontSize: "12px", padding: "4px 12px" }}
                        onClick={() => openAnotherIncident(incident.mergedIntoIncidentId)}
                    >
                        View Primary Incident →
                    </button>
                </div>
            )}

            {/* INCIDENT INFORMATION */}
            <section className="employee-section">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <h2>Incident Information</h2>
                    {isAdmin && incident.status === "CLOSED" && !incident.isArchived && (
                        <button
                            type="button"
                            className="employee-button employee-button-danger"
                            onClick={() => setShowArchiveModal(true)}
                            disabled={archiving}
                        >
                            Archive Incident
                        </button>
                    )}
                </div>
                <div className="employee-details-grid" style={{ marginTop: "12px" }}>
                    <DetailItem label="Incident Database ID" value={incident.id} />
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
                        label="Assigned Technician (User ID)"
                        value={incident.assignedTechnicianId || "Unassigned"}
                    />
                    <DetailItem
                        label="Archived Status"
                        value={incident.isArchived ? `Archived (${formatDate(incident.archivedAt)})` : "Active (Not Archived)"}
                    />
                    {incident.mergedIntoIncidentId && (
                        <DetailItem
                            label="Merged Into Primary ID"
                            value={incident.mergedIntoIncidentId}
                        />
                    )}
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
                                            <th>Technician</th>
                                            <th>Skills</th>
                                            <th>Match Score</th>
                                            <th>Skill Match</th>
                                            <th>LLM Enhanced</th>
                                            <th>Reasoning</th>
                                            <th>Action</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {recommendations.recommendations.map((rec) => {
                                            const techUserId = rec.userId || rec.technicianUserId;
                                            const techObj = techniciansList.find((t) => t.userId === techUserId || t.id === rec.technicianId);
                                            const username = rec.username || techObj?.username || "Technician";
                                            const fullName = rec.fullName || techObj?.fullName || "";
                                            const skills = (rec.skills && rec.skills.length > 0) ? rec.skills : techObj?.skills;

                                            return (
                                                <tr key={rec.technicianId}>
                                                    <td><strong>#{rec.rank}</strong></td>
                                                    <td>
                                                        <strong>{username}</strong>
                                                        {fullName && fullName !== username && (
                                                            <div style={{ fontSize: "12px", color: "#57606a" }}>{fullName}</div>
                                                        )}
                                                    </td>
                                                    <td>
                                                        {!skills || skills.length === 0 ? (
                                                            <span style={{ color: "#656d76", fontStyle: "italic", fontSize: "12px" }}>No skills listed</span>
                                                        ) : (
                                                            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                                                                {skills.map((s) => (
                                                                    <span
                                                                        key={s.id || s.skillName || s.skill_name}
                                                                        style={{
                                                                            fontSize: "11px",
                                                                            padding: "1px 6px",
                                                                            borderRadius: "10px",
                                                                            backgroundColor: "#ddf4ff",
                                                                            color: "#0969da",
                                                                            border: "1px solid #54aeff44",
                                                                            fontWeight: "500",
                                                                        }}
                                                                    >
                                                                        {s.skillName || s.skill_name} ({s.proficiencyLevel || s.proficiency_level}/5)
                                                                    </span>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </td>
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
                                                            onClick={() => handleAssignTechnician(techUserId)}
                                                        >
                                                            {assigning ? "Assigning..." : "Assign"}
                                                        </button>
                                                    </td>
                                                </tr>
                                            );
                                        })}
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
                                style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #d0d7de", minWidth: "320px" }}
                            >
                                {techniciansList.map((t) => (
                                    <option key={t.id} value={t.userId}>
                                        {t.username ? `${t.username} — ${t.fullName || t.username}` : t.fullName || "Technician"} ({t.availability}, Workload: {t.activeIncidentCount}/{t.maxCapacity})
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
                isAdmin={isAdmin && !incident.isArchived && !incident.mergedIntoIncidentId}
                onMerge={handlePromptMerge}
            />

            {/* ARCHIVE CONFIRMATION MODAL */}
            {showArchiveModal && (
                <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
                    <div style={{ backgroundColor: "#fff", padding: "24px", borderRadius: "8px", maxWidth: "480px", width: "90%", boxShadow: "0 4px 12px rgba(0,0,0,0.15)" }}>
                        <h3 style={{ margin: "0 0 12px 0" }}>Confirm Incident Archiving</h3>
                        <p style={{ margin: "12px 0", color: "#24292f" }}>
                            Are you sure you want to archive incident <strong>{incident.incidentCode}</strong> (ID: <code>{incident.id}</code>)?
                        </p>
                        <p style={{ fontSize: "13px", color: "#57606a", marginBottom: "20px" }}>
                            Archived incidents will be excluded from default active incident lists and preserved for compliance and audit logs.
                        </p>
                        <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
                            <button
                                type="button"
                                className="employee-button employee-button-secondary"
                                onClick={() => setShowArchiveModal(false)}
                                disabled={archiving}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                className="employee-button employee-button-danger"
                                onClick={handleArchive}
                                disabled={archiving}
                            >
                                {archiving ? "Archiving..." : "Yes, Archive"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* MERGE CONFIRMATION MODAL */}
            {mergeCandidate && (
                <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
                    <div style={{ backgroundColor: "#fff", padding: "24px", borderRadius: "8px", maxWidth: "520px", width: "90%", boxShadow: "0 4px 12px rgba(0,0,0,0.15)" }}>
                        <h3 style={{ margin: "0 0 12px 0" }}>Confirm Duplicate Incident Merge</h3>
                        <p style={{ margin: "12px 0", color: "#24292f" }}>
                            You are merging duplicate incident <strong>{mergeCandidate.incidentCode}</strong> into current primary incident <strong>{incident.incidentCode}</strong>.
                        </p>
                        <div style={{ backgroundColor: "#f6f8fa", padding: "12px", borderRadius: "6px", fontSize: "13px", color: "#57606a", marginBottom: "16px" }}>
                            <div>• <strong>Primary Incident:</strong> {incident.incidentCode} ({incident.id})</div>
                            <div>• <strong>Duplicate Incident:</strong> {mergeCandidate.incidentCode} ({mergeCandidate.incidentId})</div>
                            <div>• Duplicate status will be changed to <strong>CLOSED</strong>.</div>
                            <div>• Duplicate comments and history will be referenced on this primary incident.</div>
                        </div>
                        <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
                            <button
                                type="button"
                                className="employee-button employee-button-secondary"
                                onClick={() => setMergeCandidate(null)}
                                disabled={merging}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                className="employee-button employee-button-primary"
                                onClick={handleConfirmMerge}
                                disabled={merging}
                            >
                                {merging ? "Merging..." : "Confirm & Merge"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
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
