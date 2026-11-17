# Frontend Integration Placeholder

The team handbook specifies a **React.js** web application for the frontend.
The backend exposes standard REST endpoints at `/api/v1` with OpenAPI documentation accessible at `/docs`.

## Integration Contract

1. **Authentication:**
   - POST `/api/v1/auth/login` (owned by Member 1) returns `{ "accessToken": "...", "tokenType": "bearer" }`.
   - Pass `Authorization: Bearer <token>` on all protected endpoints.
2. **Technician Endpoints (Member 3):**
   - `GET /api/v1/technicians` — List all technicians with current workloads.
   - `GET /api/v1/technicians/{id}` — Fetch detailed profile and skills.
   - `GET /api/v1/technicians/recommendations?incidentId={id}&strategy={SKILL_BASED|LEAST_LOADED}&useLlm={true|false}` — Ranked recommendations with explainable justifications.
   - `POST /api/v1/incidents/{incidentId}/assign` — Execute assignment.
3. **Data Format:**
   - All request and response JSON payloads use `camelCase` field names.
   - All IDs are UUID strings.
   - All timestamps are ISO-8601 strings in UTC (`YYYY-MM-DDTHH:MM:SSZ`).
