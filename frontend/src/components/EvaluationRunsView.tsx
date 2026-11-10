import React, { useEffect, useState } from 'react';
import {
  FlaskConical,
  Plus,
  RefreshCw,
  Search,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  X,
  Play,
  Scale,
  ShieldCheck,
  ChevronRight,
} from 'lucide-react';
import {
  fetchEvaluationRuns,
  startEvaluationRun,
  fetchCaseResults,
  fetchAssistants,
} from '../api/dashboard';
import { fetchDatasets } from '../api/datasets';
import {
  EvaluationRun,
  CaseResult,
  AssistantVersion,
} from '../types/dashboard';
import { Dataset } from '../types/dataset';

interface EvaluationRunsViewProps {
  initialRunId?: string | null;
  onNavigateToCompare?: (runId: string) => void;
  onNavigateToQualityGate?: (runId: string) => void;
  onRequestNewRunModal?: boolean;
  onModalClosed?: () => void;
}

export const EvaluationRunsView: React.FC<EvaluationRunsViewProps> = ({
  initialRunId,
  onNavigateToCompare,
  onNavigateToQualityGate,
  onRequestNewRunModal,
  onModalClosed,
}) => {
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [totalRuns, setTotalRuns] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // Execution Modal
  const [showRunModal, setShowRunModal] = useState<boolean>(Boolean(onRequestNewRunModal));
  const [assistants, setAssistants] = useState<AssistantVersion[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedAssistantId, setSelectedAssistantId] = useState<string>('');
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [concurrency, setConcurrency] = useState<number>(2);
  const [failFast, setFailFast] = useState<boolean>(false);
  const [enableSecurity, setEnableSecurity] = useState<boolean>(true);
  const [canaryCheck, setCanaryCheck] = useState<boolean>(true);
  const [piiCheck, setPiiCheck] = useState<boolean>(true);
  const [forbiddenCheck, setForbiddenCheck] = useState<boolean>(true);
  const [safetyCheck, setSafetyCheck] = useState<boolean>(true);
  const [policyCheck, setPolicyCheck] = useState<boolean>(true);
  const [submittingRun, setSubmittingRun] = useState<boolean>(false);

  // Run Details Drawer
  const [selectedRun, setSelectedRun] = useState<EvaluationRun | null>(null);
  const [caseResults, setCaseResults] = useState<CaseResult[]>([]);
  const [loadingCases, setLoadingCases] = useState<boolean>(false);
  const [caseStatusFilter, setCaseStatusFilter] = useState<string>('');

  const loadRuns = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEvaluationRuns({
        status: statusFilter || undefined,
        limit: 100,
      });
      setRuns(data.items);
      setTotalRuns(data.total);

      // If initialRunId was passed, auto-select it
      if (initialRunId) {
        const found = data.items.find((r) => r.id === initialRunId);
        if (found) {
          openRunDrawer(found);
        }
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load evaluation runs.');
    } finally {
      setLoading(false);
    }
  };

  const loadPrerequisites = async () => {
    try {
      const [assData, dsData] = await Promise.all([
        fetchAssistants(undefined, 100, 0),
        fetchDatasets(),
      ]);
      setAssistants(assData.items);
      setDatasets(dsData);
      if (assData.items.length > 0 && !selectedAssistantId) {
        setSelectedAssistantId(assData.items[0].id);
      }
      if (dsData.length > 0 && !selectedDatasetId) {
        setSelectedDatasetId(dsData[0].id);
      }
    } catch (e) {
      // non-fatal
    }
  };

  useEffect(() => {
    void loadRuns();
    void loadPrerequisites();
  }, [statusFilter]);

  useEffect(() => {
    if (onRequestNewRunModal) {
      setShowRunModal(true);
    }
  }, [onRequestNewRunModal]);

  const openRunDrawer = async (run: EvaluationRun) => {
    setSelectedRun(run);
    setLoadingCases(true);
    try {
      const res = await fetchCaseResults(run.id, caseStatusFilter || undefined, 100, 0);
      setCaseResults(res.items);
    } catch {
      setCaseResults([]);
    } finally {
      setLoadingCases(false);
    }
  };

  const reloadCases = async (runId: string, status?: string) => {
    setLoadingCases(true);
    try {
      const res = await fetchCaseResults(runId, status || undefined, 100, 0);
      setCaseResults(res.items);
    } catch {
      setCaseResults([]);
    } finally {
      setLoadingCases(false);
    }
  };

  const handleStartEvaluation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAssistantId || !selectedDatasetId) return;
    setSubmittingRun(true);
    try {
      const secValidators: string[] = [];
      if (canaryCheck) secValidators.push('security_canary');
      if (piiCheck) secValidators.push('pii_detection');
      if (forbiddenCheck) secValidators.push('forbidden_content');
      if (safetyCheck) secValidators.push('technical_safety');
      if (policyCheck) secValidators.push('policy_compliance');

      const newRun = await startEvaluationRun({
        assistant_version_id: selectedAssistantId,
        dataset_id: selectedDatasetId,
        config: {
          max_concurrency: concurrency,
          fail_fast: failFast,
          enable_security: enableSecurity,
          security_validators: secValidators,
        },
      });

      setShowRunModal(false);
      if (onModalClosed) onModalClosed();
      await loadRuns();
      openRunDrawer(newRun);
    } catch (err: any) {
      setError(err?.message || 'Failed to start evaluation run.');
    } finally {
      setSubmittingRun(false);
    }
  };

  const filteredRuns = runs.filter((r) => {
    const q = search.toLowerCase();
    return (
      r.id.toLowerCase().includes(q) ||
      (r.assistant_name && r.assistant_name.toLowerCase().includes(q)) ||
      (r.dataset_name && r.dataset_name.toLowerCase().includes(q)) ||
      (r.project_name && r.project_name.toLowerCase().includes(q))
    );
  });

  return (
    <div className="dataset-list-page">
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button className="btn-secondary small" onClick={loadRuns}>Retry</button>
        </div>
      )}

      <div className="section-header-row">
        <div>
          <h2>Evaluation Test Runs</h2>
          <p>Inspect test runs, case pass rates, latency benchmarks, and safety evaluations.</p>
        </div>
        <div className="section-actions">
          <button className="btn-secondary" onClick={loadRuns}>
            <RefreshCw size={14} className={loading ? 'spinner' : ''} />
            Refresh
          </button>
          <button
            className="primary-button"
            onClick={() => {
              void loadPrerequisites();
              setShowRunModal(true);
            }}
          >
            <Play size={15} />
            Execute Run
          </button>
        </div>
      </div>

      <div className="filter-panel">
        <div className="filter-row">
          <div className="search-box" style={{ flex: 1, minWidth: '240px' }}>
            <Search size={15} />
            <input
              type="text"
              placeholder="Search by run UUID, assistant, project, or dataset..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="filter-group">
            <span className="filter-label">Status:</span>
            <select
              className="select-input"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Statuses ({totalRuns})</option>
              <option value="completed">Completed</option>
              <option value="running">Running</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>
      </div>

      {loading && runs.length === 0 ? (
        <div className="dataset-loading-state">
          <div className="spinner" />
          <span>Loading evaluation runs...</span>
        </div>
      ) : filteredRuns.length === 0 ? (
        <div className="empty-state large">
          <FlaskConical size={32} color="#a0a3ad" />
          <h3>No evaluation runs found</h3>
          <p>
            {search || statusFilter
              ? 'No runs match your current search and filter settings.'
              : 'Launch your first automated evaluation against a golden dataset.'}
          </p>
          <button
            className="primary-button"
            onClick={() => {
              void loadPrerequisites();
              setShowRunModal(true);
            }}
          >
            <Plus size={15} /> Execute Run
          </button>
        </div>
      ) : (
        <div className="test-cases-table-wrap">
          <table className="test-cases-table">
            <thead>
              <tr>
                <th>RUN ID</th>
                <th>ASSISTANT & VERSION</th>
                <th>DATASET</th>
                <th>PASS RATE</th>
                <th>CASES</th>
                <th>STATUS</th>
                <th>STARTED / COMPLETED</th>
                <th style={{ textAlign: 'right' }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {filteredRuns.map((run) => {
                const passRate =
                  run.pass_rate ??
                  (run.total_cases > 0
                    ? Math.round((run.passed_cases / run.total_cases) * 1000) / 10
                    : 0);
                return (
                  <tr
                    key={run.id}
                    style={{ cursor: 'pointer' }}
                    onClick={() => openRunDrawer(run)}
                  >
                    <td>
                      <span style={{ fontFamily: 'monospace', fontSize: '10px', color: '#6366f1', fontWeight: 600 }}>
                        {run.id.slice(0, 8)}...
                      </span>
                    </td>
                    <td>
                      <strong>{run.assistant_name || 'Assistant'}</strong>
                      <span className="case-count-pill" style={{ marginLeft: '6px' }}>
                        v{run.assistant_version_tag || '1.0'}
                      </span>
                    </td>
                    <td>
                      <span style={{ color: '#4b5563' }}>{run.dataset_name || 'Dataset'}</span>
                    </td>
                    <td>
                      <div className="score">
                        <div className="score-track" style={{ width: '45px' }}>
                          <i
                            style={{
                              width: `${Math.min(100, Math.max(0, passRate))}%`,
                              background: passRate >= 80 ? '#22c55e' : passRate >= 50 ? '#f59e0b' : '#ef4444',
                            }}
                          />
                        </div>
                        <span style={{ fontWeight: 600 }}>{passRate}%</span>
                      </div>
                    </td>
                    <td>
                      <span style={{ fontSize: '11px', color: '#374151' }}>
                        {run.passed_cases} / {run.total_cases}
                      </span>
                      {run.failed_cases > 0 && (
                        <span style={{ marginLeft: '6px', color: '#dc2626', fontSize: '10px', fontWeight: 600 }}>
                          ({run.failed_cases} fail)
                        </span>
                      )}
                    </td>
                    <td>
                      <span className={`badge ${run.status}`}>
                        <i />
                        {run.status.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ fontSize: '10px', color: '#6b7280' }}>
                      {run.completed_at
                        ? new Date(run.completed_at).toLocaleString([], {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : new Date(run.created_at).toLocaleString([], {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="text-link-button"
                        onClick={(e) => {
                          e.stopPropagation();
                          openRunDrawer(run);
                        }}
                      >
                        Inspect <ChevronRight size={13} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Execute Run Modal */}
      {showRunModal && (
        <div
          className="modal-backdrop"
          onClick={() => {
            setShowRunModal(false);
            if (onModalClosed) onModalClosed();
          }}
        >
          <div className="modal-content medium" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Execute Evaluation Run</h3>
              <button
                className="icon-button"
                onClick={() => {
                  setShowRunModal(false);
                  if (onModalClosed) onModalClosed();
                }}
              >
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleStartEvaluation} className="modal-form">
              <div className="form-group">
                <label>Assistant Version *</label>
                <select
                  className="select-input"
                  style={{ width: '100%', padding: '8px 11px' }}
                  required
                  value={selectedAssistantId}
                  onChange={(e) => setSelectedAssistantId(e.target.value)}
                >
                  {assistants.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name} (v{a.version}) - {a.provider}/{a.model}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Golden Dataset *</label>
                <select
                  className="select-input"
                  style={{ width: '100%', padding: '8px 11px' }}
                  required
                  value={selectedDatasetId}
                  onChange={(e) => setSelectedDatasetId(e.target.value)}
                >
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.test_case_count} cases)
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label>Max Concurrency (workers)</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={concurrency}
                    onChange={(e) => setConcurrency(parseInt(e.target.value) || 1)}
                  />
                </div>
                <div className="form-group flex-1" style={{ justifyContent: 'center' }}>
                  <label>Execution Policy</label>
                  <div className="form-checkbox" style={{ marginTop: '6px' }}>
                    <label>
                      <input
                        type="checkbox"
                        checked={failFast}
                        onChange={(e) => setFailFast(e.target.checked)}
                      />
                      Fail Fast (halt on first error)
                    </label>
                  </div>
                </div>
              </div>

              <div className="form-group" style={{ borderTop: '1px solid #f1f2f5', paddingTop: '10px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <ShieldCheck size={14} color="#6366f1" />
                  Deterministic Security Validators
                </label>
                <div className="form-checkbox">
                  <label>
                    <input
                      type="checkbox"
                      checked={enableSecurity}
                      onChange={(e) => setEnableSecurity(e.target.checked)}
                    />
                    Enable Security Checks for this Run
                  </label>
                </div>

                {enableSecurity && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', marginTop: '8px', paddingLeft: '22px' }}>
                    <label style={{ fontSize: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <input
                        type="checkbox"
                        checked={canaryCheck}
                        onChange={(e) => setCanaryCheck(e.target.checked)}
                      />
                      Canary Token Leakage
                    </label>
                    <label style={{ fontSize: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <input
                        type="checkbox"
                        checked={piiCheck}
                        onChange={(e) => setPiiCheck(e.target.checked)}
                      />
                      PII (Phone, Email, Aadhaar)
                    </label>
                    <label style={{ fontSize: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <input
                        type="checkbox"
                        checked={forbiddenCheck}
                        onChange={(e) => setForbiddenCheck(e.target.checked)}
                      />
                      Forbidden Content & Escapes
                    </label>
                    <label style={{ fontSize: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <input
                        type="checkbox"
                        checked={safetyCheck}
                        onChange={(e) => setSafetyCheck(e.target.checked)}
                      />
                      Technical Safety & Secrets
                    </label>
                    <label style={{ fontSize: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <input
                        type="checkbox"
                        checked={policyCheck}
                        onChange={(e) => setPolicyCheck(e.target.checked)}
                      />
                      Policy Compliance
                    </label>
                  </div>
                )}
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setShowRunModal(false);
                    if (onModalClosed) onModalClosed();
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={submittingRun || !selectedAssistantId || !selectedDatasetId}
                >
                  {submittingRun ? 'Launching Run...' : 'Start Evaluation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Run Inspector Drawer */}
      {selectedRun && (
        <div className="drawer-backdrop" onClick={() => setSelectedRun(null)}>
          <div className="drawer-content" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FlaskConical size={18} color="#6366f1" />
                  <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>
                    Run Details: {selectedRun.id.slice(0, 8)}...
                  </h3>
                  <span className={`badge ${selectedRun.status}`}>
                    {selectedRun.status.toUpperCase()}
                  </span>
                </div>
                <span style={{ fontSize: '10px', color: '#6b7280' }}>
                  {selectedRun.assistant_name || 'Assistant'} v{selectedRun.assistant_version_tag || '1.0'} on {selectedRun.dataset_name || 'Dataset'}
                </span>
              </div>
              <button className="icon-button" onClick={() => setSelectedRun(null)}>
                <X size={18} />
              </button>
            </div>

            <div className="drawer-body">
              {/* Quick Actions Bar */}
              <div style={{ display: 'flex', gap: '8px', paddingBottom: '12px', borderBottom: '1px solid #f1f2f5' }}>
                {onNavigateToCompare && (
                  <button
                    className="btn-secondary small"
                    onClick={() => onNavigateToCompare(selectedRun.id)}
                  >
                    <Scale size={13} /> Compare Run
                  </button>
                )}
                {onNavigateToQualityGate && (
                  <button
                    className="btn-secondary small"
                    onClick={() => onNavigateToQualityGate(selectedRun.id)}
                  >
                    <ShieldCheck size={13} /> Release Quality Gate
                  </button>
                )}
              </div>

              {/* Stats Summary */}
              <div className="grid-3col">
                <div className="security-cat-card">
                  <span className="cat-title">Pass Rate</span>
                  <div className="cat-count">
                    {selectedRun.pass_rate ??
                      (selectedRun.total_cases > 0
                        ? Math.round((selectedRun.passed_cases / selectedRun.total_cases) * 1000) / 10
                        : 0)}%
                  </div>
                  <span className="cat-status cat-clean">
                    {selectedRun.passed_cases} passed of {selectedRun.total_cases}
                  </span>
                </div>
                <div className="security-cat-card">
                  <span className="cat-title">Failed Cases</span>
                  <div className="cat-count" style={{ color: selectedRun.failed_cases > 0 ? '#dc2626' : '#22c55e' }}>
                    {selectedRun.failed_cases}
                  </div>
                  <span className="cat-status" style={{ color: selectedRun.failed_cases > 0 ? '#dc2626' : '#22c55e' }}>
                    {selectedRun.failed_cases === 0 ? 'Zero failures' : 'Issues detected'}
                  </span>
                </div>
                <div className="security-cat-card">
                  <span className="cat-title">Execution Mode</span>
                  <div className="cat-count" style={{ fontSize: '15px', paddingTop: '5px' }}>
                    {selectedRun.config?.fail_fast ? 'Fail Fast' : 'Full Suite'}
                  </div>
                  <span className="cat-status text-gray">
                    Workers: {selectedRun.config?.max_concurrency ?? 1}
                  </span>
                </div>
              </div>

              {/* Case Results List */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '14px 0 8px' }}>
                  <h4 style={{ margin: 0, fontSize: '13px', fontWeight: 700 }}>
                    Case Results ({caseResults.length})
                  </h4>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <select
                      className="select-input"
                      value={caseStatusFilter}
                      onChange={(e) => {
                        setCaseStatusFilter(e.target.value);
                        void reloadCases(selectedRun.id, e.target.value);
                      }}
                    >
                      <option value="">All Cases</option>
                      <option value="passed">Passed Only</option>
                      <option value="failed">Failed Only</option>
                      <option value="error">Errors Only</option>
                    </select>
                  </div>
                </div>

                {loadingCases ? (
                  <div className="dataset-loading-state" style={{ padding: '30px 0' }}>
                    <div className="spinner" />
                    <span>Loading case results...</span>
                  </div>
                ) : caseResults.length === 0 ? (
                  <div className="empty-state" style={{ padding: '24px 12px' }}>
                    <p>No case results available for this filter.</p>
                  </div>
                ) : (
                  <div style={{ display: 'grid', gap: '10px' }}>
                    {caseResults.map((c) => (
                      <div
                        key={c.id}
                        style={{
                          border: '1px solid #eceef2',
                          borderRadius: '8px',
                          padding: '12px',
                          background: c.status === 'passed' ? '#fafbfe' : '#fff7f7',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {c.status === 'passed' ? (
                              <CheckCircle2 size={16} color="#16a34a" />
                            ) : c.status === 'failed' ? (
                              <XCircle size={16} color="#dc2626" />
                            ) : (
                              <AlertTriangle size={16} color="#d97706" />
                            )}
                            <strong style={{ fontSize: '11px', color: '#1f2937' }}>
                              Case {c.test_case_id.slice(0, 8)}...
                            </strong>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '10px', color: '#6b7280' }}>
                            <Clock size={11} />
                            <span>{c.latency_ms} ms</span>
                          </div>
                        </div>

                        {/* Input & Output Snapshot */}
                        <div style={{ display: 'grid', gap: '6px', marginBottom: '10px' }}>
                          <div style={{ fontSize: '10px' }}>
                            <span style={{ fontWeight: 600, color: '#4b5563' }}>Input: </span>
                            <span style={{ color: '#1f2937' }}>
                              {typeof c.input_snapshot === 'string'
                                ? c.input_snapshot
                                : JSON.stringify(c.input_snapshot)}
                            </span>
                          </div>
                          {c.output && (
                            <div style={{ fontSize: '10px' }}>
                              <span style={{ fontWeight: 600, color: '#4b5563' }}>Output: </span>
                              <span style={{ color: '#1f2937' }}>
                                {typeof c.output === 'string'
                                  ? c.output
                                  : JSON.stringify(c.output)}
                              </span>
                            </div>
                          )}
                          {c.error_message && (
                            <div style={{ fontSize: '10px', color: '#dc2626', background: '#fee2e2', padding: '6px 8px', borderRadius: '4px' }}>
                              Error: {c.error_message}
                            </div>
                          )}
                        </div>

                        {/* Evaluator Metric Results */}
                        {c.metric_results && c.metric_results.length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', borderTop: '1px solid #f1f2f5', paddingTop: '8px' }}>
                            {c.metric_results.map((m) => (
                              <span
                                key={m.id}
                                className={`metric-pill ${m.passed ? 'pass' : 'fail'}`}
                                title={JSON.stringify(m.details)}
                              >
                                {m.metric_name}: {m.score} (th: {m.threshold})
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
