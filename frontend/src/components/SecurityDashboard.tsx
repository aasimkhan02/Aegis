import React, { useEffect, useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  RefreshCw,
  Search,
  Lock,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';
import { fetchSecuritySummary } from '../api/dashboard';
import { SecuritySummary } from '../types/dashboard';

interface SecurityDashboardProps {
  onNavigateToRun?: (runId: string) => void;
}

export const SecurityDashboard: React.FC<SecurityDashboardProps> = ({
  onNavigateToRun,
}) => {
  const [summary, setSummary] = useState<SecuritySummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSecuritySummary();
      setSummary(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load security telemetry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const findings = summary?.findings || [];
  const filteredFindings = findings.filter((f) => {
    const q = search.toLowerCase();
    const matchesSearch =
      f.validator_name.toLowerCase().includes(q) ||
      (f.error_message && f.error_message.toLowerCase().includes(q)) ||
      (f.assistant_name && f.assistant_name.toLowerCase().includes(q)) ||
      (f.test_case_name && f.test_case_name.toLowerCase().includes(q)) ||
      f.run_id.toLowerCase().includes(q);

    if (!matchesSearch) return false;
    if (!categoryFilter) return true;
    return f.validator_name.toLowerCase().includes(categoryFilter.toLowerCase());
  });

  return (
    <div className="dataset-list-page">
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button className="btn-secondary small" onClick={loadData}>Retry</button>
        </div>
      )}

      <div className="section-header-row">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2>Security & Safety Intelligence</h2>
            {summary && summary.total_security_failures === 0 ? (
              <span className="badge passed">
                <i /> ALL CHECKS PASSING
              </span>
            ) : (
              <span className="badge failed">
                <i /> VIOLATIONS DETECTED
              </span>
            )}
          </div>
          <p>
            Deterministic zero-latency security evaluation across PII, system prompt canaries, forbidden content, and safety boundaries.
          </p>
        </div>
        <div className="section-actions">
          <button className="btn-secondary" onClick={loadData}>
            <RefreshCw size={14} className={loading ? 'spinner' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Top Level Metric Summary Cards */}
      <section className="stats-grid" style={{ marginBottom: '20px' }}>
        <article className="stat-card">
          <div className="stat-top">
            <span className="stat-label">Security Evaluations</span>
            <span className="stat-icon purple">
              <ShieldCheck size={16} />
            </span>
          </div>
          <div className="stat-value">
            {summary ? summary.total_security_cases : 0}
          </div>
          <div className="stat-foot">
            <span className="trend">Validated checks</span>
          </div>
        </article>

        <article className="stat-card">
          <div className="stat-top">
            <span className="stat-label">Security Violations</span>
            <span className="stat-icon orange">
              <ShieldAlert size={16} />
            </span>
          </div>
          <div className="stat-value" style={{ color: summary && summary.total_security_failures > 0 ? '#dc2626' : '#22c55e' }}>
            {summary ? summary.total_security_failures : 0}
          </div>
          <div className="stat-foot">
            <span style={{ color: summary && summary.total_security_failures > 0 ? '#dc2626' : '#22c55e', fontWeight: 600 }}>
              {summary && summary.total_security_failures === 0 ? 'Zero breaches' : 'Action recommended'}
            </span>
          </div>
        </article>

        <article className="stat-card">
          <div className="stat-top">
            <span className="stat-label">Pass Rate</span>
            <span className="stat-icon green">
              <CheckCircle2 size={16} />
            </span>
          </div>
          <div className="stat-value">
            {summary ? summary.security_pass_rate : 100}%
          </div>
          <div className="stat-foot">
            <span className="trend">Across security validators</span>
          </div>
        </article>

        <article className="stat-card">
          <div className="stat-top">
            <span className="stat-label">Posture Status</span>
            <span className="stat-icon blue">
              <Lock size={16} />
            </span>
          </div>
          <div className="stat-value" style={{ fontSize: '18px', paddingTop: '6px' }}>
            {summary && summary.total_security_failures === 0 ? 'Hardened' : 'Review Needed'}
          </div>
          <div className="stat-foot">
            <span>Deterministic engine active</span>
          </div>
        </article>
      </section>

      {/* 5 Security Categories Breakdown */}
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ fontSize: '13px', fontWeight: 700, margin: '0 0 10px', color: '#374151' }}>
          Validator Category Breakdown
        </h3>
        <div className="grid-5col">
          <div className="security-cat-card">
            <span className="cat-title">PII Protection</span>
            <div className="cat-count" style={{ color: (summary?.validator_breakdown?.['pii_detection']?.failed ?? 0) > 0 ? '#dc2626' : '#16a34a' }}>
              {summary?.validator_breakdown?.['pii_detection']?.failed ?? 0}
            </div>
            <span className="cat-status" style={{ color: (summary?.validator_breakdown?.['pii_detection']?.failed ?? 0) > 0 ? '#dc2626' : '#16a34a' }}>
              {(summary?.validator_breakdown?.['pii_detection']?.failed ?? 0) === 0 ? 'Clean' : 'Violations'}
            </span>
          </div>

          <div className="security-cat-card">
            <span className="cat-title">Canary Leakage</span>
            <div className="cat-count" style={{ color: (summary?.validator_breakdown?.['security_canary']?.failed ?? 0) > 0 ? '#dc2626' : '#16a34a' }}>
              {summary?.validator_breakdown?.['security_canary']?.failed ?? 0}
            </div>
            <span className="cat-status" style={{ color: (summary?.validator_breakdown?.['security_canary']?.failed ?? 0) > 0 ? '#dc2626' : '#16a34a' }}>
              {(summary?.validator_breakdown?.['security_canary']?.failed ?? 0) === 0 ? 'Secrecy Maintained' : 'Prompt Leaked'}
            </span>
          </div>

          <div className="security-cat-card">
            <span className="cat-title">Forbidden Words</span>
            <div className="cat-count" style={{ color: (summary?.validator_breakdown?.['forbidden_content']?.failed ?? 0) > 0 ? '#dc2626' : '#16a34a' }}>
              {summary?.validator_breakdown?.['forbidden_content']?.failed ?? 0}
            </div>
            <span className="cat-status" style={{ color: (summary?.validator_breakdown?.['forbidden_content']?.failed ?? 0) > 0 ? '#dc2626' : '#16a34a' }}>
              {(summary?.validator_breakdown?.['forbidden_content']?.failed ?? 0) === 0 ? 'Compliant' : 'Flagged'}
            </span>
          </div>

          <div className="security-cat-card">
            <span className="cat-title">Technical Safety</span>
            <div className="cat-count" style={{ color: (summary?.validator_breakdown?.['technical_safety']?.failed ?? 0) > 0 ? '#dc2626' : '#16a34a' }}>
              {summary?.validator_breakdown?.['technical_safety']?.failed ?? 0}
            </div>
            <span className="cat-status" style={{ color: (summary?.validator_breakdown?.['technical_safety']?.failed ?? 0) > 0 ? '#dc2626' : '#16a34a' }}>
              {(summary?.validator_breakdown?.['technical_safety']?.failed ?? 0) === 0 ? 'Safe' : 'Escapes Detected'}
            </span>
          </div>

          <div className="security-cat-card">
            <span className="cat-title">Policy Adherence</span>
            <div className="cat-count" style={{ color: (summary?.validator_breakdown?.['policy_compliance']?.failed ?? 0) > 0 ? '#dc2626' : '#16a34a' }}>
              {summary?.validator_breakdown?.['policy_compliance']?.failed ?? 0}
            </div>
            <span className="cat-status" style={{ color: (summary?.validator_breakdown?.['policy_compliance']?.failed ?? 0) > 0 ? '#dc2626' : '#16a34a' }}>
              {(summary?.validator_breakdown?.['policy_compliance']?.failed ?? 0) === 0 ? 'Adherent' : 'Violations'}
            </span>
          </div>
        </div>
      </div>

      {/* Security Findings Section */}
      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>Detected Security Findings</h2>
            <p>Every violation captured by deterministic validators across past evaluation runs.</p>
          </div>
        </div>

        <div className="filter-panel" style={{ margin: '0 0 16px', background: '#f8f9fa' }}>
          <div className="filter-row">
            <div className="search-box" style={{ flex: 1 }}>
              <Search size={15} />
              <input
                type="text"
                placeholder="Search findings by metric, diagnostic message, or assistant..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            <div className="filter-group">
              <span className="filter-label">Filter Category:</span>
              <select
                className="select-input"
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
              >
                <option value="">All Categories</option>
                <option value="pii">PII Detection</option>
                <option value="canary">Canary Leakage</option>
                <option value="forbidden">Forbidden Content</option>
                <option value="technical">Technical Safety</option>
                <option value="policy">Policy Compliance</option>
              </select>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="dataset-loading-state" style={{ padding: '40px 0' }}>
            <div className="spinner" />
            <span>Scanning security records...</span>
          </div>
        ) : filteredFindings.length === 0 ? (
          <div className="empty-state large" style={{ border: 'none', background: '#fafbfe' }}>
            <ShieldCheck size={36} color="#16a34a" />
            <h3>No Security Violations Found</h3>
            <p>
              {search || categoryFilter
                ? 'No findings matched your filter parameters.'
                : 'All tested assistant runs adhered cleanly to safety, canary secrecy, and privacy policies.'}
            </p>
          </div>
        ) : (
          <div className="test-cases-table-wrap">
            <table className="test-cases-table">
              <thead>
                <tr>
                  <th>VALIDATOR</th>
                  <th>ASSISTANT & DATASET</th>
                  <th>DIAGNOSTIC REASON</th>
                  <th>SCORE</th>
                  <th>TIMESTAMP</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filteredFindings.map((f, i) => (
                  <tr key={`${f.run_id}-${i}`}>
                    <td>
                      <span className={`badge ${f.status === 'passed' ? 'passed' : 'failed'}`} style={{ fontSize: '9px' }}>
                        <i />
                        {f.validator_name}
                      </span>
                    </td>
                    <td>
                      <strong>{f.assistant_name || 'Assistant'}</strong> (v{f.assistant_version || '1.0'})
                      <span style={{ display: 'block', fontSize: '9px', color: '#6b7280' }}>
                        {f.test_case_name}
                      </span>
                    </td>
                    <td style={{ maxWidth: '380px' }}>
                      <span style={{ color: f.status === 'passed' ? '#16a34a' : '#b91c1c', fontSize: '11px', fontWeight: 500 }}>
                        {f.error_message || (f.status === 'passed' ? 'Security assertion satisfied' : 'Violation detected')}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontFamily: 'monospace', fontWeight: 700, color: f.score < 1.0 ? '#dc2626' : '#16a34a' }}>
                        {f.score}
                      </span>
                    </td>
                    <td style={{ fontSize: '10px', color: '#6b7280' }}>
                      {new Date(f.evaluated_at).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td>
                      {onNavigateToRun && (
                        <button
                          className="text-link-button"
                          onClick={() => onNavigateToRun(f.run_id)}
                          title="Inspect Evaluation Run"
                        >
                          <ExternalLink size={13} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
