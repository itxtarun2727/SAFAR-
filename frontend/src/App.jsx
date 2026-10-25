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
  Database
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
    { name: "FDR Instruments", icon: FileText },
    { name: "Bank Verification", icon: Landmark },
    { name: "Audit Trail", icon: ClipboardCheck },
    { name: "Settings", icon: Settings },
  ];

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
                <option value="bank_checker">Bank Checker [SIMULATED]</option>
                <option value="auditor">Audit Observer</option>
                <option value="admin">Portal Administrator</option>
              </select>
              <ChevronDown size={14} />
            </label>
          </div>
        </header>

        {/* Page Content Body */}
        <div className="page-content" key={refreshKey}>
          {activeTab === "Dashboard" && (
            <DashboardView
              onSelectTab={setActiveTab}
              onOpenNewModal={() => setIsNewModalOpen(true)}
              onSelectInstrumentForRecon={handleSelectInstrumentForRecon}
            />
          )}

          {activeTab === "FDR Instruments" && (
            <InstrumentsView
              onOpenNewModal={() => setIsNewModalOpen(true)}
              onSelectInstrumentForRecon={handleSelectInstrumentForRecon}
            />
          )}

          {activeTab === "Bank Verification" && (
            <BankVerificationView
              initialInstrumentId={reconInstrumentId}
            />
          )}

          {activeTab === "Audit Trail" && (
            <AuditTrailView />
          )}

          {activeTab === "Settings" && (
            <SettingsView />
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