  # ModBot - Advanced Discord Moderation Bot

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.0+-blue.svg)](https://github.com/Rapptz/discord.py)
[![Version](https://img.shields.io/badge/version-3.3.0-green.svg)](https://github.com/yourusername/modbot)

An enterprise-grade Discord moderation bot with comprehensive features including AI-powered moderation, advanced logging, ticket systems, and more.

## 🚀 Features

### Core Moderation
- **Case Management** - Track all moderation actions with case numbers
- **Warnings System** - Issue and manage warnings for users
- **Timeout/Mute** - Temporary timeout with duration support
- **Kick & Ban** - Full moderation controls with audit logs
- **Tempbans** - Automatic temporary bans with expiration
- **Mod Notes** - Internal notes for staff about users

### 🤖 AI Moderation (Powered by Groq)
- **Natural Language Processing** - Talk to the bot naturally
- **Smart Action Detection** - Understands creative commands ("terminate", "banish", etc.)
- **Conversational AI** - Chat with the bot for advice
- **Rate Limiting** - Built-in protection against API abuse (30 calls/minute per user)
- **Permission Aware** - Respects user permissions automatically

### 📋 Logging System
- **Message Logs** - Deleted and edited messages
- **Member Logs** - Joins, leaves, role changes
- **Voice Logs** - Voice activity tracking
- **Moderation Logs** - All mod actions logged
- **Audit Logs** - Server changes and updates
- **Channel Caching** - Optimized with TTL caching

### 🎫 Support Systems
- **Ticket System** - User support tickets
- **Modmail** - Direct messaging to staff
- **Reports** - User reporting system
- **Court System** - Evidence-based decisions with jury

### 🛡️ Auto-Moderation
- **Spam Detection** - Auto-detect and handle spam
- **Anti-Raid** - Protect against raid attacks
- **Word Filters** - Customizable word filtering
- **Link Protection** - Control link posting

### 📊 Additional Features
- **Reaction Roles** - Self-assignable roles
- **Voice Roles** - Auto-roles for voice channels
- **Giveaways** - Automated giveaway system
- **Staff Management** - Internal staff sanctioning
- **Utility Commands** - Snipe, userinfo, serverinfo, etc.

## 📦 Installation

### Prerequisites
- Python 3.10 or higher
- Discord Bot Token ([Get one here](https://discord.com/developers/applications))
- Optional: Groq API Key for AI features ([Get one here](https://console.groq.com/))

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/modbot.git
cd modbot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**

Create a `.env` file in the root directory:
```env
# Required
DISCORD_TOKEN=your_discord_bot_token_here

# Optional
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
OWNER_IDS=123456789,987654321
PREFIX=!

# Optional (recommended for persistent data on ephemeral hosts)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_STORAGE_BUCKET=modbot-data
SUPABASE_STORAGE_DB_PATH=modbot/modbot.db
SUPABASE_SYNC_INTERVAL_SECONDS=15
```

4. **Enable Discord Intents**

In the [Discord Developer Portal](https://discord.com/developers/applications):
- Go to your bot application
- Navigate to "Bot" section
- Enable these Privileged Gateway Intents:
  - ✅ Server Members Intent
  - ✅ Message Content Intent
  - ✅ Presence Intent

5. **Run the bot**
```bash
python bot.py
```

## ⚙️ Configuration

### Setting Up Logging Channels

Use the `/logging` command to configure where logs should be sent:

```
/logging type:mod channel:#mod-logs
/logging type:audit channel:#audit-logs
/logging type:message channel:#message-logs
/logging type:voice channel:#voice-logs
/logging type:automod channel:#automod-logs
/logging type:report channel:#reports
/logging type:ticket channel:#tickets
```

View current configuration:
```
/logconfig
```

### Announcements (Admin Only)

Send an announcement to any channel:

```
/announce channel:#announcements message:"Server maintenance tonight at 10PM." embed:true
```

Keep a “sticky” message at the bottom of a channel (Admin only). In very busy channels, bumps are rate-limited to avoid Discord rate limits, so it may lag slightly:

```
/pin message:"Please read #rules before chatting." duration:1d embed:true
```

### AI Moderation Examples

Mention the bot with natural language:

```
@ModBot terminate @User for spamming
@ModBot banish @User for being toxic, delete 1 day of messages
@ModBot execute @User for 2 hours for using slurs
@ModBot purge 50 messages in this channel
@ModBot hey, what's the best way to handle a raid?
```

### AI Moderation Controls (NEW)

Use `/aimod` to control the AI mention router per-server:

```
/aimod status
/aimod confirm enabled:true actions:ban_member,kick_member,purge_messages timeout_seconds:25
/aimod preview text:"ban @User for spam" target:@User
/aimod disable
```

## 🏗️ Architecture

### Advanced Features (v3.3.0)

#### 1. Database Connection Pooling
- Persistent SQLite connection with WAL mode
- Automatic transaction management
- Input validation on all queries
- Database indexes for optimal performance

#### 2. Advanced Caching System
- **TTL Cache** - Time-to-live caching with automatic expiration
- **LRU Eviction** - Least recently used item removal
- **Snipe Cache** - Deleted/edited messages (5min TTL, 500 items max)
- **Prefix Cache** - Guild prefixes (10min TTL)
- **Channel Cache** - Log channels (5min TTL)
- **No Memory Leaks** - Automatic cleanup prevents unbounded growth

#### 3. Rate Limiting
- Sliding window algorithm
- Per-user rate limiting for AI features
- Configurable limits (default: 30 calls/60 seconds)
- Automatic cleanup of old entries

#### 4. Enhanced Error Handling
- Comprehensive error logging
- User-friendly error messages
- Automatic channel validation
- Graceful degradation

#### 5. Performance Optimizations
- Connection pooling reduces DB overhead
- Channel caching reduces API calls
- Efficient query patterns with indexes
- Async/await throughout

## 📁 Project Structure

```
modbot/
├── bot.py                 # Main bot file with event handlers
├── database.py            # Database handler with connection pooling
├── config.py              # Configuration and constants
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
├── cogs/                  # Command modules
│   ├── aimoderation.py    # AI-powered moderation
│   ├── logging_cog.py     # Event logging system
│   ├── moderation.py      # Core moderation commands
│   ├── automod.py         # Auto-moderation features
│   ├── tickets.py         # Ticket system
│   ├── reports.py         # User reporting
│   ├── modmail.py         # Modmail system
│   ├── court.py           # Court system
│   ├── staff.py           # Staff management
│   ├── roles.py           # Role management
│   ├── voice.py           # Voice features
│   ├── antiraid.py        # Anti-raid protection
│   ├── utility.py         # Utility commands
│   ├── admin.py           # Admin commands
│   └── setup.py           # Initial setup
└── utils/                 # Utility modules
    ├── checks.py          # Permission checks
    ├── embeds.py          # Embed templates
    ├── paginator.py       # Pagination system
    ├── time_parser.py     # Time parsing utilities
    ├── cache.py           # Advanced caching (NEW)
    └── messages.py        # Message templates (NEW)
```

## 🔒 Security Features

- **Permission Hierarchy** - Respects role hierarchy
- **Input Validation** - All user inputs validated
- **SQL Injection Protection** - Parameterized queries
- **Rate Limiting** - Prevents API abuse
- **Owner-Only Commands** - Restricted admin access
- **Audit Logging** - Complete action history

## 📊 Database Schema

The bot uses SQLite with the following tables:

- `guild_settings` - Server configuration
- `cases` - Moderation case tracking
- `warnings` - User warnings
- `mod_notes` - Internal staff notes
- `tempbans` - Temporary bans
- `mod_stats` - Moderator statistics
- `reports` - User reports
- `tickets` - Support tickets
- `staff_sanctions` - Staff disciplinary actions
- `court_sessions` - Court system data
- `court_evidence` - Evidence submissions
- `court_votes` - Jury votes
- `modmail_threads` - Modmail conversations
- `modmail_messages` - Modmail message history
- `giveaways` - Giveaway tracking
- `reaction_roles` - Reaction role assignments
- `voice_roles` - Voice channel roles

## 🛠️ Development

### Running in Development Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python bot.py
```

### Database Backup

```python
# Backup guild data
backup_json = await bot.db.backup_guild_data(guild_id)
with open('backup.json', 'w') as f:
    f.write(backup_json)
```

### Database Statistics

```python
# Get database statistics
stats = await bot.db.get_database_stats()
print(f"Database size: {stats['database_size_mb']} MB")
```

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 Changelog

### Version 3.3.0 (Current)
- ✅ Added database connection pooling
- ✅ Implemented advanced TTL caching system
- ✅ Added rate limiting for AI features
- ✅ Fixed discord.py 2.0+ compatibility
- ✅ Enhanced error recovery in logging
- ✅ Added database indexes for performance
- ✅ Implemented transaction safety
- ✅ Added input validation
- ✅ Created centralized message templates
- ✅ Improved memory management
- ✅ Added backup and statistics functions

### Version 3.2.0
- Added AI moderation with Groq
- Implemented court system
- Enhanced logging system

### Version 3.1.0
- Added modmail system
- Implemented staff sanctions
- Enhanced ticket system

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper
- [Groq](https://groq.com/) - AI inference API
- [aiosqlite](https://github.com/omnilib/aiosqlite) - Async SQLite

## 📞 Support

- **Documentation**: [Wiki](https://github.com/yourusername/modbot/wiki)
- **Issues**: [GitHub Issues](https://github.com/yourusername/modbot/issues)
- **Discord**: [Support Server](https://discord.gg/yourinvite)

## ⚠️ Disclaimer

This bot is provided as-is. Always test in a development environment before deploying to production servers. Ensure you comply with Discord's Terms of Service and API guidelines.

---

Made with ❤️ by the ModBot team
