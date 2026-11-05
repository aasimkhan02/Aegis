import React, { useState } from 'react';
import { X, Upload, CheckCircle2, AlertTriangle, Sparkles } from 'lucide-react';
import { importFullDataset, importTestCases } from '../api/datasets';
import { ImportResult } from '../types/dataset';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  datasetId?: string; // If present, imports into this dataset. Otherwise, creates new dataset.
  datasetName?: string;
}

export const ImportModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onSuccess,
  datasetId,
  datasetName,
}) => {
  if (!isOpen) return null;

  const [jsonText, setJsonText] = useState('');
  const [newDatasetName, setNewDatasetName] = useState('');
  const [overwriteExisting, setOverwriteExisting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setJsonText(content);
      try {
        const parsed = JSON.parse(content);
        if (parsed.name && !datasetId && !newDatasetName) {
          setNewDatasetName(parsed.name);
        }
      } catch {
        // Not valid JSON yet, user can edit
      }
    };
    reader.readAsText(file);
  };

  const handleLoadSample = async () => {
    try {
      setIsSubmitting(true);
      // Fetch the golden dataset from backend static / API or direct JSON
      const res = await fetch('/data/bharathome_golden_dataset.json').catch(() => null);
      if (res && res.ok) {
        const data = await res.text();
        setJsonText(data);
        const parsed = JSON.parse(data);
        if (!datasetId && parsed.name) setNewDatasetName(parsed.name);
      } else {
        // Fallback: quick sample snippet
        const sampleSnippet = {
          name: "BharatHome Golden Sample",
          description: "Customer support test cases for appliances",
          test_cases: [
            {
              name: "Refrigerator Error Code E4",
              input_data: { "messages": [{ "role": "user", "content": "Display shows error E4 on my fridge." }] },
              expected_behavior: "Advise checking defrost sensor and power reset.",
              retrieval_context: [{ "doc": "Manual", "section": "8.2", "text": "Error E4 indicates defrost sensor fault." }],
              tags: ["troubleshooting", "refrigerator"]
            }
          ]
        };
        setJsonText(JSON.stringify(sampleSnippet, null, 2));
        if (!datasetId) setNewDatasetName("BharatHome Golden Sample");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();
    setGeneralError(null);
    setResult(null);

    let parsed: any;
    try {
      parsed = JSON.parse(jsonText.trim());
    } catch (err: any) {
      setGeneralError(`Invalid JSON format: ${err.message}`);
      return;
    }

    setIsSubmitting(true);
    try {
      let res: ImportResult;
      const testCases = Array.isArray(parsed) ? parsed : (parsed.test_cases || []);

      if (datasetId) {
        // Import into existing dataset
        res = await importTestCases(datasetId, {
          test_cases: testCases,
          overwrite_existing: overwriteExisting,
        });
      } else {
        // Create full dataset
        const nameToUse = newDatasetName.trim() || parsed.name || 'Imported Dataset';
        res = await importFullDataset({
          name: nameToUse,
          description: parsed.description,
          test_cases: testCases,
          overwrite_existing: overwriteExisting,
        });
      }

      setResult(res);
      if (res.imported_count > 0) {
        onSuccess();
      }
    } catch (err: any) {
      setGeneralError(err.message || 'Import failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-content medium">
        <div className="modal-header">
          <h3>
            {datasetId
              ? `Import Test Cases into "${datasetName || 'Dataset'}"`
              : 'Import Dataset from JSON'}
          </h3>
          <button className="icon-button" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        {generalError && (
          <div className="error-banner">
            <AlertTriangle size={15} />
            <span>{generalError}</span>
          </div>
        )}

        {result && (
          <div className="import-summary-card">
            <div className="summary-status">
              <CheckCircle2 size={18} className="text-green" />
              <strong>Import Completed: {result.imported_count} test case(s) added</strong>
            </div>
            {result.skipped_count > 0 && (
              <div className="summary-warning">
                <AlertTriangle size={14} className="text-amber" />
                <span>{result.skipped_count} duplicate item(s) skipped.</span>
              </div>
            )}
            {result.errors.length > 0 && (
              <div className="import-errors-list">
                <span className="errors-label">Item Notes / Errors:</span>
                <ul>
                  {result.errors.slice(0, 5).map((err, i) => (
                    <li key={i}>
                      {err.name ? `[${err.name}] ` : ''}
                      {err.error}
                    </li>
                  ))}
                  {result.errors.length > 5 && (
                    <li>...and {result.errors.length - 5} more items.</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        )}

        <form onSubmit={handleImport} className="modal-form">
          {!datasetId && (
            <div className="form-group">
              <label htmlFor="import-ds-name">Dataset Name *</label>
              <input
                id="import-ds-name"
                type="text"
                value={newDatasetName}
                onChange={(e) => setNewDatasetName(e.target.value)}
                placeholder="e.g. BharatHome Customer Support Golden Dataset"
                required={!datasetId}
              />
            </div>
          )}

          <div className="import-toolbar">
            <label className="file-upload-label">
              <Upload size={14} />
              <span>Choose JSON File</span>
              <input type="file" accept=".json" onChange={handleFileUpload} />
            </label>

            <button type="button" className="btn-secondary small" onClick={handleLoadSample}>
              <Sparkles size={14} />
              <span>Paste Sample</span>
            </button>
          </div>

          <div className="form-group">
            <label htmlFor="import-json-text">JSON Content (single object or list of test cases)</label>
            <textarea
              id="import-json-text"
              rows={8}
              value={jsonText}
              onChange={(e) => setJsonText(e.target.value)}
              placeholder='{\n  "name": "My Golden Dataset",\n  "test_cases": [\n    {\n      "name": "Case 1",\n      "input_data": {"prompt": "..."}\n    }\n  ]\n}'
              required
            />
          </div>

          <div className="form-checkbox">
            <label>
              <input
                type="checkbox"
                checked={overwriteExisting}
                onChange={(e) => setOverwriteExisting(e.target.checked)}
              />
              <span>Overwrite existing test cases with identical names</span>
            </label>
          </div>

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isSubmitting}>
              {result ? 'Done' : 'Cancel'}
            </button>
            <button type="submit" className="primary-button" disabled={isSubmitting || !jsonText.trim()}>
              {isSubmitting ? 'Importing...' : 'Validate & Import'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
