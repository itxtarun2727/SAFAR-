import { useState, useEffect } from "react";
import {
  ShieldCheck,
  LayoutDashboard,
  FileText,
  Landmark,
  ClipboardCheck,
  Settings,
  Bell,
  ChevronDown,
  UserCheck,
  Building,
  Eye,
  CheckCircle2,
  Lock
} from "lucide-react";
import "./App.css";

import { api } from "./api";
import DashboardView from "./components/DashboardView";
import InstrumentsView from "./components/InstrumentsView";
import BankVerificationView from "./components/BankVerificationView";
import AuditTrailView from "./components/AuditTrailView";
import SettingsView from "./components/SettingsView";
import NewInstrumentModal from "./components/NewInstrumentModal";

function App() {
  const [activeTab, setActiveTab] = useState("Dashboard");
  const [selectedRole, setSelectedRole] = useState("priya");
  const [currentUser, setCurrentUser] = useState(null);
  const [reconInstrumentId, setReconInstrumentId] = useState("");
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // Authenticate default persona on boot
  useEffect(() => {
    api.login("priya", "demo1234")
      .then((res) => {
        setCurrentUser(res.user);
      })
      .catch((err) => console.warn("Auto-login notice:", err));
  }, []);

  const handleRoleChange = async (username) => {
    setSelectedRole(username);
    try {
      const res = await api.login(username, "demo1234");
      setCurrentUser(res.user);
      // Increment refresh key to trigger immediate re-fetch in all views with new Bearer token
      setRefreshKey((k) => k + 1);

      // Contextual auto-switch tab based on persona for intuitive evaluation
      if (username === "bank_checker") {
        setActiveTab("Bank Verification");
      } else if (username === "auditor") {
        setActiveTab("Audit Trail");
      } else if (username === "inst_user") {
        setActiveTab("FDR Instruments");
      }
    } catch (err) {
      console.error("Role switch authentication failed:", err);
    }
  };

  const handleSelectInstrumentForRecon = (instrumentId) => {
    setReconInstrumentId(instrumentId);
    setActiveTab("Bank Verification");
  };

  const navigation = [
    { name: "Dashboard", icon: LayoutDashboard },
    {
      name: currentUser?.role === "institution" ? "My College FDRs" : "FDR Instruments",
      icon: FileText
    },
    { name: "Bank Verification", icon: Landmark },
    { name: "Audit Trail", icon: ClipboardCheck },
    { name: "Settings", icon: Settings },
  ];

  // Helper for persona details
  const getPersonaMeta = () => {
    const role = currentUser?.role || "aicte_officer";
    switch (role) {
      case "institution":
        return {
          avatarClass: "institution",
          avatarText: "GI",
          title: "Greenfield Tech User",
          scope: "Institutional Scope: Greenfield Institute of Technology (inst-001) · Showing only college-owned FDRs.",
          privilege: "College FDR Registration & Status Tracking",
        };
      case "bank_checker":
        return {
          avatarClass: "bank",
          avatarText: "BK",
          title: "Bank Checker [SIMULATED]",
          scope: "Core Banking Gateway: Direct access to ISO-20022 simulated confirmation adapter.",
          privilege: "Automated Bank Verification & Confirmation",
        };
      case "auditor":
        return {
          avatarClass: "auditor",
          avatarText: "AU",
          title: "Audit Observer",
          scope: "Compliance Watch: Read-only cryptographic inspection of append-only audit trail.",
          privilege: "Read-Only Compliance Observer",
        };
      case "aicte_senior":
        return {
          avatarClass: "senior",
          avatarText: "AR",
          title: "Dr. Anita Rao",
          scope: "AICTE Headquarters: Senior Approval & High-Value FDR Jurisdiction.",
          privilege: "Dispute Clearance & Release Authorization",
        };
      case "admin":
        return {
          avatarClass: "admin",
          avatarText: "AD",
          title: "Portal Administrator",
          scope: "Full Root Jurisdiction: Complete governance over regulatory parameters, users, and ledger.",
          privilege: "Master Configuration & Demo Controls",
        };
      default:
        return {
          avatarClass: "officer",
          avatarText: "PS",
          title: "Priya Sharma",
          scope: "AICTE Regional Bureau: Scrutiny desk for technical institution joint deposits.",
          privilege: "FDR Scrutiny, Notes & Dispute Holds",
        };
    }
  };

  const personaMeta = getPersonaMeta();

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <ShieldCheck size={26} />
          </div>
          <div>
            <h2>SAFAR</h2>
            <span>AICTE FDR PORTAL</span>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>

        <nav>
          {navigation.map(({ name, icon: Icon }) => {
            const isSelected =
              activeTab === name ||
              (activeTab === "FDR Instruments" && name === "My College FDRs");
            return (
              <button
                key={name}
                className={`nav-item ${isSelected ? "selected" : ""}`}
                onClick={() => {
                  if (name === "My College FDRs") setActiveTab("FDR Instruments");
                  else setActiveTab(name);
                }}
              >
                <Icon size={19} />
                <span>{name}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="secure-badge">
            <ShieldCheck size={19} />
            <div>
              <strong>Cryptographic Integrity</strong>
              <span>SHA-256 Chaining Active</span>
            </div>
          </div>
          <p>SIH 26265 · AICTE Govt of India</p>
        </div>
      </aside>

      {/* Main Area */}
      <main className="main-area">
        {/* Topbar */}
        <header className="topbar">
          <div>
            <span className="breadcrumb">Workspace / </span>
            <strong>{activeTab}</strong>
          </div>

          <div className="topbar-actions">
            <span className="live-indicator">
              <span /> PostgreSQL (5433) Connected
            </span>

            <button className="icon-button" aria-label="Notifications" title="System Alerts">
              <Bell size={19} />
            </button>

            <label className="role-select" title="Switch Evaluator Authentication Persona">
              <span>Persona:</span>
              <select
                value={selectedRole}
                onChange={(e) => handleRoleChange(e.target.value)}
              >
                <option value="priya">Priya Sharma (AICTE Officer)</option>
                <option value="anita">Dr. Anita Rao (Senior AICTE)</option>
                <option value="inst_user">Greenfield Tech (Technical College)</option>
                <option value="bank_checker">Bank Checker [SIMULATED]</option>
                <option value="auditor">Audit Observer (Compliance Neutral)</option>
                <option value="admin">Portal Administrator</option>
              </select>
              <ChevronDown size={14} />
            </label>
          </div>
        </header>

        {/* Page Content Body */}
        <div className="page-content" key={`${refreshKey}-${selectedRole}`}>
          {/* Persona Context Banner */}
          <section className="persona-context-banner">
            <div className="persona-left">
              <div className={`persona-avatar ${personaMeta.avatarClass}`}>
                {personaMeta.avatarText}
              </div>
              <div className="persona-details">
                <div className="persona-name-row">
                  <strong>{currentUser?.name || personaMeta.title}</strong>
                  <span className={`role-tag ${personaMeta.avatarClass}`}>
                    {currentUser?.role || selectedRole}
                  </span>
                </div>
                <p className="persona-scope-text">{personaMeta.scope}</p>
              </div>
            </div>
            <div className="persona-privilege-tag">
              {personaMeta.privilege}
            </div>
          </section>

          {activeTab === "Dashboard" && (
            <DashboardView
              currentUser={currentUser}
              onSelectTab={setActiveTab}
              onOpenNewModal={() => setIsNewModalOpen(true)}
              onSelectInstrumentForRecon={handleSelectInstrumentForRecon}
            />
          )}

          {activeTab === "FDR Instruments" && (
            <InstrumentsView
              currentUser={currentUser}
              onOpenNewModal={() => setIsNewModalOpen(true)}
              onSelectInstrumentForRecon={handleSelectInstrumentForRecon}
            />
          )}

          {activeTab === "Bank Verification" && (
            <BankVerificationView
              currentUser={currentUser}
              initialInstrumentId={reconInstrumentId}
            />
          )}

          {activeTab === "Audit Trail" && (
            <AuditTrailView currentUser={currentUser} />
          )}

          {activeTab === "Settings" && (
            <SettingsView currentUser={currentUser} />
          )}

          <footer>
            <span>SAFAR · Smart AICTE FDR Automation &amp; Registry</span>
            <span>SIH Problem Statement 26265 · Ministry of Education</span>
          </footer>
        </div>
      </main>

      {/* Register New FDR Modal */}
      <NewInstrumentModal
        isOpen={isNewModalOpen}
        onClose={() => setIsNewModalOpen(false)}
        onSuccess={() => {
          setRefreshKey((k) => k + 1);
        }}
      />
    </div>
  );
}

export default App;