import discord
from discord.ext import commands

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

client = discord.Client()
cred = credentials.Certificate('risen-59032-ffc0d0af3cc4.json')
default_app = firebase_admin.initialize_app(cred, {'databaseURL': 'https://risen-59032.firebaseio.com/'})
ref = db.reference('Guild')
prefix = '&'

okToRun = False
officerChannel = "486235037818290187"

# Roles that are allowed to talk with my bot
authorizedRoles = {
    "513372116519878716",
    "474235266190540800", # Risen Probably senpai notice me
    "474234873763201026" # Risen Probably officer
    }

authorizedChannels = {
    "486235037818290187" # Officer
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
    if message.author == client.user or not validUser(message.author) or message.channel.id != officerChannel:
        return

    m = message.content.upper()

    # Set State
    if message.author.id == sarge and m.startswith(prefix + "STATE") and message.channel.id == officerChannel:
        args = m.split(" ")
        if args[1] == 'STOP' or args[1] == 'PAUSE':
            okToRun = False
            await client.send_message(officerChannel, cssMessage("Commands are no longer available"))
            await client.change_presence(game=discord.Game(name="Unavailable"))
        elif args[1] == 'CONTINUE' or args[1] == 'START':
            okToRun = True
            await client.send_message(officerChannel, cssMessage("Commands are now available"))
            await client.change_presence(game=discord.Game(name="Available"))

    # Check if it's okay to run commands
    if not okToRun:
        return

    # Mission Commands
    if (m.startswith(prefix + "MISSION") or m.startswith(prefix + "MISSIONS")) and message.channel.id == officerChannel:
        args = m.split(" ")
        if args[1] == 'FINISH':
            finishMission()
        elif args[1] == 'START':
            startMission()

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
    alreadyQueued = ref.child('BotCommands').child('FinishMission').get()
    if alreadyQueued:
        cssMessage("Already working on it!")
    else:
        cssMessage("You got it! Finishing mission...")
        ref.child('BotCommands').update({'FinishMission':True})

# Resets mission to false
def startMission():
    ref.child('BotCommands').update({'FinishMission':False})

# returns a string that is styled in css way for discord
def cssMessage(msg):
    return "```CSS\n" + msg + "\n```"


TOKEN = ""
with open('token', 'r') as t:
    TOKEN = t.read().replace('\n','')

client.run(TOKEN, bot=True)
