import { useState, useMemo } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardContent } from '@/components/ui/Card';
import { Switch } from '@/components/ui/Switch';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Badge, Select, MultiSelect, SaveBar, SearchInput, PageSkeleton, EmptyState } from '@/components/ui/Shared';
import {
    Zap, Shield, ScrollText, ShieldAlert, Ticket, UserCheck,
    Settings2, ChevronRight, Package,
} from 'lucide-react';
import type { ModuleCapability, ModuleConfig, SettingsFieldSchema } from '@/types';
import { MOCK_CHANNELS, MOCK_ROLES } from '@/lib/mock-data';
import { cn } from '@/lib/utils';

const ICON_MAP: Record<string, typeof Zap> = {
    Zap, Shield, ScrollText, ShieldAlert, Ticket, UserCheck, Package,
};

function getIcon(hint: string) {
    return ICON_MAP[hint] || Package;
}

export function Modules() {
    const { capabilities, config, updateConfigLocal, saveConfig, discardChanges, configDirty, error } = useAppStore();
    const [search, setSearch] = useState('');
    const [settingsModal, setSettingsModal] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);

    const modules = capabilities?.modules || [];

    const filteredModules = useMemo(() => {
        if (!search) return modules;
        const q = search.toLowerCase();
        return modules.filter(m => m.name.toLowerCase().includes(q) || m.description.toLowerCase().includes(q));
    }, [modules, search]);

    const toggleModule = (id: string) => {
        if (!config) return;
        const current = config.modules[id];
        if (!current) return;
        updateConfigLocal({
            modules: {
                ...config.modules,
                [id]: { ...current, enabled: !current.enabled },
            },
        });
    };

    const handleSave = async () => {
        setSaving(true);
        try { await saveConfig(); } catch { /* handled */ }
        setSaving(false);
    };

    if (!capabilities || !config) return <PageSkeleton />;

    const channelOptions = MOCK_CHANNELS.filter(c => c.type === 0).map(c => ({ label: `#${c.name}`, value: c.id }));
    const roleOptions = MOCK_ROLES.filter(r => !r.managed).map(r => ({ label: r.name, value: r.id, color: r.color }));

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-3xl font-display font-bold text-slate-800 tracking-tight">Modules</h1>
                    <p className="text-slate-500 mt-1">Enable or disable bot features and configure their behavior.</p>
                </div>
            </div>

            <SearchInput value={search} onChange={setSearch} placeholder="Search modules..." className="w-72" />

            {filteredModules.length === 0 ? (
                <EmptyState icon={<Package className="w-8 h-8" />} title="No modules found" description="No modules match your search." />
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {filteredModules.map(mod => {
                        const modConfig = config.modules[mod.id];
                        const IconComponent = getIcon(mod.iconHint);

                        return (
                            <Card key={mod.id} className={cn('group transition-all duration-200 hover:shadow-[0_12px_40px_rgb(0,0,0,0.06)]', modConfig && !modConfig.enabled && 'opacity-60')}>
                                <CardContent className="p-5">
                                    <div className="flex items-start justify-between mb-3">
                                        <div className="flex items-center gap-3">
                                            <div className={cn(
                                                'p-2.5 rounded-xl',
                                                modConfig?.enabled ? 'bg-indigo-50 text-indigo-600' : 'bg-cream-100 text-slate-400'
                                            )}>
                                                <IconComponent className="w-5 h-5" />
                                            </div>
                                            <div>
                                                <h3 className="font-display font-semibold text-slate-800">{mod.name}</h3>
                                                <div className="flex items-center gap-1.5 mt-0.5">
                                                    <Badge variant={mod.premiumTier === 'premium' ? 'premium' : 'default'}>{mod.category}</Badge>
                                                    {mod.supportsOverrides && <Badge variant="info">Overrides</Badge>}
                                                </div>
                                            </div>
                                        </div>
                                        <Switch
                                            checked={modConfig?.enabled ?? false}
                                            onCheckedChange={() => toggleModule(mod.id)}
                                        />
                                    </div>

                                    <p className="text-sm text-slate-500 mb-4 line-clamp-2">{mod.description}</p>

                                    <button
                                        onClick={() => setSettingsModal(mod.id)}
                                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-cream-50 hover:bg-cream-100 border border-cream-200 rounded-lg transition-colors w-full justify-center"
                                    >
                                        <Settings2 className="w-3.5 h-3.5" />
                                        Configure
                                        <ChevronRight className="w-3 h-3 ml-auto" />
                                    </button>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            )}

            {settingsModal && (
                <ModuleSettingsModal
                    module={modules.find(m => m.id === settingsModal)!}
                    config={config.modules[settingsModal]}
                    channels={channelOptions}
                    roles={roleOptions}
                    onClose={() => setSettingsModal(null)}
                    onSave={(updated) => {
                        updateConfigLocal({
                            modules: { ...config.modules, [settingsModal]: updated },
                        });
                        setSettingsModal(null);
                    }}
                />
            )}

            <SaveBar dirty={configDirty} saving={saving} onSave={handleSave} onDiscard={discardChanges} error={error} />
        </div>
    );
}

// ─── Schema-Driven Module Settings Modal ────────────────────────────────────

interface ModuleSettingsModalProps {
    module: ModuleCapability;
    config: ModuleConfig;
    channels: { label: string; value: string }[];
    roles: { label: string; value: string; color?: number }[];
    onClose: () => void;
    onSave: (config: ModuleConfig) => void;
}

function ModuleSettingsModal({ module: mod, config: modConfig, channels, roles, onClose, onSave }: ModuleSettingsModalProps) {
    const [local, setLocal] = useState<ModuleConfig>(JSON.parse(JSON.stringify(modConfig)));

    const updateSetting = (key: string, value: unknown) => {
        setLocal(prev => ({
            ...prev,
            settings: { ...prev.settings, [key]: value },
        }));
    };

    const updateOverride = (key: string, value: string[]) => {
        setLocal(prev => ({
            ...prev,
            overrides: { ...prev.overrides, [key]: value },
        }));
    };

    // Group settings by section
    const sections = useMemo(() => {
        const map = new Map<string, SettingsFieldSchema[]>();
        for (const field of mod.settingsSchema) {
            const section = field.section || 'General';
            const list = map.get(section) || [];
            list.push(field);
            map.set(section, list);
        }
        return map;
    }, [mod.settingsSchema]);

    const [showAdvanced, setShowAdvanced] = useState(false);

    return (
        <Modal
            open={true}
            onClose={onClose}
            title={`${mod.name} Settings`}
            description={mod.description}
            size="lg"
            footer={
                <>
                    <Button variant="outline" onClick={onClose}>Cancel</Button>
                    <Button onClick={() => onSave(local)}>Save Settings</Button>
                </>
            }
        >
            <div className="space-y-6">
                {/* Schema-driven settings */}
                {Array.from(sections).map(([section, fields]) => {
                    const basicFields = fields.filter(f => !f.advanced);
                    const advancedFields = fields.filter(f => f.advanced);

                    return (
                        <div key={section}>
                            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">{section}</h4>
                            <div className="space-y-3">
                                {basicFields.map(field => (
                                    <SchemaField key={field.key} field={field} value={local.settings[field.key]} onChange={(v) => updateSetting(field.key, v)} channels={channels} roles={roles} />
                                ))}
                                {advancedFields.length > 0 && showAdvanced && advancedFields.map(field => (
                                    <SchemaField key={field.key} field={field} value={local.settings[field.key]} onChange={(v) => updateSetting(field.key, v)} channels={channels} roles={roles} />
                                ))}
                            </div>
                        </div>
                    );
                })}

                {mod.settingsSchema.some(f => f.advanced) && (
                    <button
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
                    >
                        {showAdvanced ? 'Hide Advanced Settings' : 'Show Advanced Settings'}
                    </button>
                )}

                {/* Override Section */}
                {mod.supportsOverrides && (
                    <div className="pt-4 border-t border-cream-200">
                        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Exceptions</h4>
                        <div className="space-y-4">
                            <div>
                                <label className="text-sm font-medium text-slate-700 mb-2 block">Ignored Channels</label>
                                <MultiSelect
                                    values={local.overrides.ignoredChannels}
                                    onChange={(v) => updateOverride('ignoredChannels', v)}
                                    options={channels}
                                    placeholder="No channels excluded"
                                />
                            </div>
                            <div>
                                <label className="text-sm font-medium text-slate-700 mb-2 block">Ignored Roles</label>
                                <MultiSelect
                                    values={local.overrides.ignoredRoles}
                                    onChange={(v) => updateOverride('ignoredRoles', v)}
                                    options={roles}
                                    placeholder="No roles excluded"
                                />
                            </div>
                        </div>
                    </div>
                )}

                {/* Logging Override */}
                <div className="pt-4 border-t border-cream-200">
                    <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Logging</h4>
                    <div>
                        <label className="text-sm font-medium text-slate-700 mb-2 block">Override Log Channel</label>
                        <Select
                            value={local.loggingRouteOverride || ''}
                            onChange={(v) => setLocal(prev => ({ ...prev, loggingRouteOverride: v || null }))}
                            options={channels}
                            placeholder="Use default log channel"
                        />
                    </div>
                </div>
            </div>
        </Modal>
    );
}

// ─── String List Field (separate component for hooks) ───────────────────────

function StringListField({ field, value, onChange }: { field: SettingsFieldSchema; value: unknown; onChange: (v: unknown) => void }) {
    const list = Array.isArray(value) ? value as string[] : [];
    const [newItem, setNewItem] = useState('');
    return (
        <div>
            <label className="text-sm font-medium text-slate-700 mb-1.5 block">{field.label}</label>
            {field.constraints?.helpText && <p className="text-xs text-slate-500 mb-2">{field.constraints.helpText}</p>}
            <div className="space-y-2">
                {list.map((item, i) => (
                    <div key={i} className="flex items-center gap-2">
                        <span className="flex-1 px-3 py-1.5 bg-cream-50 border border-cream-200 rounded-lg text-sm">{item}</span>
                        <button onClick={() => onChange(list.filter((_, idx) => idx !== i))} className="text-red-500 hover:text-red-600 text-sm font-medium">Remove</button>
                    </div>
                ))}
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={newItem}
                        onChange={(e) => setNewItem(e.target.value)}
                        placeholder={field.constraints?.placeholder || 'Add item...'}
                        className="flex-1 bg-cream-50 border border-cream-300 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none"
                        onKeyDown={(e) => { if (e.key === 'Enter' && newItem.trim()) { onChange([...list, newItem.trim()]); setNewItem(''); } }}
                    />
                    <Button variant="outline" size="sm" onClick={() => { if (newItem.trim()) { onChange([...list, newItem.trim()]); setNewItem(''); } }}>Add</Button>
                </div>
            </div>
        </div>
    );
}

// ─── Schema Field Renderer ──────────────────────────────────────────────────

interface SchemaFieldProps {
    field: SettingsFieldSchema;
    value: unknown;
    onChange: (value: unknown) => void;
    channels: { label: string; value: string }[];
    roles: { label: string; value: string; color?: number }[];
}

function SchemaField({ field, value, onChange, channels, roles }: SchemaFieldProps) {
    switch (field.type) {
        case 'boolean':
            return (
                <div className="flex items-center justify-between p-3 bg-cream-50 rounded-xl border border-cream-200">
                    <div>
                        <span className="text-sm font-medium text-slate-700">{field.label}</span>
                        {field.constraints?.helpText && (
                            <p className="text-xs text-slate-500 mt-0.5">{field.constraints.helpText}</p>
                        )}
                    </div>
                    <Switch checked={Boolean(value)} onCheckedChange={onChange} />
                </div>
            );

        case 'number':
            return (
                <div>
                    <label className="text-sm font-medium text-slate-700 mb-1.5 block">{field.label}</label>
                    {field.constraints?.helpText && <p className="text-xs text-slate-500 mb-2">{field.constraints.helpText}</p>}
                    <input
                        type="number"
                        value={Number(value) || 0}
                        onChange={(e) => onChange(Number(e.target.value))}
                        min={field.constraints?.min}
                        max={field.constraints?.max}
                        className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
                    />
                </div>
            );

        case 'string':
        case 'regex':
            return (
                <div>
                    <label className="text-sm font-medium text-slate-700 mb-1.5 block">{field.label}</label>
                    <input
                        type="text"
                        value={String(value || '')}
                        onChange={(e) => onChange(e.target.value)}
                        placeholder={field.constraints?.placeholder}
                        className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
                    />
                </div>
            );

        case 'textArea':
            return (
                <div>
                    <label className="text-sm font-medium text-slate-700 mb-1.5 block">{field.label}</label>
                    {field.constraints?.helpText && <p className="text-xs text-slate-500 mb-2">{field.constraints.helpText}</p>}
                    <textarea
                        value={String(value || '')}
                        onChange={(e) => onChange(e.target.value)}
                        rows={3}
                        className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all resize-none"
                    />
                </div>
            );

        case 'select':
            return (
                <div>
                    <label className="text-sm font-medium text-slate-700 mb-1.5 block">{field.label}</label>
                    <Select
                        value={String(value || '')}
                        onChange={onChange as (v: string) => void}
                        options={field.constraints?.options || []}
                    />
                </div>
            );

        case 'duration':
            return (
                <div>
                    <label className="text-sm font-medium text-slate-700 mb-1.5 block">{field.label} (seconds)</label>
                    <input
                        type="number"
                        value={Number(value) || 0}
                        onChange={(e) => onChange(Number(e.target.value))}
                        min={field.constraints?.min}
                        max={field.constraints?.max}
                        className="w-full bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
                    />
                </div>
            );

        case 'channelPicker':
            return (
                <div>
                    <label className="text-sm font-medium text-slate-700 mb-1.5 block">{field.label}</label>
                    <Select value={String(value || '')} onChange={onChange as (v: string) => void} options={channels} placeholder="Select channel" />
                </div>
            );

        case 'rolePicker':
            return (
                <div>
                    <label className="text-sm font-medium text-slate-700 mb-1.5 block">{field.label}</label>
                    <Select
                        value={String(value || '')}
                        onChange={onChange as (v: string) => void}
                        options={roles.map(r => ({ label: r.label, value: r.value }))}
                        placeholder="Select role"
                    />
                </div>
            );

        case 'stringList':
            return <StringListField field={field} value={value} onChange={onChange} />;

        case 'color':
            return (
                <div>
                    <label className="text-sm font-medium text-slate-700 mb-1.5 block">{field.label}</label>
                    <div className="flex items-center gap-3">
                        <input
                            type="color"
                            value={String(value || '#000000')}
                            onChange={(e) => onChange(e.target.value)}
                            className="w-10 h-10 rounded-xl border border-cream-300 cursor-pointer"
                        />
                        <input
                            type="text"
                            value={String(value || '')}
                            onChange={(e) => onChange(e.target.value)}
                            className="flex-1 bg-cream-50 border border-cream-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none"
                        />
                    </div>
                </div>
            );

        default:
            return null;
    }
}
