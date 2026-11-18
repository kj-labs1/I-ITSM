import React, { useEffect, useState } from "react";

import useIncidents from "../hooks/useIncidents";

import IncidentFilters from "../components/IncidentFilters";
import IncidentTable from "../components/IncidentTable";

import {
    localDateBoundary,
} from "../utils/incidentHelpers";

const INITIAL_FILTERS = {
    incidentCode: "",
    status: "",
    priority: "",
    category: "",
    dateFrom: "",
    dateTo: "",
};

export default function MyIncidents({
    apiClient,
    currentUser,
    onOpenIncident,
    onNavigate,
}) {
    const {
        incidents,
        loading,
        error,
        loadIncidents,
        clearError,
    } = useIncidents(apiClient);

    const [filters, setFilters] = useState(INITIAL_FILTERS);
    const [activeFilters, setActiveFilters] = useState({});

    const isTech = currentUser?.role === "TECHNICIAN";
    const isAdmin = currentUser?.role === "ADMIN";

    const fetchIncidents = async (params = {}) => {
        try {
            await loadIncidents({
                skip: 0,
                limit: 50,
                ...params,
            });
        } catch {
            // Error is displayed through the hook.
        }
    };

    useEffect(() => {
        fetchIncidents();
        // Initial fetch only. Filtering is triggered by the Apply button.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const applyFilters = () => {
        clearError();

        const params = {};

        if (filters.incidentCode.trim()) {
            params.incidentCode = filters.incidentCode.trim();
        }

        if (filters.status) {
            params.status = filters.status;
        }

        if (filters.priority) {
            params.priority = filters.priority;
        }

        if (filters.category) {
            params.category = filters.category;
        }

        if (filters.dateFrom) {
            params.dateFrom = localDateBoundary(
                filters.dateFrom
            );
        }

        if (filters.dateTo) {
            params.dateTo = localDateBoundary(
                filters.dateTo,
                true
            );
        }

        setActiveFilters(params);
        fetchIncidents(params);
    };

    const resetFilters = () => {
        setFilters(INITIAL_FILTERS);
        setActiveFilters({});
        clearError();
        fetchIncidents();
    };

    const handleOpen = (incidentId) => {
        if (onOpenIncident) {
            onOpenIncident(incidentId);
        }
    };

    return (
        <main className="employee-page">
            <div className="employee-page-header">
                <div>
                    <p className="employee-eyebrow">
                        {isTech ? "TECHNICIAN WORKSPACE" : isAdmin ? "ADMIN WORKSPACE" : "EMPLOYEE PORTAL"}
                    </p>

                    <h1>{isTech ? "Assigned Incidents" : isAdmin ? "Incident Management" : "My Incidents"}</h1>

                    <p>
                        {isTech
                            ? "View, track, and resolve IT incidents assigned directly to you."
                            : isAdmin
                              ? "Monitor, triage, and manage all organization incidents across their lifecycle."
                              : "View and track all IT incidents you have reported."}
                    </p>
                </div>

                {!isTech && (
                    <button
                        type="button"
                        className="employee-button employee-button-primary"
                        onClick={() =>
                            onNavigate
                                ? onNavigate("report-incident")
                                : null
                        }
                    >
                        + Report incident
                    </button>
                )}
            </div>

            <section className="employee-section">
                <h2>Search and filter</h2>

                <IncidentFilters
                    filters={filters}
                    onChange={setFilters}
                    onApply={applyFilters}
                    onReset={resetFilters}
                />
            </section>

            {error && (
                <div className="employee-alert employee-alert-error">
                    {error}
                </div>
            )}

            <section className="employee-section">
                <div className="employee-section-heading">
                    <div>
                        <h2>Incident records</h2>

                        <p className="employee-muted">
                            Showing up to 50 matching incidents.
                        </p>
                    </div>

                    <button
                        type="button"
                        className="employee-button employee-button-secondary"
                        onClick={() => fetchIncidents(activeFilters)}
                        disabled={loading}
                    >
                        Refresh
                    </button>
                </div>

                <IncidentTable
                    incidents={incidents}
                    loading={loading}
                    onOpen={handleOpen}
                />
            </section>
        </main>
    );
}