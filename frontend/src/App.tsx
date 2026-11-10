import { useEffect, useState } from 'react';
import {
  ChevronDown,
  Database,
  FlaskConical,
  FolderGit2,
  Gauge,
  Layers3,
  ShieldAlert,
  ShieldCheck,
  SlidersHorizontal,
  Cpu,
  ArrowUpRight,
  CircleHelp,
} from 'lucide-react';
import { DatasetList } from './components/DatasetList';
import { DatasetDetail } from './components/DatasetDetail';
import { VersionComparison } from './components/VersionComparison';
import { ReleaseQualityGate } from './components/ReleaseQualityGate';
import { OverviewDashboard } from './components/OverviewDashboard';
import { ProjectsList } from './components/ProjectsList';
import { AssistantsList } from './components/AssistantsList';
import { EvaluationRunsView } from './components/EvaluationRunsView';
import { SecurityDashboard } from './components/SecurityDashboard';
import { SettingsView } from './components/SettingsView';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
type Health = 'checking' | 'healthy' | 'unavailable';
export type NavTab =
  | 'overview'
  | 'projects'
  | 'assistants'
  | 'datasets'
  | 'runs'
  | 'security'
  | 'compare'
  | 'quality_gate'
  | 'settings';

function App() {
  const [health, setHealth] = useState<Health>('checking');
  const [navTab, setNavTab] = useState<NavTab>('overview');
  const [activeDatasetId, setActiveDatasetId] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [openExecuteRunModal, setOpenExecuteRunModal] = useState<boolean>(false);

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

  const navigateTo = (tab: string, extraId?: string) => {
    setActiveDatasetId(null);
    if (tab === 'datasets') {
      if (extraId) setActiveDatasetId(extraId);
      setNavTab('datasets');
    } else if (tab === 'runs') {
      if (extraId) setSelectedRunId(extraId);
      setNavTab('runs');
    } else if (tab === 'assistants') {
      if (extraId) setSelectedProjectId(extraId);
      setNavTab('assistants');
    } else if (tab === 'compare') {
      setNavTab('compare');
    } else if (tab === 'quality_gate') {
      setNavTab('quality_gate');
    } else if (tab === 'security') {
      setNavTab('security');
    } else if (tab === 'projects') {
      setNavTab('projects');
    } else if (tab === 'settings') {
      setNavTab('settings');
    } else {
      setNavTab('overview');
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigateTo('overview');
          }}
        >
          <span className="brand-mark"><ShieldCheck size={21} strokeWidth={2.2} /></span>
          <span>aegis<span className="brand-period">.</span></span>
        </a>

        <div className="workspace">
          <div className="workspace-icon">A</div>
          <div className="workspace-copy">
            <strong>Aegis Platform</strong>
            <span>Enterprise Quality</span>
          </div>
          <ChevronDown size={15} />
        </div>

        {/* WORKSPACE GROUP */}
        <span className="nav-label">WORKSPACE</span>
        <nav className="navigation">
          <a
            className={`nav-item ${navTab === 'overview' ? 'active' : ''}`}
            href="#overview"
            onClick={(e) => {
              e.preventDefault();
              navigateTo('overview');
            }}
          >
            <Gauge size={17} />Overview
          </a>
          <a
            className={`nav-item ${navTab === 'projects' ? 'active' : ''}`}
            href="#projects"
            onClick={(e) => {
              e.preventDefault();
              navigateTo('projects');
            }}
          >
            <FolderGit2 size={17} />Projects
          </a>
          <a
            className={`nav-item ${navTab === 'assistants' ? 'active' : ''}`}
            href="#assistants"
            onClick={(e) => {
              e.preventDefault();
              navigateTo('assistants');
            }}
          >
            <Cpu size={17} />Assistants
          </a>
          <a
            className={`nav-item ${navTab === 'datasets' ? 'active' : ''}`}
            href="#datasets"
            onClick={(e) => {
              e.preventDefault();
              navigateTo('datasets');
            }}
          >
            <Database size={17} />Datasets
          </a>
        </nav>

        {/* EVALUATION GROUP */}
        <span className="nav-label tools-label">EVALUATION</span>
        <nav className="navigation">
          <a
            className={`nav-item ${navTab === 'runs' ? 'active' : ''}`}
            href="#runs"
            onClick={(e) => {
              e.preventDefault();
              navigateTo('runs');
            }}
          >
            <FlaskConical size={17} />Test Runs
          </a>
          <a
            className={`nav-item ${navTab === 'security' ? 'active' : ''}`}
            href="#security"
            onClick={(e) => {
              e.preventDefault();
              navigateTo('security');
            }}
          >
            <ShieldAlert size={17} />Security
          </a>
          <a
            className={`nav-item ${navTab === 'compare' ? 'active' : ''}`}
            href="#compare"
            onClick={(e) => {
              e.preventDefault();
              navigateTo('compare');
            }}
          >
            <Layers3 size={17} />Version Compare
          </a>
          <a
            className={`nav-item ${navTab === 'quality_gate' ? 'active' : ''}`}
            href="#quality-gate"
            onClick={(e) => {
              e.preventDefault();
              navigateTo('quality_gate');
            }}
          >
            <ShieldCheck size={17} />Quality Gate
          </a>
        </nav>

        {/* SYSTEM CONFIGURATION */}
        <span className="nav-label tools-label">SYSTEM</span>
        <nav className="navigation">
          <a
            className={`nav-item ${navTab === 'settings' ? 'active' : ''}`}
            href="#settings"
            onClick={(e) => {
              e.preventDefault();
              navigateTo('settings');
            }}
          >
            <SlidersHorizontal size={17} />Settings
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="help-card">
            <div className="help-icon"><CircleHelp size={17} /></div>
            <strong>Aegis Evaluation Suite</strong>
            <p>Unified quality, regression detection & deterministic safety gate.</p>
            <a href="https://github.com" target="_blank" rel="noreferrer">
              Documentation <ArrowUpRight size={13} />
            </a>
          </div>
          <div className="user-row">
            <div className="avatar">AE</div>
            <div className="user-copy">
              <strong>Quality Lead</strong>
              <span>eval@aegis.ai</span>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Aegis</span>
            <span className="crumb-divider">/</span>
            {navTab === 'overview' ? (
              <strong>Overview</strong>
            ) : navTab === 'projects' ? (
              <strong>Projects</strong>
            ) : navTab === 'assistants' ? (
              <strong>Assistants & Models</strong>
            ) : navTab === 'runs' ? (
              <strong>Evaluation Test Runs</strong>
            ) : navTab === 'security' ? (
              <strong>Security Intelligence</strong>
            ) : navTab === 'compare' ? (
              <strong>Version Comparison</strong>
            ) : navTab === 'quality_gate' ? (
              <strong>Release Quality Gate</strong>
            ) : navTab === 'settings' ? (
              <strong>Settings</strong>
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
            <div className={`connection ${health}`}>
              <span className="status-dot" />API {statusText}
            </div>
            <div className="avatar top-avatar">AE</div>
          </div>
        </header>

        <div className="page-wrap">
          {navTab === 'overview' && (
            <OverviewDashboard
              onNavigate={navigateTo}
              onLaunchRunModal={() => {
                setNavTab('runs');
                setOpenExecuteRunModal(true);
              }}
            />
          )}

          {navTab === 'projects' && (
            <ProjectsList
              onNavigateToAssistants={(pId) => {
                setSelectedProjectId(pId);
                setNavTab('assistants');
              }}
              onNavigateToDatasets={() => setNavTab('datasets')}
            />
          )}

          {navTab === 'assistants' && (
            <AssistantsList
              initialProjectId={selectedProjectId}
              onLaunchEvaluation={(_id) => {
                setNavTab('runs');
                setOpenExecuteRunModal(true);
              }}
            />
          )}

          {navTab === 'datasets' && (
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
          )}

          {navTab === 'runs' && (
            <EvaluationRunsView
              initialRunId={selectedRunId}
              onRequestNewRunModal={openExecuteRunModal}
              onModalClosed={() => setOpenExecuteRunModal(false)}
              onNavigateToCompare={(_runId) => {
                setNavTab('compare');
              }}
              onNavigateToQualityGate={(_runId) => {
                setNavTab('quality_gate');
              }}
            />
          )}

          {navTab === 'security' && (
            <SecurityDashboard
              onNavigateToRun={(runId) => {
                setSelectedRunId(runId);
                setNavTab('runs');
              }}
            />
          )}

          {navTab === 'compare' && <VersionComparison />}

          {navTab === 'quality_gate' && <ReleaseQualityGate />}

          {navTab === 'settings' && <SettingsView />}

          <footer className="page-footer">
            <span>© 2026 Aegis AI Quality Platform</span>
            <span>
              <i className={`footer-dot ${health}`} />
              {health === 'healthy'
                ? 'All systems operational'
                : health === 'checking'
                ? 'Checking API telemetry'
                : 'API offline'}
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}

export default App;
