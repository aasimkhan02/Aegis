import React, { useEffect, useState } from 'react';
import {
  Layers3,
  Plus,
  RefreshCw,
  Search,
  Cpu,
  Terminal,
  FolderGit2,
  ChevronDown,
  ChevronUp,
  X,
  Play,
} from 'lucide-react';
import { fetchAssistants, createAssistant, fetchProjects } from '../api/dashboard';
import { AssistantVersion, Project } from '../types/dashboard';

interface AssistantsListProps {
  initialProjectId?: string | null;
  onLaunchEvaluation?: (assistantVersionId: string) => void;
}

export const AssistantsList: React.FC<AssistantsListProps> = ({
  initialProjectId,
  onLaunchEvaluation,
}) => {
  const [assistants, setAssistants] = useState<AssistantVersion[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(initialProjectId || '');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState<string>('');
  const [expandedPromptId, setExpandedPromptId] = useState<string | null>(null);

  // Modal state
  const [showModal, setShowModal] = useState<boolean>(false);
  const [creating, setCreating] = useState<boolean>(false);
  const [formProjectId, setFormProjectId] = useState<string>('');
  const [formName, setFormName] = useState<string>('BharatHome Assistant');
  const [formVersion, setFormVersion] = useState<string>('1.1.0');
  const [formProvider, setFormProvider] = useState<string>('mock');
  const [formModel, setFormModel] = useState<string>('deterministic-rules');
  const [formSystemPrompt, setFormSystemPrompt] = useState<string>(
    'You are a helpful customer support assistant for BharatHome.'
  );

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [assRes, projRes] = await Promise.all([
        fetchAssistants(selectedProjectId || undefined, 100, 0),
        fetchProjects(100, 0),
      ]);
      setAssistants(assRes.items);
      setProjects(projRes.items);
      if (!formProjectId && projRes.items.length > 0) {
        setFormProjectId(projRes.items[0].id);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load assistants.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, [selectedProjectId]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formProjectId || !formName || !formVersion) return;
    setCreating(true);
    try {
      await createAssistant({
        project_id: formProjectId,
        name: formName.trim(),
        version: formVersion.trim(),
        provider: formProvider.trim() || undefined,
        model: formModel.trim() || undefined,
        system_prompt: formSystemPrompt.trim() || undefined,
      });
      setShowModal(false);
      await loadData();
    } catch (err: any) {
      setError(err?.message || 'Failed to register assistant version.');
    } finally {
      setCreating(false);
    }
  };

  const filtered = assistants.filter((a) => {
    const q = search.toLowerCase();
    return (
      a.name.toLowerCase().includes(q) ||
      a.version.toLowerCase().includes(q) ||
      (a.model && a.model.toLowerCase().includes(q)) ||
      (a.provider && a.provider.toLowerCase().includes(q)) ||
      (a.project_name && a.project_name.toLowerCase().includes(q))
    );
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
          <h2>Assistant Versions</h2>
          <p>Register, inspect, and benchmark LLM models, prompts, tools, and system configurations.</p>
        </div>
        <div className="section-actions">
          <button className="btn-secondary" onClick={loadData}>
            <RefreshCw size={14} className={loading ? 'spinner' : ''} />
            Refresh
          </button>
          <button className="primary-button" onClick={() => setShowModal(true)}>
            <Plus size={16} />
            New Assistant Version
          </button>
        </div>
      </div>

      <div className="filter-panel">
        <div className="filter-row">
          <div className="search-box" style={{ flex: 1, minWidth: '240px' }}>
            <Search size={15} />
            <input
              type="text"
              placeholder="Search by name, version, model, or provider..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="filter-group">
            <span className="filter-label">Filter Project:</span>
            <select
              className="select-input"
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
            >
              <option value="">All Projects ({projects.length})</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {loading && assistants.length === 0 ? (
        <div className="dataset-loading-state">
          <div className="spinner" />
          <span>Loading assistant versions...</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state large">
          <Layers3 size={32} color="#a0a3ad" />
          <h3>No assistant versions found</h3>
          <p>
            {search || selectedProjectId
              ? 'No assistants match your current search and project filter.'
              : 'Register an assistant version to begin automated evaluation testing.'}
          </p>
          <button className="primary-button" onClick={() => setShowModal(true)}>
            <Plus size={15} /> Register Version
          </button>
        </div>
      ) : (
        <div className="datasets-grid">
          {filtered.map((av) => (
            <article key={av.id} className="dataset-card" style={{ cursor: 'default' }}>
              <div className="card-top">
                <div className="card-icon-title">
                  <div className="dataset-icon">
                    <Cpu size={18} />
                  </div>
                  <div>
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {av.name}
                      <span className="case-count-pill">v{av.version}</span>
                    </h3>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '10px', color: '#6b7280' }}>
                      <FolderGit2 size={11} />
                      <span>{av.project_name || 'Project'}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="card-tags" style={{ margin: '8px 0' }}>
                <span className="tag-badge">
                  <Terminal size={11} />
                  {av.provider || 'default'} / {av.model || 'model'}
                </span>
                {av.tools_schema && av.tools_schema.length > 0 && (
                  <span className="tag-badge">
                    {av.tools_schema.length} tools
                  </span>
                )}
              </div>

              {av.system_prompt && (
                <div style={{ marginBottom: '12px' }}>
                  <button
                    className="text-link-button"
                    onClick={() =>
                      setExpandedPromptId(expandedPromptId === av.id ? null : av.id)
                    }
                  >
                    {expandedPromptId === av.id ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    System Prompt
                  </button>
                  {expandedPromptId === av.id && (
                    <div className="context-expanded-box">
                      <pre>{av.system_prompt}</pre>
                    </div>
                  )}
                </div>
              )}

              <div className="card-footer">
                <span className="card-date">
                  Added {new Date(av.created_at).toLocaleDateString()}
                </span>
                {onLaunchEvaluation && (
                  <button
                    className="primary-button"
                    style={{ height: '28px', padding: '0 9px', fontSize: '10px' }}
                    onClick={() => onLaunchEvaluation(av.id)}
                  >
                    <Play size={11} /> Evaluate
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {/* New Assistant Version Modal */}
      {showModal && (
        <div className="modal-backdrop" onClick={() => setShowModal(false)}>
          <div className="modal-content medium" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Register Assistant Version</h3>
              <button className="icon-button" onClick={() => setShowModal(false)}>
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleCreate} className="modal-form">
              <div className="form-group">
                <label>Target Project *</label>
                <select
                  className="select-input"
                  style={{ width: '100%', padding: '8px 11px' }}
                  required
                  value={formProjectId}
                  onChange={(e) => setFormProjectId(e.target.value)}
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label>Assistant Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., BharatHome Support"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                  />
                </div>
                <div className="form-group" style={{ width: '130px' }}>
                  <label>Version Tag *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., 1.2.0"
                    value={formVersion}
                    onChange={(e) => setFormVersion(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label>Provider</label>
                  <input
                    type="text"
                    placeholder="e.g., openai, anthropic, mock"
                    value={formProvider}
                    onChange={(e) => setFormProvider(e.target.value)}
                  />
                </div>
                <div className="form-group flex-1">
                  <label>Model Identifier</label>
                  <input
                    type="text"
                    placeholder="e.g., gpt-4o, claude-3-5-sonnet"
                    value={formModel}
                    onChange={(e) => setFormModel(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-group">
                <label>System Prompt</label>
                <textarea
                  rows={4}
                  placeholder="You are an AI assistant designed to..."
                  value={formSystemPrompt}
                  onChange={(e) => setFormSystemPrompt(e.target.value)}
                />
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={creating || !formName || !formVersion || !formProjectId}
                >
                  {creating ? 'Registering...' : 'Save Version'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

