import React from "react";

import {
    INCIDENT_CATEGORIES,
    INCIDENT_STATUSES,
    PRIORITIES,
} from "../utils/incidentHelpers";

export default function IncidentFilters({
    filters,
    onChange,
    onApply,
    onReset,
}) {
    const updateField = (field, value) => {
        onChange({
            ...filters,
            [field]: value,
        });
    };

    const handleSubmit = (event) => {
        event.preventDefault();
        onApply();
    };

    return (
        <form
            className="employee-filters"
            onSubmit={handleSubmit}
        >
            <div className="employee-filter-grid">
                <div className="employee-field">
                    <label htmlFor="incidentCode">
                        Incident ID / Code
                    </label>

                    <input
                        id="incidentCode"
                        type="text"
                        placeholder="Search incident code..."
                        value={filters.incidentCode}
                        onChange={(event) =>
                            updateField(
                                "incidentCode",
                                event.target.value
                            )
                        }
                    />
                </div>

                <div className="employee-field">
                    <label htmlFor="incidentStatus">
                        Status
                    </label>

                    <select
                        id="incidentStatus"
                        value={filters.status}
                        onChange={(event) =>
                            updateField(
                                "status",
                                event.target.value
                            )
                        }
                    >
                        <option value="">All statuses</option>

                        {INCIDENT_STATUSES.map((status) => (
                            <option key={status} value={status}>
                                {status.replaceAll("_", " ")}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="employee-field">
                    <label htmlFor="incidentPriority">
                        Priority
                    </label>

                    <select
                        id="incidentPriority"
                        value={filters.priority}
                        onChange={(event) =>
                            updateField(
                                "priority",
                                event.target.value
                            )
                        }
                    >
                        <option value="">All priorities</option>

                        {PRIORITIES.map((priority) => (
                            <option
                                key={priority}
                                value={priority}
                            >
                                {priority}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="employee-field">
                    <label htmlFor="incidentCategory">
                        Category
                    </label>

                    <select
                        id="incidentCategory"
                        value={filters.category}
                        onChange={(event) =>
                            updateField(
                                "category",
                                event.target.value
                            )
                        }
                    >
                        <option value="">All categories</option>

                        {INCIDENT_CATEGORIES.map((category) => (
                            <option
                                key={category}
                                value={category}
                            >
                                {category}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="employee-field">
                    <label htmlFor="dateFrom">
                        Date from
                    </label>

                    <input
                        id="dateFrom"
                        type="date"
                        value={filters.dateFrom}
                        onChange={(event) =>
                            updateField(
                                "dateFrom",
                                event.target.value
                            )
                        }
                    />
                </div>

                <div className="employee-field">
                    <label htmlFor="dateTo">
                        Date to
                    </label>

                    <input
                        id="dateTo"
                        type="date"
                        value={filters.dateTo}
                        onChange={(event) =>
                            updateField(
                                "dateTo",
                                event.target.value
                            )
                        }
                    />
                </div>
            </div>

            <div className="employee-filter-actions">
                <button
                    type="submit"
                    className="employee-button employee-button-primary"
                >
                    Apply filters
                </button>

                <button
                    type="button"
                    className="employee-button employee-button-secondary"
                    onClick={onReset}
                >
                    Clear filters
                </button>
            </div>
        </form>
    );
}