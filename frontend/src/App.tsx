import { useEffect, useState } from 'react';
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  BookOpenCheck,
  ChevronDown,
  CircleHelp,
  Database,
  FlaskConical,
  Gauge,
  Layers3,
  Plus,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
} from 'lucide-react';
import { DatasetList } from './components/DatasetList';
import { DatasetDetail } from './components/DatasetDetail';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
type Health = 'checking' | 'healthy' | 'unavailable';
type NavTab = 'overview' | 'datasets';

function App() {
  const [health, setHealth] = useState<Health>('checking');
  const [navTab, setNavTab] = useState<NavTab>('overview');
  const [activeDatasetId, setActiveDatasetId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        const response = await fetch(`${API_BASE_URL.replace(/\/$/, '')}/health`, {
          signal: AbortSignal.timeout(4000),
        });
        const body = await response.json();
        if (active) setHealth(response.ok && body.status === 'healthy' ? 'healthy' : 'unavailable');
      } catch {
        if (active) setHealth('unavailable');
      }
    };
    void check();
    const timer = window.setInterval(check, 15000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const statusText = health === 'healthy' ? 'Connected' : health === 'checking' ? 'Checking' : 'Offline';

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" onClick={() => { setNavTab('overview'); setActiveDatasetId(null); }}>
          <span className="brand-mark"><ShieldCheck size={21} strokeWidth={2.2} /></span>
          <span>aegis<span className="brand-period">.</span></span>
        </a>
        <div className="workspace">
          <div className="workspace-icon">N</div>
          <div className="workspace-copy">
            <strong>Northstar AI</strong>
            <span>Workspace</span>
          </div>
          <ChevronDown size={15} />
        </div>
        <span className="nav-label">WORKSPACE</span>
        <nav className="navigation">
          <a
            className={`nav-item ${navTab === 'overview' ? 'active' : ''}`}
            href="#overview"
            onClick={(e) => {
              e.preventDefault();
              setNavTab('overview');
              setActiveDatasetId(null);
            }}
          >
            <Gauge size={17} />Overview
          </a>
          <a
            className={`nav-item ${navTab === 'datasets' ? 'active' : ''}`}
            href="#datasets"
            onClick={(e) => {
              e.preventDefault();
              setNavTab('datasets');
              setActiveDatasetId(null);
            }}
          >
            <Database size={17} />Datasets
          </a>
          <a className="nav-item" href="#runs"><FlaskConical size={17} />Test runs</a>
          <a className="nav-item" href="#"><Layers3 size={17} />Test suites</a>
          <a className="nav-item" href="#"><BarChart3 size={17} />Analytics</a>
        </nav>
        <span className="nav-label tools-label">MANAGE</span>
        <nav className="navigation">
          <a className="nav-item" href="#"><BookOpenCheck size={17} />Evaluations</a>
          <a className="nav-item" href="#"><SlidersHorizontal size={17} />Settings</a>
        </nav>
        <div className="sidebar-bottom">
          <div className="help-card">
            <div className="help-icon"><CircleHelp size={17} /></div>
            <strong>Getting started</strong>
            <p>Learn the basics of evaluating your AI systems.</p>
            <a href="#">Read the guide <ArrowUpRight size={13} /></a>
          </div>
          <div className="user-row">
            <div className="avatar">JD</div>
            <div className="user-copy">
              <strong>Jordan Davis</strong>
              <span>jordan@northstar.ai</span>
            </div>
            <ChevronDown size={15} />
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Workspace</span>
            <span className="crumb-divider">/</span>
            {navTab === 'overview' ? (
              <strong>Overview</strong>
            ) : activeDatasetId ? (
              <>
                <a
                  href="#datasets"
                  style={{ color: 'inherit', textDecoration: 'none' }}
                  onClick={(e) => {
                    e.preventDefault();
                    setActiveDatasetId(null);
                  }}
                >
                  Datasets
                </a>
                <span className="crumb-divider">/</span>
                <strong>Dataset Details</strong>
              </>
            ) : (
              <strong>Golden Datasets</strong>
            )}
          </div>
          <div className="top-actions">
            <div className={`connection ${health}`}><span className="status-dot" />API {statusText}</div>
            <button className="icon-button" aria-label="Search"><Search size={17} /></button>
            <div className="avatar top-avatar">JD</div>
          </div>
        </header>

        <div className="page-wrap">
          {navTab === 'datasets' ? (
            activeDatasetId ? (
              <DatasetDetail
                datasetId={activeDatasetId}
                onBack={() => setActiveDatasetId(null)}
              />
            ) : (
              <DatasetList
                onSelectDataset={(id) => setActiveDatasetId(id)}
              />
            )
          ) : (
            <>
              <section className="welcome-row">
                <div>
                  <div className="eyebrow"><span className="eyebrow-line" />THURSDAY, OCTOBER 24, 2024</div>
                  <h1>Good morning, Jordan <span className="wave">✳</span></h1>
                  <p className="welcome-subtitle">Here's what's happening with your AI quality today.</p>
                </div>
                <button
                  className="primary-button"
                  onClick={() => {
                    setNavTab('datasets');
                    setActiveDatasetId(null);
                  }}
                >
                  <Plus size={17} />Manage Datasets
                </button>
              </section>

              <section className="stats-grid" aria-label="Workspace metrics">
                <article className="stat-card">
                  <div className="stat-top">
                    <span className="stat-label">Total evaluations</span>
                    <span className="stat-icon purple"><Activity size={17} /></span>
                  </div>
                  <div className="stat-value">1,284</div>
                  <div className="stat-foot">
                    <span className="trend">↗ 12.8%</span>
                    <span>vs. last month</span>
                  </div>
                  <div className="sparkline purple-line"><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/></div>
                </article>
                <article className="stat-card">
                  <div className="stat-top">
                    <span className="stat-label">Quality score</span>
                    <span className="stat-icon green"><Sparkles size={17} /></span>
                  </div>
                  <div className="stat-value">94.2<span className="value-unit">%</span></div>
                  <div className="stat-foot">
                    <span className="trend">↗ 2.4%</span>
                    <span>vs. last month</span>
                  </div>
                  <div className="sparkline green-line"><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/></div>
                </article>
                <article className="stat-card">
                  <div className="stat-top">
                    <span className="stat-label">Security issues</span>
                    <span className="stat-icon orange"><ShieldCheck size={17} /></span>
                  </div>
                  <div className="stat-value">3</div>
                  <div className="stat-foot">
                    <span className="issue-pill">Needs review</span>
                    <span>across all models</span>
                  </div>
                  <div className="issue-bars"><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/></div>
                </article>
                <article className="stat-card">
                  <div className="stat-top">
                    <span className="stat-label">Active models</span>
                    <span className="stat-icon blue"><Layers3 size={17} /></span>
                  </div>
                  <div className="stat-value">8</div>
                  <div className="stat-foot">
                    <span className="neutral-pill">+2 new</span>
                    <span>this month</span>
                  </div>
                  <div className="model-dots"><i/><i/><i/><i/><i/><i/><i/><i/></div>
                </article>
              </section>

              <section className="content-grid">
                <article className="panel runs-panel" id="runs">
                  <div className="panel-heading">
                    <div>
                      <h2>Recent test runs</h2>
                      <p>Monitor the latest evaluation activity across your models.</p>
                    </div>
                    <button className="text-button" onClick={() => setNavTab('datasets')}>
                      View Datasets <ArrowUpRight size={14}/>
                    </button>
                  </div>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>RUN</th>
                          <th>MODEL</th>
                          <th>QUALITY SCORE</th>
                          <th>STATUS</th>
                          <th>WHEN</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td><span className="run-name"><span className="run-symbol violet"><FlaskConical size={15}/></span>Customer support v2</span></td>
                          <td><span className="model-name">GPT-4o</span></td>
                          <td><span className="score"><span className="score-track"><i style={{width:'96%'}}/></span>96.4%</span></td>
                          <td><span className="badge passed"><i/>Passed</span></td>
                          <td className="when">12 min ago</td>
                          <td><button className="more-button" aria-label="More options">···</button></td>
                        </tr>
                        <tr>
                          <td><span className="run-name"><span className="run-symbol teal"><ShieldCheck size={15}/></span>Prompt injection scan</span></td>
                          <td><span className="model-name">Claude 3.5</span></td>
                          <td><span className="score"><span className="score-track"><i style={{width:'87%'}}/></span>87.1%</span></td>
                          <td><span className="badge review"><i/>Review</span></td>
                          <td className="when">48 min ago</td>
                          <td><button className="more-button" aria-label="More options">···</button></td>
                        </tr>
                        <tr>
                          <td><span className="run-name"><span className="run-symbol amber"><BookOpenCheck size={15}/></span>Knowledge retrieval eval</span></td>
                          <td><span className="model-name">Gemini 1.5 Pro</span></td>
                          <td><span className="score"><span className="score-track"><i style={{width:'92%'}}/></span>92.8%</span></td>
                          <td><span className="badge passed"><i/>Passed</span></td>
                          <td className="when">2 hrs ago</td>
                          <td><button className="more-button" aria-label="More options">···</button></td>
                        </tr>
                        <tr>
                          <td><span className="run-name"><span className="run-symbol rose"><Activity size={15}/></span>Hallucination benchmark</span></td>
                          <td><span className="model-name">GPT-4o mini</span></td>
                          <td><span className="score"><span className="score-track"><i style={{width:'78%'}}/></span>78.3%</span></td>
                          <td><span className="badge failed"><i/>Failed</span></td>
                          <td className="when">Yesterday</td>
                          <td><button className="more-button" aria-label="More options">···</button></td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div className="table-footer">
                    <span>Showing 4 of 128 runs</span>
                    <div className="pagination">
                      <button disabled>←</button>
                      <button>→</button>
                    </div>
                  </div>
                </article>

                <aside className="right-column">
                  <article className="panel activity-panel">
                    <div className="panel-heading compact">
                      <div>
                        <h2>Security overview</h2>
                        <p>Last 7 days</p>
                      </div>
                      <button className="more-button" aria-label="More options">···</button>
                    </div>
                    <div className="security-score">
                      <div className="donut">
                        <div><strong>92</strong><span>/ 100</span></div>
                      </div>
                      <div className="security-copy">
                        <strong>Looking good</strong>
                        <span>Security posture</span>
                        <small><i/> +4.2% this month</small>
                      </div>
                    </div>
                    <div className="security-divider"/>
                    <div className="finding-row">
                      <span className="finding-icon high"><ShieldCheck size={15}/></span>
                      <span><strong>Prompt injection</strong><small>2 findings</small></span>
                      <b className="finding-count">2</b>
                    </div>
                    <div className="finding-row">
                      <span className="finding-icon medium"><Activity size={15}/></span>
                      <span><strong>Data leakage</strong><small>1 finding</small></span>
                      <b className="finding-count">1</b>
                    </div>
                    <button className="outline-button" onClick={() => setNavTab('datasets')}>
                      Manage Evaluation Datasets <ArrowUpRight size={14}/>
                    </button>
                  </article>

                  <article className="tip-card">
                    <div className="tip-spark"><Sparkles size={17}/></div>
                    <span className="tip-label">GOLDEN DATASET</span>
                    <h3>BharatHome Customer Support</h3>
                    <p>40 realistic multi-category evaluation test cases ready for assistant testing.</p>
                    <a
                      href="#datasets"
                      onClick={(e) => {
                        e.preventDefault();
                        setNavTab('datasets');
                      }}
                    >
                      Open dataset manager <ArrowUpRight size={13}/>
                    </a>
                    <div className="tip-decoration"/>
                  </article>
                </aside>
              </section>
            </>
          )}

          <footer className="page-footer">
            <span>© 2024 Aegis</span>
            <span>
              <i className={`footer-dot ${health}`}/>
              {health === 'healthy'
                ? 'All systems operational'
                : health === 'checking'
                ? 'Checking API status'
                : 'API unavailable'}
            </span>
            <a href="#">Documentation <ArrowUpRight size={12}/></a>
          </footer>
        </div>
      </main>
    </div>
  );
}

export default App;
