import React, { useEffect, useState } from 'react';
import {
  Activity,
  ArrowUpRight,
  Database,
  FlaskConical,
  Layers3,
  Plus,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import {
  fetchDashboardStats,
  fetchEvaluationRuns,
  fetchSecuritySummary,
} from '../api/dashboard';
import { DashboardStats, EvaluationRun, SecuritySummary } from '../types/dashboard';

interface OverviewDashboardProps {
  onNavigate: (tab: string, extra?: string) => void;
  onLaunchRunModal: () => void;
}

export const OverviewDashboard: React.FC<OverviewDashboardProps> = ({
  onNavigate,
  onLaunchRunModal,
}) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentRuns, setRecentRuns] = useState<EvaluationRun[]>([]);
  const [securitySummary, setSecuritySummary] = useState<SecuritySummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, runsData, secData] = await Promise.all([
        fetchDashboardStats(),
        fetchEvaluationRuns({ limit: 6 }),
        fetchSecuritySummary(),
      ]);
      setStats(statsData);
      setRecentRuns(runsData.items);
      setSecuritySummary(secData);
    } catch (err: any) {
      setError(err?.message || 'Failed to load dashboard statistics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const todayStr = new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date()).toUpperCase();

  const formatTimeAgo = (dateStr: string | null) => {
    if (!dateStr) return 'Just now';
    const date = new Date(dateStr);
    const diff = Math.floor((Date.now() - date.getTime()) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  return (
    <div className="dataset-list-page">
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button className="btn-secondary small" onClick={loadData}>Retry</button>
        </div>
      )}

      <section className="welcome-row">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-line" />
            {todayStr}
          </div>
          <h1>
            AI Evaluation Overview <span className="wave">✳</span>
          </h1>
          <p className="welcome-subtitle">
            Comprehensive real-time telemetry, quality scores, and security posture across your assistants.
          </p>
        </div>
        <div className="section-actions">
          <button className="btn-secondary" onClick={loadData} title="Refresh data">
            <RefreshCw size={14} className={loading ? 'spinner' : ''} />
            Refresh
          </button>
          <button className="primary-button" onClick={onLaunchRunModal}>
            <Plus size={16} />
            Execute Evaluation
          </button>
        </div>
      </section>

      {/* KPI Stats Grid */}
      <section className="stats-grid" aria-label="System Metrics">
        <article className="stat-card">
          <div className="stat-top">
            <span className="stat-label">Total evaluations</span>
            <span className="stat-icon purple">
              <Activity size={17} />
            </span>
          </div>
          <div className="stat-value">
            {stats ? stats.total_evaluations.toLocaleString() : '...'}
          </div>
          <div className="stat-foot">
            <span className="trend">
              {stats ? `${stats.completed_evaluations} completed` : ''}
            </span>
            <span>in database</span>
          </div>
          <div className="sparkline purple-line">
            <i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/>
          </div>
        </article>

        <article className="stat-card">
          <div className="stat-top">
            <span className="stat-label">Average quality pass rate</span>
            <span className="stat-icon green">
              <Sparkles size={17} />
            </span>
          </div>
          <div className="stat-value">
            {stats ? stats.avg_pass_rate : '0'}
            <span className="value-unit">%</span>
          </div>
          <div className="stat-foot">
            <span className="trend">Across all test runs</span>
          </div>
          <div className="sparkline green-line">
            <i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/>
          </div>
        </article>

        <article className="stat-card">
          <div className="stat-top">
            <span className="stat-label">Security violations</span>
            <span className="stat-icon orange">
              {stats && stats.security_issues_count > 0 ? (
                <ShieldAlert size={17} />
              ) : (
                <ShieldCheck size={17} />
              )}
            </span>
          </div>
          <div className="stat-value">
            {stats ? stats.security_issues_count : 0}
          </div>
          <div className="stat-foot">
            {stats && stats.security_issues_count > 0 ? (
              <span className="issue-pill" style={{ background: '#fff1f2', color: '#be123c' }}>
                Flagged issues
              </span>
            ) : (
              <span className="trend">Clean safety record</span>
            )}
            <span>across evaluations</span>
          </div>
          <div className="issue-bars">
            <i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/>
          </div>
        </article>

        <article className="stat-card">
          <div className="stat-top">
            <span className="stat-label">Models & Assistants</span>
            <span className="stat-icon blue">
              <Layers3 size={17} />
            </span>
          </div>
          <div className="stat-value">
            {stats ? stats.total_assistants : 0}
          </div>
          <div className="stat-foot">
            <span className="neutral-pill">
              {stats ? `${stats.total_projects} projects` : ''}
            </span>
            <span>registered</span>
          </div>
          <div className="model-dots">
            <i/><i/><i/><i/><i/><i/><i/><i/>
          </div>
        </article>
      </section>

      {/* Main Content Grid */}
      <section className="content-grid">
        <article className="panel runs-panel">
          <div className="panel-heading">
            <div>
              <h2>Recent Evaluation Runs</h2>
              <p>Live executions and test case outcomes from the evaluation pipeline.</p>
            </div>
            <button className="text-button" onClick={() => onNavigate('runs')}>
              View All Runs <ArrowUpRight size={14} />
            </button>
          </div>

          <div className="table-wrap">
            {recentRuns.length === 0 ? (
              <div className="empty-state" style={{ padding: '36px 16px' }}>
                <FlaskConical size={28} color="#a0a3ad" />
                <h3>No evaluation runs yet</h3>
                <p>Run your first evaluation against a golden dataset to see outcomes here.</p>
                <button className="primary-button" onClick={onLaunchRunModal}>
                  <Plus size={15} /> Execute First Run
                </button>
              </div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>RUN / ASSISTANT</th>
                    <th>DATASET</th>
                    <th>PASS RATE</th>
                    <th>CASES</th>
                    <th>STATUS</th>
                    <th>TIME</th>
                  </tr>
                </thead>
                <tbody>
                  {recentRuns.map((run) => {
                    const passRate = run.pass_rate ?? (run.total_cases > 0
                      ? Math.round((run.passed_cases / run.total_cases) * 1000) / 10
                      : 0);
                    return (
                      <tr
                        key={run.id}
                        style={{ cursor: 'pointer' }}
                        onClick={() => onNavigate('runs', run.id)}
                      >
                        <td>
                          <span className="run-name">
                            <span className="run-symbol violet">
                              <FlaskConical size={14} />
                            </span>
                            <div>
                              <strong>{run.assistant_name || 'Assistant'}</strong>
                              <small style={{ display: 'block', color: '#888d9a', fontSize: '9px' }}>
                                v{run.assistant_version_tag || '1.0'}
                              </small>
                            </div>
                          </span>
                        </td>
                        <td>
                          <span className="model-name">
                            {run.dataset_name || 'Dataset'}
                          </span>
                        </td>
                        <td>
                          <span className="score">
                            <span className="score-track">
                              <i
                                style={{
                                  width: `${Math.min(100, Math.max(0, passRate))}%`,
                                  background: passRate >= 80 ? '#22c55e' : passRate >= 50 ? '#f59e0b' : '#ef4444',
                                }}
                              />
                            </span>
                            {passRate}%
                          </span>
                        </td>
                        <td>
                          <span style={{ fontSize: '10px', color: '#4b5563' }}>
                            {run.passed_cases} / {run.total_cases}
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${run.status}`}>
                            <i />
                            {run.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="when">
                          {formatTimeAgo(run.completed_at || run.created_at)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          <div className="table-footer">
            <span>
              Showing {recentRuns.length} of {stats?.total_evaluations ?? recentRuns.length} runs
            </span>
            <button className="text-button" onClick={() => onNavigate('runs')}>
              Browse evaluation history <ArrowUpRight size={12} />
            </button>
          </div>
        </article>

        <aside className="right-column">
          {/* Security Posture Widget */}
          <article className="panel activity-panel">
            <div className="panel-heading compact">
              <div>
                <h2>Security Posture</h2>
                <p>Deterministic Validators</p>
              </div>
              <button
                className="text-button"
                onClick={() => onNavigate('security')}
                title="View full security report"
              >
                Inspect
              </button>
            </div>

            <div className="security-score">
              <div
                className="donut"
                style={{
                  background:
                    securitySummary && securitySummary.total_violations > 0
                      ? 'conic-gradient(#ef4444 0 25%, #fecaca 25% 100%)'
                      : 'conic-gradient(#22c55e 0 100%, #bbf7d0 100%)',
                }}
              >
                <div>
                  <strong>
                    {securitySummary && securitySummary.total_violations > 0
                      ? securitySummary.total_violations
                      : 0}
                  </strong>
                  <span>violations</span>
                </div>
              </div>
              <div className="security-copy">
                <strong>
                  {securitySummary && securitySummary.total_violations === 0
                    ? 'All Checks Passing'
                    : 'Security Flags Found'}
                </strong>
                <span>Safety & compliance</span>
                <small>
                  <i />
                  {securitySummary?.total_security_evaluations ?? 0} total security evaluations
                </small>
              </div>
            </div>

            <div className="security-divider" />

            <div className="finding-row">
              <span className="finding-icon medium">
                <ShieldCheck size={14} />
              </span>
              <span>
                <strong>PII & Privacy</strong>
                <small>Indian phones, emails, Aadhaar</small>
              </span>
              <b className="finding-count">
                {securitySummary?.category_breakdown.pii ?? 0}
              </b>
            </div>

            <div className="finding-row">
              <span className="finding-icon high">
                <ShieldAlert size={14} />
              </span>
              <span>
                <strong>Canary Leakage</strong>
                <small>System prompt token secrecy</small>
              </span>
              <b className="finding-count">
                {securitySummary?.category_breakdown.canary ?? 0}
              </b>
            </div>

            <div className="finding-row">
              <span className="finding-icon medium">
                <ShieldCheck size={14} />
              </span>
              <span>
                <strong>Forbidden & Technical Safety</strong>
                <small>Injection, shell escapes, secrets</small>
              </span>
              <b className="finding-count">
                {(securitySummary?.category_breakdown.forbidden_content ?? 0) +
                  (securitySummary?.category_breakdown.technical_safety ?? 0)}
              </b>
            </div>

            <button
              className="outline-button"
              onClick={() => onNavigate('security')}
            >
              Open Security Dashboard <ArrowUpRight size={13} />
            </button>
          </article>

          {/* Quick Dataset Card */}
          <article className="tip-card">
            <div className="tip-spark">
              <Database size={16} />
            </div>
            <span className="tip-label">GOLDEN DATASETS</span>
            <h3>Manage Test Suites</h3>
            <p>
              {stats?.total_datasets ?? 0} datasets configured with {stats?.total_test_cases ?? 0} test cases ready for automated evaluation.
            </p>
            <a
              href="#datasets"
              onClick={(e) => {
                e.preventDefault();
                onNavigate('datasets');
              }}
            >
              Open dataset manager <ArrowUpRight size={13} />
            </a>
            <div className="tip-decoration" />
          </article>
        </aside>
      </section>
    </div>
  );
};

