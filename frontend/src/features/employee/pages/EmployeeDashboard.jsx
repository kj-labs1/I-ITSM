import React, { useEffect } from "react";

import useIncidents from "../hooks/useIncidents";

import IncidentCard from "../components/IncidentCard";

import {
    getIncidentStats,
} from "../utils/incidentHelpers";

export default function EmployeeDashboard({
    apiClient,
    onNavigate,
    onOpenIncident,
}) {
    const {
        incidents,
        loading,
        error,
        loadIncidents,
    } = useIncidents(apiClient);

    useEffect(() => {
        loadIncidents({
            skip: 0,
            limit: 100,
        }).catch(() => {
            // Error is displayed from the hook.
        });

        // Load when the shared API client changes.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const stats = getIncidentStats(incidents);

    const recentIncidents = [...incidents]
        .sort(
            (first, second) =>
                new Date(second.createdAt) -
                new Date(first.createdAt)
        )
        .slice(0, 5);

    const navigate = (path) => {
        if (onNavigate) {
            onNavigate(path);
        } else {
            window.location.assign(path);
        }
    };

    const openIncident = (id) => {
        if (onOpenIncident) {
            onOpenIncident(id);
        } else {
            navigate(`/employee/incidents/${id}`);
        }
    };

    return (
        <main className="employee-page">
            <div className="employee-page-header">
                <div>
                    <p className="employee-eyebrow">
                        EMPLOYEE PORTAL
                    </p>

                    <h1>Welcome to your dashboard</h1>

                    <p>
                        Report IT issues and keep track of their
                        progress in one place.
                    </p>
                </div>

                <button
                    type="button"
                    className="employee-button employee-button-primary"
                    onClick={() =>
                        navigate("/employee/incidents/new")
                    }
                >
                    + Report an incident
                </button>
            </div>

            {error && (
                <div className="employee-alert employee-alert-error">
                    {error}
                </div>
            )}

            <section className="employee-stats-grid">
                <StatCard
                    label="Total incidents"
                    value={loading ? "—" : stats.total}
                    description="Incidents loaded"
                />

                <StatCard
                    label="Open incidents"
                    value={loading ? "—" : stats.open}
                    description="Awaiting closure"
                />

                <StatCard
                    label="Resolved / closed"
                    value={loading ? "—" : stats.resolved}
                    description="Resolution completed"
                />

                <StatCard
                    label="Critical incidents"
                    value={loading ? "—" : stats.critical}
                    description="Priority P1 or P2"
                />
            </section>

            <section className="employee-section">
                <div className="employee-section-heading">
                    <div>
                        <h2>Recent incidents</h2>

                        <p className="employee-muted">
                            Your five most recently reported incidents.
                        </p>
                    </div>

                    <button
                        type="button"
                        className="employee-text-button"
                        onClick={() =>
                            navigate("/employee/incidents")
                        }
                    >
                        View all incidents →
                    </button>
                </div>

                {loading ? (
                    <div className="employee-message">
                        Loading your incidents...
                    </div>
                ) : recentIncidents.length === 0 ? (
                    <div className="employee-empty-state">
                        <h3>No incidents reported yet</h3>

                        <p>
                            When you report an IT problem,
                            it will appear here.
                        </p>

                        <button
                            type="button"
                            className="employee-button employee-button-primary"
                            onClick={() =>
                                navigate("/employee/incidents/new")
                            }
                        >
                            Report your first incident
                        </button>
                    </div>
                ) : (
                    <div className="employee-card-grid">
                        {recentIncidents.map((incident) => (
                            <IncidentCard
                                key={incident.id}
                                incident={incident}
                                onOpen={openIncident}
                            />
                        ))}
                    </div>
                )}
            </section>
        </main>
    );
}

function StatCard({
    label,
    value,
    description,
}) {
    return (
        <article className="employee-stat-card">
            <span>{label}</span>

            <strong>{value}</strong>

            <small>{description}</small>
        </article>
    );
}