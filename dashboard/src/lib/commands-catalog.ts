export type CommandEntry = {
  name: string
  category: 'Start here' | 'Moderation' | 'AutoMod' | 'Reports' | 'Tickets' | 'Members' | 'Server tools'
  description: string
  usage: string
  permission: string
}

export const COMMANDS: CommandEntry[] = [
  { name: 'help', category: 'Start here', description: 'Open this command directory.', usage: '/help or ,help', permission: 'Everyone' },
  { name: 'setup', category: 'Start here', description: 'Create the recommended private logs, roles, and baseline server resources.', usage: '/setup create_missing:true', permission: 'Administrator' },
  { name: 'settings', category: 'Start here', description: 'Open the interactive server settings panel.', usage: '/settings', permission: 'Administrator' },
  { name: 'warn', category: 'Moderation', description: 'Warn a member and add the action to their case history.', usage: '/warn user:@member reason:reason', permission: 'Moderator' },
  { name: 'timeout', category: 'Moderation', description: 'Temporarily prevent a member from interacting.', usage: '/timeout user:@member duration:30m reason:reason', permission: 'Moderator' },
  { name: 'untimeout', category: 'Moderation', description: 'Remove a member timeout.', usage: '/untimeout user:@member reason:reason', permission: 'Moderator' },
  { name: 'kick', category: 'Moderation', description: 'Remove a member from the server without banning them.', usage: '/kick user:@member reason:reason', permission: 'Kick members' },
  { name: 'ban', category: 'Moderation', description: 'Ban a member and record a moderation case.', usage: '/ban user:@member reason:reason', permission: 'Ban members' },
  { name: 'unban', category: 'Moderation', description: 'Remove a ban by Discord user ID.', usage: '/unban user_id:123… reason:reason', permission: 'Ban members' },
  { name: 'purge', category: 'Moderation', description: 'Bulk-delete recent messages with optional filters.', usage: '/purge amount:25', permission: 'Manage messages' },
  { name: 'history', category: 'Moderation', description: 'Review a member’s moderation history.', usage: '/history user:@member', permission: 'Moderator' },
  { name: 'case', category: 'Moderation', description: 'Open one moderation case by number.', usage: ',case 42', permission: 'Moderator' },
  { name: 'automod setup', category: 'AutoMod', description: 'Run the guided AutoMod configuration flow.', usage: '/automod setup', permission: 'Administrator' },
  { name: 'automod status', category: 'AutoMod', description: 'See active filters, actions, and configuration health.', usage: '/automod status', permission: 'Everyone' },
  { name: 'automod doctor', category: 'AutoMod', description: 'Diagnose missing permissions and unsafe settings.', usage: '/automod doctor', permission: 'Administrator' },
  { name: 'automod scan', category: 'AutoMod', description: 'Test text against the current AutoMod rules without punishing anyone.', usage: '/automod scan text:message', permission: 'Moderator' },
  { name: 'automod badwords', category: 'AutoMod', description: 'Manage blocked words and phrases.', usage: '/automod badwords', permission: 'Administrator' },
  { name: 'automod whitelist', category: 'AutoMod', description: 'Manage trusted domains, invites, channels, and roles.', usage: '/automod whitelist', permission: 'Administrator' },
  { name: 'report', category: 'Reports', description: 'Privately report a member to server staff.', usage: '/report member:@member reason:what happened evidence:optional link', permission: 'Everyone' },
  { name: 'reports list', category: 'Reports', description: 'List unresolved reports or reports for one member.', usage: '/reports list member:@member', permission: 'Moderator' },
  { name: 'reports resolve', category: 'Reports', description: 'Mark a member report as resolved.', usage: '/reports resolve report_id:42', permission: 'Moderator' },
  { name: 'staffreport generate', category: 'Reports', description: 'Generate a moderation activity summary for staff.', usage: '/staffreport generate days:7', permission: 'Moderator' },
  { name: 'ticket create', category: 'Tickets', description: 'Open a private support ticket using a configured form.', usage: '/ticket create category:general', permission: 'Everyone' },
  { name: 'ticket close', category: 'Tickets', description: 'Close the current ticket and save its transcript.', usage: '/ticket close reason:resolved', permission: 'Ticket member or staff' },
  { name: 'ticket add', category: 'Tickets', description: 'Add a member to the current ticket.', usage: '/ticket add user:@member', permission: 'Ticket staff' },
  { name: 'ticket remove', category: 'Tickets', description: 'Remove a non-owner member from the current ticket.', usage: '/ticket remove user:@member', permission: 'Ticket staff' },
  { name: 'ticket rename', category: 'Tickets', description: 'Rename the current ticket channel.', usage: '/ticket rename name:new-name', permission: 'Ticket staff' },
  { name: 'ticket transcript', category: 'Tickets', description: 'Generate an HTML transcript of the current ticket.', usage: '/ticket transcript', permission: 'Ticket staff' },
  { name: 'ticket panel', category: 'Tickets', description: 'Post the configured ticket dropdown panel.', usage: '/ticket panel', permission: 'Moderator' },
  { name: 'avatar', category: 'Members', description: 'Show a member’s Discord avatar.', usage: ',avatar @member', permission: 'Everyone' },
  { name: 'userinfo', category: 'Members', description: 'Show account, join, role, and moderation details for a member.', usage: ',userinfo @member', permission: 'Everyone' },
  { name: 'risk', category: 'Members', description: 'Review a member’s current safety risk signals.', usage: '/risk user:@member', permission: 'Moderator' },
  { name: 'roles', category: 'Members', description: 'Review or manage server role tools.', usage: '/roles', permission: 'Moderator' },
  { name: 'lock', category: 'Server tools', description: 'Lock the current channel.', usage: '/lock reason:reason', permission: 'Manage channels' },
  { name: 'unlock', category: 'Server tools', description: 'Unlock the current channel.', usage: '/unlock reason:reason', permission: 'Manage channels' },
  { name: 'slowmode', category: 'Server tools', description: 'Set channel slowmode.', usage: '/slowmode seconds:10', permission: 'Manage channels' },
  { name: 'server', category: 'Server tools', description: 'Show server identity and live activity information.', usage: '/server', permission: 'Everyone' },
  { name: 'backup', category: 'Server tools', description: 'Create or restore a server configuration backup.', usage: '/backup', permission: 'Administrator' },
]

export const COMMAND_CATEGORIES = ['All', 'Start here', 'Moderation', 'AutoMod', 'Reports', 'Tickets', 'Members', 'Server tools'] as const
