import { useState, useEffect } from "react";
import {
  Search,
  Filter,
  Plus,
  ArrowUpRight,
  ShieldCheck,
  CheckCircle2,
  Clock,
  AlertTriangle,
  AlertCircle,
  RefreshCw,
  FileText,
  Landmark,
  X,
  KeyRound,
  Check,
  Copy
} from "lucide-react";
import { api, formatINR, formatDate } from "../api";

export default function InstrumentsView({ currentUser, onOpenNewModal, onSelectInstrumentForRecon }) {
  const [activeTab, setActiveTab] = useState("registry"); // "registry" | "release_queue" | "failed_verifications"
  const [instruments, setInstruments] = useState([]);
  const [institutions, setInstitutions] = useState([]);
  const [universities, setUniversities] = useState([]);
  const [failedReports, setFailedReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  // Senior Manager Filters
  const [selectedUnivFilter, setSelectedUnivFilter] = useState("ALL");
  const [selectedStateFilter, setSelectedStateFilter] = useState("ALL");
  const [selectedInstFilter, setSelectedInstFilter] = useState("ALL");

  // Scrutiny / Review Modal
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Release Workflow State (Recommend & Approve)
  const [activeReleaseItem, setActiveReleaseItem] = useState(null);
  const [recommendReason, setRecommendReason] = useState("");
  const [checklist, setChecklist] = useState({
    grievances_cleared: true,
    faculty_salary_compliant: true,
    regional_noc: true,
  });
  const [approveReason, setApproveReason] = useState("");
  const [processingRelease, setProcessingRelease] = useState(false);
  const [issuedCodeResult, setIssuedCodeResult] = useState(null);

  const isSenior = currentUser?.role === "aicte_senior" || currentUser?.role === "admin";
  const isOfficer = currentUser?.role === "aicte_officer";
  const isAuditor = currentUser?.role === "auditor";

  const fetchRegistryData = async () => {
    try {
      setLoading(true);
      const params = {};
      if (selectedUnivFilter !== "ALL") params.university_id = selectedUnivFilter;
      if (selectedStateFilter !== "ALL") params.state = selectedStateFilter;
      if (selectedInstFilter !== "ALL") params.institution_id = selectedInstFilter;

      const [instsData, collegesData, univsData] = await Promise.all([
        api.getInstruments(params),
        api.getInstitutions().catch(() => []),
        api.getUniversities().catch(() => []),
      ]);
      setInstruments(instsData || []);
      setInstitutions(collegesData || []);
      setUniversities(univsData || []);

      if (isSenior || isAuditor) {
        const reports = await api.getFailedVerifications().catch(() => []);
        setFailedReports(reports || []);
      }
    } catch (err) {
      console.error("Failed to fetch instruments registry:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRegistryData();
  }, [selectedUnivFilter, selectedStateFilter, selectedInstFilter]);

  const openDetails = async (id) => {
    try {
      setDetailLoading(true);
      const detail = await api.getInstrumentDetail(id);
      setSelectedDetail(detail);
    } catch (err) {
      alert("Failed to load instrument details: " + err.message);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleRecommendSubmit = async (e) => {
    e.preventDefault();
    if (!activeReleaseItem) return;
    try {
      setProcessingRelease(true);
      const relId = activeReleaseItem.release_requests?.[0]?.id || activeReleaseItem.id;
      await api.recommendRelease(relId, recommendReason, checklist);
      alert("Compliance scrutiny and recommendation recorded successfully.");
      setActiveReleaseItem(null);
      await fetchRegistryData();
    } catch (err) {
      alert("Recommendation failed: " + err.message);
    } finally {
      setProcessingRelease(false);
    }
  };

  const handleApproveSubmit = async (e) => {
    e.preventDefault();
    if (!activeReleaseItem) return;
    try {
      setProcessingRelease(true);
      const relId = activeReleaseItem.release_requests?.[0]?.id || activeReleaseItem.id;
      const res = await api.approveRelease(relId, approveReason || "Clearance verified and approved.");
      setIssuedCodeResult(res);
      await fetchRegistryData();
    } catch (err) {
      alert("Senior approval failed: " + err.message);
    } finally {
      setProcessingRelease(false);
    }
  };

  const handleApproveDeposit = async (instrumentId) => {
    try {
      await api.approveSubmission(instrumentId, "Deposit parameters verified against university records.");
      alert("Regulatory deposit approved by University Officer! Status is now ACTIVE.");
      setSelectedDetail(null);
      await fetchRegistryData();
    } catch (err) {
      alert("Deposit approval failed: " + err.message);
    }
  };

  const filtered = instruments.filter((item) => {
    const matchesStatus =
      statusFilter === "ALL" ||
      (item.status && item.status.toUpperCase() === statusFilter);
    if (!matchesStatus) return false;

    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      item.reference_no?.toLowerCase().includes(term) ||
      item.bank_name?.toLowerCase().includes(term) ||
      item.joint_holder?.toLowerCase().includes(term) ||
      item.branch?.toLowerCase().includes(term) ||
      item.institution_id?.toLowerCase().includes(term)
    );
  });

  const releaseQueueItems = instruments.filter((i) =>
    ["RELEASE_REQUESTED", "COMPLIANCE_CHECK", "APPROVED", "BANK_RELEASE_PENDING"].includes(i.status)
  );

  const getStatusBadge = (status) => {
    const s = (status || "").toLowerCase();
    if (s === "active") {
      return <span className="status-badge active"><CheckCircle2 size={13} /> Active</span>;
    }
    if (s === "disputed" || s === "rejected") {
      return <span className="status-badge disputed"><AlertTriangle size={13} /> {status}</span>;
    }
    if (s === "aicte_review") {
      return <span className="status-badge blue"><ShieldCheck size={13} /> AICTE Review</span>;
    }
    if (s === "needs_correction") {
      return <span className="status-badge amber"><AlertTriangle size={13} /> Needs Correction</span>;
    }
    if (["release_requested", "compliance_check", "approved", "bank_release_pending"].includes(s)) {
      return <span className="status-badge teal"><Clock size={13} /> Release Active</span>;
    }
    if (s === "closed") {
      return <span className="status-badge gray"><CheckCircle2 size={13} /> Closed</span>;
    }
    return <span className="status-badge pending"><Clock size={13} /> {status || "Submitted"}</span>;
  };

  return (
    <div className="view-container">
      {/* Simulation Banner Notice */}
      <div className="simulated-global-banner">
        <Landmark size={18} />
        <span>
          <strong>[SIMULATED] Regulatory Prototype Notice:</strong> Bank confirmation is simulated in this prototype. Synthetic data only.
        </span>
      </div>

      {/* Header */}
      <section className="welcome-row">
        <div>
          <p className="eyebrow">
            {isSenior
              ? "AICTE HEADQUARTERS · NATIONAL JURISDICTION"
              : isOfficer
              ? `REGIONAL DESK · ${currentUser?.university_id ? `UNIVERSITY SCOPE: ${currentUser.university_id.toUpperCase()}` : "ASSIGNED UNIVERSITY"}`
              : "REGULATORY COMPLIANCE OBSERVER"}
          </p>
          <h1>Officer Regulatory Workspace</h1>
          <p className="subtitle">
            {"AICTE \u2192 University \u2192 College hierarchy with strict query-level isolation."}
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button className="secondary-button" onClick={fetchRegistryData}>
            <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh
          </button>
        </div>
      </section>

      {/* Workspace Navigation Tabs */}
      <div className="filter-bar" style={{ marginBottom: "20px" }}>
        <div className="filter-tabs">
          <button
            className={`filter-pill ${activeTab === "registry" ? "active" : ""}`}
            onClick={() => setActiveTab("registry")}
          >
            📋 FDR Registry ({instruments.length})
          </button>
          <button
            className={`filter-pill ${activeTab === "release_queue" ? "active" : ""}`}
            onClick={() => setActiveTab("release_queue")}
          >
            ⚖️ Release Queue ({releaseQueueItems.length})
          </button>
          {(isSenior || isAuditor) && (
            <button
              className={`filter-pill ${activeTab === "failed_verifications" ? "active" : ""}`}
              onClick={() => setActiveTab("failed_verifications")}
            >
              ⚠️ Failed Verifications Report ({failedReports.length})
            </button>
          )}
        </div>
      </div>

      {/* ── Tab 1: FDR Registry ───────────────────────────────────────────────── */}
      {activeTab === "registry" && (
        <section className="content-card">
          {/* Senior Manager Filters (University, State, College) */}
          {isSenior && (
            <div className="filter-bar" style={{ marginBottom: "16px", background: "var(--bg-secondary)", padding: "12px", borderRadius: "8px" }}>
              <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center" }}>
                <div>
                  <span style={{ fontSize: "0.8rem", fontWeight: 600, display: "block", marginBottom: "4px" }}>Filter University:</span>
                  <select
                    className="filter-select"
                    value={selectedUnivFilter}
                    onChange={(e) => setSelectedUnivFilter(e.target.value)}
                  >
                    <option value="ALL">All Universities (National)</option>
                    {universities.map((u) => (
                      <option key={u.id} value={u.id}>{u.name} ({u.state})</option>
                    ))}
                  </select>
                </div>

                <div>
                  <span style={{ fontSize: "0.8rem", fontWeight: 600, display: "block", marginBottom: "4px" }}>Filter State:</span>
                  <select
                    className="filter-select"
                    value={selectedStateFilter}
                    onChange={(e) => setSelectedStateFilter(e.target.value)}
                  >
                    <option value="ALL">All States</option>
                    <option value="Delhi">Delhi</option>
                    <option value="Maharashtra">Maharashtra</option>
                  </select>
                </div>

                <div>
                  <span style={{ fontSize: "0.8rem", fontWeight: 600, display: "block", marginBottom: "4px" }}>Filter College:</span>
                  <select
                    className="filter-select"
                    value={selectedInstFilter}
                    onChange={(e) => setSelectedInstFilter(e.target.value)}
                  >
                    <option value="ALL">All Colleges</option>
                    {institutions.map((inst) => (
                      <option key={inst.id} value={inst.id}>{inst.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Quick Search and Status Filter */}
          <div className="filter-bar">
            <div className="search-box">
              <Search size={18} />
              <input
                type="text"
                placeholder="Search FDR number, bank name, college..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            <div className="filter-tabs">
              {["ALL", "AICTE_REVIEW", "ACTIVE", "DISPUTED", "CLOSED"].map((s) => (
                <button
                  key={s}
                  className={`filter-pill ${statusFilter === s ? "active" : ""}`}
                  onClick={() => setStatusFilter(s)}
                >
                  {s.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>FDR CERTIFICATE</th>
                  <th>ISSUING BANK [SIMULATED]</th>
                  <th>COLLEGE ID</th>
                  <th>PRINCIPAL AMOUNT</th>
                  <th>MATURITY DATE</th>
                  <th>STATUS</th>
                  <th>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan="7" style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                      {loading ? "Loading deposits..." : "No instruments match criteria."}
                    </td>
                  </tr>
                ) : (
                  filtered.map((item) => (
                    <tr key={item.id}>
                      <td className="fdr-number">
                        <strong>{item.reference_no}</strong>
                        <span className="sub-tag">{item.joint_holder || "AICTE Joint"}</span>
                      </td>
                      <td>
                        <div>{item.bank_name}</div>
                        <span className="sub-text">{item.branch || "Branch"} [SIMULATED]</span>
                      </td>
                      <td><code>{item.institution_id}</code></td>
                      <td className="amount">{formatINR(item.amount_paise)}</td>
                      <td>{formatDate(item.maturity_date)}</td>
                      <td>{getStatusBadge(item.status)}</td>
                      <td style={{ whiteSpace: "nowrap" }}>
                        {item.status === "AICTE_REVIEW" && (isOfficer || currentUser?.role === "admin") ? (
                          <div style={{ display: "flex", gap: "6px" }}>
                            <button
                              className="primary-button"
                              style={{ padding: "4px 8px", fontSize: "0.8rem", backgroundColor: "#0284c7" }}
                              onClick={() => handleApproveDeposit(item.id)}
                            >
                              Approve Deposit
                            </button>
                            <button
                              className="secondary-button"
                              style={{ padding: "4px 8px", fontSize: "0.8rem" }}
                              onClick={() => openDetails(item.id)}
                            >
                              Scrutiny
                            </button>
                          </div>
                        ) : (
                          <button
                            className="secondary-button"
                            style={{ padding: "4px 8px", fontSize: "0.8rem" }}
                            onClick={() => openDetails(item.id)}
                          >
                            Scrutiny View
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ── Tab 2: Release Queue ──────────────────────────────────────────────── */}
      {activeTab === "release_queue" && (
        <section className="content-card">
          <div className="section-heading">
            <div>
              <h2>Release Clearance &amp; Approval Governance Queue</h2>
              <p>Two-tier governance: University Officer verifies compliance checklist &rarr; Senior Manager approves and issues two-part code.</p>
            </div>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>FDR NUMBER</th>
                  <th>COLLEGE</th>
                  <th>AMOUNT</th>
                  <th>MATURITY DATE</th>
                  <th>STAGE / STATUS</th>
                  <th>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {releaseQueueItems.length === 0 ? (
                  <tr>
                    <td colSpan="6" style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                      No deposits currently in the release queue.
                    </td>
                  </tr>
                ) : (
                  releaseQueueItems.map((item) => (
                    <tr key={item.id}>
                      <td><strong>{item.reference_no}</strong></td>
                      <td>{item.institution_id}</td>
                      <td><strong>{formatINR(item.amount_paise)}</strong></td>
                      <td>{formatDate(item.maturity_date)}</td>
                      <td>{getStatusBadge(item.status)}</td>
                      <td>
                        {item.status === "RELEASE_REQUESTED" && isOfficer && (
                          <button
                            className="primary-button"
                            style={{ padding: "5px 10px", fontSize: "0.8rem" }}
                            onClick={() => {
                              setActiveReleaseItem(item);
                              setIssuedCodeResult(null);
                            }}
                          >
                            Scrutinize &amp; Recommend
                          </button>
                        )}
                        {item.status === "COMPLIANCE_CHECK" && isSenior && (
                          <button
                            className="primary-button"
                            style={{ padding: "5px 10px", fontSize: "0.8rem", backgroundColor: "#7c3aed" }}
                            onClick={() => {
                              setActiveReleaseItem(item);
                              setIssuedCodeResult(null);
                            }}
                          >
                            Review &amp; Approve Release
                          </button>
                        )}
                        {item.status === "BANK_RELEASE_PENDING" && (
                          <span style={{ fontSize: "0.8rem", color: "#059669" }}>
                            Awaiting Bank Confirmation
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ── Tab 3: Failed Verifications Report (Senior & Auditor Only) ─────────── */}
      {activeTab === "failed_verifications" && (isSenior || isAuditor) && (
        <section className="content-card">
          <div className="section-heading">
            <div>
              <h2>Failed Bank Verifications Compliance Report</h2>
              <p>Audit of all bank record mismatches. Deposits with 3 or more failures automatically trigger senior risk alerts.</p>
            </div>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>FDR NUMBER</th>
                  <th>INSTITUTION</th>
                  <th>BANK NAME [SIMULATED]</th>
                  <th>REASON CODE</th>
                  <th>ATTEMPTED AT</th>
                  <th>TOTAL FAILURES</th>
                  <th>RISK STATUS</th>
                </tr>
              </thead>
              <tbody>
                {failedReports.length === 0 ? (
                  <tr>
                    <td colSpan="7" style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                      No failed verification attempts recorded in the compliance ledger.
                    </td>
                  </tr>
                ) : (
                  failedReports.map((r) => {
                    const isHighRisk = r.current_failed_count >= 3;
                    return (
                      <tr key={r.id}>
                        <td><strong>{r.reference_no}</strong></td>
                        <td>{r.institution_name} ({r.institution_id})</td>
                        <td>{r.bank_name}</td>
                        <td>
                          <span style={{ color: "#b91c1c", fontWeight: 600 }}>
                            {r.reason_code}
                          </span>
                        </td>
                        <td>{formatDate(r.attempted_at)}</td>
                        <td><strong>{r.current_failed_count}</strong></td>
                        <td>
                          {isHighRisk ? (
                            <span className="status-badge red" title="Exceeded 3 failed attempts threshold">
                              <AlertTriangle size={12} /> 3+ Failures Alert
                            </span>
                          ) : (
                            <span className="status-badge amber">
                              Mismatch Logged
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ── Release Governance Modal (Recommend or Approve) ──────────────────── */}
      {activeReleaseItem && (
        <div className="modal-backdrop">
          <div className="modal-container" style={{ maxWidth: "680px" }}>
            <div className="modal-header">
              <h3>
                {activeReleaseItem.status === "RELEASE_REQUESTED"
                  ? "Officer Scrutiny & Recommendation"
                  : "Senior Manager Final Approval & Two-Part Authorization"}
              </h3>
              <button className="icon-button" onClick={() => setActiveReleaseItem(null)}><X size={18} /></button>
            </div>

            <div style={{ padding: "20px" }}>
              <div style={{ background: "var(--bg-secondary)", padding: "12px", borderRadius: "8px", marginBottom: "16px" }}>
                <div>FDR Number: <strong>{activeReleaseItem.reference_no}</strong></div>
                <div>Principal: <strong>{formatINR(activeReleaseItem.amount_paise)}</strong> · Bank: <strong>{activeReleaseItem.bank_name} [SIMULATED]</strong></div>
              </div>

              {/* University Officer Checklist */}
              {activeReleaseItem.status === "RELEASE_REQUESTED" && isOfficer && (
                <form onSubmit={handleRecommendSubmit}>
                  <p style={{ fontWeight: 600, marginBottom: "10px" }}>Statutory Clearance Checklist:</p>
                  <label style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "8px" }}>
                    <input
                      type="checkbox"
                      checked={checklist.grievances_cleared}
                      onChange={(e) => setChecklist({ ...checklist, grievances_cleared: e.target.checked })}
                    />
                    <span>No Open Student / Faculty Grievances Pending</span>
                  </label>
                  <label style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "8px" }}>
                    <input
                      type="checkbox"
                      checked={checklist.faculty_salary_compliant}
                      onChange={(e) => setChecklist({ ...checklist, faculty_salary_compliant: e.target.checked })}
                    />
                    <span>Faculty Salary Norms Cleared (7th CPC Compliance)</span>
                  </label>
                  <label style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "16px" }}>
                    <input
                      type="checkbox"
                      checked={checklist.regional_noc}
                      onChange={(e) => setChecklist({ ...checklist, regional_noc: e.target.checked })}
                    />
                    <span>AICTE University / Regional Office Inspection NOC Issued</span>
                  </label>

                  <label style={{ display: "block", fontWeight: 600, marginBottom: "6px" }}>
                    Recommendation Observations:
                  </label>
                  <textarea
                    className="text-input"
                    rows="3"
                    value={recommendReason}
                    onChange={(e) => setRecommendReason(e.target.value)}
                    placeholder="Enter official recommendation notes..."
                    required
                  />

                  <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "16px" }}>
                    <button type="button" className="secondary-button" onClick={() => setActiveReleaseItem(null)}>Cancel</button>
                    <button type="submit" className="primary-button" disabled={processingRelease}>
                      {processingRelease ? "Submitting..." : "Submit Recommendation"}
                    </button>
                  </div>
                </form>
              )}

              {/* Senior Manager Approval */}
              {activeReleaseItem.status === "COMPLIANCE_CHECK" && isSenior && !issuedCodeResult && (
                <form onSubmit={handleApproveSubmit}>
                  <div style={{ background: "#ecfdf5", border: "1px solid #10b981", padding: "12px", borderRadius: "8px", marginBottom: "16px" }}>
                    <p style={{ color: "#065f46", margin: 0, fontSize: "0.85rem" }}>
                      ✓ Pre-clearance checklist verified by University Officer.<br />
                      ✓ Separation of Duties: Senior approver differs from recommending officer.<br />
                      ✓ Simulated fresh bank re-verification will be executed atomically upon submission.
                    </p>
                  </div>

                  <label style={{ display: "block", fontWeight: 600, marginBottom: "6px" }}>
                    Approval Justification:
                  </label>
                  <textarea
                    className="text-input"
                    rows="3"
                    value={approveReason}
                    onChange={(e) => setApproveReason(e.target.value)}
                    placeholder="Enter approval justification recorded in cryptographic ledger..."
                    required
                  />

                  <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "16px" }}>
                    <button type="button" className="secondary-button" onClick={() => setActiveReleaseItem(null)}>Cancel</button>
                    <button type="submit" className="primary-button" style={{ backgroundColor: "#7c3aed" }} disabled={processingRelease}>
                      <KeyRound size={16} /> {processingRelease ? "Generating Authorization..." : "Approve & Issue Two-Part Code"}
                    </button>
                  </div>
                </form>
              )}

              {/* Display Issued Release Authorization */}
              {issuedCodeResult && (
                <div style={{ background: "#f5f3ff", border: "1px solid #7c3aed", padding: "16px", borderRadius: "8px" }}>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center", color: "#5b21b6", marginBottom: "8px" }}>
                    <CheckCircle2 size={20} />
                    <strong>Release Authorization Approved &amp; Bank Code Dispatched!</strong>
                  </div>
                  <p style={{ fontSize: "0.85rem", color: "#4c1d95", marginBottom: "12px" }}>
                    Release Ref: <strong>{issuedCodeResult.release_ref}</strong>. Bank release authorization code dispatched to partner bank inbox [SIMULATED].
                  </p>

                  <div style={{ background: "#eff6ff", padding: "12px", borderRadius: "6px", border: "1px solid #bfdbfe", marginBottom: "12px" }}>
                    <div style={{ fontWeight: 600, color: "#1e40af", fontSize: "0.85rem", marginBottom: "4px" }}>
                      🔒 Zero-Knowledge College Code Privacy
                    </div>
                    <p style={{ fontSize: "0.8rem", color: "#1e3a8a", margin: 0 }}>
                      The College Secret Release Code is never exposed to AICTE staff or senior managers. Only the college institution can claim and reveal its one-time code through their authenticated portal.
                    </p>
                  </div>

                  <button
                    className="primary-button"
                    style={{ marginTop: "8px", width: "100%", backgroundColor: "#7c3aed" }}
                    onClick={() => {
                      setActiveReleaseItem(null);
                      setIssuedCodeResult(null);
                    }}
                  >
                    Done
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Two-Column Scrutiny Modal ────────────────────────────────────────── */}
      {selectedDetail && (
        <div className="modal-backdrop">
          <div className="modal-container" style={{ maxWidth: "800px" }}>
            <div className="modal-header">
              <h3>Two-Column Trust Scrutiny: {selectedDetail.reference_no}</h3>
              <button className="icon-button" onClick={() => setSelectedDetail(null)}><X size={18} /></button>
            </div>
            <div style={{ padding: "20px" }}>
              <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "16px" }}>
                Comparison between college-submitted deposit parameters and partner bank confirmed records [SIMULATED].
              </p>

              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>FIELD ATTRIBUTE</th>
                      <th>SUBMITTED BY COLLEGE</th>
                      <th>CONFIRMED BY BANK [SIMULATED]</th>
                      <th>RECONCILIATION RESULT</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedDetail.confirmations?.length > 0 ? (
                      selectedDetail.confirmations.map((c) => (
                        <tr key={c.id}>
                          <td><strong>{c.field_name.toUpperCase()}</strong></td>
                          <td>{c.submitted_value || "—"}</td>
                          <td>{c.confirmed_value || "—"}</td>
                          <td>
                            {c.result === "match" ? (
                              <span className="status-badge active"><CheckCircle2 size={12} /> Match</span>
                            ) : c.result === "mismatch" ? (
                              <span className="status-badge red"><AlertTriangle size={12} /> Mismatch</span>
                            ) : (
                              <span className="status-badge pending"><Clock size={12} /> Pending</span>
                            )}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="4" style={{ textAlign: "center", padding: "20px" }}>
                          No field confirmations recorded yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {selectedDetail.status === "AICTE_REVIEW" && (isOfficer || currentUser?.role === "admin") && (
                <div style={{ marginTop: "20px", padding: "16px", background: "#f0fdf4", border: "1px solid #86efac", borderRadius: "8px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <strong style={{ color: "#166534" }}>University Officer Scrutiny Action</strong>
                    <p style={{ margin: "4px 0 0", fontSize: "0.85rem", color: "#15803d" }}>
                      Bank simulated records matched. Confirm AICTE scrutiny and activate regulatory deposit.
                    </p>
                  </div>
                  <button
                    className="primary-button"
                    style={{ backgroundColor: "#16a34a", padding: "8px 16px", fontWeight: 600 }}
                    onClick={() => handleApproveDeposit(selectedDetail.id)}
                  >
                    ✓ Approve Regulatory Deposit
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
