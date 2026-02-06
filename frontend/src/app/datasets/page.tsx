'use client';

import { useState, useEffect, useCallback, type ChangeEvent, type MouseEvent } from 'react';
import styles from './page.module.css';

interface Dataset {
  name: string;
  path: string;
  classes: string[];
  description?: string;
  image_count: number;
  train_count: number;
  val_count: number;
  annotated_count: number;
}

interface DatasetListResponse {
  datasets_dir: string;
  datasets: Dataset[];
}

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newDataset, setNewDataset] = useState({ name: '', classes: '', description: '' });
  const [creating, setCreating] = useState(false);

  const apiBase = typeof window !== 'undefined'
    ? localStorage.getItem('apiBase') || 'http://localhost:8000'
    : 'http://localhost:8000';

  const fetchDatasets = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch(`${apiBase}/api/v1/datasets`);
      if (!res.ok) throw new Error('Failed to fetch datasets');
      const data: DatasetListResponse = await res.json();
      setDatasets(data.datasets);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const handleCreate = async () => {
    if (!newDataset.name.trim()) return;

    setCreating(true);
    try {
      const res = await fetch(`${apiBase}/api/v1/datasets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newDataset.name.trim(),
          classes: newDataset.classes.split(',').map((c: string) => c.trim()).filter((c: string) => c),
          description: newDataset.description || undefined,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create dataset');
      }

      setShowCreateModal(false);
      setNewDataset({ name: '', classes: '', description: '' });
      fetchDatasets();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to create dataset');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete dataset "${name}"? This cannot be undone.`)) return;

    try {
      const res = await fetch(`${apiBase}/api/v1/datasets/${name}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete');
      fetchDatasets();
    } catch {
      alert('Failed to delete dataset');
    }
  };

  const handleModalClick = (e: MouseEvent) => {
    e.stopPropagation();
  };

  return (
    <div className={styles['datasets-page']}>
      <a href="/" className={styles['nav-back']}>← Back to Home</a>

      <div className={styles.header}>
        <h1>📁 Datasets</h1>
        <button className={styles['btn-primary']} onClick={() => setShowCreateModal(true)}>
          + New Dataset
        </button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {loading ? (
        <div className={styles.loading}>Loading datasets...</div>
      ) : datasets.length === 0 ? (
        <div className={styles['empty-state']}>
          <h3>No datasets yet</h3>
          <p>Create your first dataset to start training models</p>
          <button className={styles['btn-primary']} onClick={() => setShowCreateModal(true)}>
            Create Dataset
          </button>
        </div>
      ) : (
        <div className={styles['datasets-grid']}>
          {datasets.map((ds: Dataset) => (
            <div key={ds.name} className={styles['dataset-card']}>
              <div className={styles['dataset-name']}>{ds.name}</div>
              {ds.description && (
                <div className={styles['dataset-desc']}>{ds.description}</div>
              )}

              <div className={styles['dataset-stats']}>
                <div className={styles.stat}>
                  <div className={styles['stat-value']}>{ds.image_count}</div>
                  <div className={styles['stat-label']}>Images</div>
                </div>
                <div className={styles.stat}>
                  <div className={styles['stat-value']}>{ds.annotated_count}</div>
                  <div className={styles['stat-label']}>Annotated</div>
                </div>
                <div className={styles.stat}>
                  <div className={styles['stat-value']}>{ds.train_count}</div>
                  <div className={styles['stat-label']}>Train</div>
                </div>
                <div className={styles.stat}>
                  <div className={styles['stat-value']}>{ds.val_count}</div>
                  <div className={styles['stat-label']}>Val</div>
                </div>
              </div>

              {ds.classes.length > 0 && (
                <div className={styles['classes-list']}>
                  {ds.classes.slice(0, 5).map((cls: string) => (
                    <span key={cls} className={styles['class-tag']}>{cls}</span>
                  ))}
                  {ds.classes.length > 5 && (
                    <span className={styles['class-tag']}>+{ds.classes.length - 5} more</span>
                  )}
                </div>
              )}

              <div className={styles['card-actions']}>
                <a href={`/annotate?dataset=${ds.name}`} className={`${styles['btn-small']} ${styles['btn-annotate']}`}>
                  ✏️ Annotate
                </a>
                <button className={`${styles['btn-small']} ${styles['btn-delete']}`} onClick={() => handleDelete(ds.name)}>
                  🗑️ Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreateModal && (
        <div className={styles['modal-overlay']} onClick={() => setShowCreateModal(false)}>
          <div className={styles.modal} onClick={handleModalClick}>
            <h2>Create New Dataset</h2>

            <div className={styles['form-group']}>
              <label>Dataset Name</label>
              <input
                type="text"
                placeholder="my_dataset"
                value={newDataset.name}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setNewDataset({ ...newDataset, name: e.target.value })}
              />
            </div>

            <div className={styles['form-group']}>
              <label>Classes (comma-separated)</label>
              <input
                type="text"
                placeholder="person, car, truck"
                value={newDataset.classes}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setNewDataset({ ...newDataset, classes: e.target.value })}
              />
            </div>

            <div className={styles['form-group']}>
              <label>Description (optional)</label>
              <textarea
                placeholder="Dataset description..."
                value={newDataset.description}
                onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setNewDataset({ ...newDataset, description: e.target.value })}
                rows={3}
              />
            </div>

            <div className={styles['modal-actions']}>
              <button className={styles['btn-secondary']} onClick={() => setShowCreateModal(false)}>
                Cancel
              </button>
              <button className={styles['btn-primary']} onClick={handleCreate} disabled={creating}>
                {creating ? 'Creating...' : 'Create Dataset'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
