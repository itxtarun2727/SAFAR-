import { useState, useEffect } from "react";
import {
  Landmark,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Clock,
  KeyRound,
  RefreshCw,
  Copy,
  Check
} from "lucide-react";
import { api, formatINR, formatDate } from "../api";

export default function BankConsoleView({ currentUser }) {
  const [inbox, setInbox] = useState([]);
  const [loading, setLoading] = useState(true);
  const [releaseRef, setReleaseRef] = useState("");
  const [collegeCode, setCollegeCode] = useState("");
  const [processing, setProcessing] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const fetchInbox = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getBankInbox();
      setInbox(data || []);
    } catch (err) {
      console.error("Failed to load bank inbox:", err);
      setError(err.message || "Failed to fetch pending releases.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInbox();
  }, []);

  const handleSelectRelease = (item) => {
    setReleaseRef(item.release_ref);
    setMessage(null);
    setError(null);
  };

  const handleConfirmRelease = async (e) => {
    e.preventDefault();
    if (!releaseRef.trim()) {
      setError("Please select or enter the Release Reference number.");
      return;
    }
    if (!collegeCode.trim()) {
      setError("Please enter the College Two-Part Authorization Code.");
      return;
    }

    try {
      setProcessing(true);
      setError(null);
      setMessage(null);
      const res = await api.confirmBankRelease(releaseRef.trim(), collegeCode.trim());
      setMessage(res.message || "Deposit release confirmed and AICTE lien discharged successfully [SIMULATED].");
      setCollegeCode("");
      setReleaseRef("");
      await fetchInbox();
    } catch (err) {
      setError(err.message || "Release confirmation failed.");
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="view-container">
      {/* Simulation Banner Notice */}
      <div className="simulated-global-banner">
        <Landmark size={18} />
        <span>
          <strong>[SIMULATED] Bank Integration Gateway:</strong> Bank confirmation and release code verification are simulated in this prototype. Synthetic data only.
        </span>
      </div>

      <section className="welcome-row">
        <div>
          <p className="eyebrow">PARTNER CORE BANKING SYSTEM · RELEASE CONSOLE</p>
          <h1>Bank Release Processing Console [SIMULATED]</h1>
          <p className="subtitle">
            Active Bank Scope: <strong>{currentUser?.bank_id ? `Assigned to ${currentUser.bank_id.toUpperCase()}` : "Partner Bank Desk"}</strong> · Dual-key code verification.
          </p>
        </div>

        <button className="secondary-button" onClick={fetchInbox}>
          <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh Inbox
        </button>
      </section>

      {/* Confirmation Form Card */}
      <section className="content-card" style={{ marginBottom: "24px" }}>
        <div className="section-heading">
          <div>
            <h2>Confirm Regulatory Deposit Release</h2>
            <p>Enter the Release Reference and the Two-Part Authorization Code presented by the technical college.</p>
          </div>
        </div>

        {message && (
          <div className="alert-box success" style={{ marginBottom: "16px" }}>
            <CheckCircle2 size={16} />
            <span>{message}</span>
          </div>
        )}

        {error && (
          <div className="alert-box error" style={{ marginBottom: "16px" }}>
            <AlertTriangle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleConfirmRelease} style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: "16px", alignItems: "end" }}>
          <div>
            <label style={{ display: "block", marginBottom: "6px", fontSize: "0.85rem", fontWeight: 600 }}>
              Release Reference (REL-XXXX):
            </label>
            <input
              type="text"
              className="text-input"
              placeholder="e.g. REL-A1B2C3D4"
              value={releaseRef}
              onChange={(e) => setReleaseRef(e.target.value)}
              required
            />
          </div>

          <div>
            <label style={{ display: "block", marginBottom: "6px", fontSize: "0.85rem", fontWeight: 600 }}>
              College Authorization Code:
            </label>
            <input
              type="text"
              className="text-input"
              placeholder="Enter 24-character token presented by college"
              value={collegeCode}
              onChange={(e) => setCollegeCode(e.target.value)}
              required
            />
          </div>

          <div>
            <button type="submit" className="primary-button" disabled={processing} style={{ height: "42px" }}>
              <KeyRound size={16} /> {processing ? "Verifying..." : "Confirm & Discharge Lien [SIMULATED]"}
            </button>
          </div>
        </form>
      </section>

      {/* Pending Releases Inbox */}
      <section className="content-card">
        <div className="section-heading">
          <div>
            <h2>Pending Releases Awaiting Bank Execution ({inbox.length})</h2>
            <p>Authorizations approved by AICTE Senior Authority awaiting bank code matching.</p>
          </div>
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>RELEASE REF</th>
                <th>FDR NUMBER</th>
                <th>INSTITUTION</th>
                <th>PRINCIPAL AMOUNT</th>
                <th>ISSUED AT</th>
                <th>EXPIRES AT</th>
                <th>STATUS</th>
                <th>ACTION</th>
              </tr>
            </thead>
            <tbody>
              {inbox.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                    {loading ? "Checking bank inbox..." : "No pending releases awaiting confirmation at your bank."}
                  </td>
                </tr>
              ) : (
                inbox.map((item) => (
                  <tr key={item.release_ref}>
                    <td>
                      <code style={{ fontWeight: 700, color: "var(--primary-color)" }}>{item.release_ref}</code>
                    </td>
                    <td><strong>{item.reference_no}</strong></td>
                    <td>{item.institution_name}</td>
                    <td><strong>{formatINR(item.amount_paise)}</strong></td>
                    <td>{formatDate(item.issued_at)}</td>
                    <td>
                      <span style={{ color: "#d97706", fontSize: "0.85rem" }}>
                        <Clock size={12} style={{ display: "inline", marginRight: "4px" }} />
                        {formatDate(item.expires_at)}
                      </span>
                    </td>
                    <td>
                      <span className="status-badge amber">
                        <Clock size={12} /> {item.status}
                      </span>
                    </td>
                    <td>
                      <button
                        className="secondary-button"
                        style={{ padding: "5px 10px", fontSize: "0.8rem" }}
                        onClick={() => handleSelectRelease(item)}
                      >
                        Select for Release
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
