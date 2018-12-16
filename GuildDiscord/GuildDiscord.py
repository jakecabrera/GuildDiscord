import re

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
authorizedChannels = {
    "259049604627169291", # Private test channel
    "517203484467134484" # ops channel
    }

authorizedRoles = {
    "513372116519878716", # Role from my test server
    "474235266190540800", # Risen Probably senpai notice me
    "474234873763201026" # Risen Probably officer
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
    removePattern = re.compile(r'<REMOVED.*>.*\[.*\]')
    namesPattern = re.compile(r'(?<=>)[ ]?.*]')
    discordNamePattern = re.compile(r'.*#\d{4}')
    bdoNamePattern = re.compile(r'(?<=\[).*(?=\])')
    addPattern = re.compile(r'<ADDED>.*\[.*\]')

    # Set State
    if message.author.id == sarge and m.startswith(prefix + "STATE") and message.channel.id in authorizedChannels:
        args = m.split(" ")
        if args[1] == 'STOP' or args[1] == 'PAUSE':
            okToRun = False
            await client.send_message(message.channel, cssMessage("Commands are no longer available"))
            await client.change_presence(game=discord.Game(name="Unavailable"))
        elif args[1] == 'CONTINUE' or args[1] == 'START':
            okToRun = True
            await client.send_message(message.channel, cssMessage("Commands are now available"))
            await client.change_presence(game=discord.Game(name="Available"))

    # Mission Commands
    elif (m.startswith(prefix + "MISSION") or m.startswith(prefix + "MISSIONS")) and message.channel.id in authorizedChannels and okToRun:    
        botOnline = ref.child('BotCommands').child('Online').get()
        if not botOnline:
            await client.send_message(message.channel, cssMessage("The bot responsible for handling this request is not online right now."))
            return

        args = m.split(" ")
        if args[1] == 'FINISH':
            await finishMission(message.channel)
        elif args[1] == 'START': # doesn't really do anything yet
            startMission()

    # Ping Pong
    elif m.startswith(prefix + "PING"):
        await client.send_message(message.channel, "pong!")

    # Guildie Tracker
    # Check if adding guildie
    if len(addPattern.findall(m)) > 0:
        a = addPattern.findall(message.content)
        c = '\n'.join(a)
        b = namesPattern.findall(c)
        for x in b:
            args = x.lstrip().split(" ")
            dName = discordNamePattern.search(x.lstrip()).group()
            print("x: " + x)
            bName = bdoNamePattern.search(x).group()
            print(bName)
            await addGuildie(dName, bName)

    # Check if removing guildie
    if len(removePattern.findall(m)) > 0:
        a = removePattern.findall(message.content)
        c = '\n'.join(a)
        b = namesPattern.findall(c)
        for x in b:
            args = x.lstrip().split(" ")
            dName = discordNamePattern.search(x.lstrip()).group()
            print("x: " + x)
            bName = bdoNamePattern.search(x).group()
            print(bName)
            await removeGuildie(dName, bName)

    # Check if searching for guildies
    elif m.startswith(prefix + "GUILD SEARCH "):
        m = m.replace(prefix + "GUILD SEARCH ", '')
        if m.startswith('FAMILY'):
            await getGuildieByFamily(message.content[len(prefix + 'GUILD SEARCH FAMILY '):], message.channel)
        elif m.startswith('DISCORD'):
            await getGuildieByDiscord(message.content[len(prefix + 'GUILD SEARCH DISCORD '):], message.channel)


# Checks if the user has permissions to interact with the bot
def validUser(user):
    for role in authorizedRoles:
        if role in [r.id for r in user.roles]:
            return True
    return False

# Sends a signal to voice attack to turn in the mission
async def finishMission(channel):
    alreadyQueued = ref.child('BotCommands').child('FinishMission').get()

    if alreadyQueued:
        await client.send_message(channel, cssMessage("Already working on it!"))
    else:
        await client.send_message(channel, cssMessage("You got it! Finishing mission..."))
        ref.child('BotCommands').update({'FinishMission':True})

# Resets mission to false
def startMission():
    ref.child('BotCommands').update({'FinishMission':False})

# Adds an entry to the database
async def addGuildie(dName, bName):
    member = ref.child('Members').push()
    member.child("Discord").set(dName)
    member.child("Family").set(bName)
    member.child("DateAdded").set({".sv": "timestamp"})

# Removes guildie from database
async def removeGuildie(dName, bName):
    members = ref.child('Members').get()
    for member in members:
        if members[member]['Family'].upper() == bName.upper():
            print("Removing [" + bName + "] = [" + members[member]['Discord'] + "]")
            ref.child('Members').child(member).delete()

# Searches for a guildie's bdo family name by its discord name
async def getGuildieByDiscord(dName, ch):
    members = ref.child('Members').get()
    rawDName = dName.split("#")[0]
    for member in members:
        m = members[member]['Discord'].split("#")[0]
        print(m)
        if m.upper() == rawDName.upper():
            await client.send_message(ch, cssMessage("[" + members[member]['Discord'] + "] = [" + members[member]['Family'] + "]"))
            return
    await client.send_message(ch, cssMessage("[" + dName + "] was not found"))

# Searches for a guildi's discord name by its bdo family name
async def getGuildieByFamily(bName, ch):
    members = ref.child('Members').get()
    for member in members:
        if members[member]['Family'].upper() == bName.upper():
            await client.send_message(ch, cssMessage("[" + bName + "] = [" + members[member]['Discord'] + "]"))
            return
    await client.send_message(ch, cssMessage("[" + bName + "] was not found"))

# returns a string that is styled in css way for discord
def cssMessage(msg):
    return "```CSS\n" + msg + "\n```"


TOKEN = ""
with open('token', 'r') as t:
    TOKEN = t.read().replace('\n','')

client.run(TOKEN, bot=True)
