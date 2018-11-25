import discord
from discord.ext import commands

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

client = discord.Client()
cred = credentials.Certificate('risen-59032-ffc0d0af3cc4.json')
default_app = firebase_admin.initialize_app(cred, {'databaseURL': 'https://risen-59032.firebaseio.com/'})
ref = db.reference('Guild')
bot = commands.Bot(command_prefix='!')

okToRun = False
prefix = "&"

# Roles that are allowed to talk with my bot
authorizedRoles = {
    "513372116519878716"
    "474235266190540800"
    "474234873763201026"
    }

sarge = "247195865989513217" # That's me!!! o/

@client.event
async def on_ready():
    print("The bot is ready!")
    await client.change_presence(game=discord.Game(name="Unavailable"))

@client.event
async def on_message(message):
    global okToRun

    # Return if the message is from unauthorized user
    if message.author == client.user or not validUser(message.author):
        return

    m = message.content.upper()

    # Set State
    if message.author.id == sarge and m.startswith(prefix + "STATE"):
        args = m.split(" ")
        if args[1] == 'STOP' or args[1] == 'PAUSE':
            okToRun = False
            await client.send_message(message.channel, "Commands are no longer available")
            await client.change_presence(game=discord.Game(name="Unavailable"))
        elif args[1] == 'CONTINUE' or args[1] == 'START':
            okToRun = True
            await client.send_message(message.channel, "Commands are now available")
            await client.change_presence(game=discord.Game(name="Available"))

    # Check if it's okay to run commands
    if not okToRun:
        return

    # Mission Commands
    if m.startswith(prefix + "MISSION") or m.startswith(prefix + "MISSIONS"):
        args = m.split(" ")
        if args[1] == 'FINISH':
            finishMission()
        await client.send_message(message.channel, "<@%s> Mission! %s" % (message.author.id, args[1:]))

    # Ping Pong
    if m.startswith(prefix + "PING"):
        await client.send_message(message.channel, "pong!")

# Checks if the user has permissions to interact with the bot
def validUser(user):
    for role in authorizedRoles:
        if role in [r.id for r in user.roles]:
            return True
    return False

# Sends a signal to voice attack to turn in the mission
def finishMission():
    ref.child('BotCommands').update({'FinishMission':True})

TOKEN = ""
with open('token', 'r') as t:
    TOKEN = t.read().replace('\n','')

client.run(TOKEN, bot=True)
