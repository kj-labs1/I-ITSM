import { useCallback, useMemo, useState } from "react";

import { createIncidentApi } from "../api/incidentApi";
import { getErrorMessage } from "../utils/incidentHelpers";

export default function useIncidents(apiClient) {
    const api = useMemo(
        () => createIncidentApi(apiClient),
        [apiClient]
    );

    const [incidents, setIncidents] = useState([]);
    const [incident, setIncident] = useState(null);
    const [duplicates, setDuplicates] = useState([]);

    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");

    const loadIncidents = useCallback(
        async (params = {}) => {
            setLoading(true);
            setError("");

            try {
                const data = await api.getIncidents(params);
                setIncidents(data);
                return data;
            } catch (err) {
                setError(getErrorMessage(err));
                throw err;
            } finally {
                setLoading(false);
            }
        },
        [api]
    );

    const loadIncident = useCallback(
        async (incidentId) => {
            setLoading(true);
            setError("");

            try {
                const data = await api.getIncidentById(incidentId);
                setIncident(data);
                return data;
            } catch (err) {
                setError(getErrorMessage(err));
                throw err;
            } finally {
                setLoading(false);
            }
        },
        [api]
    );

    const createIncident = useCallback(
        async (payload) => {
            setSaving(true);
            setError("");

            try {
                const created = await api.createIncident(payload);

                setIncidents((previous) => [
                    created,
                    ...previous,
                ]);

                return created;
            } catch (err) {
                setError(getErrorMessage(err));
                throw err;
            } finally {
                setSaving(false);
            }
        },
        [api]
    );

    const updateIncident = useCallback(
        async (incidentId, payload) => {
            setSaving(true);
            setError("");

            try {
                const updated = await api.updateIncident(
                    incidentId,
                    payload
                );

                setIncident((previous) =>
                    previous?.id === incidentId
                        ? { ...previous, ...updated }
                        : previous
                );

                setIncidents((previous) =>
                    previous.map((item) =>
                        item.id === incidentId
                            ? { ...item, ...updated }
                            : item
                    )
                );

                return updated;
            } catch (err) {
                setError(getErrorMessage(err));
                throw err;
            } finally {
                setSaving(false);
            }
        },
        [api]
    );

    const updateIncidentStatus = useCallback(
        async (incidentId, payload) => {
            setSaving(true);
            setError("");

            try {
                const updated = await api.updateIncidentStatus(
                    incidentId,
                    payload
                );

                setIncident((previous) =>
                    previous?.id === incidentId
                        ? { ...previous, ...updated }
                        : previous
                );

                setIncidents((previous) =>
                    previous.map((item) =>
                        item.id === incidentId
                            ? { ...item, ...updated }
                            : item
                    )
                );

                return updated;
            } catch (err) {
                setError(getErrorMessage(err));
                throw err;
            } finally {
                setSaving(false);
            }
        },
        [api]
    );

    const addComment = useCallback(
        async (incidentId, payload) => {
            setSaving(true);
            setError("");

            try {
                const comment = await api.addComment(
                    incidentId,
                    payload
                );

                setIncident((previous) => {
                    if (previous?.id !== incidentId) {
                        return previous;
                    }

                    return {
                        ...previous,
                        comments: [
                            ...(previous.comments || []),
                            comment,
                        ],
                    };
                });

                return comment;
            } catch (err) {
                setError(getErrorMessage(err));
                throw err;
            } finally {
                setSaving(false);
            }
        },
        [api]
    );

    const loadDuplicates = useCallback(
        async (incidentId) => {
            setError("");

            try {
                const data = await api.getPotentialDuplicates(
                    incidentId
                );

                setDuplicates(data);
                return data;
            } catch (err) {
                setError(getErrorMessage(err));
                throw err;
            }
        },
        [api]
    );

    const archiveIncident = useCallback(
        async (incidentId) => {
            setSaving(true);
            setError("");
            try {
                const archived = await api.archiveIncident(incidentId);
                setIncident((previous) =>
                    previous?.id === incidentId ? { ...previous, ...archived } : previous
                );
                return archived;
            } catch (err) {
                setError(getErrorMessage(err));
                throw err;
            } finally {
                setSaving(false);
            }
        },
        [api]
    );

    const mergeIncidents = useCallback(
        async (primaryIncidentId, duplicateIncidentIds) => {
            setSaving(true);
            setError("");
            try {
                const res = await api.mergeIncidents(primaryIncidentId, duplicateIncidentIds);
                return res;
            } catch (err) {
                setError(getErrorMessage(err));
                throw err;
            } finally {
                setSaving(false);
            }
        },
        [api]
    );

    const loadArchivedIncidents = useCallback(
        async (params = {}) => {
            setLoading(true);
            setError("");
            try {
                const data = await api.getArchivedIncidents(params);
                setIncidents(data);
                return data;
            } catch (err) {
                setError(getErrorMessage(err));
                throw err;
            } finally {
                setLoading(false);
            }
        },
        [api]
    );

    const clearError = useCallback(() => {
        setError("");
    }, []);

    return {
        incidents,
        incident,
        duplicates,
        loading,
        saving,
        error,

        loadIncidents,
        loadIncident,
        createIncident,
        updateIncident,
        updateIncidentStatus,
        addComment,
        loadDuplicates,
        archiveIncident,
        mergeIncidents,
        loadArchivedIncidents,
        clearError,
    };
}