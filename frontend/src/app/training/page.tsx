'use client';

import { useState, useEffect, useCallback, type ChangeEvent } from 'react';
import styles from './page.module.css';

interface Dataset {
    name: string;
    image_count: number;
    annotated_count: number;
    classes: string[];
}

interface TrainingStatus {
    job_id: string;
    status: 'queued' | 'running' | 'completed' | 'failed' | 'stopped';
    dataset: string;
    current_epoch: number;
    total_epochs: number;
    progress_percent: number;
    elapsed_seconds: number;
    eta_seconds?: number;
    best_map50?: number;
    output_path?: string;
    error_message?: string;
}

interface TrainingJob {
    job_id: string;
    dataset: string;
    status: string;
    started_at: string;
    finished_at?: string;
    epochs_completed: number;
    best_map50?: number;
}

export default function TrainingPage() {
    const [datasets, setDatasets] = useState<Dataset[]>([]);
    const [selectedDataset, setSelectedDataset] = useState('');
    const [status, setStatus] = useState<TrainingStatus | null>(null);
    const [history, setHistory] = useState<TrainingJob[]>([]);
    const [logs, setLogs] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [starting, setStarting] = useState(false);

    // Training config
    const [config, setConfig] = useState({
        epochs: 100,
        batch_size: 16,
        img_size: 640,
        model_variant: 'yolov8n',
        device: 'cpu',
    });

    const apiBase = typeof window !== 'undefined'
        ? localStorage.getItem('apiBase') || 'http://localhost:8000'
        : 'http://localhost:8000';

    const fetchDatasets = useCallback(async () => {
        try {
            const res = await fetch(`${apiBase}/api/v1/datasets`);
            if (res.ok) {
                const data = await res.json();
                setDatasets(data.datasets);
                if (data.datasets.length > 0 && !selectedDataset) {
                    setSelectedDataset(data.datasets[0].name);
                }
            }
        } catch (e) {
            console.error(e);
        }
    }, [apiBase, selectedDataset]);

    const fetchStatus = useCallback(async () => {
        try {
            const res = await fetch(`${apiBase}/api/v1/training/status`);
            if (res.ok) {
                setStatus(await res.json());
            } else {
                setStatus(null);
            }
        } catch {
            setStatus(null);
        }
    }, [apiBase]);

    const fetchHistory = useCallback(async () => {
        try {
            const res = await fetch(`${apiBase}/api/v1/training/history`);
            if (res.ok) {
                const data = await res.json();
                setHistory(data.jobs);
            }
        } catch (e) {
            console.error(e);
        }
    }, [apiBase]);

    const fetchLogs = useCallback(async () => {
        try {
            const res = await fetch(`${apiBase}/api/v1/training/logs`);
            if (res.ok) {
                const data = await res.json();
                setLogs(data.logs);
            }
        } catch (e) {
            console.error(e);
        }
    }, [apiBase]);

    useEffect(() => {
        fetchDatasets();
        fetchStatus();
        fetchHistory();
        setLoading(false);
    }, [fetchDatasets, fetchStatus, fetchHistory]);

    // Poll for status when training
    useEffect(() => {
        if (status?.status === 'running' || status?.status === 'queued') {
            const interval = setInterval(() => {
                fetchStatus();
                fetchLogs();
            }, 2000);
            return () => clearInterval(interval);
        }
    }, [status?.status, fetchStatus, fetchLogs]);

    const handleStart = async () => {
        if (!selectedDataset) return;

        setStarting(true);
        try {
            const res = await fetch(`${apiBase}/api/v1/training/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    dataset: selectedDataset,
                    ...config,
                }),
            });

            if (!res.ok) {
                const err = await res.json();
                alert(err.detail || 'Failed to start training');
            } else {
                fetchStatus();
            }
        } catch {
            alert('Failed to start training');
        } finally {
            setStarting(false);
        }
    };

    const handleStop = async () => {
        try {
            await fetch(`${apiBase}/api/v1/training/stop`, { method: 'POST' });
            fetchStatus();
        } catch {
            alert('Failed to stop training');
        }
    };

    const formatTime = (seconds: number): string => {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        return h > 0 ? `${h}h ${m}m ${s}s` : m > 0 ? `${m}m ${s}s` : `${s}s`;
    };

    const isTraining = status?.status === 'running' || status?.status === 'queued';

    return (
        <div className={styles['training-page']}>
            <div className={styles.header}>
                <a href="/" className={styles['back-link']}>← Back to Home</a>
                <h1>🚀 Training</h1>
            </div>

            {/* Current Training Status */}
            {status && (
                <div className={`${styles.card} ${styles['status-card']}`}>
                    <div className={styles['status-header']}>
                        <h2>Training: {status.dataset}</h2>
                        <span className={`${styles['status-badge']} ${styles[`status-${status.status}`]}`}>{status.status}</span>
                    </div>

                    {status.status === 'running' && (
                        <>
                            <div className={styles['progress-bar']}>
                                <div className={styles['progress-fill']} style={{ width: `${status.progress_percent}%` }} />
                            </div>

                            <div className={styles['stats-grid']}>
                                <div className={styles['stat-item']}>
                                    <div className={styles['stat-value']}>{status.current_epoch}</div>
                                    <div className={styles['stat-label']}>Epoch</div>
                                </div>
                                <div className={styles['stat-item']}>
                                    <div className={styles['stat-value']}>{status.total_epochs}</div>
                                    <div className={styles['stat-label']}>Total</div>
                                </div>
                                <div className={styles['stat-item']}>
                                    <div className={styles['stat-value']}>{formatTime(status.elapsed_seconds)}</div>
                                    <div className={styles['stat-label']}>Elapsed</div>
                                </div>
                                <div className={styles['stat-item']}>
                                    <div className={styles['stat-value']}>{status.eta_seconds ? formatTime(status.eta_seconds) : '-'}</div>
                                    <div className={styles['stat-label']}>ETA</div>
                                </div>
                            </div>

                            {status.best_map50 && (
                                <p className={styles['text-success']}>
                                    Best mAP50: {(status.best_map50 * 100).toFixed(1)}%
                                </p>
                            )}

                            <button className={styles['btn-stop']} onClick={handleStop}>⏹ Stop Training</button>
                        </>
                    )}

                    {status.status === 'completed' && status.output_path && (
                        <p className={styles['text-success']}>✓ Model saved to: {status.output_path}</p>
                    )}

                    {status.status === 'failed' && status.error_message && (
                        <p className={styles['text-error']}>Error: {status.error_message}</p>
                    )}

                    {logs.length > 0 && (
                        <div className={styles['logs-container']}>
                            {logs.slice(-20).map((log: string, i: number) => (
                                <p key={i}>{log}</p>
                            ))}
                        </div>
                    )}
                </div>
            )}

            <div className={styles.grid}>
                {/* Config Panel */}
                <div className={styles.card}>
                    <h2>⚙️ Configuration</h2>

                    <div className={styles['form-group']}>
                        <label htmlFor="dataset-select">Dataset</label>
                        <select
                            id="dataset-select"
                            value={selectedDataset}
                            onChange={(e: ChangeEvent<HTMLSelectElement>) => setSelectedDataset(e.target.value)}
                            disabled={isTraining}
                        >
                            {datasets.map((ds: Dataset) => (
                                <option key={ds.name} value={ds.name}>
                                    {ds.name} ({ds.image_count} images, {ds.annotated_count} annotated)
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className={styles['form-group']}>
                        <label htmlFor="model-variant-select">Model Variant</label>
                        <select
                            id="model-variant-select"
                            value={config.model_variant}
                            onChange={(e: ChangeEvent<HTMLSelectElement>) => setConfig({ ...config, model_variant: e.target.value })}
                            disabled={isTraining}
                        >
                            <option value="yolov8n">YOLOv8n (Nano - Fast)</option>
                            <option value="yolov8s">YOLOv8s (Small)</option>
                            <option value="yolov8m">YOLOv8m (Medium)</option>
                            <option value="yolov8l">YOLOv8l (Large)</option>
                            <option value="yolov8x">YOLOv8x (Extra Large)</option>
                        </select>
                    </div>

                    <div className={styles['form-row']}>
                        <div className={styles['form-group']}>
                            <label htmlFor="epochs-input">Epochs</label>
                            <input
                                id="epochs-input"
                                type="number"
                                value={config.epochs}
                                onChange={(e: ChangeEvent<HTMLInputElement>) => setConfig({ ...config, epochs: parseInt(e.target.value) || 100 })}
                                disabled={isTraining}
                                min={1}
                                max={1000}
                            />
                        </div>
                        <div className={styles['form-group']}>
                            <label htmlFor="batch-size-input">Batch Size</label>
                            <input
                                id="batch-size-input"
                                type="number"
                                value={config.batch_size}
                                onChange={(e: ChangeEvent<HTMLInputElement>) => setConfig({ ...config, batch_size: parseInt(e.target.value) || 16 })}
                                disabled={isTraining}
                                min={1}
                                max={128}
                            />
                        </div>
                    </div>

                    <div className={styles['form-row']}>
                        <div className={styles['form-group']}>
                            <label htmlFor="img-size-input">Image Size</label>
                            <input
                                id="img-size-input"
                                type="number"
                                value={config.img_size}
                                onChange={(e: ChangeEvent<HTMLInputElement>) => setConfig({ ...config, img_size: parseInt(e.target.value) || 640 })}
                                disabled={isTraining}
                                min={32}
                                max={1280}
                                step={32}
                            />
                        </div>
                        <div className={styles['form-group']}>
                            <label htmlFor="device-select">Device</label>
                            <select
                                id="device-select"
                                value={config.device}
                                onChange={(e: ChangeEvent<HTMLSelectElement>) => setConfig({ ...config, device: e.target.value })}
                                disabled={isTraining}
                            >
                                <option value="cpu">CPU</option>
                                <option value="0">GPU 0</option>
                                <option value="cuda">CUDA (Auto)</option>
                            </select>
                        </div>
                    </div>

                    <button
                        className={styles['btn-start']}
                        onClick={handleStart}
                        disabled={isTraining || starting || !selectedDataset}
                    >
                        {starting ? 'Starting...' : isTraining ? 'Training in Progress...' : '▶ Start Training'}
                    </button>
                </div>

                {/* History Panel */}
                <div className={styles.card}>
                    <h2>📜 Training History</h2>
                    <div className={styles['history-list']}>
                        {history.length === 0 ? (
                            <p className={styles['text-muted']}>No training history yet</p>
                        ) : (
                            history.map((job: TrainingJob) => (
                                <div key={job.job_id} className={styles['history-item']}>
                                    <div>
                                        <span>{job.dataset}</span>
                                        <br />
                                        <small>
                                            {job.epochs_completed} epochs |
                                            {job.best_map50 ? ` mAP: ${(job.best_map50 * 100).toFixed(1)}%` : ' No metrics'}
                                        </small>
                                    </div>
                                    <span className={`${styles['status-badge']} ${styles[`status-${job.status}`]}`}>{job.status}</span>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
