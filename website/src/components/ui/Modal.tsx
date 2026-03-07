import React, { useState, useRef, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';

interface ModalProps {
    open: boolean;
    onClose: () => void;
    title: string;
    description?: string;
    children: React.ReactNode;
    footer?: React.ReactNode;
    size?: 'sm' | 'md' | 'lg' | 'xl';
    bodyClassName?: string;
}

export function Modal({ open, onClose, title, description, children, footer, size = 'md', bodyClassName }: ModalProps) {
    const overlayRef = useRef<HTMLDivElement>(null);

    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose();
    }, [onClose]);

    useEffect(() => {
        if (open) {
            document.addEventListener('keydown', handleKeyDown);
            document.body.style.overflow = 'hidden';
        }
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            document.body.style.overflow = '';
        };
    }, [open, handleKeyDown]);

    if (!open) return null;

    const sizeClasses = {
        sm: 'max-w-md',
        md: 'max-w-lg',
        lg: 'max-w-2xl',
        xl: 'max-w-4xl',
    };

    return (
        <div
            ref={overlayRef}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
            role="dialog"
            aria-modal="true"
            aria-label={title}
        >
            <div className="fixed inset-0 bg-black/20 backdrop-blur-sm" />
            <div className={cn(
                'relative w-full bg-white rounded-3xl shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1)] border border-cream-200 flex flex-col max-h-[85vh]',
                sizeClasses[size]
            )}>
                {/* Header */}
                <div className="flex items-center justify-between p-6 pb-4 border-b border-cream-200">
                    <div>
                        <h2 className="text-xl font-display font-bold text-slate-800">{title}</h2>
                        {description && <p className="text-sm text-slate-500 mt-1">{description}</p>}
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-cream-100 rounded-xl transition-colors text-slate-400 hover:text-slate-600"
                        aria-label="Close"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Body */}
                <div className={cn('flex-1 overflow-y-auto p-6', bodyClassName)}>
                    {children}
                </div>

                {/* Footer */}
                {footer && (
                    <div className="flex items-center justify-end gap-3 p-6 pt-4 border-t border-cream-200">
                        {footer}
                    </div>
                )}
            </div>
        </div>
    );
}

// ─── Confirm Dialog ─────────────────────────────────────────────────────────

interface ConfirmDialogProps {
    open: boolean;
    onClose: () => void;
    onConfirm: () => void;
    title: string;
    description: string;
    confirmLabel?: string;
    danger?: boolean;
    loading?: boolean;
}

export function ConfirmDialog({ open, onClose, onConfirm, title, description, confirmLabel = 'Confirm', danger = false, loading = false }: ConfirmDialogProps) {
    return (
        <Modal open={open} onClose={onClose} title={title} size="sm" footer={
            <>
                <button
                    onClick={onClose}
                    className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-cream-100 rounded-xl transition-colors"
                >
                    Cancel
                </button>
                <button
                    onClick={onConfirm}
                    disabled={loading}
                    className={cn(
                        'px-4 py-2 text-sm font-semibold rounded-xl transition-colors disabled:opacity-50',
                        danger
                            ? 'bg-red-500 text-white hover:bg-red-600'
                            : 'bg-indigo-600 text-white hover:bg-indigo-700'
                    )}
                >
                    {loading ? 'Processing...' : confirmLabel}
                </button>
            </>
        }>
            <p className="text-sm text-slate-600">{description}</p>
        </Modal>
    );
}
