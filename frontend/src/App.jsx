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
  UploadCloud,
  GraduationCap,
  KeyRound
} from "lucide-react";
import "./App.css";

import { api } from "./api";
import DashboardView from "./components/DashboardView";
import InstrumentsView from "./components/InstrumentsView";
import BankVerificationView from "./components/BankVerificationView";
import BankConsoleView from "./components/BankConsoleView";
import AuditTrailView from "./components/AuditTrailView";
import SettingsView from "./components/SettingsView";
import CollegePortalView from "./components/CollegePortalView";
import NewInstrumentModal from "./components/NewInstrumentModal";

function App() {
  const [activeTab, setActiveTab] = useState("National Dashboard");
  const [selectedRole, setSelectedRole] = useState("priya");
  const [currentUser, setCurrentUser] = useState(null);
  const [reconInstrumentId, setReconInstrumentId] = useState("");
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // Authenticate default persona on boot (Priya - Delhi State Tech Univ Officer)
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
      setRefreshKey((k) => k + 1);

      // Contextual auto-switch tab based on persona
      if (res.user.role === "institution") {
        setActiveTab("College Dashboard");
      } else if (res.user.role === "bank_checker") {
        setActiveTab("Bank Release Console");
      } else if (res.user.role === "auditor") {
        setActiveTab("Audit Trail");
      } else {
        setActiveTab("National Dashboard");
      }
    } catch (err) {
      console.error("Role switch authentication failed:", err);
    }
  };

  useEffect(() => {
    window.__safar = {
      api,
      handleRoleChange,
      setActiveTab,
      setRefreshKey,
      setIsNewModalOpen,
    };
  }, [selectedRole, activeTab]);

  const handleSelectInstrumentForRecon = (instrumentId) => {
    setReconInstrumentId(instrumentId);
    setActiveTab("Bank Verification");
  };

  const isCollege = currentUser?.role === "institution";
  const isBank = currentUser?.role === "bank_checker";

  // Sidebar navigation dynamically adapts to role
  const getNavigation = () => {
    if (isCollege) {
      return [
        { name: "College Dashboard", icon: LayoutDashboard },
        { name: "Upload New FDR", icon: UploadCloud },
        { name: "Approval & Maturity Alerts", icon: Bell },
      ];
    }
    if (isBank) {
      return [
        { name: "Bank Release Console", icon: KeyRound },
        { name: "Bank Verification Adapter", icon: Landmark },
        { name: "Audit Trail", icon: ClipboardCheck },
      ];
    }
    return [
      { name: "National Dashboard", icon: LayoutDashboard },
      { name: "FDR Registry & Release Queue", icon: FileText },
      { name: "Bank Verification", icon: Landmark },
      { name: "Audit Trail", icon: ClipboardCheck },
      { name: "Settings & Demo Clock", icon: Settings },
    ];
  };

  const navigation = getNavigation();

  // Helper for persona metadata
  const getPersonaMeta = () => {
    const role = currentUser?.role || "aicte_officer";
    switch (role) {
      case "institution":
        return {
          avatarClass: "institution",
          avatarText: "CL",
          title: currentUser?.name || "College User",
          scope: `Multi-Tenant Isolation: ${currentUser?.name || "College"} · Isolated from other colleges.`,
          privilege: "College FDR Upload, Portfolio & Release Requests",
        };
      case "bank_checker":
        return {
          avatarClass: "bank",
          avatarText: "BK",
          title: currentUser?.name || "Bank Checker [SIMULATED]",
          scope: `Core Banking Scope: ${currentUser?.bank_id ? currentUser.bank_id.toUpperCase() : "Demo Bank"} [SIMULATED]. Dual-key code verification.`,
          privilege: "Simulated Two-Part Release Confirmation & Lien Discharge",
        };
      case "auditor":
        return {
          avatarClass: "auditor",
          avatarText: "AU",
          title: "Audit Observer",
          scope: "Compliance Watch: Read-only cryptographic inspection of append-only SHA-256 audit ledger.",
          privilege: "Read-Only Compliance Observer & Failed Verification Reports",
        };
      case "aicte_senior":
        return {
          avatarClass: "senior",
          avatarText: "AR",
          title: "Dr. Anita Rao",
          scope: "AICTE Headquarters: National Jurisdiction across all Universities and States.",
          privilege: "Final Release Approval, Reissue Authorizations & Dispute Clearance",
        };
      case "admin":
        return {
          avatarClass: "admin",
          avatarText: "AD",
          title: "Portal Administrator",
          scope: "Super Administrator: Regulatory parameter configuration and tamper evidence recovery.",
          privilege: "Rules Table, Ledger Repair & Demo Controls",
        };
      default:
        return {
          avatarClass: "officer",
          avatarText: "UO",
          title: currentUser?.name || "University Officer",
          scope: `AICTE University Jurisdiction: ${currentUser?.university_id ? currentUser.university_id.toUpperCase() : "Regional University"}.`,
          privilege: "Scrutiny, Checklist Recommendation & Compliance Review",
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
            <span>
              {isCollege ? "COLLEGE PORTAL" : isBank ? "BANK CONSOLE" : "AICTE PORTAL"}
            </span>
          </div>
        </div>

        <div className="nav-label">
          {isCollege ? "COLLEGE DESK" : isBank ? "CORE BANKING [SIMULATED]" : "OFFICER WORKSPACE"}
        </div>

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
              <strong>
                {isCollege ? "Institutional Isolated" : isBank ? "Simulated Gateway" : "Cryptographic Ledger"}
              </strong>
              <span>
                {isCollege ? "Private College Scope" : isBank ? "Dual-Key Auth Active" : "SHA-256 Chained Log"}
              </span>
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
            <span className="breadcrumb">
              {isCollege ? "College Portal / " : isBank ? "Bank Gateway / " : "AICTE Central / "}
            </span>
            <strong>{activeTab}</strong>
          </div>

          <div className="topbar-actions">
            <span className="live-indicator">
              <span /> PostgreSQL (5433) Connected
            </span>

            <button className="icon-button" aria-label="Notifications" title="System Alerts">
              <Bell size={19} />
            </button>

            {/* Persona Switcher covering all 6 official scenarios */}
            <label className="role-select" title="Switch Evaluator Authentication Persona">
              <span>Persona:</span>
              <select
                value={selectedRole}
                onChange={(e) => handleRoleChange(e.target.value)}
              >
                <optgroup label="University Officers">
                  <option value="priya">Priya Sharma (Demo University A - univ-001)</option>
                  <option value="rajan">Rajan Mehta (Demo University B - univ-002)</option>
                </optgroup>
                <optgroup label="AICTE Senior Director">
                  <option value="anita">Dr. Anita Rao (Senior AICTE Director - National)</option>
                </optgroup>
                <optgroup label="Demo Partner Banks [SIMULATED]">
                  <option value="bank_a">Demo Bank A Officer (DEMOA) [SIMULATED]</option>
                  <option value="bank_b">Demo Bank B Officer (DEMOB) [SIMULATED]</option>
                  <option value="bank_c">Demo Bank C Officer (DEMOC) [SIMULATED]</option>
                </optgroup>
                <optgroup label="Technical Colleges">
                  <option value="inst_user">Delhi Institute of Technology (inst-001)</option>
                  <option value="inst_apex">Apex Engineering College (inst-002)</option>
                  <option value="inst_sunrise">Sunrise Institute of Technology (inst-003)</option>
                </optgroup>
                <optgroup label="Governance & Audit">
                  <option value="auditor">Audit Observer (Compliance Neutral)</option>
                  <option value="admin">Portal Administrator</option>
                </optgroup>
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

          {/* Conditional View Rendering based on Active Tab & Role */}
          {isCollege ? (
            <CollegePortalView
              currentUser={currentUser}
              onOpenNewModal={() => setIsNewModalOpen(true)}
            />
          ) : isBank ? (
            activeTab === "Bank Release Console" ? (
              <BankConsoleView currentUser={currentUser} />
            ) : activeTab === "Bank Verification Adapter" ? (
              <BankVerificationView currentUser={currentUser} initialInstrumentId={reconInstrumentId} />
            ) : (
              <AuditTrailView currentUser={currentUser} />
            )
          ) : (
            <>
              {activeTab === "National Dashboard" && (
                <DashboardView
                  currentUser={currentUser}
                  onSelectTab={setActiveTab}
                  onOpenNewModal={() => setIsNewModalOpen(true)}
                  onSelectInstrumentForRecon={handleSelectInstrumentForRecon}
                />
              )}

              {activeTab === "FDR Registry & Release Queue" && (
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

              {activeTab === "Settings & Demo Clock" && (
                <SettingsView currentUser={currentUser} />
              )}
            </>
          )}

          <footer>
            <span>SAFAR · Smart AICTE FDR Automation &amp; Registry</span>
            <span>SIH Problem Statement 26265 · Ministry of Education · Bank responses simulated</span>
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