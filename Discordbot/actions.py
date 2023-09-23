"""
Actions.py

Collection of use-like functions for robots

- Year 2023
- Authors: telamohn <tony@decentlabs.se>
- license: AGPLv3
"""
from overthink import AIAgent, describe, Context
from datetime import datetime

"Remind me in 3 hours to take a shower."

def check_wristwatch():
    """It shows you the current time"""
    return datetime.now().isoformat()

# Discord specific
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


@describe(user="The username of the individual you wanna look up")
async def whois(ctx: Context, user: str):
    """Use this function to lookup your user database for previous interactions
    """
    repo = ctx.get('repo')
    protocol = ctx.get('protocol')
    if repo is None: return "sorry my memory is glithcing" # TODO: fix bug
    info = repo.get_user(protocol, user)
    if info is None: return "unknown individual"
    return info



# TODO: throw morty into the mix
# https://github.com/nomic-ai/gpt4all/tree/main/gpt4all-bindings/python

class ImaginaryFriend(AIAgent):
    """TODO: experiment when token limit is reached,
        Equip your model with a phonebook.
        list it with short stereotypical systems and sort
        the extended functions as their capabilites.
        Then let your main model "call_friend(name)" to select
        which category of actions it'd like to get access to.

        --- PROJECT FOR ANOTHER DAY ---
    """
    async def output(self, messages, context):
        pass

@describe(to = "Name of friend in form of @user", message = "The message to send")
async def ask_friend(to: str, message: str):
    """
        Send pm to a friend over telegram.
    """
    return await charlie.overthink(question)



if __name__ == '__main__':
    from asyncio import get_event_loop
    loop = get_event_loop()
