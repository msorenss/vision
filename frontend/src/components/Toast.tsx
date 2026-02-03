"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

type ToastType = "success" | "error" | "warning" | "info";

type Toast = {
    id: string;
    type: ToastType;
    message: string;
    duration?: number;
};

type ToastContextType = {
    toasts: Toast[];
    addToast: (type: ToastType, message: string, duration?: number) => void;
    removeToast: (id: string) => void;
    success: (message: string) => void;
    error: (message: string) => void;
    warning: (message: string) => void;
    info: (message: string) => void;
};

const ToastContext = createContext<ToastContextType | null>(null);

let toastIdCounter = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const removeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    const addToast = useCallback(
        (type: ToastType, message: string, duration = 4000) => {
            const id = `toast-${++toastIdCounter}`;
            const toast: Toast = { id, type, message, duration };

            setToasts((prev) => [...prev, toast]);

            if (duration > 0) {
                setTimeout(() => {
                    removeToast(id);
                }, duration);
            }
        },
        [removeToast]
    );

    const success = useCallback((msg: string) => addToast("success", msg), [addToast]);
    const error = useCallback((msg: string) => addToast("error", msg, 6000), [addToast]);
    const warning = useCallback((msg: string) => addToast("warning", msg), [addToast]);
    const info = useCallback((msg: string) => addToast("info", msg), [addToast]);

    return (
        <ToastContext.Provider value={{ toasts, addToast, removeToast, success, error, warning, info }}>
            {children}
            <ToastContainer toasts={toasts} onRemove={removeToast} />
        </ToastContext.Provider>
    );
}

export function useToast() {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error("useToast must be used within ToastProvider");
    }
    return context;
}

function ToastContainer({ toasts, onRemove }: { toasts: Toast[]; onRemove: (id: string) => void }) {
    if (toasts.length === 0) return null;

    return (
        <div
            style={{
                position: "fixed",
                top: "var(--space-6)",
                right: "var(--space-6)",
                display: "flex",
                flexDirection: "column",
                gap: "var(--space-3)",
                zIndex: "var(--z-toast)",
                pointerEvents: "none",
                maxWidth: "400px",
                width: "100%"
            }}
        >
            {toasts.map((toast) => (
                <ToastItem key={toast.id} toast={toast} onClose={() => onRemove(toast.id)} />
            ))}
        </div>
    );
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
    const icons: Record<ToastType, string> = {
        success: "✓",
        error: "✕",
        warning: "⚠",
        info: "ℹ"
    };

    const colors: Record<ToastType, { bg: string; border: string; icon: string }> = {
        success: {
            bg: "var(--color-success-bg)",
            border: "var(--color-success)",
            icon: "var(--color-success)"
        },
        error: {
            bg: "var(--color-error-bg)",
            border: "var(--color-error)",
            icon: "var(--color-error)"
        },
        warning: {
            bg: "var(--color-warning-bg)",
            border: "var(--color-warning)",
            icon: "var(--color-warning)"
        },
        info: {
            bg: "var(--color-primary-light)",
            border: "var(--color-primary)",
            icon: "var(--color-primary)"
        }
    };

    const style = colors[toast.type];

    return (
        <div
            style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "var(--space-3)",
                padding: "var(--space-4)",
                background: "var(--color-bg-card)",
                backdropFilter: "blur(10px)",
                border: `1px solid ${style.border}`,
                borderLeft: `4px solid ${style.border}`,
                borderRadius: "var(--radius-lg)",
                boxShadow: "var(--shadow-lg)",
                animation: "slideInRight 0.3s ease-out",
                pointerEvents: "auto"
            }}
        >
            <span
                style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "24px",
                    height: "24px",
                    borderRadius: "50%",
                    background: style.bg,
                    color: style.icon,
                    fontWeight: "bold",
                    fontSize: "14px",
                    flexShrink: 0
                }}
            >
                {icons[toast.type]}
            </span>
            <p
                style={{
                    flex: 1,
                    margin: 0,
                    fontSize: "var(--font-size-sm)",
                    color: "var(--color-text-primary)",
                    lineHeight: 1.5
                }}
            >
                {toast.message}
            </p>
            <button
                onClick={onClose}
                style={{
                    background: "none",
                    border: "none",
                    padding: "var(--space-1)",
                    cursor: "pointer",
                    color: "var(--color-text-muted)",
                    fontSize: "18px",
                    lineHeight: 1,
                    flexShrink: 0
                }}
                aria-label="Close"
            >
                ×
            </button>
        </div>
    );
}
