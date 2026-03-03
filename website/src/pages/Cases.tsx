import { useState, useEffect } from 'react';
import { Badge, SearchInput, PageSkeleton, EmptyState, Tabs } from '@/components/ui/Shared';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { useAppStore } from '@/store/useAppStore';
import { realApiClient } from '@/lib/api';
import type { ModerationCase, CaseAction } from '@/types';
import { Gavel, AlertTriangle, UserX, Clock, Ban, ShieldCheck, FileText, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';

const ACTION_CONFIG: Record<CaseAction, { label: string; icon: typeof Gavel; color: string; bg: string }> = {
    warn: { label: 'Warning', icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50' },
    timeout: { label: 'Timeout', icon: Clock, color: 'text-orange-600', bg: 'bg-orange-50' },
    kick: { label: 'Kick', icon: UserX, color: 'text-red-500', bg: 'bg-red-50' },
    ban: { label: 'Ban', icon: Ban, color: 'text-red-700', bg: 'bg-red-50' },
    unban: { label: 'Unban', icon: ShieldCheck, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    note: { label: 'Note', icon: FileText, color: 'text-slate-600', bg: 'bg-slate-50' },
    quarantine: { label: 'Quarantine', icon: Gavel, color: 'text-purple-600', bg: 'bg-purple-50' },
};

export function Cases() {
    const { activeGuildId } = useAppStore();
    const [cases, setCases] = useState<ModerationCase[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [filterAction, setFilterAction] = useState('all');
    const [selectedCase, setSelectedCase] = useState<ModerationCase | null>(null);

    useEffect(() => {
        if (!activeGuildId) return;
        setLoading(true);
        realApiClient.getCases(activeGuildId)
            .then(res => {
                setCases(res.data);
                setLoading(false);
            })
            .catch(() => {
                setCases([]);
                setLoading(false);
            });
    }, [activeGuildId]);

    if (loading) return <PageSkeleton />;

    const actionTabs = [
        { id: 'all', label: 'All', count: cases.length },
        ...(['warn', 'timeout', 'kick', 'ban'] as CaseAction[]).map(action => ({
            id: action,
            label: ACTION_CONFIG[action].label,
            count: cases.filter(c => c.action === action).length,
        })),
    ];

    const filtered = cases.filter(c => {
        if (filterAction !== 'all' && c.action !== filterAction) return false;
        if (search) {
            const q = search.toLowerCase();
            return c.userName.toLowerCase().includes(q) || c.reason.toLowerCase().includes(q) || c.moderatorName.toLowerCase().includes(q);
        }
        return true;
    });

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-display font-bold text-slate-800 tracking-tight">Moderation Cases</h1>
                <p className="text-slate-500 mt-1">View and manage moderation actions taken in this server.</p>
            </div>

            <div className="flex items-center gap-4 flex-wrap">
                <SearchInput value={search} onChange={setSearch} placeholder="Search by user, reason, moderator..." className="w-80" />
                <Tabs tabs={actionTabs} activeTab={filterAction} onChange={setFilterAction} />
            </div>

            {filtered.length === 0 ? (
                <EmptyState icon={<Gavel className="w-8 h-8" />} title="No cases found" description="No moderation cases match your current filters." />
            ) : (
                <div className="space-y-3">
                    {filtered.map(c => {
                        const actionCfg = ACTION_CONFIG[c.action];
                        const Icon = actionCfg.icon;
                        const timeAgo = getTimeAgo(c.createdAt);

                        return (
                            <Card key={c.id} className="group hover:shadow-[0_12px_40px_rgb(0,0,0,0.06)] transition-all cursor-pointer" onClick={() => setSelectedCase(c)}>
                                <CardContent className="p-4">
                                    <div className="flex items-center gap-4">
                                        <div className={cn('p-2.5 rounded-xl', actionCfg.bg, actionCfg.color)}>
                                            <Icon className="w-4 h-4" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <span className="font-semibold text-sm text-slate-800">#{c.id}</span>
                                                <Badge variant={c.action === 'ban' ? 'danger' : c.action === 'warn' ? 'warning' : c.action === 'kick' ? 'danger' : 'info'}>
                                                    {actionCfg.label}
                                                </Badge>
                                                {c.duration && <Badge variant="default">{c.duration}</Badge>}
                                            </div>
                                            <p className="text-sm text-slate-600 mt-0.5 truncate">
                                                <span className="font-medium">{c.userName}</span>
                                                <span className="text-slate-400 mx-1.5">—</span>
                                                {c.reason}
                                            </p>
                                        </div>
                                        <div className="text-right shrink-0">
                                            <p className="text-xs text-slate-500">{timeAgo}</p>
                                            <p className="text-xs text-slate-400 mt-0.5">by {c.moderatorName}</p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            )}

            {/* Case Detail Modal */}
            {selectedCase && (
                <Modal open={true} onClose={() => setSelectedCase(null)} title={`Case #${selectedCase.id}`} size="md">
                    <div className="space-y-4">
                        <div className="flex items-center gap-3">
                            <div className={cn('p-3 rounded-xl', ACTION_CONFIG[selectedCase.action].bg, ACTION_CONFIG[selectedCase.action].color)}>
                                {(() => { const Icon = ACTION_CONFIG[selectedCase.action].icon; return <Icon className="w-5 h-5" />; })()}
                            </div>
                            <div>
                                <h3 className="font-display font-bold text-lg text-slate-800">{ACTION_CONFIG[selectedCase.action].label}</h3>
                                <p className="text-sm text-slate-500">{new Date(selectedCase.createdAt).toLocaleString()}</p>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="p-3 bg-cream-50 rounded-xl border border-cream-200">
                                <p className="text-xs text-slate-500 font-medium uppercase mb-1">User</p>
                                <p className="text-sm font-semibold text-slate-800">{selectedCase.userName}</p>
                                <p className="text-xs text-slate-400 font-mono">{selectedCase.userId}</p>
                            </div>
                            <div className="p-3 bg-cream-50 rounded-xl border border-cream-200">
                                <p className="text-xs text-slate-500 font-medium uppercase mb-1">Moderator</p>
                                <p className="text-sm font-semibold text-slate-800">{selectedCase.moderatorName}</p>
                                <p className="text-xs text-slate-400 font-mono">{selectedCase.moderatorId}</p>
                            </div>
                        </div>

                        <div className="p-3 bg-cream-50 rounded-xl border border-cream-200">
                            <p className="text-xs text-slate-500 font-medium uppercase mb-1">Reason</p>
                            <p className="text-sm text-slate-700">{selectedCase.reason}</p>
                        </div>

                        {selectedCase.duration && (
                            <div className="p-3 bg-cream-50 rounded-xl border border-cream-200">
                                <p className="text-xs text-slate-500 font-medium uppercase mb-1">Duration</p>
                                <p className="text-sm text-slate-700">{selectedCase.duration}</p>
                            </div>
                        )}
                    </div>
                </Modal>
            )}
        </div>
    );
}

function getTimeAgo(isoString: string): string {
    const diff = Date.now() - new Date(isoString).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}
