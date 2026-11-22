import React, { useState } from "react";
import { CheckIcon } from "../../../components/Icons";

import useIncidents from "../hooks/useIncidents";

export default function ReportIncident({
    apiClient,
    services = [],
    categories = [],
    onSuccess,
    onCancel,
}) {
    const {
        createIncident,
        saving,
        error,
    } = useIncidents(apiClient);

    const [form, setForm] = useState({
        serviceId: "",
        category: "",
        description: "",
        impact: 3,
        urgency: 3,
    });

    const [localError, setLocalError] = useState("");
    const [createdIncident, setCreatedIncident] = useState(null);

    const updateField = (field, value) => {
        setForm((previous) => ({
            ...previous,
            [field]: value,
        }));

        setLocalError("");
    };

    const selectedService = services.find(
        (service) =>
            String(service.id ?? service.serviceId) === form.serviceId
    );

    const selectedCategory = categories.find(
        (category) => {
            const categoryName =
                typeof category === "string"
                    ? category
                    : category.name ?? category.category;

            return categoryName === form.category;
        }
    );

    const handleSubmit = async (event) => {
        event.preventDefault();

        setLocalError("");
        setCreatedIncident(null);

        if (!selectedService) {
            setLocalError("Please select a valid service.");
            return;
        }

        if (!selectedCategory) {
            setLocalError("Please select a valid category.");
            return;
        }

        const businessCriticality = Number(
            selectedService.businessCriticality
        );

        const requiredSkill =
            typeof selectedCategory === "string"
                ? undefined
                : selectedCategory.requiredSkill ??
                  selectedCategory.required_skill;

        if (
            !Number.isInteger(businessCriticality) ||
            businessCriticality < 1 ||
            businessCriticality > 5
        ) {
            setLocalError(
                "The selected service does not have a valid business criticality configured."
            );
            return;
        }

        if (!requiredSkill) {
            setLocalError(
                "The selected category does not have a required skill mapping configured."
            );
            return;
        }

        if (form.description.trim().length < 10) {
            setLocalError(
                "Please provide a description with at least 10 characters."
            );
            return;
        }

        const payload = {
            serviceId:
                selectedService.id ?? selectedService.serviceId,

            category: form.category,

            requiredSkill,

            description: form.description.trim(),

            impact: Number(form.impact),

            urgency: Number(form.urgency),

            businessCriticality,
        };

        try {
            const result = await createIncident(payload);

            setCreatedIncident(result);

            if (onSuccess) {
                onSuccess(result);
            }
        } catch {
            // The hook provides the API error.
        }
    };

    const startAnotherIncident = () => {
        setForm({
            serviceId: "",
            category: "",
            description: "",
            impact: 3,
            urgency: 3,
        });

        setCreatedIncident(null);
    };

    if (createdIncident) {
        return (
            <main className="employee-page">
                <div className="employee-success-panel">
                    <div className="employee-success-icon">
                        <CheckIcon size={28} strokeWidth={2.5} color="#16a34a" />
                    </div>

                    <h1>Incident reported successfully</h1>

                    <p>
                        Your incident has been recorded.
                        You can track its progress from My Incidents.
                    </p>

                    <div className="employee-created-ticket">
                        <span>Incident Database ID</span>
                        <strong style={{ fontFamily: "monospace", fontSize: "12px", wordBreak: "break-all" }}>
                            {createdIncident.id}
                        </strong>

                        <span>Incident code</span>

                        <strong>
                            {createdIncident.incidentCode}
                        </strong>

                        <span>Calculated priority</span>

                        <strong>
                            {createdIncident.priority}
                        </strong>
                    </div>

                    <div className="employee-action-row">
                        <button
                            type="button"
                            className="employee-button employee-button-primary"
                            onClick={() =>
                                onSuccess ? onSuccess(createdIncident) : null
                            }
                        >
                            View incident
                        </button>

                        <button
                            type="button"
                            className="employee-button employee-button-secondary"
                            onClick={startAnotherIncident}
                        >
                            Report another incident
                        </button>
                    </div>
                </div>
            </main>
        );
    }

    return (
        <main className="employee-page">
            <div className="employee-page-header">
                <div>
                    <p className="employee-eyebrow">
                        EMPLOYEE PORTAL
                    </p>

                    <h1>Report an Incident</h1>

                    <p>
                        Provide details about the IT problem you
                        are experiencing.
                    </p>
                </div>
            </div>

            {(localError || error) && (
                <div className="employee-alert employee-alert-error">
                    {localError || error}
                </div>
            )}

            <form
                className="employee-form employee-form-panel"
                onSubmit={handleSubmit}
            >
                <div className="employee-field">
                    <label htmlFor="serviceId">
                        Affected service *
                    </label>

                    <select
                        id="serviceId"
                        required
                        value={form.serviceId}
                        onChange={(event) =>
                            updateField(
                                "serviceId",
                                event.target.value
                            )
                        }
                    >
                        <option value="">
                            Select affected service
                        </option>

                        {services.map((service) => {
                            const id =
                                service.id ?? service.serviceId;

                            return (
                                <option key={id} value={id}>
                                    {service.name}
                                </option>
                            );
                        })}
                    </select>

                    {services.length === 0 && (
                        <small>
                            Service catalogue data has not been
                            connected yet.
                        </small>
                    )}
                </div>

                <div className="employee-field">
                    <label htmlFor="category">
                        Incident category *
                    </label>

                    <select
                        id="category"
                        required
                        value={form.category}
                        onChange={(event) =>
                            updateField(
                                "category",
                                event.target.value
                            )
                        }
                    >
                        <option value="">
                            Select category
                        </option>

                        {categories.map((category) => {
                            const name =
                                typeof category === "string"
                                    ? category
                                    : category.name ??
                                      category.category;

                            return (
                                <option key={name} value={name}>
                                    {name}
                                </option>
                            );
                        })}
                    </select>
                </div>

                <div className="employee-field">
                    <label htmlFor="description">
                        Problem description *
                    </label>

                    <textarea
                        id="description"
                        rows="6"
                        required
                        minLength={10}
                        maxLength={5000}
                        placeholder="Describe the problem, what happened and when it started..."
                        value={form.description}
                        onChange={(event) =>
                            updateField(
                                "description",
                                event.target.value
                            )
                        }
                    />

                    <small>
                        {form.description.length}/5000 characters
                    </small>
                </div>

                <div className="employee-form-grid">
                    <div className="employee-field">
                        <label htmlFor="impact">
                            Impact *
                        </label>

                        <select
                            id="impact"
                            value={form.impact}
                            onChange={(event) =>
                                updateField(
                                    "impact",
                                    Number(event.target.value)
                                )
                            }
                        >
                            {[1, 2, 3, 4, 5].map((value) => (
                                <option key={value} value={value}>
                                    {value} - {impactLabel(value)}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="employee-field">
                        <label htmlFor="urgency">
                            Urgency *
                        </label>

                        <select
                            id="urgency"
                            value={form.urgency}
                            onChange={(event) =>
                                updateField(
                                    "urgency",
                                    Number(event.target.value)
                                )
                            }
                        >
                            {[1, 2, 3, 4, 5].map((value) => (
                                <option key={value} value={value}>
                                    {value} - {urgencyLabel(value)}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                <p className="employee-form-note">
                    Priority will be calculated automatically by
                    the incident management system.
                </p>

                <div className="employee-form-actions">
                    {onCancel && (
                        <button
                            type="button"
                            className="employee-button employee-button-secondary"
                            onClick={onCancel}
                        >
                            Cancel
                        </button>
                    )}

                    <button
                        type="submit"
                        disabled={
                            saving ||
                            services.length === 0 ||
                            categories.length === 0
                        }
                        className="employee-button employee-button-primary"
                    >
                        {saving
                            ? "Submitting..."
                            : "Submit incident"}
                    </button>
                </div>
            </form>
        </main>
    );
}

function impactLabel(value) {
    return {
        1: "Very low",
        2: "Low",
        3: "Moderate",
        4: "High",
        5: "Very high",
    }[value];
}

function urgencyLabel(value) {
    return {
        1: "Very low",
        2: "Low",
        3: "Moderate",
        4: "High",
        5: "Critical",
    }[value];
}