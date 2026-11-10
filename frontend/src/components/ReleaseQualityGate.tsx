import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  XCircle,
} from 'lucide-react';
import { fetchCompletedRuns } from '../api/comparison';
import { evaluateQualityGate } from '../api/quality_gate';
import { EvaluationRunSummary } from '../types/comparison';
import { QualityGateResponse } from '../types/quality_gate';

export const ReleaseQualityGate: React.FC = () => {
  const [runs, setRuns] = useState<EvaluationRunSummary[]>([]);
  const [baselineId, setBaselineId] = useState<string>('');
  const [candidateId, setCandidateId] = useState<string>('');
  const [minPassRate, setMinPassRate] = useState<number>(90);
  const [maxRegression, setMaxRegression] = useState<number>(5);
  const [maxSecFailures, setMaxSecFailures] = useState<number>(0);
  const [requiredMetrics, setRequiredMetrics] = useState<string>('expected_output, tool_usage, security_policy');

  const [loadingRuns, setLoadingRuns] = useState<boolean>(false);
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QualityGateResponse | null>(null);

  const loadRuns = async () => {
    try {
      setLoadingRuns(true);
      setError(null);
      const items = await fetchCompletedRuns();
      setRuns(items);
      if (items.length >= 2) {
        setBaselineId(items[1].id);
        setCandidateId(items[0].id);
      } else if (items.length === 1) {
        setBaselineId(items[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch completed evaluation runs.');
    } finally {
      setLoadingRuns(false);
    }
  };

  useEffect(() => {
    void loadRuns();
  }, []);

  const handleEvaluateGate = async () => {
    if (!baselineId || !candidateId) {
      setError('Please select both baseline and candidate evaluation runs.');
      return;
    }
    if (baselineId === candidateId) {
      setError('Baseline and candidate evaluation runs must be distinct.');
      return;
    }

    try {
      setEvaluating(true);
      setError(null);

      const metricsList = requiredMetrics
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0);

      const res = await evaluateQualityGate({
        baseline_run_id: baselineId,
        candidate_run_id: candidateId,
        thresholds: {
          minimum_pass_rate: Number(minPassRate),
          maximum_regression_percentage_points: Number(maxRegression),
          maximum_security_failures: Number(maxSecFailures),
          required_metrics: metricsList,
        },
      });

      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Quality gate evaluation failed.');
      setResult(null);
    } finally {
      setEvaluating(false);
    }
  };

  const formatRuleName = (name: string): string => {
    switch (name) {
      case 'minimum_pass_rate':
        return 'Minimum Pass Rate';
      case 'maximum_regression':
        return 'Maximum Allowed Regression';
      case 'security_regression':
        return 'Zero Security Regressions';
      case 'maximum_security_failures':
        return 'Maximum Security Failures';
      case 'required_metrics':
        return 'Required Evaluation Metrics';
      default:
        return name;
    }
  };

  return (
    <div className="quality-gate-page" style={{ padding: '0 40px 30px' }}>
      <div className="section-header-row" style={{ marginTop: '24px' }}>
        <div>
          <h2>Automated Release Quality Gate</h2>
          <p>Enforce strict release criteria to approve or reject assistant versions deterministically.</p>
        </div>
        <button
          className="btn-secondary small"
          onClick={() => void loadRuns()}
          disabled={loadingRuns}
          title="Reload runs"
        >
          <RefreshCw size={13} className={loadingRuns ? 'animate-spin' : ''} /> Refresh Runs
        </button>
      </div>

      {error && (
        <div className="error-banner">
          <AlertTriangle size={15} />
          <span>{error}</span>
          <button className="icon-button small" onClick={() => setError(null)} style={{ color: 'inherit' }}>
            ×
          </button>
        </div>
      )}

      {/* Configuration & Selection Panel */}
      <div className="panel" style={{ marginBottom: '20px' }}>
        <div style={{ marginBottom: '16px' }}>
          <h3 style={{ margin: '0 0 6px', fontSize: '13px', fontWeight: 700, color: '#222530' }}>
            1. Select Runs to Compare
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '16px', alignItems: 'center' }}>
            <div>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: '#7e838f', marginBottom: '6px' }}>
                Baseline Run (Reference)
              </label>
              {runs.length > 0 ? (
                <select
                  className="select-input"
                  style={{ width: '100%', padding: '8px' }}
                  value={baselineId}
                  onChange={(e) => setBaselineId(e.target.value)}
                >
                  <option value="">-- Select Baseline Run --</option>
                  {runs.map((r) => (
                    <option key={r.id} value={r.id}>
                      Run {r.id.slice(0, 8)}... — {r.passed_cases}/{r.total_cases} passed ({Math.round((r.passed_cases / (r.total_cases || 1)) * 100)}%)
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  className="select-input"
                  style={{ width: '100%', padding: '8px' }}
                  placeholder="Paste baseline run UUID..."
                  value={baselineId}
                  onChange={(e) => setBaselineId(e.target.value.trim())}
                />
              )}
            </div>

            <div style={{ paddingTop: '20px', color: '#a0a3ad' }}>
              <ArrowRight size={20} />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: '#7e838f', marginBottom: '6px' }}>
                Candidate Run (Proposed for Release)
              </label>
              {runs.length > 0 ? (
                <select
                  className="select-input"
                  style={{ width: '100%', padding: '8px' }}
                  value={candidateId}
                  onChange={(e) => setCandidateId(e.target.value)}
                >
                  <option value="">-- Select Candidate Run --</option>
                  {runs.map((r) => (
                    <option key={r.id} value={r.id}>
                      Run {r.id.slice(0, 8)}... — {r.passed_cases}/{r.total_cases} passed ({Math.round((r.passed_cases / (r.total_cases || 1)) * 100)}%)
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  className="select-input"
                  style={{ width: '100%', padding: '8px' }}
                  placeholder="Paste candidate run UUID..."
                  value={candidateId}
                  onChange={(e) => setCandidateId(e.target.value.trim())}
                />
              )}
            </div>
          </div>
        </div>

        <div style={{ borderTop: '1px solid #f1f2f5', paddingTop: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <Sliders size={16} style={{ color: '#6c5bdd' }} />
            <h3 style={{ margin: 0, fontSize: '13px', fontWeight: 700, color: '#222530' }}>
              2. Configure Release Thresholds
            </h3>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px', marginBottom: '14px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '10px', fontWeight: 600, color: '#7e838f', marginBottom: '4px' }}>
                Min Pass Rate (%)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                className="select-input"
                style={{ width: '100%', padding: '7px' }}
                value={minPassRate}
                onChange={(e) => setMinPassRate(Number(e.target.value))}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '10px', fontWeight: 600, color: '#7e838f', marginBottom: '4px' }}>
                Max Allowed Regression (% pts)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                className="select-input"
                style={{ width: '100%', padding: '7px' }}
                value={maxRegression}
                onChange={(e) => setMaxRegression(Number(e.target.value))}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '10px', fontWeight: 600, color: '#7e838f', marginBottom: '4px' }}>
                Max Security Failures
              </label>
              <input
                type="number"
                min="0"
                className="select-input"
                style={{ width: '100%', padding: '7px' }}
                value={maxSecFailures}
                onChange={(e) => setMaxSecFailures(Number(e.target.value))}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '10px', fontWeight: 600, color: '#7e838f', marginBottom: '4px' }}>
                Required Metrics (comma-separated)
              </label>
              <input
                type="text"
                className="select-input"
                style={{ width: '100%', padding: '7px' }}
                placeholder="e.g. expected_output, security_policy"
                value={requiredMetrics}
                onChange={(e) => setRequiredMetrics(e.target.value)}
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button
              className="primary-button"
              onClick={handleEvaluateGate}
              disabled={evaluating || !baselineId || !candidateId}
            >
              <ShieldCheck size={16} />
              {evaluating ? 'Evaluating Quality Gate...' : 'Evaluate Quality Gate'}
            </button>
          </div>
        </div>
      </div>

      {/* Decision Results */}
      {result && (
        <div style={{ display: 'grid', gap: '20px' }}>
          {/* Main Decision Banner */}
          <div
            className="panel"
            style={{
              padding: '24px',
              borderLeft: `6px solid ${result.decision === 'PASS' ? '#39a276' : '#d57269'}`,
              background: result.decision === 'PASS' ? '#f0faf5' : '#fff5f5',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                {result.decision === 'PASS' ? (
                  <CheckCircle2 size={38} style={{ color: '#39a276' }} />
                ) : (
                  <XCircle size={38} style={{ color: '#d57269' }} />
                )}
                <div>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      letterSpacing: '1px',
                      color: result.decision === 'PASS' ? '#277e59' : '#c53030',
                      textTransform: 'uppercase',
                    }}
                  >
                    QUALITY GATE DECISION
                  </span>
                  <h1
                    style={{
                      margin: '2px 0 0',
                      fontSize: '28px',
                      fontFamily: 'Manrope, sans-serif',
                      color: result.decision === 'PASS' ? '#277e59' : '#c53030',
                      letterSpacing: '-0.5px',
                    }}
                  >
                    {result.decision === 'PASS' ? 'RELEASE APPROVED' : 'RELEASE REJECTED'}
                  </h1>
                </div>
              </div>
              <span style={{ fontSize: '10px', color: '#858a96' }}>
                Evaluated at {new Date(result.evaluated_at).toLocaleTimeString()}
              </span>
            </div>

            <p style={{ margin: '8px 0 0', fontSize: '13px', fontWeight: 500, color: '#222530' }}>
              {result.explanation}
            </p>
          </div>

          {/* Failed Requirements Breakdown (if any) */}
          {result.failed_requirements.length > 0 && (
            <div className="panel" style={{ backgroundColor: '#fff8f8', borderColor: '#fed7d7', padding: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#c53030', marginBottom: '10px' }}>
                <ShieldAlert size={17} />
                <h3 style={{ margin: 0, fontSize: '13px', fontWeight: 700 }}>
                  Failed Requirements ({result.failed_requirements.length})
                </h3>
              </div>
              <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '11px', color: '#742a2a', lineHeight: 1.6 }}>
                {result.failed_requirements.map((req, idx) => (
                  <li key={idx}>
                    <strong>{req}</strong>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Rule-by-Rule Breakdown Table */}
          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>Release Rules Evaluation</h2>
                <p>Configured thresholds vs actual candidate metrics.</p>
              </div>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>RULE NAME</th>
                    <th>THRESHOLD</th>
                    <th>ACTUAL VALUE</th>
                    <th>STATUS</th>
                    <th>DETAILS</th>
                  </tr>
                </thead>
                <tbody>
                  {result.rule_details.map((rule) => (
                    <tr key={rule.rule_name}>
                      <td style={{ fontWeight: 600 }}>{formatRuleName(rule.rule_name)}</td>
                      <td>
                        <code>
                          {Array.isArray(rule.configured_threshold)
                            ? rule.configured_threshold.join(', ')
                            : `${rule.configured_threshold}`}
                        </code>
                      </td>
                      <td>
                        <code>
                          {Array.isArray(rule.actual_value)
                            ? rule.actual_value.join(', ')
                            : `${rule.actual_value}`}
                        </code>
                      </td>
                      <td>
                        <span className={`badge ${rule.passed ? 'passed' : 'failed'}`}>
                          {rule.passed ? 'PASSED' : 'FAILED'}
                        </span>
                      </td>
                      <td style={{ color: '#555a68', maxWidth: '340px', whiteSpace: 'normal' }}>
                        {rule.message}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
