import { useState, useEffect } from "react";
import { X, ShieldCheck, AlertCircle, Loader2 } from "lucide-react";
import { api } from "../api";

export default function NewInstrumentModal({ isOpen, onClose, onSuccess }) {
  const [institutions, setInstitutions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const todayStr = new Date().toISOString().split("T")[0];
  const defaultMaturity = new Date();
  defaultMaturity.setFullYear(defaultMaturity.getFullYear() + 10);
  const defaultMaturityStr = defaultMaturity.toISOString().split("T")[0];

  const [formData, setFormData] = useState({
    institution_id: "",
    bank_name: "State Bank of India",
    branch: "Connaught Place, New Delhi",
    reference_no: "",
    amount_rupees: "2500000",
    interest_rate: "7.25%",
    issue_date: todayStr,
    maturity_date: defaultMaturityStr,
    tenure_years: 10,
    joint_holder: "AICTE and Society / Trust",
    lien_marked: true,
  });

  useEffect(() => {
    if (isOpen) {
      api.getInstitutions()
        .then((data) => {
          setInstitutions(data);
          if (data && data.length > 0) {
            setFormData((prev) => ({
              ...prev,
              institution_id: prev.institution_id || data[0].id,
            }));
          }
        })
        .catch((err) => console.error("Failed to load institutions:", err));
      setError("");
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!formData.reference_no.trim()) {
      setError("Please provide the FDR Certificate / Reference number.");
      return;
    }
    const amountRupees = parseFloat(formData.amount_rupees);
    if (isNaN(amountRupees) || amountRupees <= 0) {
      setError("Please enter a valid deposit amount.");
      return;
    }

    try {
      setLoading(true);
      const payload = {
        institution_id: formData.institution_id,
        bank_name: formData.bank_name,
        branch: formData.branch,
        reference_no: formData.reference_no.trim(),
        amount_paise: Math.round(amountRupees * 100),
        interest_rate: formData.interest_rate,
        issue_date: formData.issue_date,
        maturity_date: formData.maturity_date,
        tenure_years: parseInt(formData.tenure_years, 10) || 10,
        type: "bank_fdr",
        joint_holder: formData.joint_holder,
        lien_marked: Boolean(formData.lien_marked),
      };

      await api.createInstrument(payload);
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err.message || "Failed to register FDR instrument.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-container">
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="brand-icon" style={{ width: 34, height: 34 }}>
              <ShieldCheck size={20} />
            </div>
            <div>
              <h3>Register Fixed Deposit Receipt</h3>
              <p>AICTE Approval Process Handbook — Mandatory Joint FDR Deposit</p>
            </div>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        {error && (
          <div className="alert-box error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-grid">
            <div className="form-group full-width">
              <label>Technical Institution</label>
              <select
                name="institution_id"
                value={formData.institution_id}
                onChange={handleChange}
                required
              >
                {institutions.map((inst) => (
                  <option key={inst.id} value={inst.id}>
                    {inst.name} ({inst.aicte_id} - {inst.state})
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Issuing Bank Name</label>
              <select name="bank_name" value={formData.bank_name} onChange={handleChange}>
                <option>State Bank of India</option>
                <option>Punjab National Bank</option>
                <option>HDFC Bank</option>
                <option>ICICI Bank</option>
                <option>Bank of Baroda</option>
                <option>Canara Bank</option>
                <option>Union Bank of India</option>
              </select>
            </div>

            <div className="form-group">
              <label>Bank Branch</label>
              <input
                type="text"
                name="branch"
                value={formData.branch}
                onChange={handleChange}
                placeholder="e.g. Connaught Place, New Delhi"
                required
              />
            </div>

            <div className="form-group">
              <label>FDR Reference / Certificate No.</label>
              <input
                type="text"
                name="reference_no"
                value={formData.reference_no}
                onChange={handleChange}
                placeholder="e.g. SBIN00998822"
                required
              />
            </div>

            <div className="form-group">
              <label>Principal Amount (₹ INR)</label>
              <input
                type="number"
                name="amount_rupees"
                value={formData.amount_rupees}
                onChange={handleChange}
                placeholder="e.g. 2500000"
                min="10000"
                step="1000"
                required
              />
            </div>

            <div className="form-group">
              <label>Interest Rate (p.a.)</label>
              <input
                type="text"
                name="interest_rate"
                value={formData.interest_rate}
                onChange={handleChange}
                placeholder="e.g. 7.25%"
              />
            </div>

            <div className="form-group">
              <label>Tenure (Years)</label>
              <input
                type="number"
                name="tenure_years"
                value={formData.tenure_years}
                onChange={handleChange}
                min="1"
                max="20"
                required
              />
            </div>

            <div className="form-group">
              <label>Deposit Date</label>
              <input
                type="date"
                name="issue_date"
                value={formData.issue_date}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label>Maturity Date</label>
              <input
                type="date"
                name="maturity_date"
                value={formData.maturity_date}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group full-width">
              <label>Joint Name Formulation</label>
              <input
                type="text"
                name="joint_holder"
                value={formData.joint_holder}
                onChange={handleChange}
                placeholder="e.g. AICTE and Society / Trust"
                required
              />
            </div>

            <div className="form-group checkbox full-width">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  name="lien_marked"
                  checked={formData.lien_marked}
                  onChange={handleChange}
                />
                <span>
                  <strong>Lien Marked to AICTE:</strong> Instrument is legally pledged with irrevocable bank lien clause.
                </span>
              </label>
            </div>
          </div>

          <div className="modal-actions">
            <button type="button" className="secondary-button" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="primary-button" disabled={loading}>
              {loading ? <><Loader2 size={16} className="spin" /> Registering...</> : "Submit FDR Record"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
