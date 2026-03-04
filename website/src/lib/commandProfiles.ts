import type { CommandConfig } from '@/types';

export type CommandTabId = 'permissions' | 'channels' | 'cooldowns' | 'advanced';

export type CommandExtraFieldKind =
  | 'boolean'
  | 'number'
  | 'string'
  | 'textArea'
  | 'select'
  | 'roleMulti'
  | 'channelMulti'
  | 'stringList'
  | 'channel'
  | 'role';

export interface CommandExtraField {
  tab: CommandTabId;
  key: string;
  label: string;
  kind: CommandExtraFieldKind;
  defaultValue: unknown;
  helpText?: string;
  placeholder?: string;
  min?: number;
  max?: number;
  options?: { label: string; value: string }[];
}

interface CommandProfileDef {
  extends?: string;
  defaults?: Partial<CommandConfig>;
  extraFields?: CommandExtraField[];
}

export interface ResolvedCommandProfile {
  requiredPermission?: string;
  defaults: Partial<CommandConfig>;
  extraFields: CommandExtraField[];
}

export const STAFF_LEVEL_OPTIONS = [
  { label: 'Everyone', value: 'everyone' },
  { label: 'Staff', value: 'staff' },
  { label: 'Mod', value: 'mod' },
  { label: 'Admin', value: 'admin' },
  { label: 'Supervisor', value: 'supervisor' },
  { label: 'Owner', value: 'owner' },
];

export const CHANNEL_MODE_OPTIONS = [
  { label: 'Enabled Everywhere', value: 'enabled_everywhere' },
  { label: 'Only Allowed Channels', value: 'only_allowed' },
  { label: 'Disabled In Ignored Channels', value: 'disabled_in_ignored' },
];

export const RESPONSE_VISIBILITY_OPTIONS = [
  { label: 'Auto', value: 'auto' },
  { label: 'Ephemeral', value: 'ephemeral' },
  { label: 'Public', value: 'public' },
];

const b = (tab: CommandTabId, key: string, label: string, defaultValue = false, helpText?: string): CommandExtraField => ({
  tab,
  key,
  label,
  kind: 'boolean',
  defaultValue,
  helpText,
});

const n = (
  tab: CommandTabId,
  key: string,
  label: string,
  defaultValue = 0,
  min?: number,
  max?: number,
): CommandExtraField => ({
  tab,
  key,
  label,
  kind: 'number',
  defaultValue,
  min,
  max,
});

const s = (tab: CommandTabId, key: string, label: string, defaultValue = '', placeholder?: string): CommandExtraField => ({
  tab,
  key,
  label,
  kind: 'string',
  defaultValue,
  placeholder,
});

const ta = (tab: CommandTabId, key: string, label: string, defaultValue = '', placeholder?: string): CommandExtraField => ({
  tab,
  key,
  label,
  kind: 'textArea',
  defaultValue,
  placeholder,
});

const sl = (
  tab: CommandTabId,
  key: string,
  label: string,
  options: { label: string; value: string }[],
  defaultValue = '',
): CommandExtraField => ({
  tab,
  key,
  label,
  kind: 'select',
  defaultValue,
  options,
});

const rl = (tab: CommandTabId, key: string, label: string): CommandExtraField => ({
  tab,
  key,
  label,
  kind: 'roleMulti',
  defaultValue: [],
});

const cl = (tab: CommandTabId, key: string, label: string): CommandExtraField => ({
  tab,
  key,
  label,
  kind: 'channelMulti',
  defaultValue: [],
});

const st = (tab: CommandTabId, key: string, label: string): CommandExtraField => ({
  tab,
  key,
  label,
  kind: 'stringList',
  defaultValue: [],
});

const channelField = (tab: CommandTabId, key: string, label: string): CommandExtraField => ({
  tab,
  key,
  label,
  kind: 'channel',
  defaultValue: '',
});

const roleField = (tab: CommandTabId, key: string, label: string): CommandExtraField => ({
  tab,
  key,
  label,
  kind: 'role',
  defaultValue: '',
});

const PERMISSION_BY_COMMAND: Record<string, string> = {
  '8ball': 'send_messages',
  adminpanel: 'administrator',
  adminrole: 'manage_roles',
  aihelp: 'send_messages',
  aimod: 'manage_messages',
  announce: 'manage_messages',
  antiraid: 'manage_guild',
  automod: 'manage_messages',
  avatar: 'send_messages',
  ban: 'ban_members',
  banlist: 'ban_members',
  banner: 'send_messages',
  blacklist: 'administrator',
  botinfo: 'send_messages',
  case: 'moderate_members',
  channelinfo: 'send_messages',
  charinfo: 'send_messages',
  choose: 'send_messages',
  clearwarnings: 'moderate_members',
  clearwarns: 'moderate_members',
  coinflip: 'send_messages',
  color: 'send_messages',
  config: 'manage_guild',
  'court-close': 'manage_messages',
  'court-evidence': 'send_messages',
  'court-file': 'send_messages',
  'court-jury': 'manage_roles',
  'court-setup-logs': 'manage_channels',
  'court-verdict': 'manage_messages',
  'court-view-evidence': 'send_messages',
  createemoji: 'manage_expressions',
  deafen: 'mute_members',
  debug: 'administrator',
  deleteemoji: 'manage_expressions',
  delwarn: 'moderate_members',
  demote: 'manage_roles',
  dm: 'manage_messages',
  editcase: 'moderate_members',
  editsnipe: 'manage_messages',
  embed: 'manage_messages',
  emoji: 'send_messages',
  emojis: 'send_messages',
  enlarge: 'send_messages',
  firstmessage: 'read_message_history',
  forum: 'manage_threads',
  giveaway: 'manage_messages',
  glock: 'manage_channels',
  guilds: 'administrator',
  gunlock: 'manage_channels',
  help: 'send_messages',
  hide: 'manage_channels',
  hideall: 'manage_channels',
  history: 'moderate_members',
  icon: 'send_messages',
  ignore: 'manage_messages',
  inrole: 'manage_roles',
  invite: 'send_messages',
  kick: 'kick_members',
  leave: 'administrator',
  load: 'administrator',
  lock: 'manage_channels',
  lockdown: 'manage_channels',
  log: 'manage_guild',
  massban: 'ban_members',
  members: 'send_messages',
  mimic: 'manage_webhooks',
  moderation: 'moderate_members',
  modlogs: 'view_audit_log',
  modmail: 'manage_messages',
  modpanel: 'moderate_members',
  modrole: 'manage_roles',
  modstats: 'moderate_members',
  mute: 'moderate_members',
  nicknameall: 'manage_nicknames',
  note: 'moderate_members',
  notes: 'moderate_members',
  nuke: 'manage_channels',
  ownerpanel: 'administrator',
  permissions: 'manage_guild',
  pin: 'manage_messages',
  ping: 'send_messages',
  poll: 'send_messages',
  promote: 'manage_roles',
  purge: 'manage_messages',
  purgebots: 'manage_messages',
  purgecontains: 'manage_messages',
  purgeembeds: 'manage_messages',
  purgeimages: 'manage_messages',
  purgelinks: 'manage_messages',
  quarantine: 'moderate_members',
  r34: 'send_messages',
  reload: 'administrator',
  remindme: 'send_messages',
  removeall: 'manage_roles',
  rename: 'manage_nicknames',
  report: 'send_messages',
  reset: 'administrator',
  resetnicks: 'manage_nicknames',
  role: 'manage_roles',
  roleall: 'manage_roles',
  rolecolor: 'manage_roles',
  roleinfo: 'send_messages',
  roles: 'send_messages',
  roll: 'send_messages',
  rules: 'manage_messages',
  sanction: 'administrator',
  say: 'manage_messages',
  serverinfo: 'send_messages',
  setnick: 'manage_nicknames',
  settings: 'manage_guild',
  setup: 'administrator',
  shutdown: 'administrator',
  slowmode: 'manage_channels',
  snipe: 'manage_messages',
  softban: 'ban_members',
  spam: 'manage_messages',
  staffguide: 'manage_guild',
  staffupdates: 'manage_guild',
  stats: 'send_messages',
  status: 'administrator',
  steal: 'manage_expressions',
  stopspam: 'manage_messages',
  strip: 'manage_roles',
  sync: 'manage_guild',
  tempban: 'ban_members',
  ticket: 'manage_messages',
  ticketpanel: 'manage_messages',
  unban: 'ban_members',
  undeafen: 'mute_members',
  unhide: 'manage_channels',
  unhideall: 'manage_channels',
  unload: 'administrator',
  unlock: 'manage_channels',
  unlockdown: 'manage_channels',
  unmute: 'moderate_members',
  unquarantine: 'moderate_members',
  uptime: 'send_messages',
  userinfo: 'send_messages',
  utility: 'send_messages',
  vc: 'move_members',
  vckick: 'move_members',
  vcmove: 'move_members',
  vcmute: 'mute_members',
  vcunmute: 'mute_members',
  verifypanel: 'manage_channels',
  warn: 'moderate_members',
  warnings: 'moderate_members',
  whitelist: 'administrator',
};

const commonForceEphemeral = [b('advanced', 'forceEphemeral', 'Force Ephemeral')];
const commonAllowTargetOthers = [b('advanced', 'allowTargetingOtherUsers', 'Allow Targeting Other Users')];
const purgeExtras: CommandExtraField[] = [
  n('advanced', 'maxPurgeAmount', 'Max Purge Amount', 100, 1, 10000),
  n('advanced', 'requireConfirmationAboveAmount', 'Require Confirmation Above Amount', 25, 0, 10000),
  b('advanced', 'allowFilterByUser', 'Allow Filter By User', true),
  b('advanced', 'allowFilterByContains', 'Allow Filter By Contains', true),
  b('advanced', 'logPurgeSummary', 'Log Purge Summary', true),
  channelField('advanced', 'purgeSummaryLogChannel', 'Purge Summary Log Channel'),
  b('advanced', 'redactDeletedContentInLogs', 'Redact Deleted Content In Logs', true),
];

const PROFILE_DEFS: Record<string, CommandProfileDef> = {
  '8ball': {
    extraFields: [
      sl('advanced', 'responsePool', 'Response Pool', [{ label: 'Default', value: 'default' }, { label: 'Custom', value: 'custom' }], 'default'),
      ta('advanced', 'customResponses', 'Custom Responses'),
      b('advanced', 'allowNsfwResponses', 'Allow NSFW Responses'),
      ...commonForceEphemeral,
    ],
  },
  adminpanel: {
    defaults: { minimumStaffLevel: 'admin' },
    extraFields: [
      b('permissions', 'ownerOnlyMode', 'Owner Only Mode'),
      b('permissions', 'restrictToAdminRolesOnly', 'Restrict To Admin Roles Only'),
      st('advanced', 'panelSectionsVisible', 'Panel Sections Visible'),
      b('advanced', 'allowEditingFromPanel', 'Allow Editing From Panel', true),
      b('advanced', 'panelOpensEphemeral', 'Panel Opens Ephemeral', true),
    ],
  },
  adminrole: {
    defaults: { enforceRoleHierarchy: true },
    extraFields: [
      n('advanced', 'maxAdminRoles', 'Max Admin Roles', 3, 0, 25),
      rl('advanced', 'protectedRoles', 'Protected Roles'),
      b('advanced', 'autoSyncDashboardAdminPermissions', 'Auto Sync Dashboard Admin Permissions', true),
    ],
  },
  aimod: {
    defaults: { minimumStaffLevel: 'admin' },
    extraFields: [
      s('advanced', 'modelVersion', 'Model Version'),
      n('advanced', 'toxicityThreshold', 'Toxicity Threshold', 70, 0, 100),
      n('advanced', 'confidenceThreshold', 'Confidence Threshold', 70, 0, 100),
      n('advanced', 'manualReviewRequiredAbove', 'Manual Review Required Above', 85, 0, 100),
      b('advanced', 'redactUserContentInLogs', 'Redact User Content In Logs', true),
      st('advanced', 'aiActionsAllowed', 'AI Actions Allowed'),
      b('advanced', 'failClosedMode', 'Fail-Closed Mode'),
    ],
  },
  announce: {
    extraFields: [
      b('channels', 'restrictToAnnouncementChannels', 'Restrict To Announcement Channels'),
      channelField('channels', 'forceSpecificChannel', 'Force Specific Channel'),
      n('advanced', 'maxMessageLength', 'Max Message Length', 2000, 1, 4000),
      b('advanced', 'blockEveryoneHere', 'Block @everyone/@here', true),
      b('advanced', 'blockRoleMentions', 'Block Role Mentions'),
      n('advanced', 'maxMentionsAllowed', 'Max Mentions Allowed', 0, 0, 50),
      b('advanced', 'blockExternalLinks', 'Block External Links'),
      b('advanced', 'blockInviteLinks', 'Block Invite Links'),
      b('advanced', 'autoPinAnnouncement', 'Auto Pin Announcement'),
      b('advanced', 'autoCrosspostNews', 'Auto Crosspost (News Channels)'),
      b('advanced', 'createThreadForAnnouncement', 'Create Thread For Announcement'),
      b('advanced', 'appendFooterBranding', 'Append Footer Branding'),
      s('advanced', 'footerBrandingText', 'Footer Branding Text'),
    ],
  },
  avatar: {
    extraFields: [
      ...commonAllowTargetOthers,
      ...commonForceEphemeral,
      b('advanced', 'allowServerAvatarVsGlobalAvatar', 'Allow Server Avatar vs Global Avatar', true),
    ],
  },
  ban: {
    defaults: { requireReason: true, requireConfirmation: true, enforceRoleHierarchy: true },
    extraFields: [
      b('permissions', 'allowTargetHigherRole', 'Allow Target Higher Role'),
      b('permissions', 'allowTargetEqualRole', 'Allow Target Equal Role'),
      n('cooldowns', 'maxBansPerHour', 'Max Bans Per Hour', 15, 0, 500),
      n('advanced', 'defaultDeleteMessageDays', 'Default Delete Message Days', 1, 0, 7),
      n('advanced', 'maxDeleteMessageDays', 'Max Delete Message Days', 7, 0, 7),
      b('advanced', 'allowSoftbanMode', 'Allow Softban Mode'),
      b('advanced', 'dmTargetOnBan', 'DM Target On Ban', true),
      ta('advanced', 'dmTemplate', 'DM Template'),
      b('advanced', 'includeAppealLink', 'Include Appeal Link'),
      s('advanced', 'appealLinkUrl', 'Appeal Link URL'),
      b('advanced', 'autoCreateCase', 'Auto Create Case', true),
      s('advanced', 'caseTag', 'Case Tag'),
      b('advanced', 'banRequiresDualApproval', 'Ban Requires Dual Approval'),
      rl('advanced', 'protectedRoles', 'Protected Roles (cannot ban)'),
      st('advanced', 'protectedUsers', 'Protected Users (cannot ban)'),
    ],
  },
  clearwarnings: {
    defaults: { requireReason: true, requireConfirmation: true },
    extraFields: [
      b('advanced', 'allowClearingExpiredOnly', 'Allow Clearing Expired Only'),
      b('advanced', 'autoLogClear', 'Auto Log Clear', true),
      rl('advanced', 'protectedRoles', 'Protected Roles'),
    ],
  },
  clearwarns: { extends: 'clearwarnings' },
  config: {
    defaults: { minimumStaffLevel: 'admin' },
    extraFields: [
      b('advanced', 'allowJsonExport', 'Allow JSON Export', true),
      b('advanced', 'allowJsonImport', 'Allow JSON Import', true),
      b('advanced', 'requireConfirmationForImport', 'Require Confirmation For Import', true),
      b('advanced', 'allowPartialImport', 'Allow Partial Import', true),
      b('advanced', 'snapshotBeforeApply', 'Snapshot Before Apply', true),
    ],
  },
  deafen: {
    defaults: { enforceRoleHierarchy: true },
    extraFields: [
      b('advanced', 'onlyIfInVoiceChannel', 'Only If In Voice Channel', true),
      n('advanced', 'autoUndeafenAfterSeconds', 'Auto Undeafen After Duration (sec)', 0, 0, 86400),
    ],
  },
  undeafen: { extends: 'deafen' },
  demote: {
    defaults: { enforceRoleHierarchy: true, requireReason: true },
    extraFields: [
      s('advanced', 'staffLadderMapping', 'Staff Ladder Mapping'),
      b('advanced', 'autoPostToStaffUpdatesChannel', 'Auto Post To Staff Updates Channel'),
      channelField('advanced', 'staffUpdatesChannel', 'Staff Updates Channel'),
    ],
  },
  promote: { extends: 'demote' },
  kick: {
    defaults: { requireReason: true, requireConfirmation: true, enforceRoleHierarchy: true },
    extraFields: [
      b('advanced', 'dmTargetOnKick', 'DM Target On Kick', true),
      ta('advanced', 'dmTemplate', 'DM Template'),
      b('advanced', 'autoCreateCase', 'Auto Create Case', true),
      rl('advanced', 'protectedRoles', 'Protected Roles'),
      st('advanced', 'protectedUsers', 'Protected Users'),
    ],
  },
  load: {
    defaults: { requireConfirmation: true, minimumStaffLevel: 'admin' },
    extraFields: [st('advanced', 'approvedCogs', 'Allow Loading Only Approved Cogs')],
  },
  reload: { extends: 'load' },
  unload: { extends: 'load' },
  lock: {
    extraFields: [
      n('advanced', 'autoUnlockAfterSeconds', 'Auto Unlock After Duration (sec)', 0, 0, 604800),
      sl('advanced', 'lockScope', 'Lock Scope', [{ label: 'Channel', value: 'channel' }, { label: 'Category', value: 'category' }], 'channel'),
      b('advanced', 'restorePreviousOverwrites', 'Restore Previous Overwrites', true),
    ],
  },
  unlock: { extends: 'lock' },
  lockdown: {
    defaults: { requireConfirmation: true },
    extraFields: [
      sl('advanced', 'scope', 'Scope', [{ label: 'All Channels', value: 'all_channels' }, { label: 'Category', value: 'category' }, { label: 'List', value: 'list' }], 'all_channels'),
      cl('advanced', 'excludeChannels', 'Exclude Channels'),
      n('advanced', 'autoUnlockAfterSeconds', 'Auto Unlock After Duration (sec)', 0, 0, 604800),
      b('advanced', 'enableRaidModeAutomatically', 'Enable Raid Mode Automatically'),
    ],
  },
  unlockdown: { extends: 'lockdown' },
  hide: {
    extraFields: [
      b('advanced', 'affectsEveryoneOnly', 'Affects @everyone Only', true),
      b('advanced', 'restorePreviousOverwrites', 'Restore Previous Overwrites', true),
    ],
  },
  unhide: { extends: 'hide' },
  hideall: {
    defaults: { requireConfirmation: true },
    extraFields: [
      cl('advanced', 'excludeChannels', 'Exclude Channels'),
      st('advanced', 'excludeCategories', 'Exclude Categories'),
      b('advanced', 'restorePreviousOverwrites', 'Restore Previous Overwrites', true),
    ],
  },
  unhideall: { extends: 'hideall' },
  massban: {
    defaults: { requireConfirmation: true },
    extraFields: [
      b('permissions', 'dualControlRequired', 'Dual Control Required', true),
      n('cooldowns', 'maxMassbansPerDay', 'Max Massbans Per Day', 1, 0, 100),
      n('advanced', 'maxTargets', 'Max Targets', 50, 1, 10000),
      b('advanced', 'requireFileUpload', 'Require File Upload'),
      b('advanced', 'previewBeforeExecute', 'Preview Before Execute', true),
      b('advanced', 'dryRunMode', 'Dry Run Mode'),
      rl('advanced', 'protectedRoles', 'Protected Roles'),
      st('advanced', 'protectedUsers', 'Protected Users'),
      b('advanced', 'autoCreateCases', 'Auto Create Cases', true),
    ],
  },
  mute: {
    defaults: { requireReason: true, enforceRoleHierarchy: true },
    extraFields: [
      n('advanced', 'defaultDurationSeconds', 'Default Duration (sec)', 3600, 0, 31536000),
      n('advanced', 'maxDurationSeconds', 'Max Duration (sec)', 604800, 0, 31536000),
      s('advanced', 'muteRoleId', 'Mute Role ID'),
      b('advanced', 'autoUnmuteOnLeave', 'Auto Unmute On Leave'),
    ],
  },
  unmute: {
    extraFields: [
      b('advanced', 'autoCloseRelatedCase', 'Auto Close Related Case', true),
      b('advanced', 'logUnmute', 'Log Unmute', true),
    ],
  },
  nuke: {
    defaults: { requireConfirmation: true },
    extraFields: [
      b('permissions', 'dualControl', 'Dual Control', true),
      b('advanced', 'cloneChannelSettings', 'Clone Channel Settings', true),
      n('advanced', 'deleteMessagesLimit', 'Delete Messages Limit', 100, 0, 10000),
      b('advanced', 'autoRecreateChannel', 'Auto Recreate Channel', true),
      channelField('advanced', 'staffLogChannel', 'Log To Staff Channel'),
    ],
  },
  purge: { defaults: { requireConfirmation: true }, extraFields: purgeExtras },
  purgebots: { extends: 'purge', extraFields: [b('advanced', 'filterLockedToBots', 'Filter Locked To Bots', true)] },
  purgecontains: { extends: 'purge', extraFields: [b('advanced', 'requireContainsString', 'Require Contains String', true), b('advanced', 'regexAllowed', 'Regex Allowed')] },
  purgeembeds: { extends: 'purge', extraFields: [b('advanced', 'filterLockedToEmbeds', 'Filter Locked To Embeds', true)] },
  purgeimages: { extends: 'purge', extraFields: [b('advanced', 'filterLockedToImagesAttachments', 'Filter Locked To Images/Attachments', true)] },
  purgelinks: { extends: 'purge', extraFields: [b('advanced', 'filterLockedToLinks', 'Filter Locked To Links', true), st('advanced', 'domainAllowBlockList', 'Domain Allow/Block List')] },
  quarantine: {
    defaults: { requireReason: true, requireConfirmation: true },
    extraFields: [
      s('advanced', 'quarantineRoleId', 'Quarantine Role ID'),
      b('advanced', 'removeRolesWhenQuarantined', 'Remove Roles When Quarantined', true),
      b('advanced', 'storeAndRestoreRoles', 'Store & Restore Roles', true),
      n('advanced', 'autoUnquarantineAfterSeconds', 'Auto Unquarantine After Duration (sec)', 0, 0, 31536000),
      rl('advanced', 'protectedRoles', 'Protected Roles'),
    ],
  },
  unquarantine: { extends: 'quarantine', extraFields: [b('advanced', 'restoreRoles', 'Restore Roles', true)] },
  rename: {
    defaults: { enforceRoleHierarchy: true },
    extraFields: [
      n('advanced', 'maxNicknameLength', 'Max Nickname Length', 32, 1, 32),
      b('advanced', 'nicknameTemplateAllowed', 'Nickname Template Allowed'),
      b('advanced', 'blockRenamingStaff', 'Block Renaming Staff', true),
    ],
  },
  setnick: { extends: 'rename', extraFields: [b('advanced', 'allowResetToOriginal', 'Allow Reset To Original')] },
  say: {
    extraFields: [
      n('advanced', 'maxMessageLength', 'Max Message Length', 2000, 1, 4000),
      b('advanced', 'blockMentions', 'Block Mentions', true),
      b('advanced', 'blockLinks', 'Block Links'),
      ...commonForceEphemeral,
      b('cooldowns', 'rateLimitStrictMode', 'Rate Limit Strict Mode', true),
    ],
  },
  snipe: {
    extraFields: [
      n('advanced', 'retentionWindowMinutes', 'Retention Window Minutes', 15, 1, 1440),
      b('advanced', 'redactAttachments', 'Redact Attachments'),
      b('advanced', 'staffOnly', 'Staff Only'),
    ],
  },
  editsnipe: { extends: 'snipe' },
  softban: {
    defaults: { requireReason: true, requireConfirmation: true },
    extraFields: [
      n('advanced', 'deleteDaysDefault', 'Delete Days Default', 1, 0, 7),
      n('advanced', 'deleteDaysMax', 'Delete Days Max', 7, 0, 7),
      b('advanced', 'autoUnbanAfterSoftban', 'Auto Unban After Softban', true),
      ta('advanced', 'dmTemplate', 'DM Template'),
      b('advanced', 'autoCreateCase', 'Auto Create Case', true),
    ],
  },
  tempban: {
    defaults: { requireReason: true, requireConfirmation: true },
    extraFields: [
      n('advanced', 'defaultDurationSeconds', 'Default Duration (sec)', 86400, 0, 31536000),
      n('advanced', 'maxDurationSeconds', 'Max Duration (sec)', 2592000, 0, 31536000),
      b('advanced', 'autoUnbanOnExpire', 'Auto Unban On Expire', true),
      b('advanced', 'dmExpiryNotice', 'DM Expiry Notice'),
      b('advanced', 'autoCreateCase', 'Auto Create Case', true),
    ],
  },
  warn: {
    defaults: { requireReason: true },
    extraFields: [
      n('advanced', 'warnDecayDays', 'Warn Decay Days', 0, 0, 3650),
      n('advanced', 'maxWarnsBeforeEscalation', 'Max Warns Before Escalation', 3, 0, 1000),
      s('advanced', 'escalationPolicyOverride', 'Escalation Policy Override'),
      n('advanced', 'autoTimeoutAfterWarns', 'Auto Timeout After X Warns', 0, 0, 1000),
      b('advanced', 'autoCreateCase', 'Auto Create Case', true),
      ta('advanced', 'dmTemplate', 'DM Template'),
    ],
  },
  whitelist: {
    defaults: { requireConfirmation: true },
    extraFields: [
      sl('advanced', 'whitelistScope', 'Whitelist Scope', [{ label: 'Users', value: 'users' }, { label: 'Roles', value: 'roles' }, { label: 'Channels', value: 'channels' }], 'users'),
      n('advanced', 'defaultWhitelistDurationSeconds', 'Default Whitelist Duration (sec)', 0, 0, 31536000),
      n('advanced', 'maxWhitelistEntries', 'Max Whitelist Entries', 500, 1, 100000),
      b('advanced', 'bypassAutomod', 'Bypass Automod'),
      b('advanced', 'bypassAntiRaid', 'Bypass AntiRaid'),
      b('advanced', 'bypassCooldowns', 'Bypass Cooldowns'),
      b('advanced', 'autoExpire', 'Auto Expire'),
      b('advanced', 'logChanges', 'Log Changes', true),
      channelField('advanced', 'logChannel', 'Log Channel'),
    ],
  },
  botinfo: { extraFields: [b('advanced', 'showShardInfo', 'Show Shard Info'), b('advanced', 'showMemoryCpu', 'Show Memory/CPU'), b('advanced', 'showBuildVersion', 'Show Build Version')] },
  banner: { extraFields: [...commonAllowTargetOthers, ...commonForceEphemeral] },
  banlist: { extraFields: [b('advanced', 'showReasons', 'Show Reasons', true), b('advanced', 'showModerator', 'Show Moderator', true), n('advanced', 'maxResultsReturned', 'Max Results Returned', 100, 1, 1000), b('advanced', 'allowExport', 'Allow Export')] },
  color: { extraFields: [b('advanced', 'allowImagePreview', 'Allow Image Preview', true)] },
  coinflip: { extraFields: [...commonForceEphemeral] },
  invite: { extraFields: [...commonForceEphemeral, b('advanced', 'allowShowingPermissionsRequested', 'Allow Showing Permissions Requested', true)] },
  members: { extraFields: [...commonForceEphemeral] },
  roles: { extraFields: [n('advanced', 'maxRolesListed', 'Max Roles Listed', 100, 1, 5000), ...commonForceEphemeral] },
  roll: { extraFields: [...commonForceEphemeral, n('advanced', 'maxDiceSides', 'Max Dice Sides', 100, 2, 1000000)] },
  stats: { extraFields: [b('advanced', 'showShardInfo', 'Show Shard Info'), b('advanced', 'showCommandUsage', 'Show Command Usage'), ...commonForceEphemeral] },
  uptime: { extraFields: [...commonForceEphemeral] },
  aihelp: { extraFields: [b('advanced', 'showInternalThresholds', 'Show Internal Thresholds'), b('advanced', 'showModelVersion', 'Show Model Version'), b('advanced', 'onlyStaffCanViewAiDetails', 'Only Staff Can View AI Details')] },
  antiraid: { defaults: { minimumStaffLevel: 'admin' }, extraFields: [n('advanced', 'joinRateThreshold', 'Join Rate Threshold (joins/min)', 10, 1, 300), n('advanced', 'accountAgeMinimumHours', 'Account Age Minimum (hours)', 24, 0, 8760), b('advanced', 'autoLockdownEnabled', 'Auto Lockdown Enabled'), b('advanced', 'autoSlowmodeEnabled', 'Auto Slowmode Enabled'), n('advanced', 'autoSlowmodeSeconds', 'Auto Slowmode Seconds', 10, 0, 21600), sl('advanced', 'actionWhenTriggered', 'Action When Triggered', [{ label: 'Alert Only', value: 'alert_only' }, { label: 'Lockdown', value: 'lockdown' }, { label: 'Quarantine Joins', value: 'quarantine_joins' }, { label: 'Kick Joins', value: 'kick_joins' }], 'alert_only'), b('advanced', 'panicModeButtonEnabled', 'Panic Mode Button Enabled', true), cl('advanced', 'panicModeScope', 'Panic Mode Scope'), rl('advanced', 'whitelistedRolesBypass', 'Whitelisted Roles Bypass'), st('advanced', 'whitelistedUsersBypass', 'Whitelisted Users Bypass')] },
  automod: { extraFields: [b('advanced', 'enableRuleEditing', 'Enable Rule Editing', true), n('advanced', 'maxRulesAllowed', 'Max Rules Allowed', 50, 1, 500), sl('advanced', 'rulePriorityMode', 'Rule Priority Mode', [{ label: 'First Match', value: 'first_match' }, { label: 'All Match', value: 'all_match' }], 'first_match'), b('advanced', 'simulationToolEnabled', 'Simulation Tool Enabled', true), st('advanced', 'defaultActionSet', 'Default Action Set'), rl('advanced', 'defaultExceptionRoles', 'Default Exceptions (Roles)'), cl('advanced', 'defaultExceptionChannels', 'Default Exceptions (Channels)'), b('advanced', 'lockDuringRaidMode', 'Lock Automod Settings During Raid Mode')] },
  case: { extraFields: [b('advanced', 'allowEditingCaseReasons', 'Allow Editing Case Reasons'), b('advanced', 'allowDeletingCases', 'Allow Deleting Cases'), b('advanced', 'requireAuditLogOnEdit', 'Require Audit Log Entry On Edit', true), sl('advanced', 'caseVisibility', 'Case Visibility', [{ label: 'Staff Only', value: 'staff_only' }, { label: 'Admin Only', value: 'admin_only' }], 'staff_only')] },
  channelinfo: { extraFields: [b('advanced', 'showPermissionOverwrites', 'Show Permission Overwrites'), b('advanced', 'showSlowmode', 'Show Slowmode')] },
  charinfo: { extraFields: [b('advanced', 'allowNsfwCharacterInfo', 'Allow NSFW Character Info'), ...commonForceEphemeral] },
  choose: { extraFields: [n('advanced', 'maxOptionsAllowed', 'Max Options Allowed', 20, 2, 200), b('advanced', 'allowWeightedOptions', 'Allow Weighted Options')] },
  'court-close': { defaults: { requireConfirmation: true }, extraFields: [b('permissions', 'requireJudgeRole', 'Require Judge Role'), rl('permissions', 'judgeRoles', 'Judge Roles'), b('advanced', 'autoGenerateTranscript', 'Auto Generate Transcript', true), b('advanced', 'autoPostTranscriptToLogs', 'Auto Post Transcript To Logs Channel', true), channelField('advanced', 'transcriptLogChannel', 'Transcript Log Channel'), b('advanced', 'autoLockEvidenceSubmissions', 'Auto Lock Evidence Submissions', true)] },
  'court-evidence': { extraFields: [b('permissions', 'restrictToCaseParticipants', 'Restrict To Case Participants', true), n('advanced', 'maxEvidenceAttachments', 'Max Evidence Attachments', 5, 0, 30), st('advanced', 'allowedFileTypes', 'Allowed File Types'), b('advanced', 'autoScanLinks', 'Auto Scan Links', true)] },
  'court-file': { extraFields: [b('permissions', 'requireVerificationRole', 'Require Verification Role'), rl('permissions', 'verificationRoles', 'Verification Roles'), st('advanced', 'caseCategories', 'Case Categories'), b('advanced', 'autoAssignJudge', 'Auto Assign Judge'), b('advanced', 'autoCreateCaseThread', 'Auto Create Case Thread', true), b('advanced', 'requireEvidenceOnFile', 'Require Evidence On File')] },
  'court-jury': { extraFields: [b('permissions', 'requireJudgeRole', 'Require Judge Role'), n('advanced', 'maxJuryMembers', 'Max Jury Members', 12, 1, 300), b('advanced', 'allowRandomJurySelection', 'Allow Random Jury Selection', true)] },
  'court-setup-logs': { extraFields: [channelField('advanced', 'transcriptChannel', 'Transcript Channel'), b('advanced', 'redactSensitiveData', 'Redact Sensitive Data', true)] },
  'court-verdict': { extraFields: [b('permissions', 'requireJudgeRole', 'Require Judge Role', true), b('permissions', 'requireJuryVote', 'Require Jury Vote'), n('advanced', 'voteDurationMinutes', 'Vote Duration (minutes)', 30, 1, 10080), b('advanced', 'verdictLockAfterDecision', 'Verdict Lock After Decision', true), b('advanced', 'autoPublishVerdict', 'Auto Publish Verdict'), channelField('advanced', 'autoPublishVerdictChannel', 'Verdict Channel')] },
  'court-view-evidence': { extraFields: [b('permissions', 'restrictToCaseParticipants', 'Restrict To Case Participants', true), b('advanced', 'showHiddenEvidenceToStaff', 'Show Hidden Evidence To Staff', true)] },
  createemoji: { extraFields: [n('advanced', 'maxEmojiSizeKb', 'Max Emoji Size (KB)', 256, 1, 5120), b('advanced', 'allowAnimated', 'Allow Animated', true), b('advanced', 'requireApprovalRole', 'Require Approval Role'), roleField('advanced', 'approvalRole', 'Approval Role')] },
  debug: { defaults: { minimumStaffLevel: 'admin' }, extraFields: [b('advanced', 'showSensitiveDebugInfo', 'Show Sensitive Debug Info'), b('advanced', 'redactTokensAndIds', 'Redact Tokens/IDs', true)] },
  deleteemoji: { defaults: { requireConfirmation: true }, extraFields: [b('advanced', 'allowDeletingAnimated', 'Allow Deleting Animated', true)] },
  delwarn: { defaults: { requireReason: true }, extraFields: [b('advanced', 'allowDeletingByCaseId', 'Allow Deleting By Case ID', true)] },
  dm: { defaults: { minimumStaffLevel: 'staff' }, extraFields: [n('advanced', 'maxMessageLength', 'Max Message Length', 2000, 1, 4000), b('advanced', 'blockLinks', 'Block Links'), b('advanced', 'forceIncludeSenderTag', 'Force Include Sender Tag', true), n('cooldowns', 'abuseRateLimitPerMinute', 'Rate Limit To Prevent Abuse', 10, 1, 1000)] },
  editcase: { defaults: { requireReason: true }, extraFields: [st('advanced', 'editableFields', 'Editable Fields'), b('advanced', 'lockEditingAfterHoursEnabled', 'Lock Editing After X Hours'), n('advanced', 'lockEditingAfterHours', 'Lock Editing After X Hours', 24, 1, 8760)] },
  embed: { extraFields: [b('advanced', 'allowCustomColors', 'Allow Custom Colors', true), b('advanced', 'allowLinks', 'Allow Links', true), b('advanced', 'blockMentions', 'Block Mentions', true), n('advanced', 'maxEmbedFields', 'Max Embed Fields', 25, 1, 25), b('advanced', 'requireApprovalAboveSize', 'Require Approval Above Size')] },
  emoji: { extraFields: [b('advanced', 'subcommandOverridesEnabled', 'Subcommand Overrides Enabled', true), b('advanced', 'allowExternalEmojiRequests', 'Allow External Emoji Requests'), n('cooldowns', 'requestRateLimitPerMinute', 'Rate Limit Requests', 10, 1, 1000)] },
  emojis: { extraFields: [b('advanced', 'includeAnimated', 'Include Animated', true), n('advanced', 'maxResults', 'Max Results', 50, 1, 500), ...commonForceEphemeral] },
  enlarge: { extraFields: [n('advanced', 'maxSizeOutput', 'Max Size Output', 1024, 64, 8192), ...commonForceEphemeral] },
  firstmessage: { extraFields: [b('advanced', 'allowCrossChannelLookup', 'Allow Cross-Channel Lookup'), b('advanced', 'staffOnly', 'Staff Only')] },
  forum: { defaults: { minimumStaffLevel: 'mod' }, extraFields: [st('advanced', 'allowedActions', 'Allowed Actions'), b('advanced', 'aiAssistanceEnabled', 'AI Assistance Enabled'), n('advanced', 'autoModerateThreshold', 'Auto-Moderate Threshold', 70, 0, 100)] },
  giveaway: { extraFields: [n('advanced', 'maxGiveawayDurationHours', 'Max Giveaway Duration (hours)', 168, 1, 8760), rl('advanced', 'minimumEntryRoles', 'Min Entry Requirements (Roles)'), n('advanced', 'minimumAccountAgeDays', 'Min Entry Requirements (Account Age Days)', 0, 0, 3650), b('advanced', 'antiFraudChecks', 'Anti-Fraud Checks', true), n('advanced', 'autoRerollLimits', 'Auto Reroll Limits', 3, 0, 100), b('advanced', 'logGiveawayResults', 'Log Giveaway Results', true), channelField('advanced', 'giveawayResultsLogChannel', 'Giveaway Results Log Channel')] },
  glock: { defaults: { requireConfirmation: true }, extraFields: [sl('advanced', 'lockScope', 'Lock Scope', [{ label: 'Current Channel', value: 'current_channel' }, { label: 'Category', value: 'category' }, { label: 'All', value: 'all' }], 'current_channel'), st('advanced', 'excludeChannelIds', 'Exclude Channel IDs'), n('advanced', 'autoUnlockAfterSeconds', 'Auto Unlock After Duration (sec)', 0, 0, 604800)] },
  gunlock: { extends: 'glock' },
  guilds: { defaults: { minimumStaffLevel: 'owner' }, extraFields: [b('permissions', 'ownerOnly', 'Owner Only', true), b('advanced', 'showInviteLinks', 'Show Invite Links'), b('advanced', 'redactSensitiveInfo', 'Redact Sensitive Info', true)] },
  help: { extraFields: [b('advanced', 'showHiddenCommandsToStaff', 'Show Hidden Commands To Staff'), b('advanced', 'allowCategoryFiltering', 'Allow Category Filtering', true), b('advanced', 'helpOpensEphemeral', 'Help Opens Ephemeral')] },
  history: { extraFields: [n('advanced', 'maxCasesReturned', 'Max Cases Returned', 100, 1, 5000), b('advanced', 'includeExpiredDeleted', 'Include Expired/Deleted'), b('advanced', 'exportAllowed', 'Export Allowed')] },
  icon: { extraFields: [...commonForceEphemeral] },
  ignore: { extraFields: [sl('advanced', 'ignoreScope', 'Ignore Scope', [{ label: 'Automod Only', value: 'automod_only' }, { label: 'Commands', value: 'commands' }, { label: 'Both', value: 'both' }], 'both'), n('advanced', 'maxIgnoredItems', 'Max Ignored Items', 100, 1, 100000), b('advanced', 'requireConfirmationForGlobalIgnore', 'Require Confirmation For Global Ignore', true)] },
  inrole: { extraFields: [n('advanced', 'maxMembersReturned', 'Max Members Returned', 100, 1, 100000), b('advanced', 'exportAllowed', 'Export Allowed')] },
  leave: { defaults: { minimumStaffLevel: 'owner', requireConfirmation: true }, extraFields: [b('permissions', 'ownerOnly', 'Owner Only', true), b('advanced', 'allowLeavingOnlyNonWhitelistedGuilds', 'Allow Leaving Only Non-Whitelisted Guilds')] },
  log: { extraFields: [st('advanced', 'eventTypesEnabled', 'Event Types Enabled'), channelField('advanced', 'defaultLogChannel', 'Default Log Channel'), st('advanced', 'perEventChannelOverrides', 'Per-Event Channel Overrides'), sl('advanced', 'embedStyle', 'Embed Style', [{ label: 'Compact', value: 'compact' }, { label: 'Detailed', value: 'detailed' }], 'detailed'), b('advanced', 'redactSensitiveData', 'Redact Sensitive Data', true), n('advanced', 'retentionDays', 'Retention Days', 0, 0, 3650)] },
  mimic: { defaults: { minimumStaffLevel: 'admin', requireConfirmation: true }, extraFields: [cl('advanced', 'webhookChannelRestriction', 'Webhook Channel Restriction'), b('advanced', 'blockMentions', 'Block Mentions', true), b('advanced', 'blockLinks', 'Block Links'), n('advanced', 'maxMessageLength', 'Max Message Length', 2000, 1, 4000), b('cooldowns', 'rateLimitStrictMode', 'Rate Limit Strict Mode', true)] },
  moderation: { extraFields: [b('advanced', 'showOnlyAllowedCommands', 'Show Only Allowed Commands', true), b('advanced', 'panelOpensEphemeral', 'Panel Opens Ephemeral', true)] },
  modlogs: { extraFields: [n('advanced', 'maxResults', 'Max Results', 100, 1, 5000), b('advanced', 'includeAutomodEvents', 'Include Automod Events', true), b('advanced', 'exportAllowed', 'Export Allowed')] },
  modmail: { defaults: { minimumStaffLevel: 'mod' }, extraFields: [b('advanced', 'anonymousMode', 'Anonymous Mode'), channelField('advanced', 'threadChannel', 'Thread Channel'), n('advanced', 'autoArchiveAfterInactivityHours', 'Auto Archive After Inactivity (hours)', 72, 1, 8760), roleField('advanced', 'staffPingRole', 'Staff Ping Role'), channelField('advanced', 'transcriptLoggingChannel', 'Transcript Logging Channel')] },
  modpanel: { extraFields: [st('advanced', 'quickActionsEnabled', 'Quick Actions Enabled'), b('advanced', 'disableDangerousButtons', 'Disable Dangerous Buttons'), b('advanced', 'ephemeralPanel', 'Ephemeral Panel', true)] },
  modrole: { defaults: { enforceRoleHierarchy: true }, extraFields: [n('advanced', 'maxModeratorRoles', 'Max Moderator Roles', 5, 0, 25), b('advanced', 'autoSyncModeratorPermissions', 'Auto Sync Moderator Permissions', true)] },
  modstats: { extraFields: [b('advanced', 'includeAutomodStats', 'Include Automod Stats', true), b('advanced', 'includeStaffLeaderboard', 'Include Staff Leaderboard', true), b('advanced', 'exportAllowed', 'Export Allowed')] },
  nicknameall: { defaults: { requireConfirmation: true }, extraFields: [sl('advanced', 'scope', 'Scope', [{ label: 'All', value: 'all' }, { label: 'Role', value: 'role' }, { label: 'Filter', value: 'filter' }], 'all'), n('advanced', 'maxUsersPerRun', 'Max Users Per Run', 100, 1, 100000), s('advanced', 'nicknameTemplate', 'Nickname Template'), b('advanced', 'skipStaff', 'Skip Staff', true)] },
  note: { extraFields: [n('advanced', 'maxNoteLength', 'Max Note Length', 1000, 1, 10000), b('advanced', 'privateNotesOnly', 'Private Notes Only', true)] },
  notes: { extraFields: [b('advanced', 'allowUserToViewOwnNotes', 'Allow User To View Own Notes'), b('advanced', 'exportAllowed', 'Export Allowed')] },
  ownerpanel: { defaults: { minimumStaffLevel: 'owner' }, extraFields: [b('permissions', 'ownerOnly', 'Owner Only', true), b('advanced', 'dangerZoneButtonsEnabled', 'Danger Zone Buttons Enabled'), s('advanced', 'forceConfirmationPhrase', 'Force Confirmation Phrase'), b('advanced', 'ephemeralPanel', 'Ephemeral Panel', true)] },
  permissions: { extraFields: [b('advanced', 'allowEditingRoleMappings', 'Allow Editing Role Mappings', true), b('advanced', 'viewOnlyMode', 'View Only Mode')] },
  pin: { extraFields: [b('advanced', 'stickyMode', 'Sticky Mode'), n('advanced', 'repostIntervalSeconds', 'Repost Interval (sec)', 0, 0, 604800), b('advanced', 'autoDeleteOldSticky', 'Auto Delete Old Sticky', true), b('advanced', 'restrictToOneStickyPerChannel', 'Restrict To One Sticky Per Channel', true)] },
  r34: { extraFields: [b('channels', 'nsfwChannelsOnly', 'NSFW Channels Only', true), cl('channels', 'allowedNsfwChannels', 'Allowed NSFW Channels'), b('advanced', 'blockDuringRaidMode', 'Block During Raid Mode', true), n('advanced', 'maxResults', 'Max Results', 10, 1, 100), b('advanced', 'redactPreviewsInLogs', 'Redact Previews In Logs', true)] },
  remindme: { extraFields: [n('advanced', 'maxReminderDurationSeconds', 'Max Reminder Duration (sec)', 2592000, 60, 31536000), n('advanced', 'maxRemindersPerUser', 'Max Reminders Per User', 20, 1, 1000), b('advanced', 'allowDmReminders', 'Allow DM Reminders', true), b('advanced', 'allowChannelReminders', 'Allow Channel Reminders', true)] },
  removeall: { defaults: { requireConfirmation: true, enforceRoleHierarchy: true }, extraFields: [rl('advanced', 'protectedRoles', 'Protected Roles'), b('advanced', 'skipStaff', 'Skip Staff', true), n('advanced', 'maxUsersPerRun', 'Max Users Per Run', 100, 1, 100000)] },
  reset: { defaults: { requireConfirmation: true }, extraFields: [b('permissions', 'ownerOnly', 'Owner Only'), s('advanced', 'confirmationPhraseRequired', 'Confirmation Phrase Required'), b('advanced', 'snapshotBeforeReset', 'Snapshot Before Reset', true), sl('advanced', 'resetScope', 'Reset Scope', [{ label: 'All', value: 'all' }, { label: 'Commands Only', value: 'commands_only' }, { label: 'Modules Only', value: 'modules_only' }, { label: 'Logging Only', value: 'logging_only' }], 'all'), b('advanced', 'lockResetDuringRaidMode', 'Lock Reset During Raid Mode', true)] },
  resetnicks: { defaults: { requireConfirmation: true }, extraFields: [sl('advanced', 'scope', 'Scope', [{ label: 'All', value: 'all' }, { label: 'Role', value: 'role' }, { label: 'Filter', value: 'filter' }], 'all'), b('advanced', 'skipStaff', 'Skip Staff', true)] },
  role: { defaults: { enforceRoleHierarchy: true }, extraFields: [rl('advanced', 'assignableRolesAllowlist', 'Assignable Roles Allowlist'), rl('advanced', 'blockedRoles', 'Blocked Roles'), n('advanced', 'maxRolesPerUser', 'Max Roles Per User', 0, 0, 250), b('advanced', 'preventAssigningStaffRoles', 'Prevent Assigning Staff Roles', true)] },
  roleall: { defaults: { requireConfirmation: true }, extraFields: [n('advanced', 'maxUsersPerRun', 'Max Users Per Run', 100, 1, 100000), b('advanced', 'skipStaff', 'Skip Staff', true), rl('advanced', 'onlyAllowCertainRoles', 'Only Allow Certain Roles')] },
  rolecolor: { defaults: { enforceRoleHierarchy: true }, extraFields: [sl('advanced', 'allowedColorsMode', 'Allowed Colors', [{ label: 'Palette', value: 'palette' }, { label: 'Any', value: 'any' }], 'palette'), b('advanced', 'requireHexValidation', 'Require Hex Validation', true)] },
  roleinfo: { extraFields: [b('advanced', 'showPermissionsBitfield', 'Show Permissions Bitfield')] },
  rules: { defaults: { minimumStaffLevel: 'mod' }, extraFields: [channelField('advanced', 'rulesChannel', 'Rules Channel'), b('advanced', 'autoPostRulesEmbed', 'Auto Post Rules Embed', true), b('advanced', 'requireAcknowledgementReaction', 'Require Acknowledgement Reaction')] },
  sanction: { defaults: { minimumStaffLevel: 'supervisor', requireReason: true, requireConfirmation: true }, extraFields: [st('advanced', 'sanctionTypesEnabled', 'Sanction Types Enabled'), b('advanced', 'autoLogToStaffUpdates', 'Auto Log To Staff Updates'), b('advanced', 'dualControlRequired', 'Dual Control Required')] },
  serverinfo: { extraFields: [b('advanced', 'showBoostInfo', 'Show Boost Info', true), b('advanced', 'showSecuritySettings', 'Show Security Settings')] },
  settings: { defaults: { minimumStaffLevel: 'admin' }, extraFields: [b('advanced', 'openInteractiveSettingsDashboard', 'Open Interactive Settings Dashboard', true), b('advanced', 'disableDangerZoneSection', 'Disable Danger Zone Section')] },
  setup: { defaults: { requireConfirmation: true }, extraFields: [b('advanced', 'createChannels', 'Create Channels', true), st('advanced', 'channelsToCreate', 'Channels To Create'), b('advanced', 'createRoles', 'Create Roles', true), st('advanced', 'rolesToCreate', 'Roles To Create'), b('advanced', 'overwriteExisting', 'Overwrite Existing'), b('advanced', 'safeModeOnly', 'Safe Mode Only', true), b('advanced', 'dryRunPreview', 'Dry Run Preview', true)] },
  shutdown: { defaults: { minimumStaffLevel: 'owner', requireConfirmation: true }, extraFields: [b('permissions', 'ownerOnly', 'Owner Only', true), n('advanced', 'gracePeriodSeconds', 'Grace Period Seconds', 15, 0, 86400), b('advanced', 'notifyStaffChannelBeforeShutdown', 'Notify Staff Channel Before Shutdown', true), channelField('advanced', 'shutdownNotificationChannel', 'Shutdown Notification Channel')] },
  slowmode: { extraFields: [n('advanced', 'maxSlowmodeSeconds', 'Max Slowmode Seconds', 21600, 0, 21600), b('advanced', 'allowDisableSlowmode', 'Allow Disable Slowmode', true)] },
  spam: { defaults: { requireConfirmation: true }, extraFields: [n('advanced', 'maxSpamIterations', 'Max Spam Iterations', 10, 1, 1000), n('advanced', 'maxSpamDurationSeconds', 'Max Spam Duration (sec)', 60, 1, 3600), n('advanced', 'maxMessageLength', 'Max Message Length', 2000, 1, 4000), b('advanced', 'blockMentions', 'Block Mentions', true), b('advanced', 'blockLinks', 'Block Links', true), b('channels', 'onlyAllowInAllowedChannels', 'Only Allow In Allowed Channels', true), b('advanced', 'autoStopIfStaffTalks', 'Auto Stop If Staff Talks', true)] },
  staffguide: { defaults: { minimumStaffLevel: 'admin' }, extraFields: [channelField('advanced', 'guideChannel', 'Guide Channel'), b('advanced', 'allowStaffEditing', 'Allow Staff Editing'), b('advanced', 'logUpdates', 'Log Updates', true)] },
  staffupdates: { defaults: { minimumStaffLevel: 'admin' }, extraFields: [channelField('advanced', 'updatesChannel', 'Updates Channel'), b('advanced', 'postPromotionDemotionLogs', 'Post Promotion/Demotion Logs', true), b('advanced', 'includeRoleDiffs', 'Include Role Diffs', true)] },
  status: { defaults: { minimumStaffLevel: 'admin' }, extraFields: [st('advanced', 'allowedStatusTypes', 'Allowed Status Types'), n('advanced', 'maxStatusLength', 'Max Status Length', 128, 1, 1024), b('advanced', 'restrictDuringRaidMode', 'Restrict During Raid Mode', true)] },
  steal: { extraFields: [b('advanced', 'allowAnimated', 'Allow Animated', true), n('advanced', 'maxEmojiSizeKb', 'Max Emoji Size', 256, 1, 5120), b('advanced', 'requireApprovalRole', 'Require Approval Role'), roleField('advanced', 'approvalRole', 'Approval Role')] },
  stopspam: { extraFields: [sl('advanced', 'whoCanStop', 'Who Can Stop', [{ label: 'Creator Only', value: 'creator_only' }, { label: 'Staff', value: 'staff' }, { label: 'Admins', value: 'admins' }], 'staff'), b('advanced', 'autoLogStopEvent', 'Auto Log Stop Event', true)] },
  strip: { defaults: { requireConfirmation: true, enforceRoleHierarchy: true }, extraFields: [rl('advanced', 'protectedRoles', 'Protected Roles'), b('advanced', 'restoreRolesOption', 'Restore Roles Option', true), b('advanced', 'autoCreateCase', 'Auto Create Case', true)] },
  sync: { extraFields: [st('advanced', 'syncTargets', 'Sync Targets'), b('advanced', 'showDiffBeforeSync', 'Show Diff Before Sync', true), b('advanced', 'autoSyncOnConfigChange', 'Auto Sync On Config Change')] },
  ticket: { extraFields: [channelField('advanced', 'threadChannel', 'Thread Channel'), roleField('advanced', 'staffRole', 'Staff Ping Role'), channelField('advanced', 'transcriptChannel', 'Transcript Logging Channel')] },
  ticketpanel: { extends: 'ticket' },
  unban: { defaults: { requireReason: true }, extraFields: [b('advanced', 'autoCreateCase', 'Auto Create Case', true), b('advanced', 'logUnbanToStaffChannel', 'Log Unban To Staff Channel', true)] },
  userinfo: { extraFields: [b('advanced', 'showPreviousNames', 'Show Previous Names'), b('advanced', 'showInfractionsSummary', 'Show Infractions Summary (staff-only)')] },
  utility: { extraFields: [b('advanced', 'showOnlyAllowedCommands', 'Show Only Allowed Commands', true), b('advanced', 'ephemeralPanel', 'Ephemeral Panel', true)] },
  vc: { extraFields: [st('advanced', 'allowedActions', 'Allowed Actions'), b('advanced', 'onlyWorksIfExecutorInVoice', 'Only Works If Executor In Voice')] },
  vckick: { defaults: { enforceRoleHierarchy: true }, extraFields: [b('advanced', 'onlySameVoiceChannel', 'Only Same Voice Channel')] },
  vcmove: { defaults: { enforceRoleHierarchy: true }, extraFields: [cl('advanced', 'allowedDestinationChannels', 'Allowed Destination Channels')] },
  vcmute: { defaults: { enforceRoleHierarchy: true }, extraFields: [b('advanced', 'autoUnmuteOnLeave', 'Auto Unmute On Leave')] },
  vcunmute: { extends: 'vcmute' },
  verifypanel: { extraFields: [channelField('advanced', 'verificationChannel', 'Verification Channel'), roleField('advanced', 'verificationRole', 'Verification Role'), n('advanced', 'autoRemoveUnverifiedAfterSeconds', 'Auto Remove Unverified After Time (sec)', 0, 0, 31536000), b('advanced', 'logVerificationEvents', 'Log Verification Events', true), channelField('advanced', 'verificationLogChannel', 'Verification Log Channel')] },
  warnings: { extraFields: [b('advanced', 'allowUserToViewOwnWarnings', 'Allow User To View Own Warnings'), b('advanced', 'includeExpired', 'Include Expired'), n('advanced', 'maxResults', 'Max Results', 100, 1, 1000), b('advanced', 'exportAllowed', 'Export Allowed')] },
};

function normalizeCommandName(name: string): string {
  return name.trim().toLowerCase();
}

function mergeProfile(base: ResolvedCommandProfile, next: CommandProfileDef): ResolvedCommandProfile {
  return {
    requiredPermission: base.requiredPermission,
    defaults: { ...base.defaults, ...(next.defaults || {}) },
    extraFields: [...base.extraFields, ...(next.extraFields || [])],
  };
}

function dedupeFieldsByKey(fields: CommandExtraField[]): CommandExtraField[] {
  const output: CommandExtraField[] = [];
  const byKey = new Map<string, number>();
  for (const field of fields) {
    const key = `${field.tab}:${field.key}`;
    const existingIndex = byKey.get(key);
    if (existingIndex === undefined) {
      byKey.set(key, output.length);
      output.push(field);
    } else {
      output[existingIndex] = field;
    }
  }
  return output;
}

export function resolveCommandProfile(name: string): ResolvedCommandProfile {
  const normalized = normalizeCommandName(name);
  const visited = new Set<string>();

  const resolveRecursive = (currentName: string): ResolvedCommandProfile => {
    if (visited.has(currentName)) {
      return { defaults: {}, extraFields: [], requiredPermission: PERMISSION_BY_COMMAND[currentName] };
    }
    visited.add(currentName);
    const current = PROFILE_DEFS[currentName];
    const fallbackPermission = PERMISSION_BY_COMMAND[currentName];
    if (!current) {
      return { defaults: {}, extraFields: [], requiredPermission: fallbackPermission };
    }
    const parent = current.extends
      ? resolveRecursive(normalizeCommandName(current.extends))
      : { defaults: {}, extraFields: [], requiredPermission: fallbackPermission };
    const merged = mergeProfile(parent, current);
    return {
      requiredPermission: fallbackPermission || merged.requiredPermission,
      defaults: merged.defaults,
      extraFields: merged.extraFields,
    };
  };

  const resolved = resolveRecursive(normalized);
  return {
    requiredPermission: resolved.requiredPermission,
    defaults: resolved.defaults,
    extraFields: dedupeFieldsByKey(resolved.extraFields),
  };
}
