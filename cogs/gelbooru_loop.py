import discord
from discord.ext import commands, tasks
import aiohttp
import random
import logging

logger = logging.getLogger("ModBot")

class SafeLoop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = 1463001859345354968 
        
        # SAFELOOP SETTINGS
        # We use Safebooru.org, which is strictly SFW.
        # Tags: just 'femboy' is enough because the whole site is safe.
        self.tags = "femboy"
        
        self.session = None
        self.safe_task.start()

    async def cog_load(self):
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        self.safe_task.cancel()
        if self.session:
            await self.session.close()

    @tasks.loop(seconds=10)
    async def safe_task(self):
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except:
                return

        # Safebooru has thousands of safe images, so we can randomise the pages again!
        # Random page between 0 and 10 to keep it fresh.
        random_pid = random.randint(0, 10)

        url = "https://safebooru.org/index.php"
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "json": "1",
            "limit": "100",
            "pid": random_pid,
            "tags": self.tags
            # Note: Safebooru doesn't require an API key for basic read access
        }
        
        headers = {"User-Agent": "ModBot/4.0.0 (Discord Bot)"}

        try:
            async with self.session.get(url, params=params, headers=headers, timeout=10) as response:
                if response.status != 200:
                    print(f"API Error: {response.status}")
                    return
                
                # Safebooru sometimes returns HTML if it crashes, check for JSON
                if response.content_type == 'application/json':
                    data = await response.json()
                else:
                    return

            if not data or not isinstance(data, list):
                print(f"No results found on Page {random_pid}. Retrying...")
                return

            post = random.choice(data)
            
            # --- IMAGE URL CONSTRUCTION ---
            # Safebooru is old. Sometimes it gives 'file_url', sometimes it doesn't.
            # We construct it manually to be safe:
            image_name = post.get("image")
            directory = post.get("directory")
            
            if post.get("file_url"):
                final_url = post.get("file_url")
            elif image_name and directory:
                final_url = f"https://safebooru.org/images/{directory}/{image_name}"
            else:
                return

            embed = discord.Embed(
                title="✨ Safebooru Drop",
                url=f"https://safebooru.org/index.php?page=post&s=view&id={post.get('id')}",
                color=0x0000ff # Blue for Safe
            )
            
            # ---------------------------------------------------------
            # "NO IMGS" SETTING
            # I commented out the big image. Uncomment the line below 
            # if you want to see the image again.
            # ---------------------------------------------------------
            # embed.set_image(url=final_url)
            
            # This sets a small thumbnail instead (less intrusive)
            embed.set_thumbnail(url=final_url)
            
            embed.set_footer(text=f"ID: {post.get('id')} • Source: Safebooru")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Loop Error: {e}")

    @safe_task.before_loop
    async def before_safe_task(self):
        await self.bot.wait_until_ready()
        if not self.session:
            self.session = aiohttp.ClientSession()

async def setup(bot):
    await bot.add_cog(SafeLoop(bot))
