import discord
from discord.ext import commands, tasks
import aiohttp
import random
import logging

# Print immediately when file is imported to prove it's loaded
print("--------------------------------------------------")
print("[SYSTEM] Rule34 Loop Extension is loading...")
print("--------------------------------------------------")

logger = logging.getLogger("ModBot")

class Rule34Loop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Your specific Channel ID
        self.channel_id = 1463001859345354968
        
        # Tags: Femboy, Ecchi (Not Safe, Not Porn), Random Order
        self.tags = "femboy -rating:general -rating:explicit sort:random"
        
        self.api_key = "4b5d1fd9db037eeb8b534b57f7d3d5e7f58f8ad8d3045fb75bd4f11f3db95345bef64f2551fd74a43b62b3f544996df06b01fec2cbb4b4cae335168f207855f2"
        self.user_id = "1900224"
        
        # Start the loop
        self.rule34_task.start()

    def cog_unload(self):
        self.rule34_task.cancel()

    # This ensures the bot is fully connected before trying to loop
    @tasks.loop(seconds=10)
    async def rule34_task(self):
        # 1. Get Channel
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            print(f"[DEBUG] Channel {self.channel_id} not found in cache. Attempting fetch...")
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except Exception as e:
                print(f"[ERROR] Could not fetch channel: {e}")
                return

        # 2. Prepare Request
        url = "https://api.rule34.xxx/index.php"
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "json": "1",
            "limit": "10",
            "tags": self.tags,
            "api_key": self.api_key,
            "user_id": self.user_id
        }
        
        # IMPORTANT: Rule34 blocks requests without this header!
        headers = {
            "User-Agent": "ModBot/3.0 (Discord Bot)"
        }

        # 3. Fetch Data
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        print(f"[WARNING] API Status: {response.status}")
                        return
                    
                    try:
                        data = await response.json()
                    except:
                        print(f"[ERROR] API returned non-JSON data (likely an HTML error page).")
                        return
                    
            if not data or not isinstance(data, list):
                print(f"[WARNING] No posts found for tags: {self.tags}")
                return

            # 4. Pick & Send
            post = random.choice(data)
            file_url = post.get("file_url")
            
            if not file_url:
                return

            embed = discord.Embed(
                title="🔥 Rule34 Ecchi Drop",
                url=f"https://rule34.xxx/index.php?page=post&s=view&id={post['id']}",
                color=0xffa500 
            )
            embed.set_image(url=file_url)
            embed.set_footer(text=f"ID: {post['id']} • Rating: {post['rating']}")
            
            await channel.send(embed=embed)
            print(f"[SUCCESS] Sent image {post['id']} to channel.")

        except Exception as e:
            print(f"[CRITICAL ERROR] Loop failed: {e}")

    @rule34_task.before_loop
    async def before_rule34_task(self):
        print("[DEBUG] Waiting for bot to be ready...")
        await self.bot.wait_until_ready()
        print("[DEBUG] Bot ready. Loop starting now.")

async def setup(bot):
    await bot.add_cog(Rule34Loop(bot))
