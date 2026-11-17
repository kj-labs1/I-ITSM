import React from "react";

export default function ResolutionPanel({
    incident,
    onStatusChange,
    saving = false,
}) {
    if (!incident) return null;

    const status = incident.status;

    if (!["RESOLVED", "VERIFIED", "CLOSED"].includes(status)) {
        return (
            <section className="employee-section">
                <h2>Resolution</h2>

                <p className="employee-muted">
                    Resolution details will appear here after
                    the assigned technician resolves the incident.
                </p>
            </section>
        );
    }

    return (
        <section className="employee-section">
            <h2>Resolution</h2>

            <div className="employee-resolution-box">
                <p className="employee-resolution-label">
                    Technician's resolution details
                </p>

                <p>
                    {incident.resolutionDetails ||
                        "No resolution details were provided."}
                </p>
            </div>

            {status === "RESOLVED" && (
                <div className="employee-resolution-action">
                    <p>
                        Please verify whether the reported issue
                        has been resolved.
                    </p>

                    <button
                        type="button"
                        disabled={saving}
                        className="employee-button employee-button-primary"
                        onClick={() => onStatusChange("VERIFIED")}
                    >
                        {saving
                            ? "Updating..."
                            : "Verify resolution"}
                    </button>
                </div>
            )}

            {status === "VERIFIED" && (
                <div className="employee-resolution-action">
                    <p>
                        The resolution has been verified.
                        You can now close this incident.
                    </p>

                    <button
                        type="button"
                        disabled={saving}
                        className="employee-button employee-button-primary"
                        onClick={() => onStatusChange("CLOSED")}
                    >
                        {saving
                            ? "Closing..."
                            : "Close incident"}
                    </button>
                </div>
            )}

            {status === "CLOSED" && (
                <p className="employee-success">
                    This incident has been successfully closed.
                </p>
            )}
        </section>
    );
}