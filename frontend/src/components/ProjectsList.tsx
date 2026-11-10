import React, { useEffect, useState } from 'react';
import {
  FolderGit2,
  Plus,
  RefreshCw,
  Search,
  Database,
  Layers3,
  FlaskConical,
  Edit2,
  X,
  Check,
} from 'lucide-react';
import { fetchProjects, createProject, updateProject } from '../api/dashboard';
import { Project } from '../types/dashboard';

interface ProjectsListProps {
  onNavigateToAssistants?: (projectId: string) => void;
  onNavigateToDatasets?: () => void;
}

export const ProjectsList: React.FC<ProjectsListProps> = ({
  onNavigateToAssistants,
  onNavigateToDatasets,
}) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState<string>('');
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [creating, setCreating] = useState<boolean>(false);
  const [newName, setNewName] = useState<string>('');
  const [newDesc, setNewDesc] = useState<string>('');

  // Editing state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState<string>('');
  const [editDesc, setEditDesc] = useState<string>('');
  const [savingEdit, setSavingEdit] = useState<boolean>(false);

  const loadProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProjects(100, 0);
      setProjects(data.items);
    } catch (err: any) {
      setError(err?.message || 'Failed to load projects.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadProjects();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await createProject({
        name: newName.trim(),
        description: newDesc.trim() || undefined,
      });
      setShowCreateModal(false);
      setNewName('');
      setNewDesc('');
      await loadProjects();
    } catch (err: any) {
      setError(err?.message || 'Failed to create project.');
    } finally {
      setCreating(false);
    }
  };

  const startEdit = (p: Project) => {
    setEditingId(p.id);
    setEditName(p.name);
    setEditDesc(p.description || '');
  };

  const handleSaveEdit = async (id: string) => {
    if (!editName.trim()) return;
    setSavingEdit(true);
    try {
      await updateProject(id, {
        name: editName.trim(),
        description: editDesc.trim(),
      });
      setEditingId(null);
      await loadProjects();
    } catch (err: any) {
      setError(err?.message || 'Failed to update project.');
    } finally {
      setSavingEdit(false);
    }
  };

  const filtered = projects.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    (p.description && p.description.toLowerCase().includes(search.toLowerCase())) ||
    p.id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="dataset-list-page">
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button className="btn-secondary small" onClick={loadProjects}>Retry</button>
        </div>
      )}

      <div className="section-header-row">
        <div>
          <h2>Projects</h2>
          <p>Organize evaluation suites, golden datasets, and assistant versions by workspace project.</p>
        </div>
        <div className="section-actions">
          <button className="btn-secondary" onClick={loadProjects}>
            <RefreshCw size={14} className={loading ? 'spinner' : ''} />
            Refresh
          </button>
          <button className="primary-button" onClick={() => setShowCreateModal(true)}>
            <Plus size={16} />
            New Project
          </button>
        </div>
      </div>

      <div className="search-bar-wrap">
        <div className="search-box">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search projects by name, description, or UUID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {loading && projects.length === 0 ? (
        <div className="dataset-loading-state">
          <div className="spinner" />
          <span>Loading projects...</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state large">
          <FolderGit2 size={32} color="#a0a3ad" />
          <h3>No projects found</h3>
          <p>
            {search
              ? 'No projects matched your search criteria.'
              : 'Create a project to group your assistants, datasets, and test runs.'}
          </p>
          <button className="primary-button" onClick={() => setShowCreateModal(true)}>
            <Plus size={15} /> Create Project
          </button>
        </div>
      ) : (
        <div className="datasets-grid">
          {filtered.map((proj) => (
            <article key={proj.id} className="dataset-card" style={{ cursor: 'default' }}>
              <div className="card-top">
                <div className="card-icon-title">
                  <div className="dataset-icon">
                    <FolderGit2 size={18} />
                  </div>
                  <div>
                    {editingId === proj.id ? (
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <input
                          type="text"
                          className="select-input"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          style={{ fontWeight: 600 }}
                        />
                        <button
                          className="btn-secondary small"
                          onClick={() => handleSaveEdit(proj.id)}
                          disabled={savingEdit}
                        >
                          <Check size={12} />
                        </button>
                        <button
                          className="btn-secondary small"
                          onClick={() => setEditingId(null)}
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ) : (
                      <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {proj.name}
                        <button
                          className="icon-button small"
                          title="Edit project"
                          onClick={() => startEdit(proj)}
                        >
                          <Edit2 size={11} />
                        </button>
                      </h3>
                    )}
                    <span style={{ fontSize: '9px', color: '#9ca3af', fontFamily: 'monospace' }}>
                      {proj.id.slice(0, 8)}...{proj.id.slice(-4)}
                    </span>
                  </div>
                </div>
              </div>

              {editingId === proj.id ? (
                <div style={{ margin: '8px 0' }}>
                  <textarea
                    className="select-input"
                    rows={2}
                    value={editDesc}
                    onChange={(e) => setEditDesc(e.target.value)}
                    style={{ width: '100%', resize: 'none' }}
                  />
                </div>
              ) : (
                <p className="card-desc">
                  {proj.description || <span className="text-muted">No description provided.</span>}
                </p>
              )}

              <div className="card-tags" style={{ marginTop: 'auto' }}>
                <span className="tag-badge">
                  <Layers3 size={11} />
                  {proj.assistant_count ?? 0} Assistants
                </span>
                <span className="tag-badge">
                  <Database size={11} />
                  {proj.dataset_count ?? 0} Datasets
                </span>
                <span className="tag-badge">
                  <FlaskConical size={11} />
                  {proj.evaluation_count ?? 0} Runs
                </span>
              </div>

              <div className="card-footer">
                <span className="card-date">
                  Created {new Date(proj.created_at).toLocaleDateString()}
                </span>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {onNavigateToAssistants && (
                    <button
                      className="text-link-button"
                      onClick={() => onNavigateToAssistants(proj.id)}
                    >
                      Assistants →
                    </button>
                  )}
                  {onNavigateToDatasets && (
                    <button
                      className="text-link-button"
                      onClick={onNavigateToDatasets}
                    >
                      Datasets →
                    </button>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="modal-backdrop" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create New Project</h3>
              <button className="icon-button" onClick={() => setShowCreateModal(false)}>
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleCreate} className="modal-form">
              <div className="form-group">
                <label>Project Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g., BharatHome Assistant Platform"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea
                  rows={3}
                  placeholder="Summary of what this evaluation project tests..."
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                />
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={creating || !newName.trim()}
                >
                  {creating ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

