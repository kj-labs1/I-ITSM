/**
 * Employee Incident API
 *
 * Uses the shared API client supplied by Member 1.
 *
 * Expected API client:
 * - apiClient.get(url, config)
 * - apiClient.post(url, data)
 * - apiClient.patch(url, data)
 *
 * Expected baseURL: http://localhost:8000/api/v1
 *
 * This module deliberately does not create its own Axios instance,
 * store JWT tokens or configure authentication interceptors.
 */

export function createIncidentApi(apiClient) {
    if (!apiClient) {
        throw new Error("A shared API client must be provided.");
    }

    const unwrap = (response) => {
        return response?.data ?? response;
    };

    return {
        async getIncidents(params = {}) {
            const response = await apiClient.get("/incidents", {
                params,
            });

            const data = unwrap(response);

            return Array.isArray(data) ? data : [];
        },

        async getIncidentById(incidentId) {
            const response = await apiClient.get(
                `/incidents/${incidentId}`
            );

            return unwrap(response);
        },

        async createIncident(payload) {
            const response = await apiClient.post(
                "/incidents",
                payload
            );

            return unwrap(response);
        },

        async updateIncident(incidentId, payload) {
            const response = await apiClient.patch(
                `/incidents/${incidentId}`,
                payload
            );

            return unwrap(response);
        },

        async updateIncidentStatus(incidentId, payload) {
            const response = await apiClient.patch(
                `/incidents/${incidentId}/status`,
                payload
            );

            return unwrap(response);
        },

        async addComment(incidentId, payload) {
            const response = await apiClient.post(
                `/incidents/${incidentId}/comments`,
                payload
            );

            return unwrap(response);
        },

        async getPotentialDuplicates(incidentId) {
            const response = await apiClient.get(
                `/incidents/${incidentId}/duplicates`
            );

            const data = unwrap(response);

            return Array.isArray(data) ? data : [];
        },
    };
}