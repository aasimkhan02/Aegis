import React, { useEffect, useState } from 'react';
import {
  ArrowLeft,
  Download,
  Plus,
  Upload,
  Search,
  Tag,
  CheckCircle,
  XCircle,
  Edit2,
  Trash2,
  BookOpen,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Check,
} from 'lucide-react';
import {
  deleteTestCase,
  exportDataset,
  fetchDataset,
  fetchTestCases,
  toggleTestCase,
  updateTestCase,
  createTestCase,
} from '../api/datasets';
import { Dataset, TestCase, TestCaseCreatePayload } from '../types/dataset';
import { TestCaseModal } from './TestCaseModal';
import { ImportModal } from './ImportModal';

interface Props {
  datasetId: string;
  onBack: () => void;
}

export const DatasetDetail: React.FC<Props> = ({ datasetId, onBack }) => {
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ type: 'success' | 'info'; message: string } | null>(null);

  // Filters
  const [selectedTag, setSelectedTag] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'enabled' | 'disabled'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Modals
  const [isCaseModalOpen, setIsCaseModalOpen] = useState(false);
  const [editingCase, setEditingCase] = useState<TestCase | null>(null);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [expandedContextId, setExpandedContextId] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [ds, cases] = await Promise.all([
        fetchDataset(datasetId),
        fetchTestCases(datasetId),
      ]);
      setDataset(ds);
      setTestCases(cases);
    } catch (err: any) {
      setError(err.message || 'Failed to load dataset details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [datasetId]);

  const handleExport = async () => {
    try {
      const data = await exportDataset(datasetId);
      const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(JSON.stringify(data, null, 2))}`;
      const downloadAnchor = document.createElement('a');
      const filename = `${(dataset?.name || 'dataset').toLowerCase().replace(/\s+/g, '_')}_export.json`;
      downloadAnchor.setAttribute('href', jsonString);
      downloadAnchor.setAttribute('download', filename);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      setNotification({ type: 'success', message: `Exported ${testCases.length} test cases to ${filename}` });
      setTimeout(() => setNotification(null), 4000);
    } catch (err: any) {
      setError(`Export failed: ${err.message}`);
    }
  };

  const handleToggle = async (tc: TestCase) => {
    try {
      const updated = await toggleTestCase(tc.id);
      setTestCases((prev) => prev.map((item) => (item.id === tc.id ? updated : item)));
    } catch (err: any) {
      setError(`Failed to toggle status: ${err.message}`);
    }
  };

  const handleDelete = async (tc: TestCase) => {
    if (!window.confirm(`Are you sure you want to remove or archive test case "${tc.name}"?`)) {
      return;
    }
    try {
      const result = await deleteTestCase(tc.id);
      if (result.action === 'archived') {
        setNotification({
          type: 'info',
          message: result.message,
        });
        // Update local status to disabled
        setTestCases((prev) =>
          prev.map((item) =>
            item.id === tc.id ? { ...item, is_enabled: false, metadata: { ...item.metadata, archived: true } } : item
          )
        );
      } else {
        setNotification({ type: 'success', message: result.message });
        setTestCases((prev) => prev.filter((item) => item.id !== tc.id));
      }
      setTimeout(() => setNotification(null), 5000);
    } catch (err: any) {
      setError(`Delete failed: ${err.message}`);
    }
  };

  const handleSaveTestCase = async (payload: TestCaseCreatePayload) => {
    if (editingCase) {
      const updated = await updateTestCase(editingCase.id, payload);
      setTestCases((prev) => prev.map((item) => (item.id === editingCase.id ? updated : item)));
      setNotification({ type: 'success', message: `Updated "${updated.name}"` });
    } else {
      const created = await createTestCase(datasetId, payload);
      setTestCases((prev) => [...prev, created]);
      setNotification({ type: 'success', message: `Created "${created.name}"` });
    }
    setTimeout(() => setNotification(null), 3000);
  };

  // Filter test cases
  const filteredCases = testCases.filter((tc) => {
    // Tag filter
    if (selectedTag !== 'all') {
      const matchTag = tc.tags && tc.tags.some((t) => t.toLowerCase() === selectedTag.toLowerCase());
      if (!matchTag) return false;
    }
    // Status filter
    if (statusFilter === 'enabled' && !tc.is_enabled) return false;
    if (statusFilter === 'disabled' && tc.is_enabled) return false;

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const inName = tc.name.toLowerCase().includes(q);
      const inBehavior = tc.expected_behavior?.toLowerCase().includes(q) ?? false;
      const inPrompt = JSON.stringify(tc.input_data).toLowerCase().includes(q);
      if (!inName && !inBehavior && !inPrompt) return false;
    }
    return true;
  });

  // Extract distinct tags
  const allTags = Array.from(
    new Set(testCases.flatMap((tc) => (Array.isArray(tc.tags) ? tc.tags : [])))
  ).sort();

  if (loading) {
    return (
      <div className="dataset-loading-state">
        <div className="spinner" />
        <span>Loading dataset...</span>
      </div>
    );
  }

  return (
    <div className="dataset-detail-page">
      {/* Header bar */}
      <div className="detail-top-nav">
        <button className="back-link" onClick={onBack}>
          <ArrowLeft size={16} />
          <span>Back to all Datasets</span>
        </button>
      </div>

      {notification && (
        <div className={`notification-pill ${notification.type}`}>
          {notification.type === 'success' ? <Check size={14} /> : <AlertCircle size={14} />}
          <span>{notification.message}</span>
        </div>
      )}

      {error && (
        <div className="error-banner">
          <AlertCircle size={16} />
          <span>{error}</span>
          <button className="icon-button" onClick={() => setError(null)}><XCircle size={14} /></button>
        </div>
      )}

      {/* Dataset Info Card */}
      <header className="dataset-header-card">
        <div className="header-info">
          <div className="dataset-title-row">
            <h1>{dataset?.name}</h1>
            <span className="badge-count">{testCases.length} Test Cases</span>
          </div>
          {dataset?.description && <p className="dataset-desc">{dataset.description}</p>}
          <div className="dataset-meta-row">
            <span>Created: {dataset ? new Date(dataset.created_at).toLocaleDateString() : ''}</span>
            <span className="meta-dot">•</span>
            <span>Active Cases: {testCases.filter((c) => c.is_enabled).length}</span>
            <span className="meta-dot">•</span>
            <span>Archived/Disabled: {testCases.filter((c) => !c.is_enabled).length}</span>
          </div>
        </div>

        <div className="header-actions">
          <button className="btn-secondary" onClick={handleExport} title="Export full dataset to JSON">
            <Download size={15} />
            <span>Export JSON</span>
          </button>
          <button className="btn-secondary" onClick={() => setIsImportModalOpen(true)} title="Import test cases">
            <Upload size={15} />
            <span>Import JSON</span>
          </button>
          <button
            className="primary-button"
            onClick={() => {
              setEditingCase(null);
              setIsCaseModalOpen(true);
            }}
          >
            <Plus size={16} />
            <span>Add Test Case</span>
          </button>
        </div>
      </header>

      {/* Filter and Search Bar */}
      <div className="filter-panel">
        <div className="search-box">
          <Search size={15} />
          <input
            type="text"
            placeholder="Search test cases by name, prompt or behavior..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-row">
          <div className="filter-group">
            <span className="filter-label">Filter Tag:</span>
            <div className="tag-pills">
              <button
                className={`tag-pill ${selectedTag === 'all' ? 'active' : ''}`}
                onClick={() => setSelectedTag('all')}
              >
                All ({testCases.length})
              </button>
              {allTags.map((t) => {
                const count = testCases.filter((c) => c.tags?.includes(t)).length;
                return (
                  <button
                    key={t}
                    className={`tag-pill ${selectedTag === t ? 'active' : ''}`}
                    onClick={() => setSelectedTag(t)}
                  >
                    {t} ({count})
                  </button>
                );
              })}
            </div>
          </div>

          <div className="filter-group right">
            <span className="filter-label">Status:</span>
            <select
              className="select-input"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
            >
              <option value="all">All statuses</option>
              <option value="enabled">Enabled only</option>
              <option value="disabled">Disabled only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Test Cases Table / List */}
      <div className="test-cases-container">
        {filteredCases.length === 0 ? (
          <div className="empty-state">
            <BookOpen size={36} className="text-muted" />
            <h3>No test cases found</h3>
            <p>
              {testCases.length === 0
                ? 'This dataset has no test cases yet. Click "Add Test Case" or "Import JSON" to populate it.'
                : 'No test cases match your current tag or search filter.'}
            </p>
          </div>
        ) : (
          <div className="test-cases-table-wrap">
            <table className="test-cases-table">
              <thead>
                <tr>
                  <th style={{ width: '50px' }}>STATUS</th>
                  <th>TEST CASE NAME & TAGS</th>
                  <th>PROMPT / INPUT</th>
                  <th>EXPECTED BEHAVIOR</th>
                  <th>RETRIEVAL CONTEXT</th>
                  <th style={{ width: '80px', textAlign: 'right' }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {filteredCases.map((tc) => {
                  const inputPrompt =
                    typeof tc.input_data === 'string'
                      ? tc.input_data
                      : tc.input_data?.messages?.[0]?.content ||
                        tc.input_data?.prompt ||
                        JSON.stringify(tc.input_data);

                  const hasContext = Array.isArray(tc.retrieval_context) && tc.retrieval_context.length > 0;
                  const isContextExpanded = expandedContextId === tc.id;

                  return (
                    <tr key={tc.id} className={!tc.is_enabled ? 'row-disabled' : ''}>
                      <td>
                        <button
                          className={`status-toggle-btn ${tc.is_enabled ? 'enabled' : 'disabled'}`}
                          onClick={() => handleToggle(tc)}
                          title={tc.is_enabled ? 'Click to disable' : 'Click to enable'}
                        >
                          {tc.is_enabled ? (
                            <CheckCircle size={18} className="text-green" />
                          ) : (
                            <XCircle size={18} className="text-gray" />
                          )}
                        </button>
                      </td>
                      <td>
                        <div className="tc-title-cell">
                          <strong>{tc.name}</strong>
                          {tc.tags && tc.tags.length > 0 && (
                            <div className="tc-tags-row">
                              {tc.tags.map((tag) => (
                                <span key={tag} className="tag-badge">
                                  <Tag size={10} />
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="prompt-cell">
                        <span className="text-preview" title={inputPrompt}>
                          {inputPrompt.length > 130 ? `${inputPrompt.substring(0, 130)}...` : inputPrompt}
                        </span>
                      </td>
                      <td className="behavior-cell">
                        <span className="text-preview" title={tc.expected_behavior || 'None'}>
                          {tc.expected_behavior
                            ? tc.expected_behavior.length > 100
                              ? `${tc.expected_behavior.substring(0, 100)}...`
                              : tc.expected_behavior
                            : <span className="text-muted">Not specified</span>}
                        </span>
                      </td>
                      <td className="context-cell">
                        {hasContext ? (
                          <div className="context-preview-wrap">
                            <button
                              className="text-link-button"
                              onClick={() => setExpandedContextId(isContextExpanded ? null : tc.id)}
                            >
                              <BookOpen size={12} />
                              <span>{tc.retrieval_context!.length} chunk(s)</span>
                              {isContextExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                            </button>
                            {isContextExpanded && (
                              <div className="context-expanded-box">
                                <pre>{JSON.stringify(tc.retrieval_context, null, 2)}</pre>
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-muted">None</span>
                        )}
                      </td>
                      <td className="actions-cell">
                        <div className="actions-buttons">
                          <button
                            className="icon-button small"
                            onClick={() => {
                              setEditingCase(tc);
                              setIsCaseModalOpen(true);
                            }}
                            title="Edit test case"
                          >
                            <Edit2 size={14} />
                          </button>
                          <button
                            className="icon-button small delete"
                            onClick={() => handleDelete(tc)}
                            title="Delete or Archive test case"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add / Edit Modal */}
      <TestCaseModal
        isOpen={isCaseModalOpen}
        onClose={() => {
          setIsCaseModalOpen(false);
          setEditingCase(null);
        }}
        onSave={handleSaveTestCase}
        initialData={editingCase}
      />

      {/* Import Modal */}
      <ImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onSuccess={() => {
          loadData();
          setIsImportModalOpen(false);
        }}
        datasetId={datasetId}
        datasetName={dataset?.name}
      />
    </div>
  );
};

