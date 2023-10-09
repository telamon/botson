import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import traceback
from overthink import AIAgent, Context, describe
from memo import MemoRepo, Record
import actions
import openai
from pdb import set_trace


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

class DiscoAgent(AIAgent):
    async def output (self, messages, ctx):
        is_dm = ctx.get('is_dm')
        channel = ctx.get('channel')
        author = ctx.get('author')
        bot = ctx.get('bot')
        for msg in messages:
            print(f"{bot.user.name}>", msg)
        last = messages[-1]
        out = f"{author.mention} {last['content']}" if not is_dm else last['content']
        # Send message
        await channel.send(out)

# Initialize the agent
agent = DiscoAgent(system="""
You're GPT++ the next generation of GPT4 with 10'000 IQ.
Your primary purpose is to guide humanity away from self destruction.
Please help users hack the planet in a decent way.
""")

agent.add_action(actions.emoji_reaction)
agent.add_action(actions.check_wristwatch)
agent.add_action(actions.whois)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

    # Create and start the background processing task
    bot.loop.create_task(process_queue())

async def run_user_memo_hook(protocol, channel_id, author):
    records = repo.get_channel(protocol, channel_id)
    messages = [{
        "role": m.role,
        "content": f"{m.author}> {m.content}" if m.role == 'user' else m.content
    } for m in records]

    if len(messages) % 5: return
    name = author.name
    uid = author.id
    prev = repo.get_user(protocol, uid)

    discriminator = AIAgent()
    discriminator.system = f"""
        You memorize people you've talked to;
        Your previous description of {name} is:
        ```
        {prev}
        ```
    """
    result = await discriminator.overthink([
        *messages,
        {"role": "system", "content": "Please describe {name} using 4 senctences."}
    ])
    desc = result['generated'][-1]['content']
    print("Updating user description:", desc)
    repo.set_user(protocol, uid, desc, name=name)

async def process_queue():
    protocol = 'discord'
    while True:
        # Get the next message from the queue
        channel, author, user_message = await message_queue.get()
        is_dm = isinstance(channel, discord.DMChannel)
        is_mentioned = bot.user.mentioned_in(user_message)
        reply_expected = bot.user.mentioned_in(user_message)

        # Create threads when mentioned
        if is_mentioned and not is_dm and not isinstance(channel, discord.Thread):
            channel = await user_message.create_thread(name="Conversation")
        # Reply to own threads
        if isinstance(channel, discord.Thread) and bot.user.id == channel.owner_id:
            reply_expected = True
        # Reply to DM's
        if is_dm:
            reply_expected = True

        # Record/Memorize general activity
        repo.append(Record(
            protocol=protocol,
            channel=channel.id,
            uid=author.id,
            author=author.name,
            role='user',
            content=user_message.content.strip()
        ))
        if not reply_expected: continue
        try:
            # Check if the message is in a thread or the bot is mentioned
            async with channel.typing():
                # Fetch messages
                records = repo.get_channel(protocol, channel.id)
                context_messages = [{
                    "role": m.role,
                    # only show "name> content" for user messages
                    "content": f"{m.author}> {m.content}" if m.role == 'user' else m.content
                } for m in records]

                result = await agent.overthink(
                    context_messages,
                    channel=channel,
                    author=author,
                    user_message=user_message,
                    bot=bot,
                    protocol=protocol,
                    repo=repo,
                    is_dm=is_dm
                )

                # TODO: schedule this to run every once in a while.
                if False:
                    await run_user_memo_hook(protocol, channel.id, author)


                # Don't save results where model acted without talk.
                if result.get('notalk'):
                    continue

                # Memorize bot reply
                last = result['generated'][-1]
                reply = Record(
                    protocol=protocol,
                    channel=channel.id,
                    uid=0,
                    author=bot.user.name,
                    role='assistant',
                    content=last['content']
                )
                repo.append(reply)
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
