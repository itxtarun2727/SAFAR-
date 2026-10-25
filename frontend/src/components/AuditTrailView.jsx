import { useState, useEffect } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Lock,
  Zap,
  CheckCircle2,
  FileCode,
  Copy,
  Check
} from "lucide-react";
import { api, formatDate } from "../api";

export default function AuditTrailView() {
  const [entries, setEntries] = useState([]);
  const [verification, setVerification] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [copiedHash, setCopiedHash] = useState("");

  const loadAuditData = async () => {
    try {
      setLoading(true);
      const [logs, verify] = await Promise.all([
        api.getAuditEntries(0, 100),
        api.verifyAuditChain(),
      ]);
      setEntries(logs || []);
      setVerification(verify);
    } catch (err) {
      console.error("Failed to load audit ledger:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAuditData();
  }, []);

  const handleSimulateTamper = async () => {
    try {
      setActionLoading(true);
      await api.simulateTamper();
      // Immediately re-verify to show red alert!
      await loadAuditData();
    } catch (err) {
      alert("Tamper simulation failed: " + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRepairChain = async () => {
    try {
      setActionLoading(true);
      await api.repairAuditChain();
      // Re-verify to show green restored status!
      await loadAuditData();
    } catch (err) {
      alert("Chain repair failed: " + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(""), 2000);
  };

  const formatHash = (h) => {
    if (!h) return "00000000...";
    return `${h.substring(0, 8)}...${h.substring(h.length - 8)}`;
  };

  return (
    <div className="view-container">
      <section className="welcome-row">
        <div>
          <p className="eyebrow">MATHEMATICAL TAMPER-EVIDENCE</p>
          <h1>Cryptographic Audit Ledger</h1>
          <p className="subtitle">
            Immutable SHA-256 hash-chained log recording every FDR lifecycle transition, scrutiny note, and bank confirmation.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button className="secondary-button" onClick={loadAuditData} disabled={loading || actionLoading}>
            <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh Ledger
          </button>
        </div>
      </section>

      {/* Verification Status Banner */}
      {verification && (
        <div className={`audit-status-card ${verification.ok ? "intact" : "tampered"}`}>
          <div className="status-main">
            <div className="status-icon">
              {verification.ok ? <ShieldCheck size={28} /> : <AlertTriangle size={28} />}
            </div>
            <div>
              <h3>
                {verification.ok
                  ? "Ledger Integrity 100% Verified"
                  : `Cryptographic Tamper Breach Detected (Block #${verification.first_broken_seq})`}
              </h3>
              <p>
                {verification.ok
                  ? `All ${verification.total_entries} blocks mathematically validated. SHA-256 hash pointers match continuous chain sequence.`
                  : "Database record modification detected! The mathematical hash of row data does not match the block's recorded hash pointer."}
              </p>
            </div>
          </div>

          {/* Evaluator Live Demo Controls */}
          <div className="evaluator-demo-bar">
            <span className="demo-label">Evaluator Live Demonstration:</span>
            <button
              className="tamper-btn"
              onClick={handleSimulateTamper}
              disabled={actionLoading}
              title="Deliberately modify a database row to prove tamper detection"
            >
              <Zap size={14} /> Simulate DB Tampering
            </button>
            <button
              className="repair-btn"
              onClick={handleRepairChain}
              disabled={actionLoading}
              title="Recompute valid cryptographic hashes to restore chain"
            >
              <CheckCircle2 size={14} /> Restore Chain Integrity
            </button>
          </div>
        </div>
      )}

      {/* Ledger Table */}
      <section className="content-card">
        <div className="section-heading">
          <div>
            <h2>Block Hash Chain</h2>
            <p>Chronological sequence of immutable audit entries ({entries.length} total blocks)</p>
          </div>
        </div>

        <div className="table-wrapper">
          <table className="audit-table">
            <thead>
              <tr>
                <th>BLOCK #</th>
                <th>TIMESTAMP</th>
                <th>ACTOR & ROLE</th>
                <th>EVENT / ACTION</th>
                <th>TRANSITION</th>
                <th>PREV BLOCK HASH</th>
                <th>SHA-256 BLOCK HASH</th>
              </tr>
            </thead>
            <tbody>
              {entries.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: "center", padding: "30px" }}>
                    {loading ? "Verifying and loading cryptographic blocks..." : "No audit entries recorded yet."}
                  </td>
                </tr>
              ) : (
                entries.map((block) => (
                  <tr key={block.id} className={!verification?.ok && block.seq === verification?.first_broken_seq ? "tampered-row" : ""}>
                    <td>
                      <span className="seq-badge">#{String(block.seq).padStart(2, "0")}</span>
                    </td>
                    <td>
                      <div>{formatDate(block.timestamp)}</div>
                      <span className="sub-text">
                        {new Date(block.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </td>
                    <td>
                      <strong>{block.actor_id}</strong>
                      <span className="sub-tag">{block.role}</span>
                    </td>
                    <td>
                      <span className="event-pill">{block.event}</span>
                    </td>
                    <td>
                      <div className="transition-flow">
                        <span>{block.from_state || "INIT"}</span>
                        <span className="arrow">➔</span>
                        <strong>{block.to_state || block.event}</strong>
                      </div>
                    </td>
                    <td>
                      <span className="hash-mono" title={block.prev_hash}>
                        {formatHash(block.prev_hash)}
                      </span>
                    </td>
                    <td>
                      <div className="hash-wrap">
                        <span className="hash-mono full" title={block.sha256}>
                          {formatHash(block.sha256)}
                        </span>
                        <button
                          className="copy-btn"
                          onClick={() => copyToClipboard(block.sha256)}
                          title="Copy Full SHA-256 Hash"
                        >
                          {copiedHash === block.sha256 ? <Check size={12} color="#168052" /> : <Copy size={12} />}
                        </button>
                      </div>
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
