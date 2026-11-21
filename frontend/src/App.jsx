import { useEffect, useMemo, useRef, useState } from "react";
import {
  EmployeeDashboard,
  MyIncidents,
  ReportIncident,
  IncidentDetails,
} from "./features/employee";
import { extractErrorMessage } from "./utils/errorHandler";

const API = "http://127.0.0.1:8000/api/v1";

async function api(path, token, options = {}) {
  const headers = { ...(options.headers || {}) };

  if (token) headers.Authorization = `Bearer ${token}`;

  if (options.body instanceof URLSearchParams) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (options.body) {
    headers["Content-Type"] = "application/json";
  }

  let response;
  try {
    response = await fetch(`${API}${path}`, { ...options, headers });
  } catch (networkErr) {
    const errorMsg = extractErrorMessage(networkErr, null, "Network error: Unable to connect to server.");
    const err = new Error(errorMsg);
    err.status = 0;
    throw err;
  }

  if (response.status === 204) return null;

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = extractErrorMessage(data, response.status);
    const error = new Error(message);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

function App() {
  const [token, setToken] = useState(localStorage.getItem("iitsm_token") || "");
  const [user, setUser] = useState(null);
  const [page, setPage] = useState(() => {
    const hash = typeof window !== "undefined" ? window.location.hash : "";
    if (hash && hash.startsWith("#incident-")) return "incident-details";
    return (typeof window !== "undefined" ? sessionStorage.getItem("iitsm_page") : null) || "dashboard";
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [data, setData] = useState([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState(() => {
    const hash = typeof window !== "undefined" ? window.location.hash : "";
    if (hash && hash.startsWith("#incident-")) {
      return hash.replace("#incident-", "");
    }
    return (typeof window !== "undefined" ? sessionStorage.getItem("iitsm_selected_incident_id") : null) || null;
  });
  const [servicesList, setServicesList] = useState([]);
  const [categoriesList, setCategoriesList] = useState([]);

  // Notification and Toast alerts state
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showNotificationsDropdown, setShowNotificationsDropdown] = useState(false);
  const [toasts, setToasts] = useState([]);
  const seenNotificationIds = useRef(new Set());

  const isAdmin = user?.role === "ADMIN";

  const apiClient = useMemo(() => ({
    get: async (path, config = {}) => {
      let query = "";
      if (config?.params) {
        const searchParams = new URLSearchParams();
        Object.entries(config.params).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== "") {
            searchParams.append(key, value);
          }
        });
        const qs = searchParams.toString();
        if (qs) query = `?${qs}`;
      }
      const res = await api(`${path}${query}`, token, { method: "GET" });
      return { data: res };
    },
    post: async (path, body) => {
      const res = await api(path, token, {
        method: "POST",
        body: body ? JSON.stringify(body) : undefined,
      });
      return { data: res };
    },
    patch: async (path, body) => {
      const res = await api(path, token, {
        method: "PATCH",
        body: body ? JSON.stringify(body) : undefined,
      });
      return { data: res };
    },
  }), [token]);

  // Polling for notifications every 15 seconds
  useEffect(() => {
    if (!token) return;

    let isMounted = true;

    async function pollNotifications() {
      try {
        const [countRes, listRes] = await Promise.all([
          api("/notifications/unread/count", token).catch(() => ({ unreadCount: 0 })),
          api("/notifications?limit=20", token).catch(() => []),
        ]);

        if (!isMounted) return;

        const count = countRes?.unreadCount ?? 0;
        setUnreadCount(count);

        if (Array.isArray(listRes)) {
          setNotifications(listRes);

          // Trigger toast for newly discovered unread notifications
          listRes.forEach((notif) => {
            if (!notif.isRead && !seenNotificationIds.current.has(notif.id)) {
              seenNotificationIds.current.add(notif.id);
              const toastId = notif.id || String(Date.now());
              setToasts((prev) => {
                if (prev.some((t) => t.id === toastId || (t.message === notif.message && t.title === notif.title))) {
                  return prev;
                }
                return [
                  ...prev,
                  {
                    id: toastId,
                    title: notif.title,
                    message: notif.message,
                    incidentId: notif.incidentId,
                    type: notif.notificationType,
                  },
                ];
              });

              setTimeout(() => {
                setToasts((prev) => prev.filter((t) => t.id !== toastId));
              }, 6000);
            }
          });
        }
      } catch (err) {
        console.error("Notification polling error:", err);
      }
    }

    pollNotifications();
    const interval = setInterval(pollNotifications, 15000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [token]);

  useEffect(() => {
    if (!token) return;
    api("/services", token).then((res) => setServicesList(Array.isArray(res) ? res : [])).catch(() => {});
    api("/categories", token).then((res) => setCategoriesList(Array.isArray(res) ? res : [])).catch(() => {});
  }, [token]);

  useEffect(() => {
    if (page === "incident-details" && selectedIncidentId) {
      sessionStorage.setItem("iitsm_selected_incident_id", selectedIncidentId);
      sessionStorage.setItem("iitsm_page", "incident-details");
      window.location.hash = `#incident-${selectedIncidentId}`;
    } else {
      sessionStorage.setItem("iitsm_page", page);
      if (window.location.hash.startsWith("#incident-")) {
        window.history.replaceState(null, "", window.location.pathname);
      }
    }
  }, [page, selectedIncidentId]);

  async function loadPage() {
    if (!token || !user) return;
    if (page === "report-incident" || page === "incident-details" || page === "my-incidents" || (page === "dashboard" && !isAdmin)) {
      return;
    }

    setLoading(true);
    setError("");

    try {
      if (page === "dashboard" && isAdmin) {
        setData(await api("/reports/summary", token));
      } else if (page === "users" && isAdmin) {
        setData(await api("/users", token));
      } else if (page === "technicians" && isAdmin) {
        setData(await api("/technicians", token));
      } else if (page === "sla" && isAdmin) {
        const [policies, violations, summary] = await Promise.all([
          api("/sla/policies", token).catch(() => []),
          api("/sla/violations?includeWarnings=true", token).catch(() => []),
          api("/sla/summary", token).catch(() => null),
        ]);
        setData({ policies, violations, summary });
      } else if (page === "audit" && isAdmin) {
        setData(await api("/audit?limit=100", token).catch(() => []));
      } else if (page === "services") {
        setData(
          await api(
            isAdmin ? "/services?include_inactive=true" : "/services",
            token,
          ),
        );
      } else if (page === "categories") {
        setData(
          await api(
            isAdmin ? "/categories?include_inactive=true" : "/categories",
            token,
          ),
        );
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleFilterAudit(filters) {
    if (!token || !isAdmin) return;
    setLoading(true);
    try {
      const searchParams = new URLSearchParams();
      if (filters.incidentId) searchParams.append("incidentId", filters.incidentId);
      if (filters.eventType) searchParams.append("eventType", filters.eventType);
      if (filters.action) searchParams.append("action", filters.action);
      if (filters.dateFrom) searchParams.append("dateFrom", new Date(filters.dateFrom).toISOString());
      if (filters.dateTo) searchParams.append("dateTo", new Date(filters.dateTo).toISOString());
      searchParams.append("limit", "100");
      const qs = searchParams.toString();
      const logs = await api(`/audit?${qs}`, token);
      setData(logs);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleNotificationClick(notif) {
    if (!notif.isRead) {
      try {
        await api(`/notifications/${notif.id}/read`, token, { method: "PATCH" });
        setNotifications((prev) =>
          prev.map((n) => (n.id === notif.id ? { ...n, isRead: true } : n))
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));
      } catch (e) {
        console.error(e);
      }
    }
    setShowNotificationsDropdown(false);
    if (notif.incidentId) {
      setSelectedIncidentId(notif.incidentId);
      setPage("incident-details");
    }
  }

  async function handleMarkAllNotificationsRead() {
    try {
      await api("/notifications/read-all", token, { method: "PATCH" });
      setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
      setUnreadCount(0);
    } catch (e) {
      console.error(e);
    }
  }

  function getNotificationIcon(type) {
    switch (type) {
      case "SLA_BREACHED":
        return "🚨";
      case "SLA_WARNING":
        return "⚠️";
      case "INCIDENT_ASSIGNED":
        return "🛠️";
      case "INCIDENT_CREATED":
        return "📝";
      case "STATUS_CHANGED":
        return "🔄";
      case "COMMENT_ADDED":
        return "💬";
      case "AVAILABILITY_CHANGED":
        return "⏱️";
      default:
        return "ℹ️";
    }
  }

  useEffect(() => {
    if (!token) return;

    api("/auth/me", token)
      .then((profile) => {
        setUser(profile);
        if (profile.role === "ADMIN") {
          setPage("dashboard");
        } else if (profile.role === "TECHNICIAN") {
          setPage("dashboard");
        } else {
          setPage("dashboard");
        }
      })
      .catch(() => {
        localStorage.removeItem("iitsm_token");
        setToken("");
        setUser(null);
      });
  }, [token]);

  useEffect(() => {
    loadPage();
  }, [page, token, user]);

  function logout() {
    localStorage.removeItem("iitsm_token");
    setToken("");
    setUser(null);
    setData([]);
    setNotifications([]);
    setUnreadCount(0);
    setToasts([]);
    setNotice("");
    setError("");
  }

  async function login(
    username,
    password,
    register = false,
    fullName = "",
    email = "",
  ) {
    setError("");
    setNotice("");

    try {
      if (register) {
        await api("/auth/register", null, {
          method: "POST",
          body: JSON.stringify({
            username,
            email,
            fullName,
            password,
          }),
        });
      }

      const form = new URLSearchParams();
      form.append("username", username);
      form.append("password", password);

      const result = await api("/auth/login", null, {
        method: "POST",
        body: form,
      });

      localStorage.setItem("iitsm_token", result.accessToken);
      setToken(result.accessToken);
      setNotice(register ? "Account created successfully." : "Welcome back!");
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function perform(path, method, body, successMessage) {
    setError("");
    setNotice("");

    try {
      const res = await api(path, token, {
        method,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      setNotice(successMessage);
      await loadPage();
      return res;
    } catch (err) {
      const cleanMsg = extractErrorMessage(err);
      setError(cleanMsg);
      throw err;
    }
  }

  if (!token || !user) {
    return <AuthScreen onLogin={login} error={error} notice={notice} />;
  }

  const isTechnician = user?.role === "TECHNICIAN";
  const isEmployee = user?.role === "EMPLOYEE";

  const pages = [
    ...(isAdmin
      ? [
          { id: "dashboard", label: "Dashboard", symbol: "▦" },
          { id: "my-incidents", label: "Incident Management", symbol: "☷" },
          { id: "report-incident", label: "Report Incident", symbol: "✚" },
          { id: "technicians", label: "Technicians", symbol: "🛠" },
          { id: "sla", label: "SLA Tracking", symbol: "⏱" },
          { id: "audit", label: "Audit Logs", symbol: "📜" },
          { id: "users", label: "Users", symbol: "♙" },
          { id: "services", label: "Services", symbol: "▣" },
          { id: "categories", label: "Categories", symbol: "≡" },
        ]
      : isTechnician
        ? [
            { id: "dashboard", label: "Dashboard", symbol: "▦" },
            { id: "my-incidents", label: "Assigned Incidents", symbol: "☷" },
            { id: "services", label: "Services", symbol: "▣" },
            { id: "categories", label: "Categories", symbol: "≡" },
          ]
        : [
            { id: "dashboard", label: "Dashboard", symbol: "▦" },
            { id: "my-incidents", label: "My Incidents", symbol: "☷" },
            { id: "report-incident", label: "Report Incident", symbol: "✚" },
            { id: "services", label: "Services", symbol: "▣" },
            { id: "categories", label: "Categories", symbol: "≡" },
          ]),
  ];

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">IT</div>
          <div>
            <strong>I-ITSM</strong>
            <span>IT Service Management</span>
          </div>
        </div>

        <div className="account">
          {/* Notification Bell */}
          <div className="notification-bell-container">
            <button
              type="button"
              className="notification-bell-btn"
              onClick={() => setShowNotificationsDropdown((prev) => !prev)}
              aria-label="Notifications"
            >
              🔔
              {unreadCount > 0 && (
                <span className="notification-badge">{unreadCount}</span>
              )}
            </button>

            {showNotificationsDropdown && (
              <div className="notification-dropdown">
                <div className="notification-dropdown-header">
                  <h3>Notifications ({unreadCount} unread)</h3>
                  {unreadCount > 0 && (
                    <button
                      type="button"
                      className="button button-small button-outline"
                      onClick={handleMarkAllNotificationsRead}
                    >
                      Mark all read
                    </button>
                  )}
                </div>
                <ul className="notification-dropdown-list">
                  {notifications.length === 0 ? (
                    <li style={{ padding: "16px", textAlign: "center", color: "#64748b", fontSize: "13px" }}>
                      No notifications
                    </li>
                  ) : (
                    notifications.map((n) => (
                      <li
                        key={n.id}
                        className={`notification-item ${!n.isRead ? "unread" : ""}`}
                        onClick={() => handleNotificationClick(n)}
                      >
                        <div className="notification-icon">
                          {getNotificationIcon(n.notificationType)}
                        </div>
                        <div className="notification-content">
                          <div className="notification-title">
                            <span>{n.title}</span>
                            {!n.isRead && <span className="unread-dot" />}
                          </div>
                          <div className="notification-message">{n.message}</div>
                          <div className="notification-time">
                            {new Date(n.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · {new Date(n.createdAt).toLocaleDateString()}
                          </div>
                        </div>
                      </li>
                    ))
                  )}
                </ul>
              </div>
            )}
          </div>

          <div className="account-info">
            <strong>{user.fullName}</strong>
            <span>{user.role}</span>
          </div>
          <button className="button button-outline" onClick={logout}>
            Logout
          </button>
        </div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <p className="nav-heading">WORKSPACE</p>
          {pages.map((item) => (
            <button
              key={item.id}
              className={`nav-link ${page === item.id ? "selected" : ""}`}
              onClick={() => {
                setPage(item.id);
                setError("");
                setNotice("");
              }}
            >
              <span className="nav-symbol">{item.symbol}</span>
              {item.label}
            </button>
          ))}

          <div className="sidebar-footer">
            <span className="status-dot" />
            API connected
          </div>
        </aside>

        <main className="main-content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">I-ITSM / {page.toUpperCase().replace("-", " ")}</p>
              <h1>
                {page === "dashboard"
                  ? isAdmin
                    ? "Admin Dashboard"
                    : isTechnician
                      ? "Technician Dashboard"
                      : "Employee Dashboard"
                  : page === "report-incident"
                    ? "Report Incident"
                    : page === "my-incidents"
                      ? isTechnician
                        ? "Assigned Incidents"
                        : isAdmin
                          ? "Incident Management"
                          : "My Incidents"
                      : page === "incident-details"
                        ? "Incident Details"
                        : page === "technicians"
                          ? "Technicians Management"
                          : page === "sla"
                            ? "SLA Tracking & Policies"
                            : page === "audit"
                              ? "Audit Logs"
                              : page === "users"
                                ? "User Management"
                                : page === "services"
                                  ? "Service Catalogue"
                                  : "Incident Categories"}
              </h1>
              <p className="subtitle">
                {page === "dashboard"
                  ? isAdmin
                    ? "Overview of your IT service management platform."
                    : isTechnician
                      ? "Overview of your assigned workloads, operational capacity, and SLA warnings."
                      : "Overview of your reported incidents and activities."
                  : page === "report-incident"
                    ? "Submit a new incident ticket to IT support."
                    : page === "my-incidents"
                      ? isTechnician
                        ? "Search, track and resolve incidents assigned to you."
                        : isAdmin
                          ? "Search, triage and assign incidents across the organization."
                          : "Search, track and view your incident requests."
                      : page === "incident-details"
                        ? "View full incident timeline, resolution details and add comments."
                        : page === "technicians"
                          ? "Manage technician profiles, capacity, and operational availability."
                          : page === "sla"
                            ? "Configure SLA response/resolution targets and monitor breach warnings."
                            : page === "audit"
                              ? "Chronological audit trail of all incident lifecycle events."
                              : page === "users"
                                ? "Manage accounts, roles and access."
                                : page === "services"
                                  ? "Manage the organisation's IT services."
                                  : "Configure incident classifications and required skills."}
              </p>
            </div>
            <div className="role-label">{user.role}</div>
          </div>

          {error && <div className="alert alert-error">{error}</div>}
          {notice && <div className="alert alert-success">{notice}</div>}

          {loading ? (
            <div className="loading">Loading data...</div>
          ) : (
            <>
              {page === "dashboard" && isAdmin && <Dashboard summary={data} />}

              {page === "dashboard" && isTechnician && (
                <TechnicianDashboard
                  apiClient={apiClient}
                  currentUser={user}
                  onOpenIncident={(id) => {
                    setSelectedIncidentId(id);
                    setPage("incident-details");
                  }}
                  onNavigate={(target) => setPage(target)}
                />
              )}

              {page === "dashboard" && user.role === "EMPLOYEE" && (
                <EmployeeDashboard
                  apiClient={apiClient}
                  onNavigate={(target) => {
                    if (target && target.includes("report")) {
                      setPage("report-incident");
                    } else {
                      setPage("my-incidents");
                    }
                  }}
                  onOpenIncident={(id) => {
                    setSelectedIncidentId(id);
                    setPage("incident-details");
                  }}
                />
              )}

              {page === "report-incident" && (
                <ReportIncident
                  apiClient={apiClient}
                  services={servicesList}
                  categories={categoriesList}
                  onSuccess={(inc) => {
                    setNotice(
                      `Incident reported successfully: ${inc.incidentCode || inc.id}`,
                    );
                    setSelectedIncidentId(inc.id);
                    setPage("incident-details");
                  }}
                  onCancel={() =>
                    setPage(user.role === "EMPLOYEE" ? "dashboard" : "my-incidents")
                  }
                />
              )}

              {page === "my-incidents" && (
                <MyIncidents
                  apiClient={apiClient}
                  currentUser={user}
                  onOpenIncident={(id) => {
                    setSelectedIncidentId(id);
                    setPage("incident-details");
                  }}
                  onNavigate={(target) => {
                    if (target && target.includes("report")) {
                      setPage("report-incident");
                    }
                  }}
                />
              )}

              {page === "incident-details" && (
                <IncidentDetails
                  apiClient={apiClient}
                  incidentId={selectedIncidentId}
                  currentUser={user}
                  onBack={() => setPage("my-incidents")}
                  onOpenIncident={(id) => {
                    setSelectedIncidentId(id);
                    setPage("incident-details");
                  }}
                />
              )}

              {page === "technicians" && isAdmin && (
                <TechniciansPage
                  technicians={Array.isArray(data) ? data : []}
                  perform={perform}
                />
              )}

              {page === "sla" && isAdmin && (
                <SLAPage
                  slaData={data}
                  perform={perform}
                />
              )}

              {page === "audit" && isAdmin && (
                <AuditPage
                  auditLogs={Array.isArray(data) ? data : []}
                  onFilter={handleFilterAudit}
                />
              )}

              {page === "users" && isAdmin && (
                <UsersPage
                  users={Array.isArray(data) ? data : []}
                  perform={perform}
                />
              )}

              {page === "services" && (
                <ServicesPage
                  services={Array.isArray(data) ? data : []}
                  perform={perform}
                  isAdmin={isAdmin}
                />
              )}

              {page === "categories" && (
                <CategoriesPage
                  categories={Array.isArray(data) ? data : []}
                  perform={perform}
                  isAdmin={isAdmin}
                />
              )}
            </>
          )}

          <footer className="main-footer">
            I-ITSM · Intelligent IT Service Management
          </footer>
        </main>
      </div>

      {/* Global Toast Notifications Container */}
      {toasts.length > 0 && (
        <div className="toast-container">
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className={`toast-card ${
                toast.type === "SLA_BREACHED"
                  ? "breach"
                  : toast.type === "SLA_WARNING"
                  ? "warning"
                  : ""
              }`}
            >
              <div className="notification-icon" style={{ fontSize: "20px" }}>
                {getNotificationIcon(toast.type)}
              </div>
              <div className="toast-body">
                <div className="toast-title">{toast.title}</div>
                <div className="toast-message">{toast.message}</div>
                {toast.incidentId && (
                  <div className="toast-actions">
                    <button
                      type="button"
                      className="button button-small button-primary"
                      onClick={() => {
                        setSelectedIncidentId(toast.incidentId);
                        setPage("incident-details");
                        setToasts((prev) => prev.filter((t) => t.id !== toast.id));
                      }}
                    >
                      View Incident
                    </button>
                  </div>
                )}
              </div>
              <button
                type="button"
                className="toast-close-btn"
                onClick={() => setToasts((prev) => prev.filter((t) => t.id !== toast.id))}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AuthScreen({ onLogin, error, notice }) {
  const [register, setRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setSubmitting(true);
    await onLogin(username, password, register, fullName, email);
    setSubmitting(false);
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="brand auth-brand">
          <div className="brand-icon">IT</div>
          <div>
            <strong>I-ITSM</strong>
            <span>IT Service Management</span>
          </div>
        </div>

        <p className="eyebrow">WELCOME</p>
        <h1>{register ? "Create your account" : "Sign in to your account"}</h1>
        <p className="subtitle">
          {register
            ? "Register as an employee to get started."
            : "Enter your credentials to continue."}
        </p>

        {error && <div className="alert alert-error">{error}</div>}
        {notice && <div className="alert alert-success">{notice}</div>}

        <form onSubmit={submit} className="form-stack">
          {register && (
            <>
              <label>Full name</label>
              <input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                minLength={2}
              />
              <label>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </>
          )}

          <label>Username</label>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />

          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />

          <button
            className="button button-primary full-width"
            disabled={submitting}
          >
            {submitting
              ? "Please wait..."
              : register
                ? "Create account"
                : "Sign in"}
          </button>
        </form>

        <p className="auth-switch">
          {register ? "Already registered?" : "Don't have an account?"}
          <button onClick={() => setRegister(!register)}>
            {register ? "Sign in" : "Register"}
          </button>
        </p>
        <p className="auth-footnote">
          Administrator accounts are created by the system administrator.
        </p>
      </div>
    </div>
  );
}

function Dashboard({ summary }) {
  if (!summary || !summary.users) {
    return <p className="empty">Dashboard summary is unavailable.</p>;
  }

  const cards = [
    ["Total users", summary.users.total, "Registered accounts"],
    ["Active users", summary.users.active, "Currently enabled"],
    ["Services", summary.services?.total ?? 0, "Catalogue entries"],
    ["Categories", summary.categories?.total ?? 0, "Incident types"],
  ];

  return (
    <>
      <div className="stats-grid">
        {cards.map(([label, value, note]) => (
          <div className="stat-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{note}</small>
          </div>
        ))}
      </div>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>User distribution</h2>
            <p>Accounts by assigned system role</p>
          </div>
        </div>
        <div className="role-stats">
          {Object.entries(summary.users.byRole || {}).map(([role, count]) => (
            <div className="role-stat" key={role}>
              <span>{role}</span>
              <strong>{count}</strong>
            </div>
          ))}
        </div>
      </section>

      <div className="stats-grid secondary-stats">
        <div className="stat-card">
          <span>Active services</span>
          <strong>{summary.services?.active ?? 0}</strong>
          <small>Available catalogue services</small>
        </div>
        <div className="stat-card">
          <span>Active categories</span>
          <strong>{summary.categories?.active ?? 0}</strong>
          <small>Enabled incident categories</small>
        </div>
        <div className="stat-card">
          <span>Inactive users</span>
          <strong>{summary.users.inactive}</strong>
          <small>Disabled accounts</small>
        </div>
        <div className="stat-card">
          <span>Inactive services</span>
          <strong>{summary.services?.inactive ?? 0}</strong>
          <small>Disabled catalogue entries</small>
        </div>
      </div>
    </>
  );
}

function UsersPage({ users, perform }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>System users</h2>
          <p>{users.length} registered accounts</p>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((item) => (
              <tr key={item.id}>
                <td>
                  <strong>{item.fullName}</strong>
                  <small>{item.username}</small>
                </td>
                <td>{item.email}</td>
                <td>
                  <select
                    value={item.role}
                    onChange={(e) =>
                      perform(
                        `/users/${item.id}`,
                        "PATCH",
                        { role: e.target.value },
                        "User role updated.",
                      )
                    }
                  >
                    <option value="EMPLOYEE">EMPLOYEE</option>
                    <option value="TECHNICIAN">TECHNICIAN</option>
                    <option value="ADMIN">ADMIN</option>
                  </select>
                </td>
                <td>
                  <span
                    className={`status ${item.isActive ? "active" : "inactive"}`}
                  >
                    {item.isActive ? "Active" : "Inactive"}
                  </span>
                </td>
                <td>
                  <button
                    className="button button-small button-outline"
                    onClick={() =>
                      perform(
                        `/users/${item.id}`,
                        "PATCH",
                        { isActive: !item.isActive },
                        "User status updated.",
                      )
                    }
                  >
                    {item.isActive ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && <p className="empty">No users found.</p>}
      </div>
    </section>
  );
}

function ServicesPage({ services, perform, isAdmin }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [criticality, setCriticality] = useState(3);

  async function create(event) {
    event.preventDefault();
    await perform(
      "/services",
      "POST",
      {
        name,
        description,
        businessCriticality: Number(criticality),
      },
      "Service created successfully.",
    );
    setName("");
    setDescription("");
    setCriticality(3);
  }

  return (
    <>
      {isAdmin && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Add a service</h2>
              <p>Create a new catalogue entry.</p>
            </div>
          </div>
          <form className="inline-form" onSubmit={create}>
            <div className="field">
              <label>Service name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="field">
              <label>Description</label>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div className="field">
              <label>Criticality</label>
              <select
                value={criticality}
                onChange={(e) => setCriticality(e.target.value)}
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </div>
            <button className="button button-primary">Add service</button>
          </form>
        </section>
      )}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Service catalogue</h2>
            <p>{services.length} services returned by the API.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Service</th>
                <th>Criticality</th>
                <th>Status</th>
                {isAdmin && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {services.map((item) => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.name}</strong>
                    <small>{item.description || "No description"}</small>
                  </td>
                  <td>
                    {isAdmin ? (
                      <select
                        value={item.businessCriticality}
                        onChange={(e) =>
                          perform(
                            `/services/${item.id}`,
                            "PATCH",
                            { businessCriticality: Number(e.target.value) },
                            "Service criticality updated.",
                          )
                        }
                      >
                        {[1, 2, 3, 4, 5].map((n) => (
                          <option key={n} value={n}>
                            {n} / 5
                          </option>
                        ))}
                      </select>
                    ) : (
                      `${item.businessCriticality} / 5`
                    )}
                  </td>
                  <td>
                    <span
                      className={`status ${item.isActive ? "active" : "inactive"}`}
                    >
                      {item.isActive ? "Active" : "Inactive"}
                    </span>
                  </td>
                  {isAdmin && (
                    <td>
                      <button
                        className="button button-small button-outline"
                        onClick={() =>
                          perform(
                            `/services/${item.id}`,
                            "PATCH",
                            { isActive: !item.isActive },
                            "Service status updated.",
                          )
                        }
                      >
                        {item.isActive ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          {services.length === 0 && <p className="empty">No services found.</p>}
        </div>
      </section>
    </>
  );
}

function CategoriesPage({ categories, perform, isAdmin }) {
  const [category, setCategory] = useState("HARDWARE");
  const [description, setDescription] = useState("");
  const [skill, setSkill] = useState("HARDWARE");

  const options = [
    "HARDWARE",
    "SOFTWARE",
    "NETWORK",
    "DATABASE",
    "CLOUD",
    "SECURITY",
    "AUTHENTICATION",
    "APPLICATION",
    "STORAGE",
  ];

  async function create(event) {
    event.preventDefault();
    await perform(
      "/categories",
      "POST",
      {
        category,
        description,
        requiredSkill: skill,
      },
      "Incident category created.",
    );
    setDescription("");
  }

  return (
    <>
      {isAdmin && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Add an incident category</h2>
              <p>Map each category to a technician skill.</p>
            </div>
          </div>
          <form className="inline-form" onSubmit={create}>
            <div className="field">
              <label>Category</label>
              <select
                value={category}
                onChange={(e) => {
                  setCategory(e.target.value);
                  setSkill(e.target.value);
                }}
              >
                {options.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Description</label>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div className="field">
              <label>Required skill</label>
              <input
                value={skill}
                onChange={(e) => setSkill(e.target.value)}
                required
              />
            </div>
            <button className="button button-primary">Add category</button>
          </form>
        </section>
      )}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Incident categories</h2>
            <p>{categories.length} active categories.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th>Description</th>
                <th>Required skill</th>
                <th>Status</th>
                {isAdmin && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {categories.map((item) => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.category}</strong>
                  </td>
                  <td>{item.description || "—"}</td>
                  <td>
                    <span className="skill-label">{item.requiredSkill}</span>
                  </td>
                  <td>
                    <span
                      className={`status ${item.isActive ? "active" : "inactive"}`}
                    >
                      {item.isActive ? "Active" : "Inactive"}
                    </span>
                  </td>
                  {isAdmin && (
                    <td>
                      <button
                        className="button button-small button-outline"
                        onClick={() =>
                          perform(
                            `/categories/${item.id}`,
                            "PATCH",
                            { isActive: !item.isActive },
                            "Category status updated.",
                          )
                        }
                      >
                        {item.isActive ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          {categories.length === 0 && (
            <p className="empty">No active categories found.</p>
          )}
        </div>
      </section>
    </>
  );
}

function EditTechnicianModal({ technician, onClose, perform }) {
  const [experienceYears, setExperienceYears] = useState(technician.experienceYears);
  const [maxCapacity, setMaxCapacity] = useState(technician.maxCapacity);
  const [newSkillName, setNewSkillName] = useState("");
  const [newProficiency, setNewProficiency] = useState(3);
  const [savingSettings, setSavingSettings] = useState(false);
  const [addingSkill, setAddingSkill] = useState(false);
  const [modalError, setModalError] = useState("");
  const [modalNotice, setModalNotice] = useState("");

  const commonSkills = [
    "HARDWARE",
    "SOFTWARE",
    "NETWORK",
    "DATABASE",
    "CLOUD",
    "SECURITY",
    "AUTHENTICATION",
    "APPLICATION",
    "STORAGE",
  ];

  async function handleSaveSettings(e) {
    e.preventDefault();
    setModalError("");
    setModalNotice("");
    setSavingSettings(true);
    try {
      await perform(
        `/technicians/${technician.id}`,
        "PATCH",
        {
          experienceYears: Number(experienceYears),
          maxCapacity: Number(maxCapacity),
        },
        "Operational parameters updated."
      );
      setModalNotice("Operational settings updated successfully.");
    } catch (err) {
      setModalError(extractErrorMessage(err));
    } finally {
      setSavingSettings(false);
    }
  }

  async function handleAddSkill(e) {
    e.preventDefault();
    if (!newSkillName.trim()) return;
    setModalError("");
    setModalNotice("");
    setAddingSkill(true);
    try {
      await perform(
        `/technicians/${technician.id}/skills`,
        "POST",
        {
          skillName: newSkillName.trim().toUpperCase(),
          proficiencyLevel: Number(newProficiency),
        },
        `Skill '${newSkillName.trim().toUpperCase()}' added.`
      );
      setNewSkillName("");
      setNewProficiency(3);
      setModalNotice("Skill saved successfully.");
    } catch (err) {
      setModalError(extractErrorMessage(err));
    } finally {
      setAddingSkill(false);
    }
  }

  async function handleRemoveSkill(skillName) {
    setModalError("");
    setModalNotice("");
    try {
      await perform(
        `/technicians/${technician.id}/skills/${encodeURIComponent(skillName)}`,
        "DELETE",
        undefined,
        `Skill '${skillName}' removed.`
      );
      setModalNotice(`Skill '${skillName}' removed.`);
    } catch (err) {
      setModalError(extractErrorMessage(err));
    }
  }

  return (
    <div
      className="modal-backdrop"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0,0,0,0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "20px",
      }}
    >
      <div
        className="modal-card"
        style={{
          backgroundColor: "#ffffff",
          borderRadius: "8px",
          maxWidth: "600px",
          width: "100%",
          maxHeight: "90vh",
          overflowY: "auto",
          boxShadow: "0 12px 28px rgba(0,0,0,0.2)",
          padding: "24px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderBottom: "1px solid #d0d7de",
            paddingBottom: "12px",
            marginBottom: "16px",
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: "18px" }}>
              Technician: {technician.username || technician.fullName || "Technician"}
            </h2>
            <p style={{ margin: "4px 0 0 0", fontSize: "13px", color: "#57606a" }}>
              {technician.fullName ? `${technician.fullName} · ` : ""}
              {technician.email || "No email listed"}
            </p>
          </div>
          <button
            type="button"
            className="button button-small button-outline"
            onClick={onClose}
            style={{ fontSize: "16px", padding: "2px 8px" }}
          >
            ✕
          </button>
        </div>

        {modalError && (
          <div className="alert alert-error" style={{ marginBottom: "14px" }}>
            {modalError}
          </div>
        )}
        {modalNotice && (
          <div className="alert alert-success" style={{ marginBottom: "14px" }}>
            {modalNotice}
          </div>
        )}

        {/* Operational Parameters Section */}
        <section
          style={{
            marginBottom: "24px",
            padding: "16px",
            backgroundColor: "#f6f8fa",
            borderRadius: "6px",
          }}
        >
          <h3 style={{ margin: "0 0 12px 0", fontSize: "15px" }}>Operational Settings</h3>
          <form
            onSubmit={handleSaveSettings}
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr auto",
              gap: "12px",
              alignItems: "flex-end",
            }}
          >
            <div className="field" style={{ margin: 0 }}>
              <label style={{ fontSize: "12px", fontWeight: "600" }}>Experience (Years)</label>
              <input
                type="number"
                min="0"
                max="50"
                value={experienceYears}
                onChange={(e) => setExperienceYears(e.target.value)}
                required
                style={{ width: "100%", padding: "6px 8px" }}
              />
            </div>
            <div className="field" style={{ margin: 0 }}>
              <label style={{ fontSize: "12px", fontWeight: "600" }}>Max Incident Capacity</label>
              <input
                type="number"
                min="1"
                max="50"
                value={maxCapacity}
                onChange={(e) => setMaxCapacity(e.target.value)}
                required
                style={{ width: "100%", padding: "6px 8px" }}
              />
            </div>
            <button
              type="submit"
              className="button button-primary button-small"
              disabled={savingSettings}
            >
              {savingSettings ? "Saving..." : "Save Settings"}
            </button>
          </form>
        </section>

        {/* Skills Management Section */}
        <section>
          <h3 style={{ margin: "0 0 12px 0", fontSize: "15px" }}>Technician Skills</h3>

          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "16px" }}>
            {!technician.skills || technician.skills.length === 0 ? (
              <p style={{ color: "#656d76", fontStyle: "italic", margin: 0 }}>
                No skills assigned yet.
              </p>
            ) : (
              technician.skills.map((s) => (
                <span
                  key={s.id || s.skillName}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "4px 10px",
                    borderRadius: "14px",
                    backgroundColor: "#ddf4ff",
                    color: "#0969da",
                    border: "1px solid #54aeff66",
                    fontSize: "13px",
                    fontWeight: "500",
                  }}
                >
                  {s.skillName} ({s.proficiencyLevel}/5)
                  <button
                    type="button"
                    onClick={() => handleRemoveSkill(s.skillName)}
                    title={`Remove ${s.skillName}`}
                    style={{
                      background: "none",
                      border: "none",
                      color: "#cf222e",
                      cursor: "pointer",
                      padding: "0 2px",
                      fontWeight: "bold",
                      fontSize: "14px",
                      lineHeight: "1",
                    }}
                  >
                    ×
                  </button>
                </span>
              ))
            )}
          </div>

          {/* Add / Update Skill Sub-form */}
          <form
            onSubmit={handleAddSkill}
            style={{
              display: "grid",
              gridTemplateColumns: "1.5fr 1fr auto",
              gap: "12px",
              alignItems: "flex-end",
              borderTop: "1px solid #e1e4e8",
              paddingTop: "14px",
            }}
          >
            <div className="field" style={{ margin: 0 }}>
              <label style={{ fontSize: "12px", fontWeight: "600" }}>Skill Name</label>
              <input
                list="common-skills-list"
                value={newSkillName}
                onChange={(e) => setNewSkillName(e.target.value)}
                placeholder="e.g. NETWORK"
                required
                style={{ width: "100%", padding: "6px 8px" }}
              />
              <datalist id="common-skills-list">
                {commonSkills.map((sk) => (
                  <option key={sk} value={sk} />
                ))}
              </datalist>
            </div>
            <div className="field" style={{ margin: 0 }}>
              <label style={{ fontSize: "12px", fontWeight: "600" }}>Proficiency (1-5)</label>
              <select
                value={newProficiency}
                onChange={(e) => setNewProficiency(e.target.value)}
                style={{ width: "100%", padding: "6px 8px" }}
              >
                {[1, 2, 3, 4, 5].map((lvl) => (
                  <option key={lvl} value={lvl}>
                    Level {lvl} {lvl === 1 ? "(Novice)" : lvl === 5 ? "(Expert)" : ""}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              className="button button-primary button-small"
              disabled={addingSkill || !newSkillName.trim()}
            >
              {addingSkill ? "Adding..." : "Add / Update Skill"}
            </button>
          </form>
        </section>

        <div style={{ marginTop: "24px", display: "flex", justifyContent: "flex-end" }}>
          <button type="button" className="button button-outline" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

function TechniciansPage({ technicians, perform }) {
  const [editingTech, setEditingTech] = useState(null);

  // Keep modal data fresh when technicians array is updated
  const activeEditingTech = editingTech
    ? technicians.find((t) => t.id === editingTech.id) || editingTech
    : null;

  return (
    <>
      {activeEditingTech && (
        <EditTechnicianModal
          technician={activeEditingTech}
          onClose={() => setEditingTech(null)}
          perform={perform}
        />
      )}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Technician Roster & Workload</h2>
            <p>Operational capacity, availability status and assigned skills.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Username</th>
                <th>Full Name</th>
                <th>Skills</th>
                <th>Availability</th>
                <th>Experience</th>
                <th>Workload / Capacity</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {technicians.map((t) => (
                <tr key={t.id}>
                  <td>
                    <strong>{t.username || "—"}</strong>
                  </td>
                  <td>{t.fullName || "—"}</td>
                  <td>
                    {!t.skills || t.skills.length === 0 ? (
                      <span style={{ color: "#656d76", fontStyle: "italic", fontSize: "13px" }}>
                        No skills added
                      </span>
                    ) : (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                        {t.skills.map((s) => (
                          <span
                            key={s.id || s.skillName}
                            style={{
                              fontSize: "12px",
                              padding: "2px 8px",
                              borderRadius: "12px",
                              backgroundColor: "#ddf4ff",
                              color: "#0969da",
                              border: "1px solid #54aeff66",
                              fontWeight: "500",
                            }}
                          >
                            {s.skillName} ({s.proficiencyLevel}/5)
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td>
                    <span className={`status ${t.availability === "AVAILABLE" ? "active" : "inactive"}`}>
                      {t.availability}
                    </span>
                  </td>
                  <td>{t.experienceYears} yrs</td>
                  <td>
                    <span className={`status ${t.activeIncidentCount >= t.maxCapacity ? "inactive" : "active"}`}>
                      {t.activeIncidentCount} / {t.maxCapacity}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      <button
                        className="button button-small button-outline"
                        onClick={() =>
                          perform(
                            `/technicians/${t.id}/availability`,
                            "PATCH",
                            { availability: t.availability === "AVAILABLE" ? "BUSY" : "AVAILABLE" },
                            `Updated availability for ${t.username || t.fullName || "technician"}`
                          )
                        }
                      >
                        Toggle {t.availability === "AVAILABLE" ? "Busy" : "Available"}
                      </button>
                      <button
                        className="button button-small button-primary"
                        onClick={() => setEditingTech(t)}
                      >
                        View & Edit
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {technicians.length === 0 && (
            <p className="empty">No technicians registered.</p>
          )}
        </div>
      </section>
    </>
  );
}

function SLAPage({ slaData, perform }) {
  const policies = Array.isArray(slaData?.policies) ? slaData.policies : [];
  const violations = Array.isArray(slaData?.violations) ? slaData.violations : [];
  const summary = slaData?.summary || null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {summary && (
        <section className="sla-summary-grid">
          <div className="sla-summary-card">
            <span>Total SLA Tracked</span>
            <strong>{summary.totalTracked}</strong>
          </div>
          <div className="sla-summary-card compliance">
            <span>In Compliance / Met</span>
            <strong>{summary.metCount}</strong>
          </div>
          <div className="sla-summary-card breach">
            <span>Breached Incidents</span>
            <strong>{summary.breachedCount}</strong>
          </div>
          <div className="sla-summary-card warning">
            <span>Approaching Breach</span>
            <strong>{summary.warningCount}</strong>
          </div>
          <div className="sla-summary-card compliance">
            <span>Overall Compliance</span>
            <strong>{summary.complianceRate}%</strong>
          </div>
        </section>
      )}

      {summary?.byPriority && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Priority SLA Breakdown</h2>
              <p>Performance metrics segmented by incident urgency level.</p>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Priority</th>
                  <th>Total Tracked</th>
                  <th>Targets Met</th>
                  <th>Breached</th>
                  <th>Compliance Rate</th>
                </tr>
              </thead>
              <tbody>
                {summary.byPriority.map((row) => (
                  <tr key={row.priority}>
                    <td><strong>{row.priority}</strong></td>
                    <td>{row.total}</td>
                    <td>{row.met}</td>
                    <td>{row.breached}</td>
                    <td>
                      <span className={`status ${row.complianceRate >= 90 ? "active" : row.complianceRate >= 70 ? "warning" : "inactive"}`}>
                        {row.complianceRate}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>SLA Policies (P1–P4)</h2>
            <p>Configured response and resolution time targets by priority.</p>
          </div>
          <button
            className="button button-primary"
            onClick={() =>
              perform("/sla/check", "POST", {}, "SLA check evaluated across all active incidents.")
            }
          >
            ⚡ Run SLA Evaluation Sweep
          </button>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Priority</th>
                <th>Policy Name</th>
                <th>Response Target</th>
                <th>Resolution Target</th>
                <th>Warning Threshold</th>
                <th>Escalation</th>
              </tr>
            </thead>
            <tbody>
              {policies.map((p) => (
                <tr key={p.id}>
                  <td><strong>{p.priority}</strong></td>
                  <td>{p.name}</td>
                  <td>{p.responseTimeMinutes} mins</td>
                  <td>{p.resolutionTimeMinutes} mins ({Math.round(p.resolutionTimeMinutes / 60)} hrs)</td>
                  <td>{p.warningThresholdPercent}%</td>
                  <td>{p.escalationEnabled ? "Enabled" : "Disabled"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {policies.length === 0 && (
            <p className="empty">No SLA policies configured.</p>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Active SLA Violations & Warnings</h2>
            <p>Incidents approaching or past configured SLA deadlines.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Incident ID</th>
                <th>Priority</th>
                <th>SLA Status</th>
                <th>Breached?</th>
                <th>Warning Sent?</th>
                <th>Response Deadline</th>
                <th>Resolution Deadline</th>
              </tr>
            </thead>
            <tbody>
              {violations.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", color: "#697586" }}>
                    No active SLA violations or warnings recorded.
                  </td>
                </tr>
              ) : (
                violations.map((v) => (
                  <tr key={v.id}>
                    <td style={{ fontFamily: "monospace", fontSize: "12px" }}>{v.incidentId}</td>
                    <td><strong>{v.priority}</strong></td>
                    <td>
                      <span className={`status ${v.status === "BREACHED" ? "inactive" : "active"}`}>
                        {v.status}
                      </span>
                    </td>
                    <td>{v.isBreached ? "YES" : "No"}</td>
                    <td>{v.warningSent ? "YES" : "No"}</td>
                    <td>{new Date(v.responseDueAt).toLocaleString()}</td>
                    <td>{new Date(v.resolutionDueAt).toLocaleString()}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function AuditPage({ auditLogs, onFilter }) {
  const [incidentId, setIncidentId] = useState("");
  const [eventType, setEventType] = useState("");
  const [action, setAction] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const logs = Array.isArray(auditLogs) ? auditLogs : [];

  const handleApply = (e) => {
    e.preventDefault();
    if (onFilter) {
      onFilter({ incidentId, eventType, action, dateFrom, dateTo });
    }
  };

  const handleReset = () => {
    setIncidentId("");
    setEventType("");
    setAction("");
    setDateFrom("");
    setDateTo("");
    if (onFilter) {
      onFilter({});
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Filter Audit Trail</h2>
            <p>Query audit entries by incident ID, event type, action or date range.</p>
          </div>
        </div>
        <form onSubmit={handleApply} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px", alignItems: "end" }}>
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "600", marginBottom: "4px" }}>Incident ID</label>
            <input
              type="text"
              placeholder="e.g. UUID"
              value={incidentId}
              onChange={(e) => setIncidentId(e.target.value)}
              style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", border: "1px solid #cbd5e1" }}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "600", marginBottom: "4px" }}>Event Type</label>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", border: "1px solid #cbd5e1" }}
            >
              <option value="">All Event Types</option>
              <option value="IncidentCreatedEvent">IncidentCreatedEvent</option>
              <option value="IncidentAssignedEvent">IncidentAssignedEvent</option>
              <option value="IncidentStatusChangedEvent">IncidentStatusChangedEvent</option>
              <option value="IncidentCommentAddedEvent">IncidentCommentAddedEvent</option>
              <option value="PriorityChangedEvent">PriorityChangedEvent</option>
              <option value="SLAWarningEvent">SLAWarningEvent</option>
              <option value="SLABreachedEvent">SLABreachedEvent</option>
              <option value="SLAMetEvent">SLAMetEvent</option>
              <option value="IncidentArchivedEvent">IncidentArchivedEvent</option>
              <option value="IncidentMergedEvent">IncidentMergedEvent</option>
            </select>
          </div>
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "600", marginBottom: "4px" }}>Action</label>
            <select
              value={action}
              onChange={(e) => setAction(e.target.value)}
              style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", border: "1px solid #cbd5e1" }}
            >
              <option value="">All Actions</option>
              <option value="INCIDENT_CREATED">INCIDENT_CREATED</option>
              <option value="INCIDENT_ASSIGNED">INCIDENT_ASSIGNED</option>
              <option value="STATUS_CHANGED">STATUS_CHANGED</option>
              <option value="COMMENT_ADDED">COMMENT_ADDED</option>
              <option value="PRIORITY_CHANGED">PRIORITY_CHANGED</option>
              <option value="SLA_WARNING_TRIGGERED">SLA_WARNING_TRIGGERED</option>
              <option value="SLA_BREACHED">SLA_BREACHED</option>
              <option value="SLA_MET">SLA_MET</option>
              <option value="INCIDENT_ARCHIVED">INCIDENT_ARCHIVED</option>
              <option value="INCIDENT_MERGED">INCIDENT_MERGED</option>
            </select>
          </div>
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "600", marginBottom: "4px" }}>From Date</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", border: "1px solid #cbd5e1" }}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "600", marginBottom: "4px" }}>To Date</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", border: "1px solid #cbd5e1" }}
            />
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <button type="submit" className="button button-primary" style={{ flexGrow: 1 }}>
              Filter
            </button>
            <button type="button" className="button button-outline" onClick={handleReset}>
              Reset
            </button>
          </div>
        </form>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>System Audit Trail</h2>
            <p>{logs.length} chronological audit entries</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Incident ID</th>
                <th>Actor ID</th>
                <th>Action</th>
                <th>Event Type</th>
                <th>Previous Value</th>
                <th>New Value</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: "center", color: "#697586" }}>
                    No audit log entries matching filters.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id}>
                    <td style={{ fontSize: "12px", whiteSpace: "nowrap" }}>
                      {new Date(log.occurredAt).toLocaleString()}
                    </td>
                    <td style={{ fontFamily: "monospace", fontSize: "11px" }}>{log.incidentId || "—"}</td>
                    <td style={{ fontFamily: "monospace", fontSize: "11px" }}>{log.actorId || "System"}</td>
                    <td><strong>{log.action}</strong></td>
                    <td><span className="skill-label">{log.eventType}</span></td>
                    <td>{log.previousValue || "—"}</td>
                    <td>{log.newValue || "—"}</td>
                    <td style={{ fontSize: "12px" }}>{log.details || "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function TechnicianDashboard({ apiClient, currentUser, onOpenIncident, onNavigate }) {
  const [techProfile, setTechProfile] = useState(null);
  const [assignedIncidents, setAssignedIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      // Find technician profile
      const techsRes = await apiClient.get("/technicians");
      const myProfile = (techsRes?.data || []).find(
        (t) => t.userId === currentUser.id
      );
      if (myProfile) {
        setTechProfile(myProfile);
      }

      // Load assigned incidents
      const incRes = await apiClient.get("/incidents", {
        params: { assignedTechnicianId: currentUser.id, limit: 50 },
      });
      setAssignedIncidents(incRes?.data || []);
    } catch (err) {
      console.error("Failed to load technician dashboard data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggleAvailability = async () => {
    if (!techProfile) return;
    setToggling(true);
    const newStatus = techProfile.availability === "AVAILABLE" ? "BUSY" : "AVAILABLE";
    try {
      await apiClient.patch(`/technicians/${techProfile.id}/availability`, {
        availability: newStatus,
      });
      setTechProfile({ ...techProfile, availability: newStatus });
    } catch (err) {
      console.error("Failed to update availability", err);
    } finally {
      setToggling(false);
    }
  };

  const activeIncidents = assignedIncidents.filter(
    (i) => !["RESOLVED", "VERIFIED", "CLOSED"].includes(i.status)
  );
  const criticalActive = activeIncidents.filter((i) => i.priority === "P1");
  const highActive = activeIncidents.filter((i) => i.priority === "P2");
  const isNearCapacity = techProfile && activeIncidents.length >= techProfile.maxCapacity;

  if (loading) {
    return <div className="loading">Loading technician metrics...</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Operational Warnings Banner */}
      {(criticalActive.length > 0 || highActive.length > 0 || isNearCapacity) && (
        <section className="technician-warnings-container">
          {criticalActive.map((inc) => (
            <div key={inc.id} className="warning-card critical">
              <div className="warning-card-content">
                <strong>🚨 Critical Priority Incident (P1) Assigned</strong>
                <p>
                  Incident <strong>{inc.incidentCode || inc.id}</strong> ({inc.category}) is in <strong>{inc.status}</strong> status. Immediate response required to avoid SLA breach!
                </p>
              </div>
              <button
                type="button"
                className="button button-small button-primary"
                onClick={() => onOpenIncident(inc.id)}
              >
                Open Incident
              </button>
            </div>
          ))}

          {highActive.map((inc) => (
            <div key={inc.id} className="warning-card">
              <div className="warning-card-content">
                <strong>⚠️ High Priority Incident (P2) Active</strong>
                <p>
                  Incident <strong>{inc.incidentCode || inc.id}</strong> ({inc.category}) is in <strong>{inc.status}</strong> status.
                </p>
              </div>
              <button
                type="button"
                className="button button-small button-outline"
                onClick={() => onOpenIncident(inc.id)}
              >
                Open Incident
              </button>
            </div>
          ))}

          {isNearCapacity && (
            <div className="warning-card">
              <div className="warning-card-content">
                <strong>⚠️ Workload Capacity Warning</strong>
                <p>
                  You are currently handling <strong>{activeIncidents.length}</strong> active incidents, reaching your configured capacity of <strong>{techProfile.maxCapacity}</strong>.
                </p>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Quick Stat Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <span>Active Assigned Incidents</span>
          <strong>{activeIncidents.length}</strong>
          <small>In progress or pending</small>
        </div>
        <div className="stat-card">
          <span>Workload Capacity</span>
          <strong>
            {activeIncidents.length} / {techProfile?.maxCapacity ?? "—"}
          </strong>
          <small>{isNearCapacity ? "At Maximum Capacity" : "Available Capacity"}</small>
        </div>
        <div className="stat-card">
          <span>Operational Availability</span>
          <strong style={{ color: techProfile?.availability === "AVAILABLE" ? "#10b981" : "#ef4444" }}>
            {techProfile?.availability || "AVAILABLE"}
          </strong>
          <small>
            <button
              type="button"
              className="button button-small button-outline"
              style={{ marginTop: "6px" }}
              disabled={toggling || !techProfile}
              onClick={handleToggleAvailability}
            >
              Set to {techProfile?.availability === "AVAILABLE" ? "Busy" : "Available"}
            </button>
          </small>
        </div>
        <div className="stat-card">
          <span>Critical / High Incidents</span>
          <strong style={{ color: criticalActive.length > 0 ? "#ef4444" : "#1e293b" }}>
            {criticalActive.length + highActive.length}
          </strong>
          <small>{criticalActive.length} P1 Critical, {highActive.length} P2 High</small>
        </div>
      </div>

      {/* Assigned Incidents Table */}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Assigned Active Incidents</h2>
            <p>Directly assigned incidents requiring technical investigation or resolution.</p>
          </div>
          <button
            type="button"
            className="button button-outline"
            onClick={() => onNavigate && onNavigate("my-incidents")}
          >
            View All Incidents
          </button>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Category</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {activeIncidents.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", color: "#697586" }}>
                    No active assigned incidents at this time.
                  </td>
                </tr>
              ) : (
                activeIncidents.map((inc) => (
                  <tr key={inc.id}>
                    <td><strong>{inc.incidentCode || inc.id}</strong></td>
                    <td>{inc.category}</td>
                    <td>
                      <span className={`status ${inc.priority === "P1" ? "inactive" : inc.priority === "P2" ? "warning" : "active"}`}>
                        {inc.priority}
                      </span>
                    </td>
                    <td>
                      <span className="status active">{inc.status}</span>
                    </td>
                    <td style={{ fontSize: "12px" }}>
                      {new Date(inc.createdAt).toLocaleString()}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="button button-small button-outline"
                        onClick={() => onOpenIncident(inc.id)}
                      >
                        Open Details
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default App;
