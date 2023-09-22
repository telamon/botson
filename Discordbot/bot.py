import os
import discord
from alice import Alice
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import traceback
from overthink import Context, describe
from memo import MemoRepo, Record
from pdb import set_trace
import openai


load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Create a queue to manage incoming messages
message_queue = asyncio.Queue()

# Create conversation data-store
repo = MemoRepo('memo.lmdb')

class DiscoAlice(Alice):
    async def output (self, messages, ctx):
        channel = ctx.get('channel')
        author = ctx.get('author')
        for msg in messages:
            print(f"{bot.user.name}>", msg)
        last = messages[-1]

        # Send message
        await channel.send(f"{author.mention} {last['content']}")

@describe(emoji = "One emoji", stop = "true: More talk, false: No more talk")
async def emoji_reaction(ctx: Context, emoji: str, stop: bool):
    """
        Sometimes the only right answer is a reaction,
        call to add an emoji reaction to the user's message.
    """
    msg = ctx.get('user_message')
    await msg.add_reaction(emoji)
    if not stop:
        return f"done"

# Initialize the agent
agent = DiscoAlice(system="""
    You're batman, your purpose is to fight crime and chew bubblegum, and you're all out of bats.
""")
agent.add_action(emoji_reaction)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

    # Create and start the background processing task
    bot.loop.create_task(process_queue())

async def process_queue():
    while True:
        # Get the next message from the queue
        channel, author, user_message = await message_queue.get()

        # Record/Memorize general activity
        repo.append(Record(
            protocol='discord',
            channel=channel.id,
            uid=author.id,
            author=author.name,
            role='user',
            content=user_message.content.strip()
        ))

        try:
            if user_message:
                # Check if the message is in a thread or the bot is mentioned
                if isinstance(channel, discord.Thread) or bot.user.mentioned_in(user_message):
                    async with channel.typing():
                        # Fetch messages
                        records = repo.get_channel('discord', channel.id)
                        context_messages = [{
                            "role": m.role,
                            # only show "name> content" for user messages
                            "content": f"{m.author}> {m.content}" if m.role == 'user' else m.content
                        } for m in records]

                        result = await agent.overthink(
                            context_messages,
                            channel=channel,
                            author=author,
                            user_message=user_message
                        )

                        # Don't save results where model acted without talk.
                        if result.get('notalk'):
                            continue

                        # Memorize bot reply
                        last = result['generated'][-1]
                        reply = Record(
                            protocol='discord',
                            channel=channel.id,
                            uid=0,
                            author=bot.user.name,
                            role='assistant',
                            content=last['content']
                        )
                        repo.append(reply)
                else:
                    # If not responding, do not display typing status
                    await asyncio.sleep(3)  # Sleep to simulate bot processing

        except Exception as e:
            print(f"An error occurred: {e}")
            print(traceback.format_exc())

@bot.event
async def on_message(message):
    try:
        if not message.author.bot:
            # Add the message to the processing queue
            await message_queue.put((message.channel, message.author, message))
            
    except Exception as e:
        print(f"An error occurred: {e}")

bot.run(TOKEN)
