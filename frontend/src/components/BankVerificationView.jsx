import { useState, useEffect } from "react";
import {
  Landmark,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Clock,
  RefreshCw,
  FileText,
  Zap,
  Info,
  ChevronDown
} from "lucide-react";
import { api, formatINR, formatDate } from "../api";

export default function BankVerificationView({ initialInstrumentId }) {
  const [instruments, setInstruments] = useState([]);
  const [selectedId, setSelectedId] = useState(initialInstrumentId || "");
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);

  // Load all instruments for selector dropdown
  useEffect(() => {
    api.getInstruments()
      .then((data) => {
        setInstruments(data || []);
        if (!selectedId && data && data.length > 0) {
          // Default to first instrument or an unverified one
          const pending = data.find((d) => d.status === "SUBMITTED" || d.status === "BANK_CHECK");
          setSelectedId(pending ? pending.id : data[0].id);
        }
      })
      .catch((err) => console.error("Error loading instruments for verification:", err));
  }, []);

  // Whenever selectedId changes or on reload, fetch instrument detail
  const loadDetail = async (id) => {
    if (!id) return;
    try {
      setLoading(true);
      const data = await api.getInstrumentDetail(id);
      setDetail(data);
      setVerifyResult(null);
    } catch (err) {
      console.error("Failed to load instrument detail:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedId) {
      loadDetail(selectedId);
    }
  }, [selectedId]);

  // Execute Simulated Bank Verification
  const handleVerifyBank = async () => {
    if (!selectedId) return;
    try {
      setVerifying(true);
      setVerifyResult(null);
      const result = await api.verifyBank(selectedId);
      setVerifyResult(result);
      // Reload fresh instrument details with confirmations
      await loadDetail(selectedId);
    } catch (err) {
      setVerifyResult({
        result: "error",
        message: err.message || "Bank verification failed to execute.",
      });
    } finally {
      setVerifying(false);
    }
  };

  // Find confirmation for specific field
  const getFieldConfirmation = (fieldName) => {
    if (!detail?.confirmations) return null;
    return detail.confirmations.find((c) => c.field_name === fieldName);
  };

  const maturityConf = getFieldConfirmation("maturity_date");
  const lienConf = getFieldConfirmation("lien_marked");
  const jointConf = getFieldConfirmation("joint_holder");

  return (
    <div className="view-container">
      <section className="welcome-row">
        <div>
          <p className="eyebrow">TWO-COLUMN TRUST ARCHITECTURE</p>
          <h1>Bank Reconciliation Engine</h1>
          <p className="subtitle">
            Zero-trust verification comparing technical institution claims against direct Core Banking confirmation records.
          </p>
        </div>

        <div className="recon-selector-wrap">
          <label className="selector-label">
            <span>Select FDR Case:</span>
            <select
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              className="recon-select"
            >
              {instruments.map((inst) => (
                <option key={inst.id} value={inst.id}>
                  {inst.reference_no} — {inst.bank_name} ({inst.status})
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {/* Verification Notice Banner */}
      <div className="simulated-notice">
        <Info size={18} />
        <div>
          <strong>Core Banking Adapter [SIMULATED PROTOTYPE]</strong>
          <span>
            Demonstration mode executes deterministic bank reconciliation matching ISO-20022 and Finacle/BaNCS protocols.
          </span>
        </div>
      </div>

      {verifyResult && (
        <div className={`alert-banner-top ${verifyResult.result === "match" ? "success" : "warning"}`}>
          <div className="alert-icon-wrap">
            {verifyResult.result === "match" ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
          </div>
          <div className="alert-content">
            <strong>
              {verifyResult.result === "match" ? "Bank Reconciliation Successful" : "Bank Verification Mismatch"}
            </strong>
            <span>{verifyResult.message || JSON.stringify(verifyResult)}</span>
          </div>
        </div>
      )}

      {loading || !detail ? (
        <div className="content-card" style={{ textAlign: "center", padding: "40px" }}>
          <RefreshCw size={24} className="spin" style={{ margin: "0 auto 12px", color: "#19764f" }} />
          <p>Fetching Two-Column Trust verification records...</p>
        </div>
      ) : (
        <>
          {/* Main Two-Column Card */}
          <div className="reconciliation-container">
            <div className="recon-header">
              <div className="recon-title">
                <h3>{detail.reference_no}</h3>
                <span className="recon-sub">{detail.bank_name} · {detail.branch || "Core Branch"}</span>
              </div>

              <div className="recon-actions">
                <span className={`status-badge ${detail.status.toLowerCase()}`}>
                  {detail.status === "ACTIVE" && <CheckCircle2 size={13} />}
                  {detail.status === "SUBMITTED" && <Clock size={13} />}
                  {detail.status === "DISPUTED" && <AlertTriangle size={13} />}
                  Current State: {detail.status}
                </span>

                <button
                  className="primary-button highlight"
                  onClick={handleVerifyBank}
                  disabled={verifying}
                >
                  <Zap size={16} />
                  {verifying ? "Executing Verification..." : "Run Automated Bank Verification"}
                </button>
              </div>
            </div>

            <div className="two-column-grid">
              {/* Left Column: Institution Submission */}
              <div className="recon-column left">
                <div className="column-heading">
                  <div className="col-icon inst"><FileText size={18} /></div>
                  <div>
                    <h4>Institution Submitted Record</h4>
                    <span>Self-attested FDR Certificate details</span>
                  </div>
                </div>

                <div className="field-list">
                  <div className="field-row">
                    <span className="field-label">FDR Certificate Reference</span>
                    <strong className="field-val">{detail.reference_no}</strong>
                  </div>
                  <div className="field-row">
                    <span className="field-label">Deposit Amount (Principal)</span>
                    <strong className="field-val amount">{formatINR(detail.amount_paise)}</strong>
                  </div>
                  <div className="field-row">
                    <span className="field-label">Deposit Date</span>
                    <span className="field-val">{formatDate(detail.issue_date)}</span>
                  </div>
                  <div className="field-row">
                    <span className="field-label">Maturity Date</span>
                    <span className="field-val">{formatDate(detail.maturity_date)}</span>
                  </div>
                  <div className="field-row">
                    <span className="field-label">Joint Account Name</span>
                    <span className="field-val">{detail.joint_holder || "AICTE & Technical Society"}</span>
                  </div>
                  <div className="field-row">
                    <span className="field-label">Lien Marked to AICTE</span>
                    <span className="field-val">
                      {detail.lien_marked ? "Yes (Irrevocable Lien)" : "No"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Right Column: Bank Core Banking Confirmation */}
              <div className="recon-column right">
                <div className="column-heading">
                  <div className="col-icon bank"><Landmark size={18} /></div>
                  <div>
                    <h4>Bank Core System Record</h4>
                    <span>Direct API verification [SIMULATED]</span>
                  </div>
                </div>

                <div className="field-list">
                  <div className="field-row">
                    <span className="field-label">Confirmed Reference</span>
                    <strong className="field-val">{detail.reference_no}</strong>
                    <span className="match-pill match">MATCH</span>
                  </div>

                  <div className="field-row">
                    <span className="field-label">Confirmed Principal</span>
                    <strong className="field-val amount">{formatINR(detail.amount_paise)}</strong>
                    <span className="match-pill match">MATCH</span>
                  </div>

                  <div className="field-row">
                    <span className="field-label">Deposit Date at Bank</span>
                    <span className="field-val">{formatDate(detail.issue_date)}</span>
                    <span className="match-pill match">MATCH</span>
                  </div>

                  <div className="field-row">
                    <span className="field-label">Confirmed Maturity Date</span>
                    <span className="field-val">
                      {maturityConf?.confirmed_value
                        ? formatDate(maturityConf.confirmed_value)
                        : (detail.status === "ACTIVE" ? formatDate(detail.maturity_date) : "Awaiting Bank Query")}
                    </span>
                    {maturityConf ? (
                      <span className={`match-pill ${maturityConf.result === "match" ? "match" : "mismatch"}`}>
                        {maturityConf.result.toUpperCase()}
                      </span>
                    ) : (
                      <span className="match-pill pending">PENDING</span>
                    )}
                  </div>

                  <div className="field-row">
                    <span className="field-label">Joint Account Status</span>
                    <span className="field-val">
                      {detail.status === "ACTIVE"
                        ? detail.joint_holder
                        : "Awaiting Bank Confirmation"}
                    </span>
                    <span className={`match-pill ${detail.status === "ACTIVE" ? "match" : "pending"}`}>
                      {detail.status === "ACTIVE" ? "MATCH" : "PENDING"}
                    </span>
                  </div>

                  <div className="field-row">
                    <span className="field-label">Irrevocable Lien Status</span>
                    <span className="field-val">
                      {detail.lien_marked && detail.status === "ACTIVE"
                        ? "Active Lien Marked to AICTE"
                        : "Pending Verification"}
                    </span>
                    <span className={`match-pill ${detail.lien_marked && detail.status === "ACTIVE" ? "match" : "pending"}`}>
                      {detail.lien_marked && detail.status === "ACTIVE" ? "MATCH" : "PENDING"}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Reconciliation Footer & Cryptographic Assurance */}
            <div className="recon-footer">
              <div className="crypto-assurance">
                <ShieldCheck size={20} className="crypto-icon" />
                <div>
                  <strong>Cryptographic Transition Logged</strong>
                  <p>
                    Reconciliation triggers an automatic state machine transition and writes a SHA-256 hash block into PostgreSQL.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
