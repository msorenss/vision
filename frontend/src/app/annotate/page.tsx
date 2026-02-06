'use client';

import { useState, useEffect, useCallback, useRef, Suspense, type MouseEvent as ReactMouseEvent } from 'react';
import { useSearchParams } from 'next/navigation';
import styles from './page.module.css';

interface Annotation {
    class_id: number;
    x_center: number;
    y_center: number;
    width: number;
    height: number;
}

interface ImageInfo {
    id: string;
    filename: string;
    split: string;
    has_annotations: boolean;
    annotation_count: number;
}

function AnnotateContent() {
    const searchParams = useSearchParams();
    const dataset = searchParams.get('dataset') || '';

    const [images, setImages] = useState<ImageInfo[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [annotations, setAnnotations] = useState<Annotation[]>([]);
    const [classes, setClasses] = useState<string[]>([]);
    const [selectedClass, setSelectedClass] = useState(0);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [drawing, setDrawing] = useState(false);
    const [startPos, setStartPos] = useState<{ x: number; y: number } | null>(null);
    const [currentBox, setCurrentBox] = useState<{ x1: number; y1: number; x2: number; y2: number } | null>(null);

    const canvasRef = useRef<HTMLCanvasElement>(null);
    const imageRef = useRef<HTMLImageElement>(null);

    const apiBase = typeof window !== 'undefined'
        ? localStorage.getItem('apiBase') || 'http://localhost:8000'
        : 'http://localhost:8000';

    const currentImage = images[currentIndex];

    const fetchImages = useCallback(async () => {
        if (!dataset) return;
        try {
            const res = await fetch(`${apiBase}/api/v1/datasets/${dataset}/images`);
            if (!res.ok) throw new Error('Failed to fetch images');
            const data = await res.json();
            setImages(data.images);
        } catch (e) {
            console.error(e);
        }
    }, [apiBase, dataset]);

    const fetchClasses = useCallback(async () => {
        if (!dataset) return;
        try {
            const res = await fetch(`${apiBase}/api/v1/datasets/${dataset}/classes`);
            if (!res.ok) throw new Error('Failed to fetch classes');
            const data = await res.json();
            setClasses(data.classes);
        } catch (e) {
            console.error(e);
        }
    }, [apiBase, dataset]);

    const fetchAnnotations = useCallback(async () => {
        if (!dataset || !currentImage) return;
        try {
            const res = await fetch(
                `${apiBase}/api/v1/datasets/${dataset}/images/${currentImage.id}/annotations?split=${currentImage.split}`
            );
            if (!res.ok) throw new Error('Failed to fetch annotations');
            const data = await res.json();
            setAnnotations(data.annotations);
        } catch (e) {
            console.error(e);
        }
    }, [apiBase, dataset, currentImage]);

    useEffect(() => {
        fetchImages();
        fetchClasses();
    }, [fetchImages, fetchClasses]);

    useEffect(() => {
        if (currentImage) {
            fetchAnnotations();
            setLoading(true);
        }
    }, [currentImage, fetchAnnotations]);

    const drawCanvas = useCallback(() => {
        const canvas = canvasRef.current;
        const img = imageRef.current;
        if (!canvas || !img) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;

        ctx.drawImage(img, 0, 0);

        // Draw existing annotations
        annotations.forEach((ann: Annotation) => {
            const x = (ann.x_center - ann.width / 2) * canvas.width;
            const y = (ann.y_center - ann.height / 2) * canvas.height;
            const w = ann.width * canvas.width;
            const h = ann.height * canvas.height;

            const colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];
            const color = colors[ann.class_id % colors.length];

            ctx.strokeStyle = color;
            ctx.lineWidth = 3;
            ctx.strokeRect(x, y, w, h);

            ctx.fillStyle = color;
            ctx.fillRect(x, y - 24, Math.max(w, 60), 24);
            ctx.fillStyle = '#fff';
            ctx.font = '14px sans-serif';
            ctx.fillText(classes[ann.class_id] || `Class ${ann.class_id}`, x + 4, y - 8);
        });

        // Draw current box being drawn
        if (currentBox) {
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 2;
            ctx.setLineDash([5, 5]);
            ctx.strokeRect(
                currentBox.x1,
                currentBox.y1,
                currentBox.x2 - currentBox.x1,
                currentBox.y2 - currentBox.y1
            );
            ctx.setLineDash([]);
        }
    }, [annotations, classes, currentBox]);

    useEffect(() => {
        drawCanvas();
    }, [drawCanvas, loading]);

    const handleMouseDown = (e: ReactMouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const x = (e.clientX - rect.left) * scaleX;
        const y = (e.clientY - rect.top) * scaleY;

        setDrawing(true);
        setStartPos({ x, y });
        setCurrentBox({ x1: x, y1: y, x2: x, y2: y });
    };

    const handleMouseMove = (e: ReactMouseEvent<HTMLCanvasElement>) => {
        if (!drawing || !startPos) return;

        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const x = (e.clientX - rect.left) * scaleX;
        const y = (e.clientY - rect.top) * scaleY;

        setCurrentBox({
            x1: Math.min(startPos.x, x),
            y1: Math.min(startPos.y, y),
            x2: Math.max(startPos.x, x),
            y2: Math.max(startPos.y, y),
        });
    };

    const handleMouseUp = () => {
        if (!drawing || !currentBox) {
            setDrawing(false);
            return;
        }

        const canvas = canvasRef.current;
        if (!canvas) return;

        const w = currentBox.x2 - currentBox.x1;
        const h = currentBox.y2 - currentBox.y1;

        if (w > 10 && h > 10) {
            const newAnn: Annotation = {
                class_id: selectedClass,
                x_center: (currentBox.x1 + w / 2) / canvas.width,
                y_center: (currentBox.y1 + h / 2) / canvas.height,
                width: w / canvas.width,
                height: h / canvas.height,
            };
            setAnnotations([...annotations, newAnn]);
        }

        setDrawing(false);
        setStartPos(null);
        setCurrentBox(null);
    };

    const handleSave = async () => {
        if (!dataset || !currentImage) return;

        setSaving(true);
        try {
            const res = await fetch(
                `${apiBase}/api/v1/datasets/${dataset}/images/${currentImage.id}/annotations?split=${currentImage.split}`,
                {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ annotations }),
                }
            );
            if (!res.ok) throw new Error('Failed to save');
        } catch {
            alert('Failed to save annotations');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = (index: number) => {
        setAnnotations(annotations.filter((_: Annotation, i: number) => i !== index));
    };

    const handlePrev = () => {
        if (currentIndex > 0) setCurrentIndex(currentIndex - 1);
    };

    const handleNext = () => {
        if (currentIndex < images.length - 1) setCurrentIndex(currentIndex + 1);
    };

    if (!dataset) {
        return (
            <div className={styles['no-dataset']}>
                <h2>No dataset selected</h2>
                <p>Go to <a href="/datasets">Datasets</a> and click Annotate on a dataset.</p>
            </div>
        );
    }

    return (
        <div className={styles['annotate-page']}>
            <div className={styles.sidebar}>
                <div className={styles['sidebar-header']}>
                    <h2>📁 {dataset}</h2>
                    <p>{images.length} images</p>
                </div>

                <div className={styles['class-selector']}>
                    <h3>Select Class</h3>
                    <div className={styles['class-buttons']}>
                        {classes.map((cls: string, i: number) => (
                            <button
                                key={cls}
                                className={`${styles['class-btn']} ${selectedClass === i ? styles.active : ''}`}
                                onClick={() => setSelectedClass(i)}
                            >
                                {cls}
                            </button>
                        ))}
                    </div>
                </div>

                <div className={styles['annotations-list']}>
                    <h3>Annotations ({annotations.length})</h3>
                    {annotations.map((ann: Annotation, i: number) => (
                        <div key={i} className={styles['ann-item']}>
                            <span>{classes[ann.class_id] || `Class ${ann.class_id}`}</span>
                            <button className={styles['ann-delete']} onClick={() => handleDelete(i)}>×</button>
                        </div>
                    ))}
                </div>

                <div className={styles['sidebar-footer']}>
                    <button className={styles['btn-save']} onClick={handleSave} disabled={saving}>
                        {saving ? 'Saving...' : '💾 Save Annotations'}
                    </button>
                </div>
            </div>

            <div className={styles['main-content']}>
                <div className={styles.toolbar}>
                    <a href="/datasets" className={styles['back-link']}>← Back to Datasets</a>
                    <div className={styles['nav-controls']}>
                        <button className={styles['nav-btn']} onClick={handlePrev} disabled={currentIndex === 0}>
                            ◀ Prev
                        </button>
                        <span className={styles['nav-info']}>
                            {currentIndex + 1} / {images.length}
                            {currentImage && ` - ${currentImage.filename}`}
                        </span>
                        <button className={styles['nav-btn']} onClick={handleNext} disabled={currentIndex >= images.length - 1}>
                            Next ▶
                        </button>
                    </div>
                    <div></div>
                </div>

                <div className={styles['canvas-container']}>
                    {currentImage ? (
                        <>
                            <img
                                ref={imageRef}
                                src={`${apiBase}/api/v1/datasets/${dataset}/images/${currentImage.id}/file?split=${currentImage.split}`}
                                alt={currentImage.filename}
                                onLoad={() => { setLoading(false); drawCanvas(); }}
                                className={styles['hidden-img']}
                            />
                            <canvas
                                ref={canvasRef}
                                onMouseDown={handleMouseDown}
                                onMouseMove={handleMouseMove}
                                onMouseUp={handleMouseUp}
                                onMouseLeave={handleMouseUp}
                            />
                        </>
                    ) : (
                        <p className={styles['no-images']}>No images to annotate</p>
                    )}
                </div>
            </div>
        </div>
    );
}

export default function AnnotatePage() {
    return (
        <Suspense fallback={<div className={styles['no-dataset']}>Loading...</div>}>
            <AnnotateContent />
        </Suspense>
    );
}
