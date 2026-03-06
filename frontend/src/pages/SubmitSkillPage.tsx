import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import api from '../api/client';
import { useCategories } from '../hooks/useCategories';

interface SkillForm {
  name: string;
  description: string;
  content: string;
  version: string;
  category_id: number | '';
  tag_names: string;
}

export default function SubmitSkillPage() {
  const navigate = useNavigate();
  const { data: categories } = useCategories();
  const [showPreview, setShowPreview] = useState(false);
  const [form, setForm] = useState<SkillForm>({
    name: '',
    description: '',
    content: '# Skill Name\n\n## Overview\n\n## Instructions\n\n## Example\n',
    version: '1.0.0',
    category_id: '',
    tag_names: '',
  });
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: async () => {
      const tags = form.tag_names
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      const { data } = await api.post('/skills', {
        name: form.name,
        description: form.description,
        content: form.content,
        version: form.version,
        category_id: Number(form.category_id),
        tag_names: tags,
      });
      return data;
    },
    onSuccess: (data) => {
      navigate(`/skills/${data.slug}`);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to create skill');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!form.name || !form.description || !form.content || !form.category_id) {
      setError('Please fill in all required fields');
      return;
    }
    mutation.mutate();
  };

  const updateField = (field: keyof SkillForm, value: string | number) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Submit a Skill</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => updateField('name', e.target.value)}
              placeholder="e.g. Python Best Practices"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Category *</label>
            <select
              value={form.category_id}
              onChange={(e) => updateField('category_id', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Select a category</option>
              {categories?.map((cat) => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description *</label>
          <textarea
            value={form.description}
            onChange={(e) => updateField('description', e.target.value)}
            placeholder="Brief description of what this skill does..."
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tags (comma-separated)</label>
            <input
              type="text"
              value={form.tag_names}
              onChange={(e) => updateField('tag_names', e.target.value)}
              placeholder="python, testing, best-practices"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Version</label>
            <input
              type="text"
              value={form.version}
              onChange={(e) => updateField('version', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-sm font-medium text-gray-700">SKILL.md Content *</label>
            <button
              type="button"
              onClick={() => setShowPreview(!showPreview)}
              className="text-xs text-indigo-600 hover:underline"
            >
              {showPreview ? 'Edit' : 'Preview'}
            </button>
          </div>
          {showPreview ? (
            <div className="min-h-[300px] p-4 bg-white border border-gray-300 rounded-md prose prose-sm max-w-none">
              <ReactMarkdown>{form.content}</ReactMarkdown>
            </div>
          ) : (
            <textarea
              value={form.content}
              onChange={(e) => updateField('content', e.target.value)}
              rows={14}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          )}
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="px-6 py-2.5 bg-indigo-600 text-white font-medium rounded-md hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {mutation.isPending ? 'Publishing...' : 'Publish Skill'}
          </button>
        </div>
      </form>
    </div>
  );
}
