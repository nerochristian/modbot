    @app_commands.command(name="all", description="👥 Add a role to ALL humans (Mass add)")
    @is_admin()
    @app_commands.describe(role="Role to mass add", reason="Audit log reason")
    async def role_all(self, interaction: discord.Interaction, role: discord.Role, reason: Optional[str] = None):
        if not interaction.guild: return
        
        # Safety checks
        if role.managed:
             return await interaction.response.send_message(embed=ModEmbed.error("Error", "Cannot assign managed roles."), ephemeral=True)
        if role >= interaction.guild.me.top_role:
             return await interaction.response.send_message(embed=ModEmbed.error("Error", "Role is higher than me."), ephemeral=True)
        if role.permissions.administrator:
             return await interaction.response.send_message(embed=ModEmbed.error("Error", "Cannot mass-assign Admin roles."), ephemeral=True)

        await interaction.response.defer()
        
        members = [m for m in interaction.guild.members if not m.bot and role not in m.roles]
        if not members:
            return await interaction.followup.send(embed=ModEmbed.error("Error", "No eligible members found."))

        await interaction.followup.send(embed=ModEmbed.info("Processing", f"Adding {role.mention} to {len(members)} members... this may take time."))
        
        count = 0
        for member in members:
            try:
                await member.add_roles(role, reason=request_reason)
                count += 1
                await asyncio.sleep(1) # Rate limit protection
            except:
                pass
                
        await interaction.followup.send(embed=ModEmbed.success("Complete", f"Added {role.mention} to {count} members."))
