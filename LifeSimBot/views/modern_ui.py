# views/modern_ui.py
"""
Modern UI Components System - Simple, Clean, and Powerful
Uses Discord Components v2 to create a consistent, beautiful user experience
"""

import discord
from typing import Optional, List, Dict, Callable, Any
from datetime import datetime, timezone

from views.v2_embed import apply_v2_embed_layout, disable_all_interactive

# ============= COLOR SCHEME =============

class Colors:
    """Modern, accessible color palette"""
    PRIMARY = 0x5865F2      # Discord Blurple
    SUCCESS = 0x57F287      # Green
    WARNING = 0xFEE75C      # Yellow
    DANGER = 0xED4245       # Red
    SECONDARY = 0x4E5D94    # Muted Blue
    DARK = 0x2C2F33         # Dark Gray
    LIGHT = 0xFFFFFF        # White
    INFO = 0x3498DB         # Light Blue
    
    # Category specific
    ECONOMY = 0x2ECC71      # Emerald
    JOBS = 0x3498DB         # Blue
    SOCIAL = 0xE91E63       # Pink
    GAMING = 0x9B59B6       # Purple
    ADMIN = 0xE74C3C        # Red


# ============= ICONS & EMOJIS =============

class Icons:
    """Consistent icon set for UI elements"""
    # Navigation
    HOME = "🏠"
    BACK = "⬅️"
    NEXT = "➡️"
    REFRESH = "🔄"
    CLOSE = "❌"
    
    # Actions
    CHECK = "✅"
    CANCEL = "❌"
    INFO = "ℹ️"
    SEARCH = "🔍"
    SETTINGS = "⚙️"
    
    # Status
    ONLINE = "🟢"
    OFFLINE = "🔴"
    IDLE = "🟡"
    LOADING = "⏳"
    
    # Features
    MONEY = "💰"
    LEVEL = "⭐"
    ENERGY = "⚡"
    HEART = "❤️"
    SHIELD = "🛡️"
    TROPHY = "🏆"
    
    # Categories
    JOBS = "💼"
    SHOP = "🛒"
    INVENTORY = "🎒"
    CASINO = "🎰"
    CRIME = "🔪"
    SOCIAL = "👥"


# ============= BASE MODERN VIEW =============

class ModernView(discord.ui.LayoutView):
    """
    Base view with modern styling and common functionality
    All custom views should inherit from this
    """
    
    def __init__(self, user: discord.User, *, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.user = user
        self.message: Optional[discord.Message] = None
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the command user can interact"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                f"{Icons.CANCEL} This isn't your menu!",
                ephemeral=True
            )
            return False
        return True
    
    async def on_timeout(self):
        """Disable all components on timeout"""
        if self.message:
            disable_all_interactive(self)
            try:
                await self.message.edit(view=self)
            except:
                pass
    
    def create_embed(
        self,
        title: str,
        description: str = None,
        color: int = Colors.PRIMARY,
        fields: List[Dict[str, Any]] = None,
        footer: str = None,
        thumbnail: str = None,
        image: str = None
    ) -> discord.Embed:
        """Create a consistently styled embed"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", True)
                )
        
        if footer:
            embed.set_footer(text=footer, icon_url=self.user.display_avatar.url)
        else:
            embed.set_footer(text=f"Requested by {self.user.name}", icon_url=self.user.display_avatar.url)
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        if image:
            embed.set_image(url=image)
        
        return embed
    
    async def update(self, interaction: discord.Interaction, embed: discord.Embed = None):
        """Update the view with new content"""
        if embed is not None:
            apply_v2_embed_layout(self, embed=embed)
        await interaction.response.edit_message(view=self)


# ============= MODERN PAGINATION VIEW =============

class PaginatedView(ModernView):
    """
    Modern paginated view with smooth navigation
    Perfect for lists, shops, leaderboards, etc.
    """
    
    def __init__(self, user: discord.User, items: List[Any], items_per_page: int = 5, *, timeout: float = 180):
        super().__init__(user, timeout=timeout)
        self.items = items
        self.items_per_page = items_per_page
        self.current_page = 0
        self.total_pages = max(1, (len(items) + items_per_page - 1) // items_per_page)
        
        # Add navigation buttons
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.clear_items()
        
        # First page button
        first_btn = discord.ui.Button(
            emoji="⏮️",
            style=discord.ButtonStyle.secondary,
            disabled=self.current_page == 0,
            row=0
        )
        first_btn.callback = self.first_page
        self.add_item(first_btn)
        
        # Previous button
        prev_btn = discord.ui.Button(
            emoji="◀️",
            style=discord.ButtonStyle.primary,
            disabled=self.current_page == 0,
            row=0
        )
        prev_btn.callback = self.previous_page
        self.add_item(prev_btn)
        
        # Page indicator
        page_btn = discord.ui.Button(
            label=f"Page {self.current_page + 1}/{self.total_pages}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
            row=0
        )
        self.add_item(page_btn)
        
        # Next button
        next_btn = discord.ui.Button(
            emoji="▶️",
            style=discord.ButtonStyle.primary,
            disabled=self.current_page >= self.total_pages - 1,
            row=0
        )
        next_btn.callback = self.next_page
        self.add_item(next_btn)
        
        # Last page button
        last_btn = discord.ui.Button(
            emoji="⏭️",
            style=discord.ButtonStyle.secondary,
            disabled=self.current_page >= self.total_pages - 1,
            row=0
        )
        last_btn.callback = self.last_page
        self.add_item(last_btn)
        
        # Refresh button
        refresh_btn = discord.ui.Button(
            emoji=Icons.REFRESH,
            style=discord.ButtonStyle.secondary,
            row=1
        )
        refresh_btn.callback = self.refresh
        self.add_item(refresh_btn)
        
        # Close button
        close_btn = discord.ui.Button(
            emoji=Icons.CLOSE,
            style=discord.ButtonStyle.danger,
            row=1
        )
        close_btn.callback = self.close
        self.add_item(close_btn)
    
    def get_page_items(self) -> List[Any]:
        """Get items for current page"""
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        return self.items[start:end]
    
    async def first_page(self, interaction: discord.Interaction):
        self.current_page = 0
        self.update_buttons()
        await self.update_page(interaction)
    
    async def previous_page(self, interaction: discord.Interaction):
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await self.update_page(interaction)
    
    async def next_page(self, interaction: discord.Interaction):
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        self.update_buttons()
        await self.update_page(interaction)
    
    async def last_page(self, interaction: discord.Interaction):
        self.current_page = self.total_pages - 1
        self.update_buttons()
        await self.update_page(interaction)
    
    async def refresh(self, interaction: discord.Interaction):
        """Refresh current page"""
        self.update_buttons()
        await self.update_page(interaction)
    
    async def close(self, interaction: discord.Interaction):
        """Close the view"""
        embed = self.create_embed(
            title=f"{Icons.CHECK} Closed",
            description="This menu has been closed.",
            color=Colors.SECONDARY
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    async def update_page(self, interaction: discord.Interaction):
        """Override this method to customize page display"""
        raise NotImplementedError("Subclasses must implement update_page()")


# ============= MODERN CONFIRMATION DIALOG =============

class ConfirmationView(ModernView):
    """
    Beautiful confirmation dialog with clear yes/no options
    """
    
    def __init__(
        self,
        user: discord.User,
        title: str,
        description: str,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
        color: int = Colors.WARNING,
        *,
        timeout: float = 60
    ):
        super().__init__(user, timeout=timeout)
        self.title = title
        self.description = description
        self.color = color
        self.value: Optional[bool] = None
        
        # Add buttons
        confirm_btn = discord.ui.Button(
            label=confirm_label,
            style=discord.ButtonStyle.success,
            emoji=Icons.CHECK,
            row=0
        )
        confirm_btn.callback = self.confirm
        self.add_item(confirm_btn)
        
        cancel_btn = discord.ui.Button(
            label=cancel_label,
            style=discord.ButtonStyle.danger,
            emoji=Icons.CANCEL,
            row=0
        )
        cancel_btn.callback = self.cancel
        self.add_item(cancel_btn)
    
    def get_embed(self) -> discord.Embed:
        """Get the confirmation embed"""
        return self.create_embed(
            title=self.title,
            description=self.description,
            color=self.color
        )
    
    async def confirm(self, interaction: discord.Interaction):
        """User confirmed"""
        self.value = True
        self.stop()
        
    async def cancel(self, interaction: discord.Interaction):
        """User cancelled"""
        self.value = False
        self.stop()


# ============= MODERN SELECT MENU =============

class ModernSelect(discord.ui.Select):
    """
    Enhanced select menu with modern styling
    """
    
    def __init__(
        self,
        options: List[discord.SelectOption],
        placeholder: str = "Choose an option...",
        min_values: int = 1,
        max_values: int = 1,
        row: int = 0
    ):
        super().__init__(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options[:25],  # Discord limit
            row=row
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Override in subclass"""
        pass


# ============= MODERN BUTTON =============

class ModernButton(discord.ui.Button):
    """
    Enhanced button with consistent styling
    """
    
    def __init__(
        self,
        label: str = None,
        emoji: str = None,
        style: discord.ButtonStyle = discord.ButtonStyle.primary,
        disabled: bool = False,
        row: int = 0,
        callback_func: Callable = None
    ):
        super().__init__(
            label=label,
            emoji=emoji,
            style=style,
            disabled=disabled,
            row=row
        )
        self.callback_func = callback_func
    
    async def callback(self, interaction: discord.Interaction):
        if self.callback_func:
            await self.callback_func(interaction)


# ============= UTILITY FUNCTIONS =============

def create_progress_bar(current: int, total: int, length: int = 10, filled: str = "█", empty: str = "░") -> str:
    """Create a visual progress bar"""
    if total <= 0:
        return empty * length
    
    filled_length = int((current / total) * length)
    filled_length = max(0, min(length, filled_length))
    
    return filled * filled_length + empty * (length - filled_length)


def format_stat_box(title: str, value: str, inline: bool = True) -> Dict[str, Any]:
    """Create a formatted stat field"""
    return {
        "name": f"**{title}**",
        "value": value,
        "inline": inline
    }


def create_info_embed(
    title: str,
    description: str,
    user: discord.User,
    color: int = Colors.INFO
) -> discord.Embed:
    """Quick info embed"""
    embed = discord.Embed(
        title=f"{Icons.INFO} {title}",
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"Requested by {user.name}", icon_url=user.display_avatar.url)
    return embed


def create_success_embed(
    title: str,
    description: str,
    user: discord.User
) -> discord.Embed:
    """Quick success embed"""
    embed = discord.Embed(
        title=f"{Icons.CHECK} {title}",
        description=description,
        color=Colors.SUCCESS,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"Requested by {user.name}", icon_url=user.display_avatar.url)
    return embed


def create_error_embed(
    title: str,
    description: str,
    user: discord.User
) -> discord.Embed:
    """Quick error embed"""
    embed = discord.Embed(
        title=f"{Icons.CANCEL} {title}",
        description=description,
        color=Colors.DANGER,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"Requested by {user.name}", icon_url=user.display_avatar.url)
    return embed


# ============= MODERN CARD VIEW =============

class CardView(ModernView):
    """
    Card-style view for displaying single items with actions
    Perfect for profile, item details, etc.
    """
    
    def __init__(self, user: discord.User, *, timeout: float = 180):
        super().__init__(user, timeout=timeout)
    
    def create_card_embed(
        self,
        title: str,
        thumbnail: str = None,
        fields: List[Dict[str, Any]] = None,
        color: int = Colors.PRIMARY,
        footer: str = None
    ) -> discord.Embed:
        """Create a card-style embed"""
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", True)
                )
        
        if footer:
            embed.set_footer(text=footer, icon_url=self.user.display_avatar.url)
        else:
            embed.set_footer(text=f"{self.user.name}", icon_url=self.user.display_avatar.url)
        
        return embed
