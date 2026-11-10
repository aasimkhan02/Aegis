import React, { useState, useEffect } from 'react';
import {
  SlidersHorizontal,
  Server,
  CheckCircle2,
  Save,
  RotateCcw,
} from 'lucide-react';

export const SettingsView: React.FC = () => {
  const [concurrency, setConcurrency] = useState<number>(2);
  const [timeout, setTimeoutSec] = useState<number>(30);
  const [failFast, setFailFast] = useState<boolean>(false);
  const [autoSecurity, setAutoSecurity] = useState<boolean>(true);
  const [savedNotice, setSavedNotice] = useState<boolean>(false);

  useEffect(() => {
    const saved = localStorage.getItem('aegis_settings');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.concurrency) setConcurrency(parsed.concurrency);
        if (parsed.timeout) setTimeoutSec(parsed.timeout);
        if (parsed.failFast !== undefined) setFailFast(parsed.failFast);
        if (parsed.autoSecurity !== undefined) setAutoSecurity(parsed.autoSecurity);
      } catch {
        // ignore
      }
    }
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    localStorage.setItem(
      'aegis_settings',
      JSON.stringify({
        concurrency,
        timeout,
        failFast,
        autoSecurity,
      })
    );
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 3000);
  };

  const handleReset = () => {
    setConcurrency(2);
    setTimeoutSec(30);
    setFailFast(false);
    setAutoSecurity(true);
    localStorage.removeItem('aegis_settings');
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 3000);
  };

  const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  return (
    <div className="dataset-list-page">
      {savedNotice && (
        <div className="notification-pill success">
          <CheckCircle2 size={16} />
          <span>Evaluation preferences saved successfully.</span>
        </div>
      )}

      <div className="section-header-row">
        <div>
          <h2>Evaluation & System Settings</h2>
          <p>Configure evaluation execution defaults, worker parallelism, and inspect environment capabilities.</p>
        </div>
      </div>

      <div className="grid-2col" style={{ alignItems: 'start' }}>
        {/* Execution Defaults Card */}
        <form onSubmit={handleSave} className="setting-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <SlidersHorizontal size={18} color="#6366f1" />
            <h3 className="setting-title" style={{ margin: 0 }}>Execution Defaults</h3>
          </div>
          <p className="setting-desc">
            These preferences will be applied as initial defaults whenever executing new evaluation suites.
          </p>

          <div className="form-group" style={{ marginBottom: '14px' }}>
            <label>Default Worker Concurrency (1 - 10)</label>
            <input
              type="number"
              min={1}
              max={10}
              value={concurrency}
              onChange={(e) => setConcurrency(parseInt(e.target.value) || 1)}
            />
          </div>

          <div className="form-group" style={{ marginBottom: '14px' }}>
            <label>Case Execution Timeout (seconds)</label>
            <input
              type="number"
              min={5}
              max={300}
              value={timeout}
              onChange={(e) => setTimeoutSec(parseInt(e.target.value) || 30)}
            />
          </div>

          <div className="form-group" style={{ marginBottom: '14px' }}>
            <div className="form-checkbox">
              <label>
                <input
                  type="checkbox"
                  checked={failFast}
                  onChange={(e) => setFailFast(e.target.checked)}
                />
                Default to Fail Fast (abort run on first case error)
              </label>
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: '18px' }}>
            <div className="form-checkbox">
              <label>
                <input
                  type="checkbox"
                  checked={autoSecurity}
                  onChange={(e) => setAutoSecurity(e.target.checked)}
                />
                Automatically enable deterministic security validators
              </label>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '9px', borderTop: '1px solid #f1f2f5', paddingTop: '14px' }}>
            <button type="submit" className="primary-button">
              <Save size={14} /> Save Preferences
            </button>
            <button type="button" className="btn-secondary" onClick={handleReset}>
              <RotateCcw size={14} /> Reset Defaults
            </button>
          </div>
        </form>

        {/* System & Engine Architecture Card */}
        <div className="setting-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Server size={18} color="#10b981" />
            <h3 className="setting-title" style={{ margin: 0 }}>System Telemetry & Engines</h3>
          </div>
          <p className="setting-desc">
            Integrated evaluation frameworks, deterministic validators, and database connectivity.
          </p>

          <div style={{ display: 'grid', gap: '10px' }}>
            <div style={{ padding: '10px 12px', background: '#fafbfe', border: '1px solid #eceef2', borderRadius: '7px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ fontSize: '11px', color: '#1f2937' }}>Backend API Service</strong>
                <span className="badge passed" style={{ fontSize: '8px' }}><i /> ONLINE</span>
              </div>
              <span style={{ fontSize: '10px', color: '#6b7280', fontFamily: 'monospace' }}>
                {apiBase}
              </span>
            </div>

            <div style={{ padding: '10px 12px', background: '#fafbfe', border: '1px solid #eceef2', borderRadius: '7px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ fontSize: '11px', color: '#1f2937' }}>Database Engine</strong>
                <span className="badge passed" style={{ fontSize: '8px' }}><i /> CONNECTED</span>
              </div>
              <span style={{ fontSize: '10px', color: '#6b7280' }}>
                PostgreSQL with SQLAlchemy ORM (ACID transactions & schema migrations)
              </span>
            </div>

            <div style={{ padding: '10px 12px', background: '#fafbfe', border: '1px solid #eceef2', borderRadius: '7px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ fontSize: '11px', color: '#1f2937' }}>Security Validator Engine</strong>
                <span className="badge passed" style={{ fontSize: '8px' }}><i /> READY</span>
              </div>
              <span style={{ fontSize: '10px', color: '#6b7280' }}>
                Zero-LLM deterministic rules (Canary token secrecy, PII regex, forbidden lexicons, safety boundaries)
              </span>
            </div>

            <div style={{ padding: '10px 12px', background: '#fafbfe', border: '1px solid #eceef2', borderRadius: '7px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ fontSize: '11px', color: '#1f2937' }}>DeepEval & Ragas Evaluators</strong>
                <span className="badge passed" style={{ fontSize: '8px' }}><i /> MOUNTED</span>
              </div>
              <span style={{ fontSize: '10px', color: '#6b7280' }}>
                Faithfulness, Answer Relevancy, Hallucination, Context Precision
              </span>
            </div>

            <div style={{ padding: '10px 12px', background: '#fafbfe', border: '1px solid #eceef2', borderRadius: '7px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ fontSize: '11px', color: '#1f2937' }}>Promptfoo Engine</strong>
                <span className="badge passed" style={{ fontSize: '8px' }}><i /> MOUNTED</span>
              </div>
              <span style={{ fontSize: '10px', color: '#6b7280' }}>
                Automated adversarial prompt assertions & red-teaming
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
