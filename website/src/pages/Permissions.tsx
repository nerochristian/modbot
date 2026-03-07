import { useState } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge, Select, MultiSelect, SaveBar, PageSkeleton, EmptyState } from '@/components/ui/Shared';
import { Modal } from '@/components/ui/Modal';
import { Shield, Users, Plus, X, Crown, Lock, Pencil } from 'lucide-react';
import type { DashboardRole, DashboardCapability, DashboardPermissionMapping } from '@/types';
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

const EDITABLE_DASHBOARD_ROLES: DashboardRole[] = ['admin', 'moderator', 'viewer'];
const ALL_CAPABILITIES = Object.keys(CAPABILITY_LABELS) as DashboardCapability[];

export function Permissions() {
    const { config, roles, updateConfigLocal, saveConfig, discardChanges, configDirty, error } = useAppStore();
    const [saving, setSaving] = useState(false);
    const [addMappingModal, setAddMappingModal] = useState(false);
    const [editingDashboardRole, setEditingDashboardRole] = useState<DashboardRole | null>(null);

    const discordRoles = roles
        .filter(r => !r.managed)
        .sort((a, b) => {
            const byPosition = b.position - a.position;
            if (byPosition !== 0) return byPosition;
            return a.name.localeCompare(b.name);
        });
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

    const addMappings = (roleIds: string[], dashboardRole: DashboardRole) => {
        if (!config) return;
        const permissions = config.permissions || { roleMappings: [], userOverrides: [] };
        const uniqueRoleIds = Array.from(new Set(roleIds));
        if (uniqueRoleIds.length === 0) return;
        const existingRoleIds = new Set((permissions.roleMappings || []).map(mapping => mapping.roleId));
        const newMappings = uniqueRoleIds
            .filter(roleId => !existingRoleIds.has(roleId))
            .map(roleId => ({
                roleId,
                dashboardRole,
                capabilities: DASHBOARD_ROLE_CAPABILITIES[dashboardRole],
            }));
        if (newMappings.length === 0) return;
        updateConfigLocal({
            permissions: {
                ...permissions,
                roleMappings: [
                    ...(permissions.roleMappings || []),
                    ...newMappings,
                ],
            },
        });
        setAddMappingModal(false);
    };

    const setDashboardRoleAssignments = (dashboardRole: DashboardRole, selectedRoleIds: string[]) => {
        if (!config) return;
        const permissions = config.permissions || { roleMappings: [], userOverrides: [] };
        const uniqueRoleIds = Array.from(new Set(selectedRoleIds));
        const selectedRoleSet = new Set(uniqueRoleIds);
        const currentMappings = permissions.roleMappings || [];
        const nextMappings: DashboardPermissionMapping[] = [];

        for (const mapping of currentMappings) {
            if (selectedRoleSet.has(mapping.roleId)) continue;
            if (mapping.dashboardRole === dashboardRole) continue;
            nextMappings.push(mapping);
        }

        for (const roleId of uniqueRoleIds) {
            nextMappings.push({
                roleId,
                dashboardRole,
                capabilities: DASHBOARD_ROLE_CAPABILITIES[dashboardRole],
            });
        }

        updateConfigLocal({
            permissions: {
                ...permissions,
                roleMappings: nextMappings,
            },
        });
        setEditingDashboardRole(null);
    };

    if (!config) return <PageSkeleton />;

    const permissions = config.permissions || { roleMappings: [], userOverrides: [] };
    const roleMappings = permissions.roleMappings || [];
    const mappedRoleIds = roleMappings.map(m => m.roleId);
    const unmappedRoles = discordRoles.filter(r => !mappedRoleIds.includes(r.id));
    const discordRoleById = new Map(discordRoles.map(r => [r.id, r]));
    const sortedRoleMappings = [...roleMappings].sort((a, b) => {
        const aPos = discordRoleById.get(a.roleId)?.position ?? -1;
        const bPos = discordRoleById.get(b.roleId)?.position ?? -1;
        if (aPos !== bPos) return bPos - aPos;
        const aName = discordRoleById.get(a.roleId)?.name || a.roleId;
        const bName = discordRoleById.get(b.roleId)?.name || b.roleId;
        return aName.localeCompare(bName);
    });
    const mappedRolesByDashboardRole: Record<DashboardRole, { id: string; name: string; color?: number }[]> = {
        owner: [],
        admin: [],
        moderator: [],
        viewer: [],
    };

    for (const mapping of roleMappings) {
        const discordRole = discordRoleById.get(mapping.roleId);
        mappedRolesByDashboardRole[mapping.dashboardRole].push({
            id: mapping.roleId,
            name: discordRole?.name || mapping.roleId,
            color: discordRole?.color,
        });
    }

    for (const dashboardRole of ROLE_HIERARCHY) {
        mappedRolesByDashboardRole[dashboardRole].sort((a, b) => {
            const aPos = discordRoleById.get(a.id)?.position ?? -1;
            const bPos = discordRoleById.get(b.id)?.position ?? -1;
            return bPos - aPos;
        });
    }

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
                            <CardDescription>Each role grants a set of capabilities. Edit Admin, Moderator, and Viewer to choose which Discord roles belong to each level.</CardDescription>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                        {ROLE_HIERARCHY.map(role => {
                            const isEditable = EDITABLE_DASHBOARD_ROLES.includes(role);
                            const grantedCapabilities = DASHBOARD_ROLE_CAPABILITIES[role];
                            const restrictedCapabilities = ALL_CAPABILITIES.filter(cap => !grantedCapabilities.includes(cap));
                            const mappedRolesForCard = mappedRolesByDashboardRole[role];

                            return (
                                <div key={role} className={cn('p-4 rounded-2xl border', ROLE_COLORS[role])}>
                                    <div className="flex items-start justify-between gap-2 mb-3">
                                        <h4 className="font-semibold text-sm">{ROLE_LABELS[role]}</h4>
                                        {isEditable && (
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => setEditingDashboardRole(role)}
                                                className="h-7 px-2.5 text-[11px] bg-white/70 border-white/70 hover:bg-white gap-1"
                                            >
                                                <Pencil className="w-3 h-3" />
                                                Edit
                                            </Button>
                                        )}
                                    </div>

                                    <div className="space-y-3">
                                        <div>
                                            <p className="text-[10px] uppercase tracking-wide font-semibold mb-1 opacity-80">Mapped Discord Roles</p>
                                            {mappedRolesForCard.length === 0 ? (
                                                <p className="text-xs font-medium opacity-75">No roles mapped</p>
                                            ) : (
                                                <div className="flex flex-wrap gap-1">
                                                    {mappedRolesForCard.map(mappedRole => (
                                                        <span key={mappedRole.id} className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 bg-white/70 rounded font-medium">
                                                            {mappedRole.color !== undefined && (
                                                                <span
                                                                    className="w-2 h-2 rounded-full"
                                                                    style={{ backgroundColor: `#${mappedRole.color.toString(16).padStart(6, '0')}` }}
                                                                />
                                                            )}
                                                            {mappedRole.name}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>

                                        <div>
                                            <p className="text-[10px] uppercase tracking-wide font-semibold mb-1 opacity-80">Can Do</p>
                                            <div className="flex flex-wrap gap-1">
                                                {grantedCapabilities.map(capability => (
                                                    <span key={capability} className="text-[10px] px-1.5 py-0.5 bg-white/70 rounded text-current font-medium">
                                                        {CAPABILITY_LABELS[capability]}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>

                                        <div>
                                            <p className="text-[10px] uppercase tracking-wide font-semibold mb-1 opacity-80">Cannot Do</p>
                                            {restrictedCapabilities.length === 0 ? (
                                                <p className="text-xs font-medium opacity-75">No restrictions</p>
                                            ) : (
                                                <div className="flex flex-wrap gap-1">
                                                    {restrictedCapabilities.map(capability => (
                                                        <span key={capability} className="text-[10px] px-1.5 py-0.5 bg-white/40 rounded text-current/85 font-medium line-through">
                                                            {CAPABILITY_LABELS[capability]}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
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
                            {sortedRoleMappings.map(mapping => {
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
                    onAdd={addMappings}
                />
            )}

            {editingDashboardRole && (
                <EditDashboardRoleModal
                    dashboardRole={editingDashboardRole}
                    roles={roleOptions}
                    selectedRoleIds={mappedRolesByDashboardRole[editingDashboardRole].map(role => role.id)}
                    onClose={() => setEditingDashboardRole(null)}
                    onSave={setDashboardRoleAssignments}
                />
            )}

            <SaveBar dirty={configDirty} saving={saving} onSave={handleSave} onDiscard={discardChanges} error={error} />
        </div>
    );
}

// ─── Add Mapping Modal ──────────────────────────────────────────────────────

interface EditDashboardRoleModalProps {
    dashboardRole: DashboardRole;
    roles: { label: string; value: string; color?: number }[];
    selectedRoleIds: string[];
    onClose: () => void;
    onSave: (dashboardRole: DashboardRole, roleIds: string[]) => void;
}

function EditDashboardRoleModal({ dashboardRole, roles, selectedRoleIds, onClose, onSave }: EditDashboardRoleModalProps) {
    const [selectedRoles, setSelectedRoles] = useState<string[]>(selectedRoleIds);
    const deniedCapabilities = ALL_CAPABILITIES.filter(cap => !DASHBOARD_ROLE_CAPABILITIES[dashboardRole].includes(cap));

    return (
        <Modal
            open={true}
            onClose={onClose}
            title={`Edit ${ROLE_LABELS[dashboardRole]} Role Mappings`}
            description={`Choose which Discord roles should be treated as ${ROLE_LABELS[dashboardRole].toLowerCase()}s.`}
            size="md"
            footer={
                <>
                    <Button variant="outline" onClick={onClose}>Cancel</Button>
                    <Button onClick={() => onSave(dashboardRole, selectedRoles)}>Save</Button>
                </>
            }
        >
            <div className="space-y-5">
                <div>
                    <label className="text-sm font-medium text-slate-700 mb-2 block">Discord Roles</label>
                    <MultiSelect
                        values={selectedRoles}
                        onChange={setSelectedRoles}
                        options={roles}
                        placeholder={`No ${ROLE_LABELS[dashboardRole].toLowerCase()} roles selected`}
                    />
                </div>

                <div className="rounded-2xl border border-cream-200 bg-cream-50 p-4 space-y-3">
                    <div>
                        <p className="text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1">Can Do</p>
                        <div className="flex flex-wrap gap-1">
                            {DASHBOARD_ROLE_CAPABILITIES[dashboardRole].map(capability => (
                                <span key={capability} className="text-[10px] px-1.5 py-0.5 bg-emerald-50 text-emerald-700 rounded font-medium border border-emerald-200">
                                    {CAPABILITY_LABELS[capability]}
                                </span>
                            ))}
                        </div>
                    </div>

                    <div>
                        <p className="text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1">Cannot Do</p>
                        {deniedCapabilities.length === 0 ? (
                            <p className="text-xs text-slate-500">No restrictions.</p>
                        ) : (
                            <div className="flex flex-wrap gap-1">
                                {deniedCapabilities.map(capability => (
                                    <span key={capability} className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded font-medium border border-slate-200 line-through">
                                        {CAPABILITY_LABELS[capability]}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </Modal>
    );
}

interface AddMappingModalProps {
    roles: { label: string; value: string; color?: number }[];
    onClose: () => void;
    onAdd: (roleIds: string[], dashboardRole: DashboardRole) => void;
}

function AddMappingModal({ roles, onClose, onAdd }: AddMappingModalProps) {
    const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
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
                        disabled={selectedRoles.length === 0}
                        onClick={() => onAdd(selectedRoles, selectedDashboardRole)}
                    >
                        {selectedRoles.length > 1 ? 'Add Mappings' : 'Add Mapping'}
                    </Button>
                </>
            }
        >
            <div className="space-y-5">
                <div>
                    <label className="text-sm font-medium text-slate-700 mb-2 block">Discord Roles</label>
                    <MultiSelect
                        values={selectedRoles}
                        onChange={setSelectedRoles}
                        options={roles}
                        placeholder="Select role(s)..."
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
