import { useState, useEffect } from "react";
import {
  FileText,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowUpRight,
  Search,
  ShieldCheck,
  Landmark,
  Plus,
  RefreshCw,
  AlertCircle
} from "lucide-react";
import { api, formatINR, formatDate } from "../api";

export default function DashboardView({ onSelectTab, onOpenNewModal, onSelectInstrumentForRecon }) {
  const [stats, setStats] = useState(null);
  const [instruments, setInstruments] = useState([]);
  const [auditStatus, setAuditStatus] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(true);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [statsData, instData, auditData] = await Promise.all([
        api.getDashboardStats().catch(() => null),
        api.getInstruments().catch(() => []),
        api.verifyAuditChain().catch(() => null),
      ]);

      setStats(statsData);
      setInstruments(instData || []);
      setAuditStatus(auditData);
    } catch (err) {
      console.error("Dashboard data load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  // Filter instruments by search term
  const filteredInstruments = instruments.filter((item) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      item.reference_no?.toLowerCase().includes(term) ||
      item.bank_name?.toLowerCase().includes(term) ||
      item.status?.toLowerCase().includes(term) ||
      item.joint_holder?.toLowerCase().includes(term)
    );
  });

  const totalCount = instruments.length;
  const activeCount = stats?.active ?? instruments.filter((i) => i.status === "ACTIVE").length;
  const expiringCount = stats?.expiring ?? instruments.filter((i) => i.current_stage === "STAGE_90" || i.status === "MATURED").length;
  const disputedCount = stats?.disputed ?? instruments.filter((i) => i.status === "DISPUTED").length;

  const metrics = [
    { title: "Total Registered FDRs", value: totalCount, note: "Live instruments in registry", icon: FileText, color: "blue" },
    { title: "Active & Verified", value: activeCount, note: "Bank confirmed & lien active", icon: CheckCircle2, color: "green" },
    { title: "Expiring (90-Day Window)", value: expiringCount, note: "Action required for renewal", icon: Clock, color: "amber" },
    { title: "Disputed / Flagged", value: disputedCount, note: "Requires scrutiny action", icon: AlertTriangle, color: "red" },
  ];

  const getStatusBadge = (status) => {
    const s = (status || "").toLowerCase();
    if (s === "active") {
      return <span className="status-badge active"><CheckCircle2 size={13} /> Active</span>;
    }
    if (s === "disputed" || s === "rejected") {
      return <span className="status-badge disputed"><AlertTriangle size={13} /> {status}</span>;
    }
    if (s === "matured" || s === "encashed") {
      return <span className="status-badge amber"><AlertCircle size={13} /> {status}</span>;
    }
    return <span className="status-badge pending"><Clock size={13} /> {status || "Submitted"}</span>;
  };

  return (
    <div className="view-container">
      {/* Welcome Row */}
      <section className="welcome-row">
        <div>
          <p className="eyebrow">FINANCIAL DEPOSIT REPOSITORY · SIH 26265</p>
          <h1>Executive Overview</h1>
          <p className="subtitle">
            Automated monitoring of technical institution joint FDRs, automated bank confirmation, and tamper-proof audit trails.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button className="secondary-button" onClick={loadDashboardData} title="Refresh Live Data">
            <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh
          </button>
          <button className="primary-button" onClick={onOpenNewModal}>
            <Plus size={18} /> Register New FDR
          </button>
        </div>
      </section>

      {/* Alert Notice if items are disputed or expiring */}
      {(disputedCount > 0 || expiringCount > 0) && (
        <div className="alert-banner-top">
          <div className="alert-icon-wrap">
            <AlertTriangle size={18} />
          </div>
          <div className="alert-content">
            <strong>Maturity & Compliance Attention Required</strong>
            <span>
              {disputedCount > 0 ? `${disputedCount} FDR has an active dispute/hold. ` : ""}
              {expiringCount > 0 ? `${expiringCount} FDR is within the 90-day AICTE maturity window. ` : ""}
              Review items to prevent unapproved security deposit encashment.
            </span>
          </div>
          <button className="text-button" onClick={() => onSelectTab("FDR Instruments")}>
            Review Now <ArrowUpRight size={14} />
          </button>
        </div>
      )}

      {/* Metrics Grid */}
      <section className="metrics-grid">
        {metrics.map(({ title, value, note, icon: Icon }) => (
          <article className="metric-card" key={title}>
            <div className="metric-top">
              <span>{title}</span>
              <div className="metric-icon">
                <Icon size={20} />
              </div>
            </div>
            <h2>{value}</h2>
            <p>{note}</p>
          </article>
        ))}
      </section>

      {/* Recent FDR Instruments */}
      <section className="content-card">
        <div className="section-heading">
          <div>
            <h2>Live FDR Registry</h2>
            <p>Active Fixed Deposit Receipts in the PostgreSQL database ({instruments.length} total records)</p>
          </div>
          <button className="secondary-button" onClick={() => onSelectTab("FDR Instruments")}>
            Full Registry <ArrowUpRight size={16} />
          </button>
        </div>

        <div className="search-box">
          <Search size={17} />
          <input
            placeholder="Search by FDR reference, bank, or status..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>FDR REFERENCE</th>
                <th>BANK & BRANCH</th>
                <th>DEPOSIT AMOUNT</th>
                <th>MATURITY DATE</th>
                <th>STATUS</th>
                <th>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {filteredInstruments.length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: "center", padding: "28px" }}>
                    {loading ? "Loading live data from PostgreSQL..." : "No instruments match the search query."}
                  </td>
                </tr>
              ) : (
                filteredInstruments.slice(0, 6).map((item) => (
                  <tr key={item.id}>
                    <td className="fdr-number">
                      <strong>{item.reference_no}</strong>
                      <span className="sub-tag">{item.joint_holder || "AICTE Joint"}</span>
                    </td>
                    <td>
                      <div>{item.bank_name}</div>
                      <span className="sub-text">{item.branch || "Head Office"}</span>
                    </td>
                    <td className="amount">{formatINR(item.amount_paise)}</td>
                    <td>{formatDate(item.maturity_date)}</td>
                    <td>{getStatusBadge(item.status)}</td>
                    <td>
                      <button
                        className="table-action-button"
                        onClick={() => onSelectInstrumentForRecon(item.id)}
                        title="Open Two-Column Bank Verification"
                      >
                        Reconcile <ArrowUpRight size={13} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Bottom Grid: Live Audit Integrity & Bank Reconciliation */}
      <section className="bottom-grid">
        <article className="info-card">
          <div className={`info-icon ${auditStatus?.ok ? "green" : "red"}`}>
            <ShieldCheck size={22} />
          </div>
          <div>
            <h3>SHA-256 Cryptographic Audit Ledger</h3>
            <p>
              Every lifecycle event, transition, and bank confirmation is cryptographically chained with SHA-256 hashes.
            </p>
            {auditStatus?.ok ? (
              <strong className="healthy">
                ● 100% Intact ({auditStatus.total_entries} Blocks Verified)
              </strong>
            ) : (
              <strong className="tampered">
                ⚠️ TAMPER DETECTED at Block #{auditStatus?.first_broken_seq}
              </strong>
            )}
            <div style={{ marginTop: "10px" }}>
              <button className="text-button" onClick={() => onSelectTab("Audit Trail")}>
                View Cryptographic Trail <ArrowUpRight size={15} />
              </button>
            </div>
          </div>
        </article>

        <article className="info-card">
          <div className="info-icon blue">
            <Landmark size={22} />
          </div>
          <div>
            <h3>Two-Column Trust Reconciliation</h3>
            <p>
              Independent verification comparing institution-submitted FDR details with Core Banking records [SIMULATED].
            </p>
            <strong className="healthy">● Direct Bank Adapter Ready</strong>
            <div style={{ marginTop: "10px" }}>
              <button className="text-button" onClick={() => onSelectTab("Bank Verification")}>
                Open Verification Engine <ArrowUpRight size={15} />
              </button>
            </div>
          </div>
        </article>
      </section>
    </div>
  );
}
