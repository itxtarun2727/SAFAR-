import { useState } from "react";
import {
ShieldCheck,
LayoutDashboard,
FileText,
Landmark,
ClipboardCheck,
Settings,
Search,
Bell,
ChevronDown,
ArrowUpRight,
Clock,
CheckCircle2,
AlertTriangle,
Plus,
} from "lucide-react";
import "./App.css";

function App() {
const [activeTab, setActiveTab] = useState("Dashboard");
const [role, setRole] = useState("Admin");

const metrics = [
{ title: "Total FDRs", value: "248", note: "All registered instruments", icon: FileText },
{ title: "Active FDRs", value: "186", note: "Currently active", icon: CheckCircle2 },
{ title: "Pending Verification", value: "24", note: "Awaiting bank confirmation", icon: Clock },
{ title: "Disputed Records", value: "08", note: "Require attention", icon: AlertTriangle },
];

const instruments = [
{ id: "FDR-2026-001", bank: "State Bank of India", amount: "₹25,00,000", maturity: "15 Nov 2026", status: "Active" },
{ id: "FDR-2026-002", bank: "Punjab National Bank", amount: "₹18,50,000", maturity: "22 Nov 2026", status: "Pending" },
{ id: "FDR-2026-003", bank: "HDFC Bank", amount: "₹32,00,000", maturity: "30 Nov 2026", status: "Disputed" },
{ id: "FDR-2026-004", bank: "Bank of Baroda", amount: "₹12,75,000", maturity: "05 Dec 2026", status: "Active" },
];

const navigation = [
{ name: "Dashboard", icon: LayoutDashboard },
{ name: "FDR Instruments", icon: FileText },
{ name: "Bank Verification", icon: Landmark },
{ name: "Audit Trail", icon: ClipboardCheck },
{ name: "Settings", icon: Settings },
];

return (
<div className="app-shell">
<aside className="sidebar">
<div className="brand">
<div className="brand-icon"><ShieldCheck size={26} /></div>
<div>
<h2>SAFAR</h2>
<span>AICTE FDR PORTAL</span>
</div>
</div>

    <div className="nav-label">WORKSPACE</div>

    <nav>
      {navigation.map(({ name, icon: Icon }) => (
        <button
          key={name}
          className={`nav-item ${activeTab === name ? "selected" : ""}`}
          onClick={() => setActiveTab(name)}
        >
          <Icon size={19} />
          <span>{name}</span>
        </button>
      ))}
    </nav>

    <div className="sidebar-bottom">
      <div className="secure-badge">
        <ShieldCheck size={19} />
        <div>
          <strong>Secure Environment</strong>
          <span>Audit integrity enabled</span>
        </div>
      </div>
      <p>SIH 26265 · AICTE</p>
    </div>
  </aside>

  <main className="main-area">
    <header className="topbar">
      <div>
        <span className="breadcrumb">Workspace / </span>
        <strong>{activeTab}</strong>
      </div>

      <div className="topbar-actions">
        <span className="live-indicator"><span /> Demo Environment</span>
        <button className="icon-button" aria-label="Notifications"><Bell size={19} /></button>
        <label className="role-select">
          <span>Role</span>
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            <option>Admin</option>
            <option>Institution</option>
            <option>Bank Officer</option>
            <option>Auditor</option>
          </select>
          <ChevronDown size={14} />
        </label>
      </div>
    </header>

    <div className="page-content">
      <section className="welcome-row">
        <div>
          <p className="eyebrow">FINANCIAL DEPOSIT MANAGEMENT</p>
          <h1>{activeTab === "Dashboard" ? "Executive Overview" : activeTab}</h1>
          <p className="subtitle">
            Monitor fixed deposit receipts, bank verification, and audit integrity.
          </p>
        </div>

        <button className="primary-button" onClick={() => setActiveTab("FDR Instruments")}>
          <Plus size={18} /> Register New FDR
        </button>
      </section>

      <section className="metrics-grid">
        {metrics.map(({ title, value, note, icon: Icon }) => (
          <article className="metric-card" key={title}>
            <div className="metric-top">
              <span>{title}</span>
              <div className="metric-icon"><Icon size={20} /></div>
            </div>
            <h2>{value}</h2>
            <p>{note}</p>
          </article>
        ))}
      </section>

      <section className="content-card">
        <div className="section-heading">
          <div>
            <h2>Recent FDR Instruments</h2>
            <p>Overview of registered fixed deposit receipts</p>
          </div>
          <button className="secondary-button" onClick={() => setActiveTab("FDR Instruments")}>
            View all <ArrowUpRight size={16} />
          </button>
        </div>

        <div className="search-box">
          <Search size={17} />
          <input placeholder="Search by FDR number or bank..." />
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>FDR NUMBER</th>
                <th>BANK</th>
                <th>DEPOSIT AMOUNT</th>
                <th>MATURITY DATE</th>
                <th>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {instruments.map((item) => (
                <tr key={item.id}>
                  <td className="fdr-number">{item.id}</td>
                  <td>{item.bank}</td>
                  <td className="amount">{item.amount}</td>
                  <td>{item.maturity}</td>
                  <td>
                    <span className={`status-badge ${item.status.toLowerCase()}`}>
                      {item.status === "Active" && <CheckCircle2 size={13} />}
                      {item.status === "Pending" && <Clock size={13} />}
                      {item.status === "Disputed" && <AlertTriangle size={13} />}
                      {item.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="bottom-grid">
        <article className="info-card">
          <div className="info-icon green"><ShieldCheck size={22} /></div>
          <div>
            <h3>Audit Integrity</h3>
            <p>Hash-chain verification status</p>
            <strong className="healthy">● Demo interface ready</strong>
          </div>
        </article>

        <article className="info-card">
          <div className="info-icon blue"><Landmark size={22} /></div>
          <div>
            <h3>Bank Reconciliation</h3>
            <p>Compare submitted and bank-confirmed FDR details.</p>
            <button className="text-button" onClick={() => setActiveTab("Bank Verification")}>
              Open verification <ArrowUpRight size={15} />
            </button>
          </div>
        </article>
      </section>

      <footer>SAFAR · AICTE FDR Management Portal <span>SIH 26265 · Frontend Preview</span></footer>
    </div>
  </main>
</div>

);
}

export default App;