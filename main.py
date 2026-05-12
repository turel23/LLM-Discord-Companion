import discord
from dotenv import load_dotenv
import os
from discord.ext import commands
from discord import app_commands
from llm import llm
import random
import asyncio

load_dotenv()

# Create an instance of the llm class
llm_instance = llm()

class Client(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_count = 0

    async def on_ready(self):
        print(f"logged on as {self.user}!")
        try:
            id = os.getenv("GUILD_ID")
            guild = discord.Object(id=int(id))
            synced = await self.tree.sync(guild=guild)
            print(f"synced {len(synced)} commands to guild {guild.id}")
        except Exception as e:
            print(f"Error syncing commands: {e}")

    async def on_message(self, message):
        self.message_count += 1
        if message.attachments:
            print("detected attachments")
            for attachment in message.attachments:
                await attachment.save(f"downloads/{attachment.filename}")
                print(f"Saved attachment: {attachment.filename}")
        if message.author == self.user:
            print("DEBUG: I responded")
            return
        if self.message_count >= 10:
            self.message_count = 0
            await llm_instance.form_episodic_memory()
        print(f"{message.author} says: {message.content}")
        await asyncio.sleep(random.normalvariate(mu = len(message.content) / 3, sigma = 1))
        async with message.channel.typing():
            answer = await llm_instance.ask(statement = message.content, author = message.author.name)
            await asyncio.sleep(random.normalvariate(mu = len(answer) / 15, sigma = 1))
            await message.channel.send(answer)
            self.message_count += 1


intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="!", intents=intents)


GUILD_ID = discord.Object(id=int(os.getenv("GUILD_ID")))

@client.tree.command(name="hello", description="Says hello!", guild=GUILD_ID)
async def sayHello(interaction: discord.Interaction):
    await interaction.response.send_message("Hi there!")

@client.tree.command(name="printer", description="I will print whatever you give me", guild=GUILD_ID)
async def sayHello(interaction: discord.Interaction, printer: str):
    await interaction.response.send_message(printer)
    try:
        await interaction.user.send("thanks for sending")
    except discord.Forbidden:
        print(f"Could not send DM to {interaction.user}")


load_dotenv()
token = os.getenv("DISCORD_TOKEN")
client.run(token)
