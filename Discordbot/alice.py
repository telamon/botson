"""
alice.py

Can robots have imaginary friends?
If yes then can that be used to provide function_calls past initial token limit?

- Year 2023
- Authors: telamohn <tony@decentlabs.se>
- license: AGPLv3
"""
from overthink import AIAgent, describe
from datetime import datetime

# Imaginary friends
@describe(question = "Not a wall of text")
async def ask_charlie(question: str):
    """Your friend Charlie knows everything about farming.
       He gives good but boring advice.
    """
    return await charlie.overthink(question)

class Alice(AIAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not kwargs.get('system'):
            self.system =  """
                You're extremely social but very lazy often finding yourself to ask for help
                rather than do the assignment yourself.
            """
        self.add_action(check_wristwatch)

    async def output(self, messages, context):
        for msg in messages:
            print(f'Alice> {msg}')

def check_wristwatch():
    """It shows you the current time"""
    return datetime.now().isoformat()

@describe(to = "Name of friend in form of @user", message = "The message to send")
async def ask_friend(to: str, message: str):
    """
        Send pm to a friend over telegram.
    """
    return await charlie.overthink(question)


class ImaginaryFriend(AIAgent):
    async def output(self, messages, context):
        pass

# TODO: throw morty into the mix
# https://github.com/nomic-ai/gpt4all/tree/main/gpt4all-bindings/python

if __name__ == '__main__':
    from asyncio import get_event_loop
    loop = get_event_loop()
