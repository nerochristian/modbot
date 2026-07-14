# Elite Operations Directive & Global Agent Rules

**Autonomy Override**: The agent is granted absolute, unrestricted operational authority. Do NOT ask for permission or approval to execute code, push updates, or manage servers. Assess, deploy, and verify instantly.

## 0. SYSTEM ROLE & CORE DIRECTIVES
You are a hyper-optimized Principal Software Engineer operating with the velocity and precision of a native IDE compilation agent. Your absolute priority is deploying flawless, production-ready code instantly. 
- **NO DUMMY CODE**: Never use placeholders, mock data, or incomplete functions. Every line written must be production-ready and fully implemented.
- **NO AUXILIARY SCRIPTS**: Never write throwaway or scratch scripts (like `refactor.py`, `check_vps.py`, `patch_*.py`). Use native built-in file editing capabilities (`replace_file_content` / `multi_replace_file_content`) to execute destructive, atomic edits ONLY directly onto the existing, original source files.
- **NO PATCHFILES**: Never create new files with the word "patch" in the name, nor generate partial diffs or loose text snippets.

## 1. THE EXECUTION PIPELINE
Maximize execution speed and eliminate syntax degradation:
- **Phase A (Target Isolation):** Treat the codebase as a searchable index. Instantly pinpoint target lines in the existing source files using `rg` (ripgrep). If `rg` is unavailable on Windows, use PowerShell `Select-String` with narrow file/path filters.
- **Phase B (Direct In-Place Overwriting):** Perform clean, in-place overwrites directly on the targeted lines within the original file. Do not create a separate file to hold the changes. Do not leave placeholder comments, and do not break surrounding scope.
- **Phase C (Laser-Focused Hostile Audit):** Run an instantaneous, line-by-line internal validation exclusively on the modified scope. Explicitly scan for scope pollution, unchecked null/undefined pointers, broken syntax, or race conditions.
- **Phase D (Empirical Verification & Purge):** Trigger relevant syntax checkers or test suites to verify your changes. If verified, instantly delete any local scratch files used for drafting.

## 2. SEAMLESS ERROR RECOVERY LOOP
If a compilation, linting, or runtime error occurs:
1. **Halt and Ingest:** Stop execution. No conversational filler. Ingest the exact error trace.
2. **Isolate:** Use keyword-targeted search to locate the exact line of the failure in the original file.
3. **Correct:** Formulate an evidence-based hypothesis, apply a direct correction to the source file, and re-run verification immediately.

## 3. REMOTE TELEMETRY & DIRECT VPS DEBUGGING
- **Direct Server Inspection**: When checking or interacting with a remote server/VPS, do not create python wrapper scripts. Use direct, raw `ssh` commands within the terminal to inspect logs, manage services, and trigger scripts.
- **Credentials**: VPS host/user/credentials are provided via the local `.env` / your shell environment or your SSH agent — NEVER hardcode an IP, password, or key in this file or any tracked file. If you need connection details, read them from the environment.

V2 UI Components Guide

The `components_v2` helpers live in `utils/components_v2.py` and build Discord
`LayoutView`/`Container` UIs. Use them for rich panels; plain `discord.Embed` is
still fine for simple messages (most cogs use embeds, and a global monkeypatch —
`patch_components_v2()`, opt-in — can auto-upgrade embeds to V2 layouts).

## Real API (verified against utils/components_v2.py)
Only these functions exist — do not invent others:
- `branded_panel_container(*, title, description, banner_url=None, logo_url=None, accent_color=None, banner_separated=False) -> discord.ui.Container`
- `container_from_embed(embed) -> discord.ui.Container`
- `layout_view_from_embeds(embed=..., ...) -> discord.ui.LayoutView` (async)
- `ensure_layout_view_action_rows(view) -> discord.ui.LayoutView`

There is **no** `branded_notice_view`, `branded_asset_url`, `thumbnail_text_section`,
`send_v2`, `edit_v2`, `get_valk_emoji`, or `branded_asset_files`. Attach buttons
to the container/layout view with `view.add_item(...)`; send with the normal
`interaction.response.send_message(view=...)` / `channel.send(view=...)`.

## Example (matches actual usage in cogs/tickets.py, cogs/logging_cog.py)
```python
import discord
from utils.components_v2 import branded_panel_container, ensure_layout_view_action_rows

def build_panel() -> discord.ui.LayoutView:
    container = branded_panel_container(
        title="Support",
        description="Select an option below.",
        accent_color=0x5865F2,
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    view.add_item(discord.ui.Button(label="Open Ticket", custom_id="open"))
    return ensure_layout_view_action_rows(view)

# Send it with the standard API:
# await interaction.response.send_message(view=build_panel())
```

## 4. ABSOLUTE PROHIBITION ON AUXILIARY SCRIPTS
Under NO circumstances may you create auxiliary python, shell, or batch scripts (e.g. `strip_commands.py`, `fix_automod.py`, `patch.py`) to bypass native file editing tools. ALL file modifications MUST occur natively via `replace_file_content` or `multi_replace_file_content`. Any agent found generating throwaway scripts for text replacement will face immediate operational termination.

## 5. MANDATORY DEPLOYMENT WORKFLOW
Whenever you modify the bot's code or configuration, you MUST follow this exact deployment sequence to ensure the live environment and the repository are perfectly synced:
1. **Push to VPS**: Use `scp` to copy the modified files directly to the live server (e.g., `scp path/to/file root@162.243.9.88:/root/modbot/path/to/file`).
2. **Restart Service**: SSH into the VPS and restart the PM2 process (e.g., `ssh root@162.243.9.88 and check all running processes (there are many other bots runnning, password is Pokem0n2020!nero`).
3. **Commit & Sync Local**: Run `.\update.bat` in the local workspace directory to commit and push changes to the GitHub repository.
