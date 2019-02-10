import re
import os
import io
import collections
import time
import fileinput
from pathlib import Path

import discord
from discord.ext import commands

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

dir_path = os.path.dirname(os.path.realpath(__file__))
stateFileExists = Path(dir_path + '/state').is_file()

client = discord.Client()
cred = credentials.Certificate(dir_path + '/risen-59032-ffc0d0af3cc4.json')
default_app = firebase_admin.initialize_app(cred, {'databaseURL': 'https://risen-59032.firebaseio.com/'})
ref = db.reference('Guild')
prefix = '&'

# File to check if still available to complete missions or not
if not stateFileExists:
    with open(dir_path + '/state', 'x') as f:
        f.write("Available: False\n")

state = {}
with open(dir_path + '/state') as f:
    content = f.readlines()
    for line in content:
        state[line.split(':')[0].strip()] = line.split(':')[1].strip()

okToRun = state['Available'] == 'True'
authorizedChannels = {
    "259049604627169291", # Private test channel
    "517203484467134484" # ops channel
    }

databaseChannels = {
    "474242123143577610", # Add-and-remove
    "259049604627169291" # Private test channel
    }

authorizedRoles = {
    "539836157656301570", # Leadership
    "513372116519878716", # Role from my test server
    "474234873763201026", # Senpai notice me
    "474235266190540800", # Risen officer
    }

sarge = "247195865989513217" # That's me!!! o/
hooligans = "474236074017685506"
guildRoles = {
    "539836157656301570", # Leadership
    hooligans,
    "474234873763201026", # Senpai Notice Me
    "474235266190540800", # Officer
    "475010938148225036" # Lead vegan dev
    }

@client.event
async def on_ready():
    print("The bot is ready!")
    await client.send_message(client.get_channel("259049604627169291"), "Online!")
    if not okToRun:
        await client.change_presence(game=discord.Game(name="Unavailable"))
    else:
        await client.change_presence(game=discord.Game(name="Available"))

@client.event
async def on_message(message):
    global okToRun

    # Return if the message is from unauthorized user
    if message.author == client.user or not validUser(message.author):
        return

    m = message.content.upper()
    removePattern = re.compile(r'<(?:REMOVED|LEFT).*>.*\[.*\]')
    updatePattern = re.compile(r'<UPDATE[D]?.*>.*\[.*\]')
    namesPattern = re.compile(r'(?<=>)[ ]?.*]')
    discordNamePattern = re.compile(r'.*#\d{4}')
    bdoNamePattern = re.compile(r'(?<=\[).*(?=\])')
    addPattern = re.compile(r'<ADDED>.*\[.*\]')
    
    # Set State
    if message.author.id == sarge and m.startswith(prefix + "STATE") and message.channel.id in authorizedChannels:
        args = m.split(" ")
        if args[1] == 'STOP' or args[1] == 'PAUSE':
            okToRun = False
            with fileinput.FileInput(dir_path + '/state', inplace=True, backup='.bak') as f:
                for line in f:
                    print(line.replace('Available: True', 'Available: False'), end='')
            await client.send_message(message.channel, cssMessage("Commands are no longer available"))
            await client.change_presence(game=discord.Game(name="Unavailable"))
        elif args[1] == 'CONTINUE' or args[1] == 'START':
            okToRun = True
            with fileinput.FileInput(dir_path + '/state', inplace=True, backup='.bak') as f:
                for line in f:
                    print(line.replace('Available: False', 'Available: True'), end='')
            await client.send_message(message.channel, cssMessage("Commands are now available"))
            await client.change_presence(game=discord.Game(name="Available"))
        print("okToRun changed to [" + str(okToRun) + "]")

    # Mission Commands
    elif (m.startswith(prefix + "MISSION") or m.startswith(prefix + "MISSIONS")) and message.channel.id in authorizedChannels and okToRun:    
        botOnline = ref.child('BotCommands').child('Online').get()
        if not botOnline:
            await client.send_message(message.channel, cssMessage("The bot responsible for handling this request is not online right now."))
            return

        args = m.split(" ")
        if args[1] == 'FINISH':
            print("Attempting to finish mission...")
            await finishMission(message.channel)
        elif args[1] == 'START': # doesn't really do anything yet
            startMission()

    # Ping Pong
    elif m.startswith(prefix + "PING"):
        print("Ping!")
        #roles = message.server.roles
        #msg = ""
        #for role in roles:
        #    msg += role.id + ":\t" + role.name + "\n"
        #await client.send_message(client.get_channel("259049604627169291"), msg)
        #channels = message.server.channels
        #msg = ""
        #for channel in channels:
        #    msg += channel.id + ":\t" + channel.name + "\n"
        #await client.send_message(client.get_channel("259049604627169291"), msg)
        await client.send_message(message.channel, "pong!")

    # Help!
    elif m.startswith(prefix + "HELP"):
        print("Displaying Help Message...")
        await showHelp(message.channel)

    elif m.startswith("=PAT"):
        time.sleep(2)
        await client.send_message(message.channel, "There there")

    # Guildie Tracker
    # Check if adding guildie
    if len(addPattern.findall(m)) > 0 and message.channel.id in databaseChannels:
        a = addPattern.findall(message.content)
        c = '\n'.join(a)
        b = namesPattern.findall(c)
        for x in b:
            args = x.lstrip().split(" ")
            dName = discordNamePattern.search(x.lstrip()).group()
            bName = bdoNamePattern.search(x).group()
            await addGuildie(dName, bName, message.channel)

    # Check if removing guildie
    if len(removePattern.findall(m)) > 0 and message.channel.id in databaseChannels:
        a = removePattern.findall(message.content)
        c = '\n'.join(a)
        b = namesPattern.findall(c)
        for x in b:
            args = x.lstrip().split(" ")
            dName = discordNamePattern.search(x.lstrip()).group()
            bName = bdoNamePattern.search(x).group()
            await removeGuildie(dName, bName, message.channel)
            
    # Check if updating guildie
    if len(updatePattern.findall(m)) > 0 and message.channel.id in databaseChannels:
        print("Updating!")
        a = updatePattern.findall(message.content)
        c = '\n'.join(a)
        b = namesPattern.findall(c)
        for x in b:
            args = x.lstrip().split(" ")
            dName = discordNamePattern.search(x.lstrip()).group()
            bName = bdoNamePattern.search(x).group()
            await updateGuildie(dName, bName, message.channel)

    # Guild operations
    if m.startswith(prefix + "GUILD"):
        i = len(prefix + "GUILD ")
        m = m[i:]
        # Search operations
        if m.startswith("SEARCH"):
            i += len("SEARCH ")
            m = m[len("SEARCH "):]
            # Search by family
            if m.startswith('FAMILY') or m.startswith('BDO'):
                if m.startswith('FAMILY'):
                    i += len('FAMILY ')
                else:
                    i += len('BDO ')
                await getGuildieByFamily(message.content[i:], message.channel, message.server)
            # Search by discord
            elif m.startswith('DISCORD'):
                i += len('DISCORD ')
                await getGuildieByDiscord(message.content[i:], message.channel, message.server)
        if m.startswith("LIST"):
            await getGuildList(message.channel, message.server)
        if m.startswith("GET MISSING"):
            await getDiscordMissing(message.channel, message.server)


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

# Display help info
async def showHelp(ch):
    helpMessage = (
        "HELP WINDOW\n\n" +
        "# Guild Member Searching (Case-Sensitive):\n" +
        "# To search by a guild members discord name use:\n" +
        "\t[" + prefix + "guild search discord <USER_NAME_GOES_HERE>]\n" + 
        "# To search by a guild members bdo family name use:\n" +
        "\t[" + prefix + "guild search family <USER_NAME_GOES_HERE>]\n" +
        "\t[" + prefix + "guild search bdo <USER_NAME_GOES_HERE>]"
    )
    if ch.id in authorizedChannels:
        helpMessage += (
            "\n\nSUPER SECRET OFFICER ONLY COMMANDS\n\n" +
            "# Finish a mission but ONLY IF HERBERT IS AVAILABLE:\n" +
            "\t[" + prefix + "mission finish]\n" +
            "# To get a list of mismatched named guild members:\n" +
            "\t[" + prefix + "guild get missing]"
            )
    await client.send_message(ch, cssMessage(helpMessage))
    return

# Adds an entry to the database
async def addGuildie(dName, bName, ch):
    dName = dName.replace('@', '')
    members = ref.child('Members').get()
    for member in members:
        m = members[member]
        if m['Family'].upper() == bName.upper() or m['Discord'] == dName:
            print("Member already exists")
            if m['Family'].upper() == bName.upper():
                await client.send_message(ch, cssMessage("Member already exists with that Family name"))
            else:
                await client.send_message(ch, cssMessage("Member already exists with that Discord name"))
            return
    member = ref.child('Members').push()
    member.child("Discord").set(dName)
    member.child("Family").set(bName)
    member.child("DateAdded").set({".sv": "timestamp"})
    print("Added dName: [" + dName + "]\t[" + bName + "]")
    await client.send_message(ch, cssMessage("Added Discord:  [" + dName + "]\n\tBdo Family: [" + bName + "]"))

# Removes guildie from database
async def removeGuildie(dName, bName, ch):
    dName = dName.replace('@', '')
    members = ref.child('Members').get()
    removedSomeone = False
    for member in members:
        if members[member]['Family'].upper() == bName.upper():
            print("Removing [" + bName + "] = [" + members[member]['Discord'] + "]")
            ref.child('Members').child(member).delete()
            removedSomeone = True
            await client.send_message(ch, cssMessage("Removed Discord: [" + dName + "]\n\t Bdo Family: [" + bName + "]"))
        if removedSomeone:
            return
    await client.send_message(ch, cssMessage("No matching member found in database for:\n\tDiscord: [" + dName + "]\n\tBDO Family: [" + bName + "]"))


# Update guildie
async def updateGuildie(dName, bName, ch):
    print(dName)
    print(bName)
    members = ref.child('Members').get()
    updatedSomeone = False
    for member in members:
        if members[member]['Family'] == bName:
            oldDiscord = members[member]['Discord']
            ref.child('Members').child(member).update({'Discord': dName})
            updatedSomeone = True
            await client.send_message(ch, cssMessage("Updated [" + bName + "] Discord name from [" + oldDiscord + "] to [" + dName + "]"))
        elif members[member]['Discord'] == dName:
            oldFamily = members[member]['Family']
            ref.child('Members').child(member).update({'Family': bName})
            updatedSomeone = True
            await client.send_message(ch, cssMessage("Updated [" + dName + "] BDO family name from [" + oldFamily + "] to [" + bName + "]"))
        if updatedSomeone:
            return
    await client.send_message(ch, cssMessage("No matching member found in database for:\n\tDiscord: [" + dName + "]\n\tBDO Family: [" + bName + "]"))


# Searches for a guildie's bdo family name by its discord name
async def getGuildieByDiscord(dName, ch, ser):
    print("Getting guildie by discord")
    members = ref.child('Members').get()
    mem = ser.get_member_named(dName)
    print(mem)
    if mem != None:
        for member in members:
            m = members[member]['Discord']
            if m.upper() == str(mem).upper():
                msg = (
                    "Results for  [" + dName + "]:\n\n" +
                    "Discord =    [" + m + "]\n" +
                    "BDO Family = [" + members[member]['Family'] + "]"
                    )
                if mem.nick != None:
                    msg += "\nNickname =   [" + mem.nick + "]"
                print(msg)
                await client.send_message(ch, cssMessage(msg))
                return
    print("[" + dName + "] was not found")
    await client.send_message(ch, cssMessage("[" + dName + "] was not found"))

# Searches for a guildie's discord name by its bdo family name
async def getGuildieByFamily(bName, ch, ser):
    members = ref.child('Members').get()
    for member in members:
        if members[member]['Family'].upper() == bName.upper():
            msg = (
                "Results for  [" + bName + "]:\n\n" +
                "Discord =    [" + members[member]['Discord'] + "]\n" +
                "BDO Family = [" + members[member]['Family'] + "]"
                )
            dName = members[member]['Discord']
            mem = ser.get_member_named(dName)
            if mem != None and mem.nick != None:
                msg += "\nNickname =   [" + mem.nick + "]"
            print(msg)
            await client.send_message(ch, cssMessage(msg))
            return
    print("[" + bName + "] was not found")
    await client.send_message(ch, cssMessage("[" + bName + "] was not found"))

# Get a list of current guild members!
async def getGuildList(ch, ser):
    print("Getting list of guild members!")
    members = ref.child('Members').get()
    guildList = {}
    msg = ""
    for member in members:
        info = [members[member]['Discord']]
        dName = ser.get_member_named(members[member]['Discord'])
        if dName != None and dName.nick != None:
            info.append(dName.nick)
        guildList[members[member]['Family']] = info
    guildList = collections.OrderedDict(sorted(guildList.items()))
    i = 1
    for k, v in guildList.items():
        msg += str(i) + ": Family: " + k + "\r\n    Discord: " + v[0] + "\r\n"
        if len(v) > 1:
            msg += "    Nickname: " + v[1] + "\r\n"
        i += 1
    with io.open(dir_path + "/guildList.txt", "w", encoding="utf-8") as f:
        f.write(msg)
    await client.send_file(ch, dir_path + "/guildList.txt")

# Gets the discrepencies in guild members
async def getDiscordMissing(ch, ser):
    await client.send_typing(ch)
    members = ref.child('Members').get()

    # Get all bdo members from firebase
    dNameMembers = {}
    print("Getting firbase members")
    for member in members:
        dNameMembers[members[member]['Discord']] = members[member]['Family']

    # Get all hooligans from discord
    hooligans = []
    print("getting discord members")
    for member in ser.members:
        isGuildMember = False
        for mRole in member.roles:
            if mRole.id in guildRoles:
                isGuildMember = True
        if isGuildMember:
            hooligans.append(member.name + '#' + member.discriminator)

    # Compare hooligans against the bdo members
    discordMissing = []
    print("Comparing")
    for member in hooligans:
        if not member in dNameMembers:
            discordMissing.append(member)

    # Compare bdo members against hooligans
    bdoMissing = []
    for member in dNameMembers.keys():
        if not member in hooligans:
            bdoMissing.append(member)

    if len(discordMissing) > 0:
        msg = ''
        for member in discordMissing:
            msg += member + '\r\n'
        print("Writing")
        with io.open(dir_path + "/guildDiscordMissing.txt", "w", encoding="utf-8") as f:
            f.write(msg)
        await client.send_message(ch, cssMessage("The following members were found in discord as part of the guild but not in BDO:\n\n" + msg))
    if len(bdoMissing) > 0:
        msg = ''
        for member in bdoMissing:
            msg += member + '\r\n'
            msg += '\t\tFamily Name: ' + dNameMembers[member] + '\r\n'
        print("Writing")
        with io.open(dir_path + "/guildBdoMissing.txt", "w", encoding="utf-8") as f:
            f.write(msg)
        await client.send_message(ch, cssMessage("The following members were found in BDO as part of the guild but are not a Hooligan:\n\n" + msg))
    if len(bdoMissing) == 0 and len(discordMissing) == 0:
        await client.send_message(ch, cssMessage("All members accounted for!"))

# returns a string that is styled in css way for discord
def cssMessage(msg):
    return "```CSS\n" + msg + "\n```"


TOKEN = ""
with open(dir_path + '/token', 'r') as t:
    TOKEN = t.read().replace('\n','')

client.run(TOKEN, bot=True)
