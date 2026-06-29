# Taste (Continuously Learned by [CommandCode][cmd])

[cmd]: https://commandcode.ai/

# code-style
- In JSX inline styles, use CSS custom property references (`var(--token)`) instead of hardcoded hex color values for brand, semantic, and surface colors. The CSS token system should be the single source of truth for all colors. Confidence: 0.70

# deepseek
- Organize DeepSeek web chats as one chat per server channel, named with the convention "ServerName -> Channel". Confidence: 0.70
- When performing AI research, do not include chat history in the research prompt. Confidence: 0.65

# discord-bot
- Bot responses should not repeat or echo back what a user said when asked to do so (anti-repetition safety). Confidence: 0.65
- Research responses should include a "View Sources" button at the bottom of the embed. Confidence: 0.60
- Avoid forced slang in bot responses; keep the tone natural and unforced. Confidence: 0.65

# aimoderation
- The aimoderation module (cogs/moderation/ai/aimoderation.py, ~6,400 line monolith) should be fully rewritten — the user finds the current code quality unacceptable. Keep the same functionality but with clean, modular architecture. Confidence: 0.85

