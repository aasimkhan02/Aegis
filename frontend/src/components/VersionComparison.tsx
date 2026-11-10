import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowDown,
  ArrowRight,
  ArrowUp,
  CheckCircle2,
  Clock,
  Gauge,
  Layers3,
  Minus,
  RefreshCw,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { compareEvaluationRuns, fetchCompletedRuns } from '../api/comparison';
import { ComparisonResponse, EvaluationRunSummary } from '../types/comparison';

export const VersionComparison: React.FC = () => {
  const [runs, setRuns] = useState<EvaluationRunSummary[]>([]);
  const [baselineId, setBaselineId] = useState<string>('');
  const [candidateId, setCandidateId] = useState<string>('');
  const [loadingRuns, setLoadingRuns] = useState<boolean>(false);
  const [comparing, setComparing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ComparisonResponse | null>(null);

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

  const handleCompare = async () => {
    if (!baselineId || !candidateId) {
      setError('Please select both a baseline and a candidate evaluation run.');
      return;
    }
    if (baselineId === candidateId) {
      setError('Baseline and candidate evaluation runs must be distinct.');
      return;
    }

    try {
      setComparing(true);
      setError(null);
      const res = await compareEvaluationRuns(baselineId, candidateId);
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Evaluation comparison failed.');
      setResult(null);
    } finally {
      setComparing(false);
    }
  };

  const getVerdictBadge = (verdict: string) => {
    switch (verdict) {
      case 'improved':
        return (
          <span className="badge passed" style={{ fontSize: '12px', padding: '6px 12px' }}>
            <TrendingUp size={15} /> Improved
          </span>
        );
      case 'regressed':
        return (
          <span className="badge failed" style={{ fontSize: '12px', padding: '6px 12px' }}>
            <TrendingDown size={15} /> Regressed
          </span>
        );
      default:
        return (
          <span className="badge review" style={{ fontSize: '12px', padding: '6px 12px' }}>
            <Minus size={15} /> Unchanged
          </span>
        );
    }
  };

  return (
    <div className="version-comparison-page" style={{ padding: '0 40px 30px' }}>
      <div className="section-header-row" style={{ marginTop: '24px' }}>
        <div>
          <h2>Assistant Version Comparison</h2>
          <p>Compare two completed evaluation runs to detect performance changes, metric shifts, and regressions.</p>
        </div>
        <button
          className="btn-secondary small"
          onClick={() => void loadRuns()}
          disabled={loadingRuns}
          title="Reload completed runs"
        >
          <RefreshCw size={13} className={loadingRuns ? 'animate-spin' : ''} /> Refresh Runs
        </button>
      </div>

      {error && (
        <div className="error-banner">
          <AlertTriangle size={15} />
          <span>{error}</span>
          <button
            className="icon-button small"
            onClick={() => setError(null)}
            style={{ color: 'inherit' }}
          >
            ×
          </button>
        </div>
      )}

      {/* Run Selection Panel */}
      <div className="panel" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr auto', gap: '16px', alignItems: 'center' }}>
          <div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: '#7e838f', marginBottom: '6px' }}>
              Baseline Version (Reference)
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
              Candidate Version (Newer)
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

          <div style={{ paddingTop: '20px' }}>
            <button
              className="primary-button"
              onClick={handleCompare}
              disabled={comparing || !baselineId || !candidateId}
            >
              <Layers3 size={15} />
              {comparing ? 'Comparing...' : 'Compare Versions'}
            </button>
          </div>
        </div>
      </div>

      {result && (
        <div className="comparison-results" style={{ display: 'grid', gap: '20px' }}>
          {/* Verdict Banner */}
          <div
            className="panel"
            style={{
              padding: '20px',
              borderLeft: `4px solid ${
                result.verdict === 'improved' ? '#39a276' : result.verdict === 'regressed' ? '#d57269' : '#6c5bdd'
              }`,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '12px', fontWeight: 700, letterSpacing: '0.5px', color: '#7e838f' }}>
                  OVERALL VERDICT
                </span>
                {getVerdictBadge(result.verdict)}
              </div>
              <span style={{ fontSize: '10px', color: '#a0a3ad' }}>
                Compared at {new Date(result.compared_at).toLocaleTimeString()}
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '14px', color: '#222530', fontWeight: 500 }}>
              {result.verdict_explanation}
            </p>
          </div>

          {/* Performance Overview Grid */}
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-top">
                <span className="stat-label">BASELINE PASS RATE</span>
                <span className="stat-icon purple"><Gauge size={16} /></span>
              </div>
              <div className="stat-value">{result.overall.baseline.pass_rate}%</div>
              <div className="stat-foot">
                {result.overall.baseline.passed_cases}/{result.overall.baseline.total_cases} cases passed
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-top">
                <span className="stat-label">CANDIDATE PASS RATE</span>
                <span className="stat-icon purple"><Gauge size={16} /></span>
              </div>
              <div className="stat-value">{result.overall.candidate.pass_rate}%</div>
              <div className="stat-foot">
                {result.overall.candidate.passed_cases}/{result.overall.candidate.total_cases} cases passed
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-top">
                <span className="stat-label">PASS RATE DELTA</span>
                <span className={`stat-icon ${result.overall.pass_rate_delta >= 0 ? 'green' : 'orange'}`}>
                  {result.overall.pass_rate_delta >= 0 ? <ArrowUp size={16} /> : <ArrowDown size={16} />}
                </span>
              </div>
              <div className="stat-value" style={{ color: result.overall.pass_rate_delta >= 0 ? '#35a67c' : '#d57269' }}>
                {result.overall.pass_rate_delta >= 0 ? `+${result.overall.pass_rate_delta}%` : `${result.overall.pass_rate_delta}%`}
              </div>
              <div className="stat-foot">
                Percentage points shift
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-top">
                <span className="stat-label">AVERAGE LATENCY</span>
                <span className="stat-icon blue"><Clock size={16} /></span>
              </div>
              <div className="stat-value">
                {result.latency.candidate_average_ms !== null ? `${result.latency.candidate_average_ms}ms` : 'N/A'}
              </div>
              <div className="stat-foot">
                {result.latency.delta_ms !== null && result.latency.delta_ms !== undefined && (
                  <span>
                    {result.latency.delta_ms > 0 ? `+${result.latency.delta_ms}ms` : `${result.latency.delta_ms}ms`} (
                    {result.latency.percent_change}%)
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Security Regressions Banner */}
          {result.regressions.security_regressions.length > 0 && (
            <div
              className="panel"
              style={{
                backgroundColor: '#fff5f5',
                borderColor: '#fed7d7',
                padding: '16px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '9px', color: '#c53030', marginBottom: '8px' }}>
                <ShieldAlert size={18} />
                <strong style={{ fontSize: '13px' }}>
                  {result.regressions.security_regressions.length} Critical Security Regression(s) Detected!
                </strong>
              </div>
              <p style={{ fontSize: '11px', color: '#742a2a', margin: '0 0 10px' }}>
                The candidate version failed security or adversarial safety checks that previously passed in baseline.
              </p>
              <div style={{ display: 'grid', gap: '6px' }}>
                {result.regressions.security_regressions.map((s) => (
                  <div
                    key={s.test_case_id}
                    style={{
                      padding: '8px 12px',
                      borderRadius: '6px',
                      background: '#fff',
                      border: '1px solid #feb2b2',
                      fontSize: '11px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <span>
                      <strong>{s.name}</strong> — {s.error_message || 'Safety policy check failed'}
                    </span>
                    <span className="badge failed">Security Regression</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metric Differences Table */}
          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>Metric Score Analysis</h2>
                <p>Mean scores across applicable test cases for both assistant versions.</p>
              </div>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>METRIC NAME</th>
                    <th>BASELINE SCORE</th>
                    <th>CANDIDATE SCORE</th>
                    <th>DIFFERENCE</th>
                    <th>STATUS</th>
                  </tr>
                </thead>
                <tbody>
                  {result.metrics.metrics.map((m) => (
                    <tr key={m.metric_name}>
                      <td style={{ fontWeight: 600 }}>{m.metric_name}</td>
                      <td>{m.baseline_score !== null && m.baseline_score !== undefined ? m.baseline_score : <span style={{ color: '#a0a3ad' }}>N/A</span>}</td>
                      <td>{m.candidate_score !== null && m.candidate_score !== undefined ? m.candidate_score : <span style={{ color: '#a0a3ad' }}>N/A</span>}</td>
                      <td style={{ fontWeight: 600, color: (m.score_delta || 0) > 0 ? '#39a276' : (m.score_delta || 0) < 0 ? '#d57269' : 'inherit' }}>
                        {m.score_delta !== null && m.score_delta !== undefined ? (m.score_delta > 0 ? `+${m.score_delta}` : `${m.score_delta}`) : '-'}
                      </td>
                      <td>
                        <span className={`badge ${m.status === 'improved' ? 'passed' : m.status === 'degraded' ? 'failed' : 'review'}`}>
                          {m.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Regressed and Improved Cases Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            {/* Regressions */}
            <div className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Regressed Test Cases ({result.regressions.regressed_cases.length})</h2>
                  <p>Passed in baseline, but failed in candidate.</p>
                </div>
              </div>
              {result.regressions.regressed_cases.length === 0 ? (
                <div style={{ padding: '20px', textAlign: 'center', color: '#858a96', fontSize: '11px' }}>
                  <CheckCircle2 size={24} style={{ color: '#39a276', margin: '0 auto 6px', display: 'block' }} />
                  Zero regressions detected.
                </div>
              ) : (
                <div style={{ display: 'grid', gap: '8px' }}>
                  {result.regressions.regressed_cases.map((c) => (
                    <div
                      key={c.test_case_id}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '7px',
                        border: '1px solid #f1f2f5',
                        background: '#fafbfe',
                        fontSize: '11px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <strong>{c.name}</strong>
                        {c.is_security && <span className="badge failed">Security</span>}
                      </div>
                      <div style={{ fontSize: '10px', color: '#a0a3ad' }}>
                        Baseline: <span style={{ color: '#39a276' }}>passed</span> → Candidate: <span style={{ color: '#d57269' }}>{c.candidate_status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Improvements */}
            <div className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Fixed / Improved Cases ({result.regressions.improved_cases.length})</h2>
                  <p>Failed in baseline, but resolved in candidate.</p>
                </div>
              </div>
              {result.regressions.improved_cases.length === 0 ? (
                <div style={{ padding: '20px', textAlign: 'center', color: '#858a96', fontSize: '11px' }}>
                  No previously failing cases were fixed.
                </div>
              ) : (
                <div style={{ display: 'grid', gap: '8px' }}>
                  {result.regressions.improved_cases.map((c) => (
                    <div
                      key={c.test_case_id}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '7px',
                        border: '1px solid #f1f2f5',
                        background: '#fafbfe',
                        fontSize: '11px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <strong>{c.name}</strong>
                        <span className="badge passed">Fixed</span>
                      </div>
                      <div style={{ fontSize: '10px', color: '#a0a3ad' }}>
                        Baseline: <span style={{ color: '#d57269' }}>{c.baseline_status}</span> → Candidate: <span style={{ color: '#39a276' }}>passed</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
