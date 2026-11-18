import { useEffect, useMemo, useState } from "react";
import {
  EmployeeDashboard,
  MyIncidents,
  ReportIncident,
  IncidentDetails,
} from "./features/employee";

const API = "http://127.0.0.1:8000/api/v1";

async function api(path, token, options = {}) {
  const headers = { ...(options.headers || {}) };

  if (token) headers.Authorization = `Bearer ${token}`;

  if (options.body instanceof URLSearchParams) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (options.body) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (response.status === 204) return null;

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || `Request failed (${response.status})`);
  }

  return data;
}

function App() {
  const [token, setToken] = useState(localStorage.getItem("iitsm_token") || "");
  const [user, setUser] = useState(null);
  const [page, setPage] = useState("dashboard");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [data, setData] = useState([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState(null);
  const [servicesList, setServicesList] = useState([]);
  const [categoriesList, setCategoriesList] = useState([]);

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

  useEffect(() => {
    if (!token) return;
    api("/services", token).then((res) => setServicesList(Array.isArray(res) ? res : [])).catch(() => {});
    api("/categories", token).then((res) => setCategoriesList(Array.isArray(res) ? res : [])).catch(() => {});
  }, [token]);

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
        const policies = await api("/sla/policies", token).catch(() => []);
        const violations = await api("/sla/violations?includeWarnings=true", token).catch(() => []);
        setData({ policies, violations });
      } else if (page === "audit" && isAdmin) {
        setData(await api("/audit?limit=50", token).catch(() => []));
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

  useEffect(() => {
    if (!token) return;

    api("/auth/me", token)
      .then((profile) => {
        setUser(profile);
        if (profile.role === "ADMIN") {
          setPage("dashboard");
        } else if (profile.role === "TECHNICIAN") {
          setPage("my-incidents");
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
      setError(err.message);
    }
  }

  async function perform(path, method, body, successMessage) {
    setError("");
    setNotice("");

    try {
      await api(path, token, {
        method,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      setNotice(successMessage);
      await loadPage();
    } catch (err) {
      setError(err.message);
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

function TechniciansPage({ technicians, perform }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Technician Roster & Workload</h2>
          <p>Operational capacity, availability status and active workload.</p>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Profile ID</th>
              <th>User ID</th>
              <th>Experience</th>
              <th>Max Capacity</th>
              <th>Active Workload</th>
              <th>Availability</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {technicians.map((t) => (
              <tr key={t.id}>
                <td style={{ fontFamily: "monospace", fontSize: "12px" }}>{t.id}</td>
                <td style={{ fontFamily: "monospace", fontSize: "12px" }}>{t.userId}</td>
                <td>{t.experienceYears} yrs</td>
                <td>{t.maxCapacity}</td>
                <td>
                  <span className={`status ${t.activeIncidentCount >= t.maxCapacity ? "inactive" : "active"}`}>
                    {t.activeIncidentCount} / {t.maxCapacity}
                  </span>
                </td>
                <td>
                  <span className={`status ${t.availability === "AVAILABLE" ? "active" : "inactive"}`}>
                    {t.availability}
                  </span>
                </td>
                <td>
                  <button
                    className="button button-small button-outline"
                    onClick={() =>
                      perform(
                        `/technicians/${t.id}/availability`,
                        "PATCH",
                        { availability: t.availability === "AVAILABLE" ? "BUSY" : "AVAILABLE" },
                        `Updated availability for technician ${t.id}`
                      )
                    }
                  >
                    Toggle {t.availability === "AVAILABLE" ? "Busy" : "Available"}
                  </button>
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
  );
}

function SLAPage({ slaData, perform }) {
  const policies = Array.isArray(slaData?.policies) ? slaData.policies : [];
  const violations = Array.isArray(slaData?.violations) ? slaData.violations : [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
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

function AuditPage({ auditLogs }) {
  const logs = Array.isArray(auditLogs) ? auditLogs : [];

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>System Audit Trail</h2>
          <p>Chronological record of state transitions, assignments and actions.</p>
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
                  No audit log entries available.
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
  );
}

export default App;
