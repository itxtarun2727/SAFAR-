import { useState, useEffect } from "react";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  Clock,
  AlertTriangle,
  AlertCircle,
  Plus,
  RefreshCw,
  Landmark,
  ShieldCheck,
  Calendar,
  DollarSign,
  FileCheck,
  Copy,
  Check,
  KeyRound
} from "lucide-react";
import { api, formatINR, formatDate } from "../api";

export default function CollegePortalView({ currentUser, onOpenNewModal }) {
  const [activeSubTab, setActiveSubTab] = useState("portfolio"); // "portfolio" | "upload" | "alerts"
  const [instruments, setInstruments] = useState([]);
  const [banks, setBanks] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [releasedCodes, setReleasedCodes] = useState({}); // instrumentId -> { code, ref }
  const [copiedCode, setCopiedCode] = useState(null);

  // Direct Quick Upload Form State
  const [uploadForm, setUploadForm] = useState({
    bank_id: "bank-001",
    bank_name: "Demo Bank A",
    branch: "Connaught Place Branch",
    reference_no: "",
    amount_rupees: "2500000",
    interest_rate: "7.25%",
    issue_date: new Date().toISOString().split("T")[0],
    maturity_date: new Date(new Date().setFullYear(new Date().getFullYear() + 10)).toISOString().split("T")[0],
    tenure_years: 10,
    joint_holder: "AICTE & College Society",
    lien_marked: true,
    file_name: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [actionLoadingId, setActionLoadingId] = useState(null);

  const loadCollegeData = async () => {
    try {
      setLoading(true);
      const [instData, alertData, banksData] = await Promise.all([
        api.getInstruments().catch(() => []),
        api.getAlerts().catch(() => []),
        api.getBanks().catch(() => []),
      ]);
      setInstruments(instData || []);
      setAlerts(alertData || []);
      setBanks(banksData || []);
      if (banksData && banksData.length > 0 && !uploadForm.bank_id) {
        setUploadForm((p) => ({ ...p, bank_id: banksData[0].id, bank_name: banksData[0].name }));
      }
    } catch (err) {
      console.error("Failed to load college data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCollegeData();
  }, []);

  const handleBankChange = (e) => {
    const bId = e.target.value;
    const found = banks.find((b) => b.id === bId);
    setUploadForm((prev) => ({
      ...prev,
      bank_id: bId,
      bank_name: found ? found.name : "Demo Bank A",
    }));
  };

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    setSubmitError("");
    setSubmitSuccess("");

    if (!uploadForm.reference_no.trim()) {
      setSubmitError("Please enter the FDR Certificate number.");
      return;
    }
    const amount = parseFloat(uploadForm.amount_rupees);
    if (isNaN(amount) || amount <= 0) {
      setSubmitError("Please enter a valid deposit amount.");
      return;
    }

    try {
      setSubmitting(true);
      const payload = {
        institution_id: currentUser?.institution_id || currentUser?.institution_ids?.[0] || "inst-001",
        bank_id: uploadForm.bank_id,
        bank_name: uploadForm.bank_name,
        branch: uploadForm.branch,
        reference_no: uploadForm.reference_no.trim(),
        amount_paise: Math.round(amount * 100),
        interest_rate: uploadForm.interest_rate,
        issue_date: uploadForm.issue_date,
        maturity_date: uploadForm.maturity_date,
        tenure_years: parseInt(uploadForm.tenure_years, 10) || 10,
        type: "bank_fdr",
        joint_holder: uploadForm.joint_holder,
        lien_marked: Boolean(uploadForm.lien_marked),
      };

      const res = await api.createInstrument(payload);
      setSubmitSuccess(`FDR Certificate ${uploadForm.reference_no} submitted! Automatic bank check completed [SIMULATED]. Status: ${res.status}`);
      setUploadForm((prev) => ({
        ...prev,
        reference_no: "",
        amount_rupees: "2500000",
        file_name: "",
      }));
      await loadCollegeData();
      setActiveSubTab("portfolio");
    } catch (err) {
      setSubmitError(err.message || "Failed to submit FDR certificate.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRequestRelease = async (instrumentId) => {
    try {
      setActionLoadingId(instrumentId);
      await api.requestRelease(instrumentId, {
        kind: "release",
        reason: "Deposit has reached maturity date. Requesting official lien discharge.",
      });
      await loadCollegeData();
      alert("Release request submitted to AICTE University Officer for compliance clearance.");
    } catch (err) {
      alert("Release request failed: " + err.message);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleClaimCode = async (releaseRef, instrumentId) => {
    try {
      setActionLoadingId(instrumentId);
      const res = await api.claimReleaseCode(releaseRef);
      setReleasedCodes((prev) => ({
        ...prev,
        [instrumentId]: { code: res.college_code, ref: res.release_ref },
      }));
    } catch (err) {
      alert("Failed to claim release code: " + err.message);
    } finally {
      setActionLoadingId(null);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(text);
    setTimeout(() => setCopiedCode(null), 2500);
  };

  const todayStr = new Date().toISOString().split("T")[0];

  const getCollegeStatusBadge = (item) => {
    const status = (item.status || "").toUpperCase();
    const isMatured = item.maturity_date && item.maturity_date <= todayStr;

    if (status === "SUBMITTED" || status === "BANK_CHECK") {
      return (
        <span className="status-badge pending" title="Submitted to system and undergoing simulated bank verification">
          <Clock size={13} /> Pending
        </span>
      );
    }
    if (status === "AICTE_REVIEW") {
      return (
        <span className="status-badge blue" title="Bank matched; undergoing AICTE University Officer review">
          <ShieldCheck size={13} /> In review
        </span>
      );
    }
    if (status === "ACTIVE") {
      if (isMatured) {
        return (
          <span className="status-badge purple" title="FDR has reached maturity date">
            <AlertCircle size={13} /> Matured
          </span>
        );
      }
      return (
        <span className="status-badge active" title="Approved by AICTE and active regulatory deposit">
          <CheckCircle2 size={13} /> Approved
        </span>
      );
    }
    if (status === "NEEDS_CORRECTION") {
      return (
        <div>
          <span className="status-badge amber" title="Discrepancy with bank record">
            <AlertTriangle size={13} /> Needs correction
          </span>
          <div style={{ fontSize: "0.75rem", color: "#b45309", marginTop: "3px" }}>
            Reason: Amount / tenure mismatch with bank record
          </div>
        </div>
      );
    }
    if (status === "REJECTED") {
      return (
        <div>
          <span className="status-badge red" title="Rejected by AICTE scrutiny officer">
            <AlertCircle size={13} /> Rejected
          </span>
          <div style={{ fontSize: "0.75rem", color: "#b91c1c", marginTop: "3px" }}>
            Reason: Rejection recorded by University Officer
          </div>
        </div>
      );
    }
    if (["RELEASE_REQUESTED", "COMPLIANCE_CHECK", "APPROVED", "BANK_RELEASE_PENDING"].includes(status)) {
      return (
        <span className="status-badge teal" title="Clearance and lien release workflow active">
          <Clock size={13} /> Release in progress
        </span>
      );
    }
    if (status === "CLOSED") {
      return (
        <span className="status-badge gray" title="Lien discharged by bank and deposit closed">
          <CheckCircle2 size={13} /> Closed
        </span>
      );
    }
    if (status === "DISPUTED") {
      return (
        <span className="status-badge red" title="Dispute hold active">
          <AlertTriangle size={13} /> Dispute Hold
        </span>
      );
    }
    return <span className="status-badge pending">{status}</span>;
  };

  return (
    <div className="view-container">
      {/* Simulation Banner */}
      <div className="simulated-global-banner">
        <Landmark size={18} />
        <span>
          <strong>[SIMULATED] Regulatory Prototype Notice:</strong> Bank confirmation is simulated in this prototype. Synthetic data only.
        </span>
      </div>

      {/* College Header */}
      <section className="welcome-row">
        <div>
          <p className="eyebrow">
            INSTITUTION PORTAL · {currentUser?.name?.toUpperCase() || "TECHNICAL COLLEGE DESK"}
          </p>
          <h1>College Regulatory Deposit Portal</h1>
          <p className="subtitle">
            Multi-Tenant Isolation: Strictly scoped to your college. Other colleges cannot view your records.
          </p>
        </div>

        <button className="primary-button" onClick={() => setActiveSubTab("upload")}>
          <UploadCloud size={18} /> Upload New FDR Receipt
        </button>
      </section>

      {/* College Metric Cards */}
      <section className="metrics-grid">
        <article className="metric-card">
          <div className="metric-top">
            <span>My Registered FDRs</span>
            <div className="metric-icon"><FileText size={20} /></div>
          </div>
          <h2>{instruments.length}</h2>
          <p>College regulatory joint deposits</p>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>Approved &amp; Active</span>
            <div className="metric-icon"><CheckCircle2 size={20} /></div>
          </div>
          <h2>{instruments.filter((i) => i.status === "ACTIVE").length}</h2>
          <p>Verified lien active with AICTE</p>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>Pending Review</span>
            <div className="metric-icon"><Clock size={20} /></div>
          </div>
          <h2>{instruments.filter((i) => ["SUBMITTED", "BANK_CHECK", "AICTE_REVIEW"].includes(i.status)).length}</h2>
          <p>Undergoing verification</p>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>Action Required</span>
            <div className="metric-icon"><AlertTriangle size={20} /></div>
          </div>
          <h2>{instruments.filter((i) => ["NEEDS_CORRECTION", "REJECTED", "DISPUTED"].includes(i.status)).length}</h2>
          <p>Correction or scrutiny action</p>
        </article>
      </section>

      {/* Sub-Tab Navigation */}
      <div className="filter-bar" style={{ marginBottom: "20px" }}>
        <div className="filter-tabs">
          <button
            className={`filter-pill ${activeSubTab === "portfolio" ? "active" : ""}`}
            onClick={() => setActiveSubTab("portfolio")}
          >
            📂 My Registered FDRs ({instruments.length})
          </button>
          <button
            className={`filter-pill ${activeSubTab === "upload" ? "active" : ""}`}
            onClick={() => setActiveSubTab("upload")}
          >
            📤 Upload New FDR Certificate
          </button>
          <button
            className={`filter-pill ${activeSubTab === "alerts" ? "active" : ""}`}
            onClick={() => setActiveSubTab("alerts")}
          >
            🔔 Status &amp; Maturity Alerts ({alerts.length})
          </button>
        </div>

        <button className="secondary-button" onClick={loadCollegeData} title="Refresh Live Data">
          <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh
        </button>
      </div>

      {submitSuccess && (
        <div className="alert-box success" style={{ marginBottom: "16px" }}>
          <CheckCircle2 size={16} />
          <span>{submitSuccess}</span>
        </div>
      )}

      {/* ── Sub-Tab 1: Portfolio View ─────────────────────────────────────────── */}
      {activeSubTab === "portfolio" && (
        <section className="content-card">
          <div className="section-heading">
            <div>
              <h2>College Joint FDR Portfolio</h2>
              <p>State Machine Status: Pending · In review · Approved · Needs correction · Rejected · Matured · Release in progress · Closed</p>
            </div>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>FDR NUMBER</th>
                  <th>ISSUING BANK (SIMULATED)</th>
                  <th>PRINCIPAL AMOUNT</th>
                  <th>MATURITY &amp; TENURE</th>
                  <th>STATUS</th>
                  <th>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {instruments.length === 0 ? (
                  <tr>
                    <td colSpan="6" style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                      {loading ? "Loading college FDRs..." : "No FDRs registered yet. Click 'Upload New FDR' to submit."}
                    </td>
                  </tr>
                ) : (
                  instruments.map((item) => {
                    const isMatured = item.maturity_date && item.maturity_date <= todayStr;
                    const canRequestRelease = item.status === "ACTIVE" && isMatured;

                    return (
                      <tr key={item.id}>
                        <td className="fdr-number">
                          <strong>{item.reference_no}</strong>
                          <span className="sub-tag">{item.joint_holder || "AICTE Joint"}</span>
                        </td>
                        <td>
                          <div><strong>{item.bank_name}</strong></div>
                          <span className="sub-text">{item.branch || "Branch"} [SIMULATED]</span>
                        </td>
                        <td className="amount">{formatINR(item.amount_paise)}</td>
                        <td>
                          <div>Matures: <strong>{formatDate(item.maturity_date)}</strong></div>
                          <span className="sub-text">{item.tenure_years} Years (from {formatDate(item.issue_date)})</span>
                        </td>
                        <td>{getCollegeStatusBadge(item)}</td>
                        <td>
                          {canRequestRelease ? (
                            <button
                              className="primary-button"
                              style={{ padding: "6px 12px", fontSize: "0.8rem", backgroundColor: "#7c3aed" }}
                              onClick={() => handleRequestRelease(item.id)}
                              disabled={actionLoadingId === item.id}
                            >
                              {actionLoadingId === item.id ? "Submitting..." : "Request Release"}
                            </button>
                          ) : item.status === "BANK_RELEASE_PENDING" ? (
                            releasedCodes[item.id] ? (
                              <div style={{ fontSize: "0.8rem", color: "#059669", display: "flex", alignItems: "center", gap: "6px" }}>
                                <KeyRound size={14} />
                                <span style={{ fontFamily: "monospace", fontWeight: 700 }}>{releasedCodes[item.id].code}</span>
                                <button
                                  className="secondary-button"
                                  style={{ padding: "2px 6px", fontSize: "0.75rem" }}
                                  onClick={() => copyToClipboard(releasedCodes[item.id].code)}
                                  title="Copy claimed code"
                                >
                                  {copiedCode === releasedCodes[item.id].code ? <Check size={12} /> : <Copy size={12} />}
                                </button>
                              </div>
                            ) : item.active_release_ref ? (
                              <button
                                className="primary-button"
                                style={{ padding: "6px 10px", fontSize: "0.75rem", backgroundColor: "#059669" }}
                                onClick={() => handleClaimCode(item.active_release_ref, item.id)}
                                disabled={actionLoadingId === item.id}
                              >
                                <KeyRound size={13} style={{ display: "inline", marginRight: "4px" }} />
                                {actionLoadingId === item.id ? "Claiming..." : "Claim Code"}
                              </button>
                            ) : (
                              <div style={{ fontSize: "0.8rem", color: "#059669" }}>
                                <KeyRound size={14} style={{ display: "inline", marginRight: "4px" }} />
                                Release Authorized
                              </div>
                            )
                          ) : (
                            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>—</span>
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

      {/* ── Sub-Tab 2: Submit Interface with Bank Selector ────────────────────── */}
      {activeSubTab === "upload" && (
        <section className="content-card">
          <div className="section-heading">
            <div>
              <h2>Submit Regulatory FDR Certificate</h2>
              <p>Select your partner bank and enter deposit parameters. Bank check runs automatically upon submission.</p>
            </div>
          </div>

          {submitError && (
            <div className="alert-box error" style={{ marginBottom: "16px" }}>
              <AlertCircle size={16} />
              <span>{submitError}</span>
            </div>
          )}

          <form onSubmit={handleUploadSubmit} className="modal-form">
            <div className="form-grid">
              {/* Bank Selector (Fictional Banks Only) */}
              <div className="form-group">
                <label>Partner Bank [SIMULATED]:</label>
                <select value={uploadForm.bank_id} onChange={handleBankChange} required>
                  {banks.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name} ({b.ifsc_prefix}) [SIMULATED]
                    </option>
                  ))}
                  {banks.length === 0 && (
                    <>
                      <option value="bank-001">Demo Bank A (DEMOA) [SIMULATED]</option>
                      <option value="bank-002">Demo Bank B (DEMOB) [SIMULATED]</option>
                      <option value="bank-003">Demo Bank C (DEMOC) [SIMULATED]</option>
                    </>
                  )}
                </select>
              </div>

              <div className="form-group">
                <label>Branch Office:</label>
                <input
                  type="text"
                  value={uploadForm.branch}
                  onChange={(e) => setUploadForm({ ...uploadForm, branch: e.target.value })}
                  placeholder="e.g. Connaught Place Branch"
                  required
                />
              </div>

              <div className="form-group">
                <label>FDR Number / Reference:</label>
                <input
                  type="text"
                  value={uploadForm.reference_no}
                  onChange={(e) => setUploadForm({ ...uploadForm, reference_no: e.target.value })}
                  placeholder="e.g. DEMOA00269910"
                  required
                />
              </div>

              <div className="form-group">
                <label>Principal Amount (₹ INR):</label>
                <input
                  type="number"
                  value={uploadForm.amount_rupees}
                  onChange={(e) => setUploadForm({ ...uploadForm, amount_rupees: e.target.value })}
                  min="50000"
                  step="1000"
                  required
                />
              </div>

              <div className="form-group">
                <label>Issue Date:</label>
                <input
                  type="date"
                  value={uploadForm.issue_date}
                  onChange={(e) => setUploadForm({ ...uploadForm, issue_date: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label>Maturity Date:</label>
                <input
                  type="date"
                  value={uploadForm.maturity_date}
                  onChange={(e) => setUploadForm({ ...uploadForm, maturity_date: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label>Tenure (Years):</label>
                <input
                  type="number"
                  value={uploadForm.tenure_years}
                  onChange={(e) => setUploadForm({ ...uploadForm, tenure_years: e.target.value })}
                  min="1"
                  max="20"
                  required
                />
              </div>

              <div className="form-group">
                <label>Joint Holder Designation:</label>
                <input
                  type="text"
                  value={uploadForm.joint_holder}
                  onChange={(e) => setUploadForm({ ...uploadForm, joint_holder: e.target.value })}
                  required
                />
              </div>
            </div>

            <div style={{ marginTop: "20px", display: "flex", justifyContent: "flex-end", gap: "12px" }}>
              <button type="button" className="secondary-button" onClick={() => setActiveSubTab("portfolio")}>
                Cancel
              </button>
              <button type="submit" className="primary-button" disabled={submitting}>
                <UploadCloud size={16} /> {submitting ? "Submitting..." : "Submit FDR (Auto-Verify with Bank)"}
              </button>
            </div>
          </form>
        </section>
      )}

      {/* ── Sub-Tab 3: Status & Maturity Alerts ───────────────────────────────── */}
      {activeSubTab === "alerts" && (
        <section className="content-card">
          <div className="section-heading">
            <div>
              <h2>College Compliance &amp; Maturity Notices</h2>
              <p>Maturity notices (180D, 90D, 60D, 30D, 7D, Due Today) and verification notices</p>
            </div>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>ALERT STAGE</th>
                  <th>FDR NUMBER</th>
                  <th>DUE DATE</th>
                  <th>SENT AT</th>
                  <th>CHANNEL</th>
                  <th>STATUS</th>
                </tr>
              </thead>
              <tbody>
                {alerts.length === 0 ? (
                  <tr>
                    <td colSpan="6" style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                      No active alerts or escalation notices for your college.
                    </td>
                  </tr>
                ) : (
                  alerts.map((a) => (
                    <tr key={a.id}>
                      <td>
                        <span className="status-badge amber">
                          <AlertTriangle size={13} /> {a.stage}
                        </span>
                      </td>
                      <td><strong>{a.instrument_id}</strong></td>
                      <td>{formatDate(a.due_at)}</td>
                      <td>{formatDate(a.sent_at)}</td>
                      <td><code>{a.channel}</code></td>
                      <td>
                        {a.acknowledged_at ? (
                          <span className="badge-tag green">Acknowledged</span>
                        ) : (
                          <span className="badge-tag red">Active Notice</span>
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
    </div>
  );
}
