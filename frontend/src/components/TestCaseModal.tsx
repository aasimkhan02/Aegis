import React, { useState } from 'react';
import { X, AlertCircle } from 'lucide-react';
import { TestCase, TestCaseCreatePayload } from '../types/dataset';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSave: (payload: TestCaseCreatePayload) => Promise<void>;
  initialData?: TestCase | null;
}

export const TestCaseModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onSave,
  initialData,
}) => {
  if (!isOpen) return null;

  const [name, setName] = useState(initialData?.name || '');
  const [prompt, setPrompt] = useState<string>(() => {
    if (!initialData) return '';
    const input = initialData.input_data;
    if (typeof input === 'string') return input;
    if (input?.messages && Array.isArray(input.messages)) {
      const userMsg = input.messages.find((m: any) => m.role === 'user');
      return userMsg?.content || JSON.stringify(input, null, 2);
    }
    if (input?.prompt) return String(input.prompt);
    return JSON.stringify(input, null, 2);
  });
  const [expectedBehavior, setExpectedBehavior] = useState(initialData?.expected_behavior || '');
  const [expectedOutput, setExpectedOutput] = useState<string>(() => {
    if (!initialData?.expected_output) return '';
    return typeof initialData.expected_output === 'string'
      ? initialData.expected_output
      : JSON.stringify(initialData.expected_output, null, 2);
  });
  const [retrievalContext, setRetrievalContext] = useState<string>(() => {
    if (!initialData?.retrieval_context || initialData.retrieval_context.length === 0) return '';
    return JSON.stringify(initialData.retrieval_context, null, 2);
  });
  const [tags, setTags] = useState(initialData?.tags?.join(', ') || '');
  const [isEnabled, setIsEnabled] = useState(initialData?.is_enabled ?? true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Test case name is required.');
      return;
    }
    if (!prompt.trim()) {
      setError('Customer input prompt is required.');
      return;
    }

    let parsedRetrieval: any = [];
    if (retrievalContext.trim()) {
      try {
        parsedRetrieval = JSON.parse(retrievalContext.trim());
      } catch {
        // If not valid JSON, treat as a single string/text chunk
        parsedRetrieval = [{ text: retrievalContext.trim() }];
      }
    }

    let parsedExpectedOutput: any = null;
    if (expectedOutput.trim()) {
      try {
        parsedExpectedOutput = JSON.parse(expectedOutput.trim());
      } catch {
        parsedExpectedOutput = { summary: expectedOutput.trim() };
      }
    }

    let parsedInputData: any;
    try {
      parsedInputData = JSON.parse(prompt.trim());
    } catch {
      parsedInputData = {
        messages: [{ role: 'user', content: prompt.trim() }],
      };
    }

    const payload: TestCaseCreatePayload = {
      name: name.trim(),
      input_data: parsedInputData,
      expected_output: parsedExpectedOutput,
      expected_behavior: expectedBehavior.trim() || undefined,
      retrieval_context: parsedRetrieval,
      tags: tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
      is_enabled: isEnabled,
    };

    setIsSubmitting(true);
    setError(null);
    try {
      await onSave(payload);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to save test case');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-content large">
        <div className="modal-header">
          <h3>{initialData ? 'Edit Test Case' : 'New Test Case'}</h3>
          <button className="icon-button" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        {error && (
          <div className="error-banner">
            <AlertCircle size={15} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label htmlFor="tc-name">Test Case Name *</label>
            <input
              id="tc-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Refrigerator Error Code E4 Troubleshooting"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="tc-tags">Category Tags (comma-separated)</label>
            <input
              id="tc-tags"
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="e.g. troubleshooting, refrigerator, warranty"
            />
          </div>

          <div className="form-group">
            <label htmlFor="tc-prompt">Customer Input Prompt *</label>
            <textarea
              id="tc-prompt"
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="What does the customer say or ask?"
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group flex-1">
              <label htmlFor="tc-behavior">Expected Behavior</label>
              <textarea
                id="tc-behavior"
                rows={3}
                value={expectedBehavior}
                onChange={(e) => setExpectedBehavior(e.target.value)}
                placeholder="How the assistant should respond or behave..."
              />
            </div>
            <div className="form-group flex-1">
              <label htmlFor="tc-expected-out">Expected Output (Text or JSON)</label>
              <textarea
                id="tc-expected-out"
                rows={3}
                value={expectedOutput}
                onChange={(e) => setExpectedOutput(e.target.value)}
                placeholder='e.g. {"must_include": ["defrost sensor", "unplug"]}'
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="tc-context">Retrieval Context (Knowledge / Manual Passages)</label>
            <textarea
              id="tc-context"
              rows={3}
              value={retrievalContext}
              onChange={(e) => setRetrievalContext(e.target.value)}
              placeholder='[{"document": "Manual v2", "section": "8.2", "text": "Error E4 indicates..."}]'
            />
          </div>

          <div className="form-checkbox">
            <label>
              <input
                type="checkbox"
                checked={isEnabled}
                onChange={(e) => setIsEnabled(e.target.checked)}
              />
              <span>Enabled for evaluations</span>
            </label>
          </div>

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" className="primary-button" disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : initialData ? 'Update Test Case' : 'Create Test Case'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

