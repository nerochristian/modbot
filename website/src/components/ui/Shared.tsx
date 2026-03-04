import React, { useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { X, Search, ChevronDown, Check } from 'lucide-react';

// ─── Badge ──────────────────────────────────────────────────────────────────

interface BadgeProps {
    children: React.ReactNode;
    variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'premium';
    className?: string;
}

const badgeVariants = {
    default: 'bg-cream-100 text-slate-600 border-cream-200',
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    warning: 'bg-amber-50 text-amber-700 border-amber-200',
    danger: 'bg-red-50 text-red-700 border-red-200',
    info: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    premium: 'bg-purple-50 text-purple-700 border-purple-200',
};

export function Badge({ children, variant = 'default', className }: BadgeProps) {
    return (
        <span className={cn(
            'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-semibold border',
            badgeVariants[variant],
            className,
        )}>
            {children}
        </span>
    );
}

// ─── Select ─────────────────────────────────────────────────────────────────

interface SelectProps {
    value: string;
    onChange: (value: string) => void;
    options: { label: string; value: string }[];
    placeholder?: string;
    className?: string;
    disabled?: boolean;
}

export function Select({ value, onChange, options, placeholder, className, disabled }: SelectProps) {
    const [open, setOpen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);
    const selected = options.find((opt) => opt.value === value);
    const hasValue = value !== '';

    useEffect(() => {
        if (!open) return;
        function handleClick(e: MouseEvent) {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [open]);

    const selectValue = (nextValue: string) => {
        onChange(nextValue);
        setOpen(false);
    };

    return (
        <div ref={containerRef} className={cn('relative', className)}>
            <button
                type="button"
                disabled={disabled}
                onClick={() => setOpen((prev) => !prev)}
                className="w-full min-h-[42px] bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all disabled:opacity-50 disabled:cursor-not-allowed text-left flex items-center justify-between gap-2"
            >
                <span className={cn('truncate', hasValue || selected ? 'text-slate-700' : 'text-slate-400')}>
                    {selected?.label || (hasValue ? value : (placeholder || 'Select...'))}
                </span>
                <ChevronDown className={cn('w-4 h-4 text-slate-400 shrink-0 transition-transform', open && 'rotate-180')} />
            </button>

            {open && !disabled && (
                <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-white rounded-2xl border border-cream-200 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.08)] overflow-hidden">
                    <div className="max-h-64 overflow-y-auto p-1">
                        {placeholder && (
                            <button
                                type="button"
                                onClick={() => selectValue('')}
                                className={cn(
                                    'w-full flex items-center justify-between gap-3 px-3 py-2 rounded-xl text-sm transition-colors text-left',
                                    value === '' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-cream-50'
                                )}
                            >
                                <span className="truncate">{placeholder}</span>
                                {value === '' && <Check className="w-4 h-4 shrink-0" />}
                            </button>
                        )}

                        {options.length === 0 ? (
                            <div className="px-3 py-4 text-center text-sm text-slate-400">No options</div>
                        ) : (
                            options.map((opt) => (
                                <button
                                    key={opt.value}
                                    type="button"
                                    onClick={() => selectValue(opt.value)}
                                    className={cn(
                                        'w-full flex items-center justify-between gap-3 px-3 py-2 rounded-xl text-sm transition-colors text-left',
                                        value === opt.value ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700 hover:bg-cream-50'
                                    )}
                                >
                                    <span className="truncate">{opt.label}</span>
                                    {value === opt.value && <Check className="w-4 h-4 shrink-0" />}
                                </button>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

// ─── MultiSelect ────────────────────────────────────────────────────────────

interface MultiSelectProps {
    values: string[];
    onChange: (values: string[]) => void;
    options: { label: string; value: string; color?: number }[];
    placeholder?: string;
    searchable?: boolean;
    className?: string;
    maxDisplay?: number;
}

export function MultiSelect({ values, onChange, options, placeholder = 'Select...', searchable = true, className, maxDisplay = 5 }: MultiSelectProps) {
    const [open, setOpen] = useState(false);
    const [search, setSearch] = useState('');
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        function handleClick(e: MouseEvent) {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, []);

    const filtered = search
        ? options.filter(o => o.label.toLowerCase().includes(search.toLowerCase()))
        : options;

    const selected = options.filter(o => values.includes(o.value));
    const displaySelected = selected.slice(0, maxDisplay);
    const remaining = selected.length - maxDisplay;

    const toggle = (val: string) => {
        if (values.includes(val)) {
            onChange(values.filter(v => v !== val));
        } else {
            onChange([...values, val]);
        }
    };

    const removeItem = (val: string, e: React.MouseEvent) => {
        e.stopPropagation();
        onChange(values.filter(v => v !== val));
    };

    return (
        <div ref={containerRef} className={cn('relative', className)}>
            <button
                type="button"
                onClick={() => setOpen(!open)}
                className="w-full min-h-[42px] bg-cream-50 border border-cream-300 rounded-xl px-3 py-2 text-left text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all flex items-center flex-wrap gap-1.5"
            >
                {displaySelected.length > 0 ? (
                    <>
                        {displaySelected.map(item => (
                            <span key={item.value} className="inline-flex items-center gap-1 px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-md text-xs font-medium border border-indigo-200">
                                {item.label}
                                <X className="w-3 h-3 cursor-pointer hover:text-indigo-900" onClick={(e) => removeItem(item.value, e)} />
                            </span>
                        ))}
                        {remaining > 0 && (
                            <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded-md text-xs font-medium">
                                +{remaining} more
                            </span>
                        )}
                    </>
                ) : (
                    <span className="text-slate-400">{placeholder}</span>
                )}
                <ChevronDown className="w-4 h-4 text-slate-400 ml-auto shrink-0" />
            </button>

            {open && (
                <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-white rounded-2xl border border-cream-200 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.08)] max-h-64 flex flex-col">
                    {searchable && (
                        <div className="p-2 border-b border-cream-200">
                            <div className="relative">
                                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                                <input
                                    type="text"
                                    value={search}
                                    onChange={(e) => setSearch(e.target.value)}
                                    placeholder="Search..."
                                    className="w-full pl-9 pr-3 py-2 text-sm bg-cream-50 border border-cream-200 rounded-xl outline-none focus:border-indigo-400"
                                    autoFocus
                                />
                            </div>
                        </div>
                    )}
                    <div className="overflow-y-auto p-1">
                        {filtered.length === 0 && (
                            <div className="px-3 py-4 text-center text-sm text-slate-400">No results</div>
                        )}
                        {filtered.map((opt) => (
                            <button
                                key={opt.value}
                                type="button"
                                onClick={() => toggle(opt.value)}
                                className={cn(
                                    'w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm transition-colors text-left',
                                    values.includes(opt.value)
                                        ? 'bg-indigo-50 text-indigo-700'
                                        : 'text-slate-700 hover:bg-cream-50'
                                )}
                            >
                                <div className={cn(
                                    'w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-colors',
                                    values.includes(opt.value)
                                        ? 'bg-indigo-600 border-indigo-600'
                                        : 'border-cream-300'
                                )}>
                                    {values.includes(opt.value) && (
                                        <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                        </svg>
                                    )}
                                </div>
                                {opt.color !== undefined && (
                                    <div
                                        className="w-3 h-3 rounded-full shrink-0"
                                        style={{ backgroundColor: opt.color ? `#${opt.color.toString(16).padStart(6, '0')}` : '#95a5a6' }}
                                    />
                                )}
                                {opt.label}
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

// ─── Tabs ───────────────────────────────────────────────────────────────────

interface TabsProps {
    tabs: { id: string; label: string; count?: number }[];
    activeTab: string;
    onChange: (id: string) => void;
    className?: string;
}

export function Tabs({ tabs, activeTab, onChange, className }: TabsProps) {
    return (
        <div className={cn('flex gap-1 bg-cream-100 rounded-xl p-1', className)}>
            {tabs.map(tab => (
                <button
                    key={tab.id}
                    onClick={() => onChange(tab.id)}
                    className={cn(
                        'px-4 py-2 rounded-lg text-sm font-medium transition-all',
                        activeTab === tab.id
                            ? 'bg-white text-slate-900 shadow-sm'
                            : 'text-slate-500 hover:text-slate-700'
                    )}
                >
                    {tab.label}
                    {tab.count !== undefined && (
                        <span className={cn(
                            'ml-2 px-1.5 py-0.5 rounded-md text-xs',
                            activeTab === tab.id
                                ? 'bg-indigo-100 text-indigo-700'
                                : 'bg-cream-200 text-slate-500'
                        )}>
                            {tab.count}
                        </span>
                    )}
                </button>
            ))}
        </div>
    );
}

// ─── SaveBar ────────────────────────────────────────────────────────────────

interface SaveBarProps {
    dirty: boolean;
    saving: boolean;
    onSave: () => void;
    onDiscard: () => void;
    error?: string | null;
}

export function SaveBar({ dirty, saving, onSave, onDiscard, error }: SaveBarProps) {
    if (!dirty && !error) return null;

    return (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-4 bg-slate-800 text-white px-6 py-3 rounded-2xl shadow-[0_20px_60px_-15px_rgba(0,0,0,0.3)] animate-in slide-in-from-bottom-4">
            {error ? (
                <span className="text-red-300 text-sm font-medium">{error}</span>
            ) : (
                <span className="text-sm font-medium text-slate-200">You have unsaved changes</span>
            )}
            <div className="flex gap-2">
                <button
                    onClick={onDiscard}
                    className="px-4 py-1.5 text-sm font-medium text-slate-300 hover:text-white rounded-lg hover:bg-slate-700 transition-colors"
                >
                    Discard
                </button>
                <button
                    onClick={onSave}
                    disabled={saving}
                    className="px-4 py-1.5 text-sm font-semibold bg-indigo-500 hover:bg-indigo-600 rounded-lg transition-colors disabled:opacity-50"
                >
                    {saving ? 'Saving...' : 'Save Changes'}
                </button>
            </div>
        </div>
    );
}

// ─── Skeleton ───────────────────────────────────────────────────────────────

interface SkeletonProps {
    className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
    return (
        <div className={cn('animate-pulse bg-cream-200 rounded-xl', className)} />
    );
}

// ─── PageSkeleton ───────────────────────────────────────────────────────────

export function PageSkeleton() {
    return (
        <div className="space-y-8 animate-pulse">
            <div>
                <Skeleton className="h-10 w-64 mb-3" />
                <Skeleton className="h-5 w-96" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="bg-white rounded-3xl border border-cream-200 p-6 space-y-4">
                        <div className="flex items-center gap-3">
                            <Skeleton className="h-10 w-10 rounded-2xl" />
                            <Skeleton className="h-5 w-32" />
                        </div>
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-3/4" />
                    </div>
                ))}
            </div>
        </div>
    );
}

// ─── EmptyState ─────────────────────────────────────────────────────────────

interface EmptyStateProps {
    icon: React.ReactNode;
    title: string;
    description: string;
    action?: React.ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
    return (
        <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="p-4 bg-cream-100 rounded-2xl text-slate-400 mb-4">
                {icon}
            </div>
            <h3 className="text-lg font-display font-semibold text-slate-800 mb-2">{title}</h3>
            <p className="text-sm text-slate-500 max-w-md mb-6">{description}</p>
            {action}
        </div>
    );
}

// ─── SearchInput ────────────────────────────────────────────────────────────

interface SearchInputProps {
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
    className?: string;
}

export function SearchInput({ value, onChange, placeholder = 'Search...', className }: SearchInputProps) {
    return (
        <div className={cn('relative', className)}>
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
                type="text"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder={placeholder}
                className="w-full pl-9 pr-4 py-2.5 bg-cream-50 border border-cream-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
            />
        </div>
    );
}
