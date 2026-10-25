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
  X
} from "lucide-react";
import { api, formatINR, formatDate } from "../api";

export default function InstrumentsView({ currentUser, onOpenNewModal, onSelectInstrumentForRecon }) {
  const [instruments, setInstruments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchInstruments = async () => {
    try {
      setLoading(true);
      const data = await api.getInstruments();
      setInstruments(data || []);
    } catch (err) {
      console.error("Failed to fetch instruments:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInstruments();
  }, []);

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
      item.branch?.toLowerCase().includes(term)
    );
  });

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
      <section className="welcome-row">
        <div>
          <p className="eyebrow">
            {currentUser?.role === "institution" ? "INSTITUTIONAL ASSET PORTFOLIO" : "REGULATORY ASSET INVENTORY"}
          </p>
          <h1>
            {currentUser?.role === "institution" ? "My College Registered FDRs" : "FDR Instruments Registry"}
          </h1>
          <p className="subtitle">
            {currentUser?.role === "institution"
              ? "Displaying Fixed Deposit Receipts registered by Greenfield Institute of Technology (inst-001) under AICTE jurisdiction."
              : "Comprehensive registry of technical institution Fixed Deposit Receipts, joint accounts, and lien status."}
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <button className="secondary-button" onClick={fetchInstruments} title="Refresh Table">
            <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh
          </button>
          {currentUser?.role === "auditor" ? (
            <span className="badge-tag gray" style={{ padding: "8px 12px", fontSize: "11px" }}>
              🔒 Read-Only Compliance Auditor
            </span>
          ) : (
            <button className="primary-button" onClick={onOpenNewModal}>
              <Plus size={18} /> Register New FDR
            </button>
          )}
        </div>
      </section>

      {/* Filter and Search Bar */}
      <div className="filter-bar">
        <div className="search-box" style={{ marginBottom: 0 }}>
          <Search size={17} />
          <input
            placeholder="Search by FDR reference, bank, joint holder..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filter-tabs">
          {["ALL", "ACTIVE", "SUBMITTED", "DISPUTED", "MATURED"].map((st) => (
            <button
              key={st}
              className={`filter-pill ${statusFilter === st ? "active" : ""}`}
              onClick={() => setStatusFilter(st)}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Table Card */}
      <section className="content-card">
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>FDR REFERENCE</th>
                <th>BANK & BRANCH</th>
                <th>PRINCIPAL AMOUNT</th>
                <th>INTEREST & TENURE</th>
                <th>MATURITY DATE</th>
                <th>LIEN STATUS</th>
                <th>STATUS</th>
                <th>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: "center", padding: "30px" }}>
                    {loading ? "Loading FDR instruments..." : "No instruments found matching criteria."}
                  </td>
                </tr>
              ) : (
                filtered.map((item) => (
                  <tr key={item.id}>
                    <td className="fdr-number">
                      <strong>{item.reference_no}</strong>
                      <span className="sub-tag">{item.id}</span>
                    </td>
                    <td>
                      <div>{item.bank_name}</div>
                      <span className="sub-text">{item.branch || "General Branch"}</span>
                    </td>
                    <td className="amount">{formatINR(item.amount_paise)}</td>
                    <td>
                      <div>{item.interest_rate || "N/A"}</div>
                      <span className="sub-text">{item.tenure_years} Years</span>
                    </td>
                    <td>
                      <div>{formatDate(item.maturity_date)}</div>
                      <span className="sub-text">Issued: {formatDate(item.issue_date)}</span>
                    </td>
                    <td>
                      {item.lien_marked ? (
                        <span className="badge-tag green">Lien Marked</span>
                      ) : (
                        <span className="badge-tag gray">No Lien</span>
                      )}
                    </td>
                    <td>{getStatusBadge(item.status)}</td>
                    <td>
                      <div style={{ display: "flex", gap: "6px" }}>
                        <button
                          className="table-action-button"
                          onClick={() => onSelectInstrumentForRecon(item.id)}
                          title="Open Two-Column Bank Verification"
                        >
                          Reconcile
                        </button>
                        <button
                          className="table-action-button secondary"
                          onClick={() => openDetails(item.id)}
                          title="View Complete FDR Metadata"
                        >
                          Details
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

      {/* Details Modal */}
      {selectedDetail && (
        <div className="modal-backdrop" onClick={() => setSelectedDetail(null)}>
          <div className="modal-container large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <div className="brand-icon" style={{ width: 34, height: 34 }}>
                  <FileText size={19} />
                </div>
                <div>
                  <h3>FDR Record Details — {selectedDetail.reference_no}</h3>
                  <p>Institution: {selectedDetail.institution?.name || selectedDetail.institution_id}</p>
                </div>
              </div>
              <button className="icon-button" onClick={() => setSelectedDetail(null)}>
                <X size={18} />
              </button>
            </div>

            <div className="details-body">
              <div className="details-grid">
                <div className="detail-item">
                  <span className="detail-label">Bank Name</span>
                  <strong className="detail-value">{selectedDetail.bank_name}</strong>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Branch</span>
                  <strong className="detail-value">{selectedDetail.branch || "N/A"}</strong>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Principal Deposit</span>
                  <strong className="detail-value amount">{formatINR(selectedDetail.amount_paise)}</strong>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Interest Rate</span>
                  <strong className="detail-value">{selectedDetail.interest_rate || "N/A"}</strong>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Issue Date</span>
                  <strong className="detail-value">{formatDate(selectedDetail.issue_date)}</strong>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Maturity Date</span>
                  <strong className="detail-value">{formatDate(selectedDetail.maturity_date)}</strong>
                </div>
                <div className="detail-item full-width">
                  <span className="detail-label">Joint Name on FDR</span>
                  <strong className="detail-value">{selectedDetail.joint_holder || "AICTE & Technical Society"}</strong>
                </div>
                <div className="detail-item">
                  <span className="detail-label">FSM Status</span>
                  <div>{getStatusBadge(selectedDetail.status)}</div>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Lifecycle Stage</span>
                  <strong className="detail-value">{selectedDetail.current_stage || "NORMAL"}</strong>
                </div>
              </div>

              {/* Scrutiny Notes & Disputes */}
              {selectedDetail.disputes && selectedDetail.disputes.length > 0 && (
                <div className="section-block">
                  <h4>Active Regulatory Holds / Disputes</h4>
                  {selectedDetail.disputes.map((disp) => (
                    <div key={disp.id} className="dispute-box">
                      <AlertTriangle size={16} />
                      <div>
                        <strong>{disp.reason}</strong>
                        <span>Opened by: {disp.opened_by} on {formatDate(disp.opened_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Quick Navigation to Reconciliation */}
              <div className="modal-actions" style={{ marginTop: "24px" }}>
                <button
                  className="secondary-button"
                  onClick={() => setSelectedDetail(null)}
                >
                  Close
                </button>
                <button
                  className="primary-button"
                  onClick={() => {
                    const id = selectedDetail.id;
                    setSelectedDetail(null);
                    onSelectInstrumentForRecon(id);
                  }}
                >
                  Reconcile with Bank <ArrowUpRight size={15} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
