import { useState } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge, Select, MultiSelect, SaveBar, PageSkeleton, EmptyState } from '@/components/ui/Shared';
import { Modal } from '@/components/ui/Modal';
import { Shield, Users, UserCheck, Plus, X, Settings2, Crown, Lock } from 'lucide-react';
import type { DashboardRole, DashboardCapability, DashboardPermissionMapping, DashboardUserOverride } from '@/types';
import { DASHBOARD_ROLE_CAPABILITIES } from '@/types';
import { cn } from '@/lib/utils';

const ROLE_HIERARCHY: DashboardRole[] = ['owner', 'admin', 'moderator', 'viewer'];

const ROLE_LABELS: Record<DashboardRole, string> = {
    owner: 'Owner',
    admin: 'Admin',
    moderator: 'Moderator',
    viewer: 'Viewer',
};

const ROLE_COLORS: Record<DashboardRole, string> = {
    owner: 'bg-amber-50 text-amber-700 border-amber-200',
    admin: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    moderator: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    viewer: 'bg-slate-50 text-slate-600 border-slate-200',
};

const CAPABILITY_LABELS: Record<DashboardCapability, string> = {
    view_dashboard: 'View Dashboard',
    view_commands: 'View Commands',
    manage_commands: 'Manage Commands',
    view_modules: 'View Modules',
    manage_modules: 'Manage Modules',
    view_logging: 'View Logging',
    manage_logging: 'Manage Logging',
    view_cases: 'View Cases',
    manage_cases: 'Manage Cases',
    view_automod: 'View Automod',
    manage_automod: 'Manage Automod',
    manage_permissions: 'Manage Permissions',
    export_data: 'Export Data',
    danger_zone_actions: 'Danger Zone',
    run_sync_operations: 'Sync Operations',
    view_audit: 'View Audit Log',
};

export function Permissions() {
    const { config, roles, updateConfigLocal, saveConfig, discardChanges, configDirty, error } = useAppStore();
    const [saving, setSaving] = useState(false);
    const [addMappingModal, setAddMappingModal] = useState(false);

    const discordRoles = roles.filter(r => !r.managed);
    const roleOptions = discordRoles.map(r => ({ label: r.name, value: r.id, color: r.color }));

    const handleSave = async () => {
        setSaving(true);
        try { await saveConfig(); } catch { /* handled */ }
        setSaving(false);
    };

    const removeMapping = (roleId: string) => {
        if (!config) return;
        const permissions = config.permissions || { roleMappings: [], userOverrides: [] };
        updateConfigLocal({
            permissions: {
                ...permissions,
                roleMappings: (permissions.roleMappings || []).filter(m => m.roleId !== roleId),
            },
        });
    };

    const updateMapping = (roleId: string, dashboardRole: DashboardRole) => {
        if (!config) return;
        const permissions = config.permissions || { roleMappings: [], userOverrides: [] };
        updateConfigLocal({
            permissions: {
                ...permissions,
                roleMappings: (permissions.roleMappings || []).map(m =>
                    m.roleId === roleId ? { ...m, dashboardRole, capabilities: DASHBOARD_ROLE_CAPABILITIES[dashboardRole] } : m
                ),
            },
        });
    };

    const addMapping = (roleId: string, dashboardRole: DashboardRole) => {
        if (!config) return;
        const permissions = config.permissions || { roleMappings: [], userOverrides: [] };
        const existing = (permissions.roleMappings || []).find(m => m.roleId === roleId);
        if (existing) return;
        updateConfigLocal({
            permissions: {
                ...permissions,
                roleMappings: [
                    ...(permissions.roleMappings || []),
                    { roleId, dashboardRole, capabilities: DASHBOARD_ROLE_CAPABILITIES[dashboardRole] },
                ],
            },
        });
        setAddMappingModal(false);
    };

    if (!config) return <PageSkeleton />;

    const permissions = config.permissions || { roleMappings: [], userOverrides: [] };
    const roleMappings = permissions.roleMappings || [];
    const mappedRoleIds = roleMappings.map(m => m.roleId);
    const unmappedRoles = discordRoles.filter(r => !mappedRoleIds.includes(r.id));

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-3xl font-display font-bold text-slate-800 tracking-tight">Permissions</h1>
                    <p className="text-slate-500 mt-1">Map Discord roles to dashboard access levels and control who can manage the bot.</p>
                </div>
            </div>

            {/* Dashboard Role Reference */}
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
                            <Crown className="w-4 h-4" />
                        </div>
                        <div>
                            <CardTitle className="text-lg">Dashboard Roles</CardTitle>
                            <CardDescription>Each role grants a set of capabilities. Higher roles include all lower-role capabilities.</CardDescription>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                        {ROLE_HIERARCHY.map(role => (
                            <div key={role} className={cn('p-4 rounded-2xl border', ROLE_COLORS[role])}>
                                <h4 className="font-semibold text-sm mb-2">{ROLE_LABELS[role]}</h4>
                                <div className="flex flex-wrap gap-1">
                                    {DASHBOARD_ROLE_CAPABILITIES[role].slice(0, 4).map(cap => (
                                        <span key={cap} className="text-[10px] px-1.5 py-0.5 bg-white/60 rounded text-current font-medium">
                                            {CAPABILITY_LABELS[cap]}
                                        </span>
                                    ))}
                                    {DASHBOARD_ROLE_CAPABILITIES[role].length > 4 && (
                                        <span className="text-[10px] px-1.5 py-0.5 bg-white/60 rounded text-current font-medium">
                                            +{DASHBOARD_ROLE_CAPABILITIES[role].length - 4} more
                                        </span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Role Mappings */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-emerald-50 text-emerald-600 rounded-xl">
                                <Shield className="w-4 h-4" />
                            </div>
                            <div>
                                <CardTitle className="text-lg">Role Mappings</CardTitle>
                                <CardDescription>Assign Discord roles to dashboard permission levels.</CardDescription>
                            </div>
                        </div>
                        <Button size="sm" variant="outline" className="gap-2" onClick={() => setAddMappingModal(true)}>
                            <Plus className="w-4 h-4" />
                            Add Mapping
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    {roleMappings.length === 0 ? (
                        <EmptyState icon={<Users className="w-8 h-8" />} title="No mappings" description="Add a role mapping to grant dashboard access." />
                    ) : (
                        <div className="space-y-3">
                            {roleMappings.map(mapping => {
                                const discordRole = discordRoles.find(r => r.id === mapping.roleId);
                                return (
                                    <div key={mapping.roleId} className="flex items-center gap-4 p-4 bg-cream-50 rounded-2xl border border-cream-200">
                                        <div className="flex items-center gap-3 flex-1 min-w-0">
                                            {discordRole && (
                                                <div
                                                    className="w-3 h-3 rounded-full shrink-0"
                                                    style={{ backgroundColor: `#${discordRole.color.toString(16).padStart(6, '0')}` }}
                                                />
                                            )}
                                            <span className="font-medium text-sm text-slate-800 truncate">
                                                {discordRole?.name || mapping.roleId}
                                            </span>
                                        </div>
                                        <Select
                                            value={mapping.dashboardRole}
                                            onChange={(v) => updateMapping(mapping.roleId, v as DashboardRole)}
                                            options={ROLE_HIERARCHY.map(r => ({ label: ROLE_LABELS[r], value: r }))}
                                            className="w-40"
                                        />
                                        <Badge variant={
                                            mapping.dashboardRole === 'owner' ? 'warning' :
                                                mapping.dashboardRole === 'admin' ? 'info' :
                                                    mapping.dashboardRole === 'moderator' ? 'success' : 'default'
                                        }>
                                            {DASHBOARD_ROLE_CAPABILITIES[mapping.dashboardRole].length} capabilities
                                        </Badge>
                                        <button
                                            onClick={() => removeMapping(mapping.roleId)}
                                            className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Security Notice */}
            <Card className="border-amber-200">
                <CardContent className="p-5">
                    <div className="flex items-start gap-3">
                        <div className="p-2 bg-amber-50 text-amber-600 rounded-xl shrink-0 mt-0.5">
                            <Lock className="w-4 h-4" />
                        </div>
                        <div>
                            <h4 className="font-semibold text-sm text-amber-900">Security Notice</h4>
                            <p className="text-xs text-amber-700 mt-1">
                                Permission checks are enforced server-side. The UI only hides elements — the backend always validates capabilities before executing operations. Users cannot grant permissions they don&apos;t possess (privilege escalation prevention).
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Add Mapping Modal */}
            {addMappingModal && (
                <AddMappingModal
                    roles={unmappedRoles.map(r => ({ label: r.name, value: r.id, color: r.color }))}
                    onClose={() => setAddMappingModal(false)}
                    onAdd={addMapping}
                />
            )}

            <SaveBar dirty={configDirty} saving={saving} onSave={handleSave} onDiscard={discardChanges} error={error} />
        </div>
    );
}

// ─── Add Mapping Modal ──────────────────────────────────────────────────────

interface AddMappingModalProps {
    roles: { label: string; value: string; color?: number }[];
    onClose: () => void;
    onAdd: (roleId: string, dashboardRole: DashboardRole) => void;
}

function AddMappingModal({ roles, onClose, onAdd }: AddMappingModalProps) {
    const [selectedRole, setSelectedRole] = useState('');
    const [selectedDashboardRole, setSelectedDashboardRole] = useState<DashboardRole>('viewer');

    return (
        <Modal
            open={true}
            onClose={onClose}
            title="Add Role Mapping"
            description="Map a Discord role to a dashboard permission level."
            size="sm"
            footer={
                <>
                    <Button variant="outline" onClick={onClose}>Cancel</Button>
                    <Button
                        disabled={!selectedRole}
                        onClick={() => selectedRole && onAdd(selectedRole, selectedDashboardRole)}
                    >
                        Add Mapping
                    </Button>
                </>
            }
        >
            <div className="space-y-5">
                <div>
                    <label className="text-sm font-medium text-slate-700 mb-2 block">Discord Role</label>
                    <Select
                        value={selectedRole}
                        onChange={setSelectedRole}
                        options={roles.map(r => ({ label: r.label, value: r.value }))}
                        placeholder="Select a role..."
                    />
                </div>
                <div>
                    <label className="text-sm font-medium text-slate-700 mb-2 block">Dashboard Role</label>
                    <Select
                        value={selectedDashboardRole}
                        onChange={(v) => setSelectedDashboardRole(v as DashboardRole)}
                        options={ROLE_HIERARCHY.map(r => ({ label: ROLE_LABELS[r], value: r }))}
                    />
                </div>
            </div>
        </Modal>
    );
}
