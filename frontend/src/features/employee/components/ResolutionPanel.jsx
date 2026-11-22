import React, { useState } from "react";
import {
    CheckIcon,
    CheckCircle2Icon,
    PlayIcon,
    LockIcon,
} from "../../../components/Icons";

export default function ResolutionPanel({
    incident,
    currentUser,
    onStatusChange,
    saving = false,
}) {
    const [resolutionText, setResolutionText] = useState("");
    const [actionError, setActionError] = useState("");

    if (!incident) return null;

    const status = incident.status;
    const role = currentUser?.role || "EMPLOYEE";
    const isTech = role === "TECHNICIAN";
    const isAdmin = role === "ADMIN";
    const isEmp = role === "EMPLOYEE";

    const handleAction = async (newStatus, extraPayload = {}) => {
        setActionError("");
        try {
            await onStatusChange(newStatus, extraPayload);
        } catch (err) {
            setActionError(err.message || "Failed to update incident status.");
        }
    };

    return (
        <section className="employee-section">
            <h2>Incident Resolution & Lifecycle Actions</h2>

            {actionError && (
                <div className="employee-alert employee-alert-error" style={{ marginBottom: "16px" }}>
                    {actionError}
                </div>
            )}

            {/* Display resolution details if present */}
            {["RESOLVED", "VERIFIED", "CLOSED"].includes(status) && (
                <div className="employee-resolution-box" style={{ marginBottom: "20px" }}>
                    <p className="employee-resolution-label">
                        Technician's resolution details
                    </p>
                    <p>
                        {incident.resolutionDetails || "No resolution details were provided."}
                    </p>
                </div>
            )}

            {/* TECHNICIAN & ADMIN ACTIONS */}
            {(isTech || isAdmin) && (
                <>
                    {status === "ASSIGNED" && (
                        <div className="employee-resolution-action">
                            <p>
                                This incident has been assigned to you. Acknowledge receipt to notify the team.
                            </p>
                            <button
                                type="button"
                                disabled={saving}
                                className="employee-button employee-button-primary"
                                onClick={() => handleAction("ACKNOWLEDGED")}
                                style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
                            >
                                {saving ? "Acknowledging..." : (
                                    <>
                                        <CheckIcon size={16} strokeWidth={2.5} /> Acknowledge Incident
                                    </>
                                )}
                            </button>
                        </div>
                    )}

                    {status === "ACKNOWLEDGED" && (
                        <div className="employee-resolution-action">
                            <p>
                                Incident acknowledged. When you begin working on this issue, start active resolution work.
                            </p>
                            <button
                                type="button"
                                disabled={saving}
                                className="employee-button employee-button-primary"
                                onClick={() => handleAction("IN_PROGRESS")}
                                style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
                            >
                                {saving ? "Starting..." : (
                                    <>
                                        <PlayIcon size={14} /> Start Work (In Progress)
                                    </>
                                )}
                            </button>
                        </div>
                    )}

                    {status === "IN_PROGRESS" && (
                        <div className="employee-resolution-action" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                            <p>
                                Active work is in progress. Enter detailed resolution steps before marking as resolved:
                            </p>
                            <textarea
                                className="employee-textarea"
                                rows={4}
                                style={{ width: "100%", padding: "10px", borderRadius: "6px", border: "1px solid #d0d7de" }}
                                placeholder="Describe the resolution steps taken (required)..."
                                value={resolutionText}
                                onChange={(e) => setResolutionText(e.target.value)}
                            />
                            <div>
                                <button
                                    type="button"
                                    disabled={saving || !resolutionText.trim()}
                                    className="employee-button employee-button-primary"
                                    onClick={() => handleAction("RESOLVED", { resolutionDetails: resolutionText })}
                                    style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
                                >
                                    {saving ? "Resolving..." : (
                                        <>
                                            <CheckCircle2Icon size={16} /> Mark Incident as Resolved
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    )}

                    {status === "RESOLVED" && isTech && !isAdmin && (
                        <p className="employee-muted">
                            Incident marked as RESOLVED. Awaiting employee verification.
                        </p>
                    )}
                </>
            )}

            {/* EMPLOYEE & ADMIN ACTIONS */}
            {(isEmp || isAdmin) && (
                <>
                    {status === "RESOLVED" && (
                        <div className="employee-resolution-action">
                            <p>
                                Please test and verify whether the reported issue has been completely resolved.
                            </p>
                            <button
                                type="button"
                                disabled={saving}
                                className="employee-button employee-button-primary"
                                onClick={() => handleAction("VERIFIED")}
                                style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
                            >
                                {saving ? "Verifying..." : (
                                    <>
                                        <CheckIcon size={16} strokeWidth={2.5} /> Verify Resolution
                                    </>
                                )}
                            </button>
                        </div>
                    )}

                    {status === "VERIFIED" && (
                        <div className="employee-resolution-action">
                            <p>
                                The resolution has been verified. You can now permanently close this incident.
                            </p>
                            <button
                                type="button"
                                disabled={saving}
                                className="employee-button employee-button-primary"
                                onClick={() => handleAction("CLOSED")}
                                style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
                            >
                                {saving ? "Closing..." : (
                                    <>
                                        <LockIcon size={16} /> Close Incident
                                    </>
                                )}
                            </button>
                        </div>
                    )}

                    {status === "CLOSED" && (
                        <p className="employee-success" style={{ color: "#1a7f37", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: "6px" }}>
                            <CheckCircle2Icon size={18} color="#16a34a" /> This incident has been successfully closed and archived.
                        </p>
                    )}

                    {!["RESOLVED", "VERIFIED", "CLOSED"].includes(status) && isEmp && (
                        <p className="employee-muted">
                            {status === "NEW" && "Incident has been reported and is awaiting triage."}
                            {status === "CLASSIFIED" && "Incident is classified and awaiting technician assignment."}
                            {status === "ASSIGNED" && "Incident is assigned to a technician."}
                            {status === "ACKNOWLEDGED" && "Technician has acknowledged this incident."}
                            {status === "IN_PROGRESS" && "Technician is actively investigating and working on resolution."}
                        </p>
                    )}
                </>
            )}
        </section>
    );
}
