import React, { useEffect, useState } from 'react';
import {
  Plus,
  Upload,
  Search,
  Database,
  Layers,
  Calendar,
  Tag,
  Trash2,
  Edit3,
  ChevronRight,
  AlertCircle,
  Sparkles,
  CheckCircle,
  X,
} from 'lucide-react';
import { createDataset, deleteDataset, fetchDatasets, updateDataset } from '../api/datasets';
import { Dataset } from '../types/dataset';
import { ImportModal } from './ImportModal';

interface Props {
  onSelectDataset: (datasetId: string) => void;
}

export const DatasetList: React.FC<Props> = ({ onSelectDataset }) => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [editingDataset, setEditingDataset] = useState<Dataset | null>(null);

  // Form fields
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadDatasets = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDatasets(searchQuery);
      setDatasets(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load datasets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      loadDatasets();
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleCreateOrUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsSubmitting(true);
    try {
      if (editingDataset) {
        const updated = await updateDataset(editingDataset.id, {
          name: name.trim(),
          description: description.trim() || undefined,
        });
        setDatasets((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
        setNotification(`Updated "${updated.name}"`);
      } else {
        const created = await createDataset({
          name: name.trim(),
          description: description.trim() || undefined,
        });
        setDatasets((prev) => [created, ...prev]);
        setNotification(`Created "${created.name}"`);
      }
      setIsCreateModalOpen(false);
      setEditingDataset(null);
      setName('');
      setDescription('');
      setTimeout(() => setNotification(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Operation failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, ds: Dataset) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete dataset "${ds.name}"?`)) return;

    try {
      await deleteDataset(ds.id);
      setDatasets((prev) => prev.filter((d) => d.id !== ds.id));
      setNotification(`Dataset "${ds.name}" deleted.`);
      setTimeout(() => setNotification(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Delete failed');
    }
  };

  const openEditModal = (e: React.MouseEvent, ds: Dataset) => {
    e.stopPropagation();
    setEditingDataset(ds);
    setName(ds.name);
    setDescription(ds.description || '');
    setIsCreateModalOpen(true);
  };

  return (
    <div className="dataset-list-page">
      {/* Top Banner and Actions */}
      <div className="section-header-row">
        <div>
          <h2>Golden Datasets</h2>
          <p>Manage benchmark test suites, expected behaviors, and retrieval context for assistant evaluation.</p>
        </div>

        <div className="section-actions">
          <button className="btn-secondary" onClick={() => setIsImportModalOpen(true)}>
            <Upload size={15} />
            <span>Import JSON</span>
          </button>
          <button
            className="primary-button"
            onClick={() => {
              setEditingDataset(null);
              setName('');
              setDescription('');
              setIsCreateModalOpen(true);
            }}
          >
            <Plus size={16} />
            <span>New Dataset</span>
          </button>
        </div>
      </div>

      {notification && (
        <div className="notification-pill success">
          <CheckCircle size={15} />
          <span>{notification}</span>
        </div>
      )}

      {error && (
        <div className="error-banner">
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* Search and Filter */}
      <div className="search-bar-wrap">
        <div className="search-box">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search datasets by name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Datasets Grid */}
      {loading ? (
        <div className="dataset-loading-state">
          <div className="spinner" />
          <span>Loading datasets...</span>
        </div>
      ) : datasets.length === 0 ? (
        <div className="empty-state large">
          <Database size={42} className="text-muted" />
          <h3>No datasets found</h3>
          <p>Create your first dataset or import the BharatHome Appliances golden dataset to get started.</p>
          <div className="empty-actions">
            <button className="primary-button" onClick={() => setIsCreateModalOpen(true)}>
              <Plus size={16} />
              <span>Create Dataset</span>
            </button>
            <button className="btn-secondary" onClick={() => setIsImportModalOpen(true)}>
              <Sparkles size={16} />
              <span>Import Golden Dataset</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="datasets-grid">
          {datasets.map((ds) => (
            <div
              key={ds.id}
              className="dataset-card"
              onClick={() => onSelectDataset(ds.id)}
            >
              <div className="card-top">
                <div className="card-icon-title">
                  <span className="dataset-icon">
                    <Database size={18} />
                  </span>
                  <div>
                    <h3>{ds.name}</h3>
                    <span className="case-count-pill">
                      <Layers size={12} />
                      {ds.test_case_count} test case{ds.test_case_count === 1 ? '' : 's'}
                    </span>
                  </div>
                </div>

                <div className="card-actions">
                  <button
                    className="icon-button small"
                    onClick={(e) => openEditModal(e, ds)}
                    title="Edit name & description"
                  >
                    <Edit3 size={14} />
                  </button>
                  <button
                    className="icon-button small delete"
                    onClick={(e) => handleDelete(e, ds)}
                    title="Delete dataset"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {ds.description && <p className="card-desc">{ds.description}</p>}

              {ds.tags && ds.tags.length > 0 && (
                <div className="card-tags">
                  {ds.tags.slice(0, 4).map((t) => (
                    <span key={t} className="tag-badge small">
                      <Tag size={10} />
                      {t}
                    </span>
                  ))}
                  {ds.tags.length > 4 && (
                    <span className="tag-more">+{ds.tags.length - 4} more</span>
                  )}
                </div>
              )}

              <div className="card-footer">
                <span className="card-date">
                  <Calendar size={12} />
                  {new Date(ds.created_at).toLocaleDateString()}
                </span>
                <span className="view-link">
                  Manage test cases <ChevronRight size={14} />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create / Edit Modal */}
      {isCreateModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <div className="modal-header">
              <h3>{editingDataset ? 'Edit Dataset' : 'Create New Dataset'}</h3>
              <button
                className="icon-button"
                onClick={() => {
                  setIsCreateModalOpen(false);
                  setEditingDataset(null);
                }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateOrUpdate} className="modal-form">
              <div className="form-group">
                <label htmlFor="ds-name-input">Dataset Name *</label>
                <input
                  id="ds-name-input"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. BharatHome Customer Support Benchmark"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="ds-desc-input">Description</label>
                <textarea
                  id="ds-desc-input"
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="What evaluation scenarios or models is this dataset designed for?"
                />
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setIsCreateModalOpen(false);
                    setEditingDataset(null);
                  }}
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button type="submit" className="primary-button" disabled={isSubmitting}>
                  {isSubmitting
                    ? 'Saving...'
                    : editingDataset
                    ? 'Save Changes'
                    : 'Create Dataset'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Import Modal */}
      <ImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onSuccess={() => {
          loadDatasets();
          setIsImportModalOpen(false);
        }}
      />
    </div>
  );
};
