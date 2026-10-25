import { useState, useEffect } from "react";
import {
  Clock,
  FastForward,
  RotateCcw,
  Sliders,
  ShieldAlert,
  Server,
  UserCheck,
  CheckCircle2,
  RefreshCw
} from "lucide-react";
import { api, formatDate } from "../api";

export default function SettingsView() {
  const [clock, setClock] = useState(null);
  const [rules, setRules] = useState([]);
  const [clockLoading, setClockLoading] = useState(false);
  const [advanceMsg, setAdvanceMsg] = useState("");

  const loadData = async () => {
    try {
      const [clk, rls] = await Promise.all([
        api.getClock().catch(() => null),
        api.getRules().catch(() => []),
      ]);
      setClock(clk);
      setRules(rls || []);
    } catch (err) {
      console.error("Error loading settings:", err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAdvance = async (days) => {
    try {
      setClockLoading(true);
      setAdvanceMsg("");
      const res = await api.advanceClock(days);
      setClock({
        current_time: res.new_time,
        today: res.today,
        is_simulated: true,
      });
      setAdvanceMsg(`Clock advanced by +${days} days. Daily alert scheduler evaluated.`);
    } catch (err) {
      alert("Failed to advance clock: " + err.message);
    } finally {
      setClockLoading(false);
    }
  };

  const handleReset = async () => {
    try {
      setClockLoading(true);
      setAdvanceMsg("");
      const res = await api.resetClock();
      setClock({
        current_time: res.current_time,
        today: res.current_time.split("T")[0],
        is_simulated: false,
      });
      setAdvanceMsg("Clock restored to real host system time.");
    } catch (err) {
      alert("Failed to reset clock: " + err.message);
    } finally {
      setClockLoading(false);
    }
  };

  return (
    <div className="view-container">
      <section className="welcome-row">
        <div>
          <p className="eyebrow">PORTAL CONTROLS & DEMO ENVIRONMENT</p>
          <h1>Settings & Simulation Controls</h1>
          <p className="subtitle">
            Configure AICTE regulatory parameters, test scenario time-travel, and review evaluator authentication personas.
          </p>
        </div>
      </section>

      {/* Evaluator Simulation Clock Card */}
      <section className="content-card">
        <div className="section-heading">
          <div className="heading-with-icon">
            <div className="brand-icon" style={{ width: 36, height: 36 }}>
              <Clock size={20} />
            </div>
            <div>
              <h2>Evaluator Time-Travel Simulation Clock</h2>
              <p>Simulate lifecycle progression across 10-year maturity thresholds for Scenario 4 evaluation.</p>
            </div>
          </div>
        </div>

        <div className="clock-panel">
          <div className="clock-status">
            <span className="clock-label">CURRENT SIMULATED DATE:</span>
            <h2 className="clock-date">
              {clock?.today ? formatDate(clock.today) : "Real-time Sync"}
            </h2>
            <span className={`clock-badge ${clock?.is_simulated ? "simulated" : "real"}`}>
              {clock?.is_simulated ? "● Time-Travel Active" : "● Real System Time"}
            </span>
          </div>

          <div className="clock-actions">
            <button
              className="primary-button clock-btn"
              onClick={() => handleAdvance(30)}
              disabled={clockLoading}
            >
              <FastForward size={16} /> Fast-Forward +30 Days
            </button>
            <button
              className="primary-button clock-btn"
              onClick={() => handleAdvance(90)}
              disabled={clockLoading}
            >
              <FastForward size={16} /> Fast-Forward +90 Days
            </button>
            <button
              className="secondary-button"
              onClick={handleReset}
              disabled={clockLoading}
            >
              <RotateCcw size={15} /> Reset Clock
            </button>
          </div>
        </div>

        {advanceMsg && (
          <div className="alert-box success" style={{ marginTop: "16px" }}>
            <CheckCircle2 size={16} />
            <span>{advanceMsg}</span>
          </div>
        )}
      </section>

      <div className="bottom-grid" style={{ marginTop: "24px" }}>
        {/* Evaluator Credentials Roster */}
        <section className="content-card">
          <div className="section-heading">
            <div className="heading-with-icon">
              <div className="brand-icon" style={{ width: 34, height: 34 }}>
                <UserCheck size={18} />
              </div>
              <div>
                <h2>Evaluator Role Personas</h2>
                <p>Standard password for all accounts: <code>demo1234</code></p>
              </div>
            </div>
          </div>

          <div className="roster-list">
            <div className="roster-item">
              <div>
                <strong>priya</strong>
                <span>Priya Sharma</span>
              </div>
              <span className="role-tag">aicte_officer</span>
            </div>
            <div className="roster-item">
              <div>
                <strong>anita</strong>
                <span>Dr. Anita Rao</span>
              </div>
              <span className="role-tag senior">aicte_senior</span>
            </div>
            <div className="roster-item">
              <div>
                <strong>bank_checker</strong>
                <span>Bank Checker [SIMULATED]</span>
              </div>
              <span className="role-tag bank">bank_checker</span>
            </div>
            <div className="roster-item">
              <div>
                <strong>auditor</strong>
                <span>Audit Observer</span>
              </div>
              <span className="role-tag auditor">auditor</span>
            </div>
            <div className="roster-item">
              <div>
                <strong>admin</strong>
                <span>Portal Administrator</span>
              </div>
              <span className="role-tag admin">admin</span>
            </div>
          </div>
        </section>

        {/* AICTE Regulatory Parameters */}
        <section className="content-card">
          <div className="section-heading">
            <div className="heading-with-icon">
              <div className="brand-icon" style={{ width: 34, height: 34 }}>
                <Sliders size={18} />
              </div>
              <div>
                <h2>AICTE Regulatory Rules</h2>
                <p>Configurable approval process handbook thresholds</p>
              </div>
            </div>
          </div>

          <div className="rules-list">
            {rules.length === 0 ? (
              <p style={{ color: "#8996a8", fontSize: "12px" }}>Loading regulatory parameters...</p>
            ) : (
              rules.map((rule) => (
                <div key={rule.key} className="rule-item">
                  <div className="rule-info">
                    <strong>{rule.key}</strong>
                    <span className="rule-clause">{rule.clause_reference || "AICTE APH Guidelines"}</span>
                  </div>
                  <span className="rule-val">{rule.value}</span>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
