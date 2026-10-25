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
  FileCheck
} from "lucide-react";
import { api, formatINR, formatDate } from "../api";

export default function CollegePortalView({ currentUser, onOpenNewModal }) {
  const [activeSubTab, setActiveSubTab] = useState("portfolio"); // "portfolio" | "upload" | "alerts"
  const [instruments, setInstruments] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  // Direct Quick Upload Form State
  const [uploadForm, setUploadForm] = useState({
    bank_name: "State Bank of India",
    branch: "Connaught Place, New Delhi",
    reference_no: "",
    amount_rupees: "2500000",
    interest_rate: "7.25%",
    issue_date: new Date().toISOString().split("T")[0],
    maturity_date: new Date(new Date().setFullYear(new Date().getFullYear() + 10)).toISOString().split("T")[0],
    tenure_years: 10,
    joint_holder: "AICTE & Greenfield Institute of Technology",
    lien_marked: true,
    file_name: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState("");
  const [submitError, setSubmitError] = useState("");

  const loadCollegeData = async () => {
    try {
      setLoading(true);
      const [instData, alertData] = await Promise.all([
        api.getInstruments().catch(() => []),
        api.getAlerts().catch(() => []),
      ]);
      setInstruments(instData || []);
      setAlerts(alertData || []);
    } catch (err) {
      console.error("Failed to load college data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCollegeData();
  }, []);

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
        institution_id: currentUser?.institution_ids?.[0] || "inst-001",
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

      await api.createInstrument(payload);
      setSubmitSuccess(`FDR Certificate ${uploadForm.reference_no} uploaded successfully! Status: SUBMITTED (Dispatched to AICTE scrutiny desk).`);
      setUploadForm((prev) => ({
        ...prev,
        reference_no: "",
        amount_rupees: "2500000",
        file_name: "",
      }));
      // Refresh portfolio
      await loadCollegeData();
      setActiveSubTab("portfolio");
    } catch (err) {
      setSubmitError(err.message || "Failed to submit FDR certificate.");
    } finally {
      setSubmitting(false);
    }
  };

  const activeFDRs = instruments.filter((i) => i.status === "ACTIVE");
  const pendingFDRs = instruments.filter((i) => i.status === "SUBMITTED" || i.status === "BANK_CHECK");
  const rejectedFDRs = instruments.filter((i) => i.status === "REJECTED" || i.status === "DISPUTED");
  const expiringFDRs = instruments.filter((i) => i.current_stage === "STAGE_90" || i.status === "MATURED");

  const getStatusBadge = (status) => {
    const s = (status || "").toLowerCase();
    if (s === "active") {
      return <span className="status-badge active"><CheckCircle2 size={13} /> Approved & Active</span>;
    }
    if (s === "disputed" || s === "rejected") {
      return <span className="status-badge disputed"><AlertTriangle size={13} /> {status === "rejected" ? "Bank Rejected" : "Dispute Hold"}</span>;
    }
    if (s === "matured") {
      return <span className="status-badge amber"><AlertCircle size={13} /> Matured</span>;
    }
    return <span className="status-badge pending"><Clock size={13} /> Under Verification</span>;
  };

  return (
    <div className="view-container">
      {/* College Header */}
      <section className="welcome-row">
        <div>
          <p className="eyebrow">INSTITUTION PORTAL · GREENFIELD INSTITUTE OF TECHNOLOGY</p>
          <h1>College FDR Management &amp; Upload System</h1>
          <p className="subtitle">
            AICTE ID: 1-10992837 · Exclusively isolated to your college deposits. Other colleges cannot view your records.
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
          <p>Total college joint deposits</p>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>Approved &amp; Active</span>
            <div className="metric-icon"><CheckCircle2 size={20} /></div>
          </div>
          <h2>{activeFDRs.length}</h2>
          <p>Lien verified by issuing bank</p>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>Under Verification</span>
            <div className="metric-icon"><Clock size={20} /></div>
          </div>
          <h2>{pendingFDRs.length}</h2>
          <p>Awaiting bank confirmation</p>
        </article>

        <article className="metric-card">
          <div className="metric-top">
            <span>Action Required</span>
            <div className="metric-icon"><AlertTriangle size={20} /></div>
          </div>
          <h2>{rejectedFDRs.length + expiringFDRs.length}</h2>
          <p>Maturity renewal or dispute hold</p>
        </article>
      </section>

      {/* College Sub-Tabs Navigation */}
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
            🔔 Approval &amp; Maturity Alerts ({alerts.length + rejectedFDRs.length + expiringFDRs.length})
          </button>
        </div>

        <button className="secondary-button" onClick={loadCollegeData} title="Refresh Live Data">
          <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh
        </button>
      </div>

      {submitSuccess && (
        <div className="alert-box success">
          <CheckCircle2 size={16} />
          <span>{submitSuccess}</span>
        </div>
      )}

      {/* ── Sub-Tab 1: My Registered FDRs Portfolio ─────────────────────────── */}
      {activeSubTab === "portfolio" && (
        <section className="content-card">
          <div className="section-heading">
            <div>
              <h2>College Joint FDR Portfolio</h2>
              <p>Strictly scoped to Greenfield Institute of Technology (inst-001)</p>
            </div>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>FDR CERTIFICATE NO</th>
                  <th>ISSUING BANK &amp; BRANCH</th>
                  <th>PRINCIPAL AMOUNT</th>
                  <th>TENURE &amp; MATURITY</th>
                  <th>AICTE LIEN CLAUSE</th>
                  <th>APPROVAL STATUS</th>
                </tr>
              </thead>
              <tbody>
                {instruments.length === 0 ? (
                  <tr>
                    <td colSpan="6" style={{ textAlign: "center", padding: "30px" }}>
                      {loading ? "Loading college FDRs..." : "No FDRs registered yet. Click 'Upload New FDR' above."}
                    </td>
                  </tr>
                ) : (
                  instruments.map((item) => (
                    <tr key={item.id}>
                      <td className="fdr-number">
                        <strong>{item.reference_no}</strong>
                        <span className="sub-tag">{item.joint_holder || "AICTE Joint"}</span>
                      </td>
                      <td>
                        <div>{item.bank_name}</div>
                        <span className="sub-text">{item.branch || "Branch Office"}</span>
                      </td>
                      <td className="amount">{formatINR(item.amount_paise)}</td>
                      <td>
                        <div>Matures: {formatDate(item.maturity_date)}</div>
                        <span className="sub-text">{item.tenure_years} Years (from {formatDate(item.issue_date)})</span>
                      </td>
                      <td>
                        {item.lien_marked ? (
                          <span className="badge-tag green">Lien Marked to AICTE</span>
                        ) : (
                          <span className="badge-tag gray">Pending Endorsement</span>
                        )}
                      </td>
                      <td>{getStatusBadge(item.status)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ── Sub-Tab 2: Direct Upload Interface ──────────────────────────────── */}
      {activeSubTab === "upload" && (
        <section className="content-card">
          <div className="section-heading">
            <div>
              <h2>Upload Fixed Deposit Receipt (FDR) Certificate</h2>
              <p>Mandatory joint deposit with AICTE under Approval Process Handbook regulations</p>
            </div>
          </div>

          {submitError && (
            <div className="alert-box error">
              <AlertCircle size={16} />
              <span>{submitError}</span>
            </div>
          )}

          <form onSubmit={handleUploadSubmit} className="modal-form" style={{ marginTop: "10px" }}>
            {/* File Drag and Drop Mock Area */}
            <div className="upload-dropzone">
              <UploadCloud size={36} color="#168052" />
              <div>
                <strong>Drag and drop FDR Certificate scan or receipt (PDF, JPG, PNG)</strong>
                <p>Authorized format: Maximum file size 10MB. Must include issuing bank seal.</p>
              </div>
              <input
                type="file"
                id="fdr-file-input"
                style={{ display: "none" }}
                onChange={(e) => {
                  if (e.target.files?.[0]) {
                    setUploadForm((p) => ({ ...p, file_name: e.target.files[0].name }));
                  }
                }}
              />
              <button
                type="button"
                className="secondary-button"
                onClick={() => document.getElementById("fdr-file-input")?.click()}
              >
                {uploadForm.file_name ? `Selected: ${uploadForm.file_name}` : "Browse Computer Files"}
              </button>
            </div>

            <div className="form-grid" style={{ marginTop: "20px" }}>
              <div className="form-group">
                <label>Issuing Bank Name</label>
                <select
                  value={uploadForm.bank_name}
                  onChange={(e) => setUploadForm({ ...uploadForm, bank_name: e.target.value })}
                >
                  <option>State Bank of India</option>
                  <option>Punjab National Bank</option>
                  <option>HDFC Bank</option>
                  <option>ICICI Bank</option>
                  <option>Bank of Baroda</option>
                  <option>Canara Bank</option>
                  <option>Union Bank of India</option>
                </select>
              </div>

              <div className="form-group">
                <label>Bank Branch</label>
                <input
                  type="text"
                  value={uploadForm.branch}
                  onChange={(e) => setUploadForm({ ...uploadForm, branch: e.target.value })}
                  placeholder="e.g. Connaught Place, New Delhi"
                  required
                />
              </div>

              <div className="form-group">
                <label>FDR Certificate / Account Number</label>
                <input
                  type="text"
                  value={uploadForm.reference_no}
                  onChange={(e) => setUploadForm({ ...uploadForm, reference_no: e.target.value })}
                  placeholder="e.g. SBIN00889911"
                  required
                />
              </div>

              <div className="form-group">
                <label>Principal Deposit Amount (₹ INR)</label>
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
                <label>Interest Rate (p.a.)</label>
                <input
                  type="text"
                  value={uploadForm.interest_rate}
                  onChange={(e) => setUploadForm({ ...uploadForm, interest_rate: e.target.value })}
                  placeholder="e.g. 7.25%"
                />
              </div>

              <div className="form-group">
                <label>Tenure (Years)</label>
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
                <label>Deposit / Issue Date</label>
                <input
                  type="date"
                  value={uploadForm.issue_date}
                  onChange={(e) => setUploadForm({ ...uploadForm, issue_date: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label>Maturity Date</label>
                <input
                  type="date"
                  value={uploadForm.maturity_date}
                  onChange={(e) => setUploadForm({ ...uploadForm, maturity_date: e.target.value })}
                  required
                />
              </div>

              <div className="form-group full-width">
                <label>Joint Name Formulation on Certificate</label>
                <input
                  type="text"
                  value={uploadForm.joint_holder}
                  onChange={(e) => setUploadForm({ ...uploadForm, joint_holder: e.target.value })}
                  required
                />
              </div>

              <div className="form-group checkbox full-width">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={uploadForm.lien_marked}
                    onChange={(e) => setUploadForm({ ...uploadForm, lien_marked: e.target.checked })}
                  />
                  <span>
                    <strong>Irrevocable Lien Pledge:</strong> The college confirms this deposit is pledged in favor of AICTE and cannot be liquidated or pledged for credit without explicit AICTE clearance.
                  </span>
                </label>
              </div>
            </div>

            <div className="modal-actions" style={{ marginTop: "24px" }}>
              <button
                type="button"
                className="secondary-button"
                onClick={() => setActiveSubTab("portfolio")}
              >
                Cancel
              </button>
              <button type="submit" className="primary-button" disabled={submitting}>
                {submitting ? "Uploading & Registering..." : "Submit FDR to AICTE"}
              </button>
            </div>
          </form>
        </section>
      )}

      {/* ── Sub-Tab 3: Approval & Maturity Alerts ───────────────────────────── */}
      {activeSubTab === "alerts" && (
        <section className="content-card">
          <div className="section-heading">
            <div>
              <h2>College Compliance Notices &amp; Status Alerts</h2>
              <p>Direct notifications on FDR approvals, rejections, and upcoming maturity deadlines</p>
            </div>
          </div>

          <div className="college-alerts-list">
            {/* Notice 1: Active Approved FDRs */}
            {activeFDRs.map((inst) => (
              <div key={`appr-${inst.id}`} className="alert-card-item success">
                <div className="alert-card-icon"><CheckCircle2 size={20} /></div>
                <div className="alert-card-info">
                  <strong>FDR {inst.reference_no} Verified &amp; Approved by Bank</strong>
                  <p>
                    {inst.bank_name} confirmed the joint deposit of {formatINR(inst.amount_paise)} with active AICTE lien.
                  </p>
                  <span className="alert-meta">Maturity Date: {formatDate(inst.maturity_date)} · Status: ACTIVE</span>
                </div>
              </div>
            ))}

            {/* Notice 2: Expiring or Matured FDRs */}
            {expiringFDRs.map((inst) => (
              <div key={`exp-${inst.id}`} className="alert-card-item warning">
                <div className="alert-card-icon"><Clock size={20} /></div>
                <div className="alert-card-info">
                  <strong>Maturity Notice: FDR {inst.reference_no} Nearing 10-Year Expiry</strong>
                  <p>
                    Deposit reaches maturity on {formatDate(inst.maturity_date)}. Please submit the renewal receipt before 30 days to avoid compliance flags.
                  </p>
                  <span className="alert-meta">AICTE Regulation: Approval Process Handbook Section 4.2</span>
                </div>
              </div>
            ))}

            {/* Notice 3: Rejected / Disputed FDRs */}
            {rejectedFDRs.map((inst) => (
              <div key={`rej-${inst.id}`} className="alert-card-item danger">
                <div className="alert-card-icon"><AlertTriangle size={20} /></div>
                <div className="alert-card-info">
                  <strong>Action Required: Bank Mismatch or Dispute on FDR {inst.reference_no}</strong>
                  <p>
                    Bank verification or AICTE scrutiny flagged a discrepancy. Please re-check the maturity date and principal details.
                  </p>
                  <span className="alert-meta">Status: {inst.status}</span>
                </div>
              </div>
            ))}

            {/* In-app scheduled alerts */}
            {alerts.map((al) => (
              <div key={al.id} className="alert-card-item info">
                <div className="alert-card-icon"><Calendar size={20} /></div>
                <div className="alert-card-info">
                  <strong>Regulatory Notification: Stage {al.stage}</strong>
                  <p>Automatic compliance notice generated for FDR reference ID {al.instrument_id}.</p>
                  <span className="alert-meta">Sent on: {formatDate(al.sent_at)}</span>
                </div>
              </div>
            ))}

            {activeFDRs.length === 0 && expiringFDRs.length === 0 && rejectedFDRs.length === 0 && alerts.length === 0 && (
              <p style={{ textAlign: "center", padding: "30px", color: "#64748b" }}>
                No active notices or warnings for Greenfield Institute of Technology.
              </p>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
