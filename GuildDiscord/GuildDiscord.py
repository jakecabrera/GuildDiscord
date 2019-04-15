import re
import os
import io
import collections
import time
import fileinput
from pathlib import Path
from difflib import get_close_matches
from datetime import datetime

import discord
from discord.ext import commands

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

import guild
from guild import Guild

dir_path = os.path.dirname(os.path.realpath(__file__))
stateFileExists = Path(dir_path + '/state').is_file()

client = discord.Client()
cred = credentials.Certificate(dir_path + '/risen-59032-ffc0d0af3cc4.json')
default_app = firebase_admin.initialize_app(cred, {'databaseURL': 'https://risen-59032.firebaseio.com/'})
ref = db.reference('Guild')
risenServer = None
risenGuild = None

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

@client.event
async def on_ready():
    global risenServer
    global risenGuild
    print("The bot is ready!")
    await client.send_message(client.get_channel(Guild.AUTHORIZED_CHANNELS['test']), "Online!")
    risenServer = client.get_server('474229539636248596')
    risenGuild = Guild(client, ref, risenServer)
    if not okToRun:
        await client.change_presence(game=discord.Game(name="Unavailable"))
    else:
        await client.change_presence(game=discord.Game(name="Available"))

@client.event
async def on_member_remove(member):
    if not risenServer.id == member.server.id:
        return
    msg = member.top_role.name + " " + member.name + "#" + member.discriminator + " has left the server."
    msg = msg.replace('@everyone ', '')
    print(msg)
    await client.send_message(client.get_channel(Guild.DATABASE_CHANNELS['addAndRemove']), Guild.cssMessage(msg))

@client.event
async def on_message(message):
    global okToRun

    # Return if the message is from unauthorized user
    if message.author == client.user or not Guild.isValidUser(message.author):
        return

    m = message.content.upper()
    removePattern = re.compile(r'<(?:REMOVED|LEFT).*>.*\[.*\]')
    updatePattern = re.compile(r'<UPDATE[D]?.*>.*\[.*\]')
    namesPattern = re.compile(r'(?<=>)[ ]?.*]')
    discordNamePattern = re.compile(r'.*#\d{4}')
    bdoNamePattern = re.compile(r'(?<=\[).*(?=\])')
    addPattern = re.compile(r'<ADDED>.*\[.*\]')
    
    # Set State
    if message.author.id == Guild.SARGE and m.startswith(Guild.prefix + "STATE") and Guild.isAuthorizedChannel(message.channel):
        args = m.split(" ")
        if args[1] == 'STOP' or args[1] == 'PAUSE':
            okToRun = False
            with fileinput.FileInput(dir_path + '/state', inplace=True, backup='.bak') as f:
                for line in f:
                    print(line.replace('Available: True', 'Available: False'), end='')
            await client.send_message(message.channel,Guild.cssMessage("Commands are no longer available"))
            await client.change_presence(game=discord.Game(name="Unavailable"))
        elif args[1] == 'CONTINUE' or args[1] == 'START':
            okToRun = True
            with fileinput.FileInput(dir_path + '/state', inplace=True, backup='.bak') as f:
                for line in f:
                    print(line.replace('Available: False', 'Available: True'), end='')
            await client.send_message(message.channel,Guild.cssMessage("Commands are now available"))
            await client.change_presence(game=discord.Game(name="Available"))
        print("okToRun changed to [" + str(okToRun) + "]")

    # Mission Commands
    elif (m.startswith(Guild.prefix + "MISSION") or m.startswith(Guild.prefix + "MISSIONS")) and Guild.isAuthorizedChannel(message.channel) and okToRun:    
        botOnline = ref.child('BotCommands').child('Online').get()
        if not botOnline:
            await client.send_message(message.channel,Guild.cssMessage("The bot responsible for handling this request is not online right now."))
            return

        args = m.split(" ")
        if args[1] == 'FINISH':
            print("Attempting to finish mission...")
            await finishMission(message.channel)
        elif args[1] == 'START': # doesn't really do anything yet
            startMission()

    # Ping Pong
    elif m.startswith(Guild.prefix + "PING"):
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
        #await client.send_message(client.get_channel("259049604627169291"), str(message.server.id))
        await client.send_message(message.channel, "pong!")

    #elif m.startswith(Guild.prefix + "FIX DATABASE"):
    #    for k, v in ref.child('Members').get().items():
    #        ref.child('Members').child(k).child('discordID').delete()
    #    for k, v in ref.child('Alumni').get().items():
    #        ref.child('Alumni').child(k).child('discordID').delete()
    #    return

    # Help!
    elif m.startswith(Guild.prefix + "HELP"):
        print("Displaying Help Message...")
        await showHelp(message.channel)

    elif m.startswith("<HELP>"):
        print("Moxie? Is that you?")
        msg = (
            "<ADDED> discord_name#1234 [bdo_family_name]" +
            "\n<REMOVED> discord_name#1234 [bdo_family_name]" +
            "\n<LEFT> discord_name#1234 [bdo_family_name]" +
            "\n<UPDATED> discord_name#1234 [bdo_family_name]" +
            "\n\nThe above are the ones Herbert officially recognizes so far. so basically you state in angle brackets '<>' what is happening, then you put their discord name with the discriminator (the numbers that follow the name), and then you put the bdo *family* name in square brackets '[]'." +
            "\n\nIf you are adding someone to the guild and for some weird reason you don't know their discord name, it is **okay** to omit the discord name as so:" +
            "\n<ADDED> [bdo_family_name]" +
            "\n\nIf they have a cool down, can't join just yet, or is added as a friendo for any reason, the format is as follows:" +
            "\n<FRIENDO (reason why friendo)> discord_name#1234 [bdo_family_name]" +
            "\nexample:" +
            "\n<FRIENDO 24h COOLDOWN> sarge841#8833 [Aeldrelm]" +
            "\n\nWith friendo, a lot of the times you won't know the bdo family name when friendoing. In those cases, omitting the bdo family name is **okay**. Like so:" +
            "\n<FRIENDO> sarge841#8833 []" 
            )
        await client.send_message(message.channel,Guild.cssMessage(msg))

    elif m.startswith("=PAT"):
        time.sleep(2)
        await client.send_message(message.channel, "There there")

    elif m.startswith(Guild.prefix + "SPOILER"):
        c = message.content.split(" ")[1:]
        c = list(map(lambda x: "||" + x + "||", c))
        msg = " ".join(c)
        await client.send_message(message.channel, msg)

    # Guildie Tracker
    # Check if adding guildie
    if len(addPattern.findall(m)) > 0 and Guild.isDatabaseChannel(message.channel):
        mesg = message.content
        for mention in message.mentions:
            mesg = mesg.replace("<@" + mention.id + ">", mention.name + "#" + mention.discriminator)
            mesg = mesg.replace("<@!" + mention.id + ">", mention.name + "#" + mention.discriminator)
        a = addPattern.findall(mesg)
        c = '\n'.join(a)
        b = namesPattern.findall(c)
        for x in b:
            #Discord Name
            dName = ""
            disResults = discordNamePattern.search(x.lstrip())
            if not disResults == None:
                dName = discordNamePattern.search(x.lstrip()).group()
            #BDO Name
            bName = ""
            bdoResults = bdoNamePattern.search(x)
            if not bdoResults == None:
                bName = bdoResults.group()
            adder = message.author.name + "#" + message.author.discriminator
            await risenGuild.addGuildie(dName, bName, adder, message)

    # Check if removing guildie
    if len(removePattern.findall(m)) > 0 and Guild.isDatabaseChannel(message.channel):
        mesg = message.content
        for mention in message.mentions:
            mesg = mesg.replace("<@" + mention.id + ">", mention.name + "#" + mention.discriminator)
            mesg = mesg.replace("<@!" + mention.id + ">", mention.name + "#" + mention.discriminator)
        a = removePattern.findall(mesg)
        c = '\n'.join(a)
        b = namesPattern.findall(c)
        for x in b:
            args = x.lstrip().split(" ")
            #Remover
            remover = message.author.name + "#" + message.author.discriminator
            #Discord Name
            dName = ""
            disResults = discordNamePattern.search(x.lstrip())
            if not disResults == None:
                dName = discordNamePattern.search(x.lstrip()).group()
            #BDO Name
            bName = ""
            bdoResults = bdoNamePattern.search(x)
            if not bdoResults == None:
                bName = bdoResults.group()
            await risenGuild.removeGuildie(dName, bName, remover, message)
            
    # Check if updating guildie
    if len(updatePattern.findall(m)) > 0 and Guild.isDatabaseChannel(message.channel):
        print("Updating!")
        mesg = message.content
        for mention in message.mentions:
            mesg = mesg.replace("<@" + mention.id + ">", mention.name + "#" + mention.discriminator)
            mesg = mesg.replace("<@!" + mention.id + ">", mention.name + "#" + mention.discriminator)
        a = updatePattern.findall(mesg)
        c = '\n'.join(a)
        b = namesPattern.findall(c)
        for x in b:
            args = x.lstrip().split(" ")
            dName = discordNamePattern.search(x.lstrip()).group()
            bName = bdoNamePattern.search(x).group()
            await risenGuild.updateGuildie(dName, bName, message)

    # Guild operations
    if m.startswith(Guild.prefix + "GUILD"):
        i = len(Guild.prefix + "GUILD ")
        m = m[i:]
        if m.startswith("SEARCH"):
            mesg = message.content
            for mention in message.mentions:
                mesg = mesg.replace("<@" + mention.id + ">", mention.name + "#" + mention.discriminator)
                mesg = mesg.replace("<@!" + mention.id + ">", mention.name + "#" + mention.discriminator)
            m = m[len(m.split(" ")[0]) + 1:]
            i += len("SEARCH ")
            alt = m.startswith("-A ")
            if alt:
                i += len(m.split(" ")[0]) + 1
            print("alt?: " + str(alt))
            await risenGuild.searchMembers(mesg[i:], message, alt=alt)
        if m.startswith("LIST"):
            await risenGuild.getGuildList(message)
        if m.startswith("GET MISSING"):
            await risenGuild.getDiscordMissing(message)
        print("End Guild Ops")

    # Alumni operations
    if m.startswith(Guild.prefix + "ALUMNI"):
        i = len(Guild.prefix + "ALUMNI ")
        m = m[i:]
        if m.startswith("SEARCH"):
            mesg = message.content
            for mention in message.mentions:
                mesg = mesg.replace("<@" + mention.id + ">", mention.name + "#" + mention.discriminator)
                mesg = mesg.replace("<@!" + mention.id + ">", mention.name + "#" + mention.discriminator)
            m = m[len(m.split(" ")[0]) + 1:]
            i += len("SEARCH ")
            alt = m.startswith("-A ")
            if alt:
                i += len(m.split(" ")[0]) + 1
            print("alt?: " + str(alt))
            await risenGuild.searchMembers(mesg[i:], message, group=MemberModule.ALUMNI, alt=alt)
    return

# Sends a signal to voice attack to turn in the mission
async def finishMission(channel):
    alreadyQueued = ref.child('BotCommands').child('FinishMission').get()

    if alreadyQueued:
        await client.send_message(channel,Guild.cssMessage("Already working on it!"))
    else:
        await client.send_message(channel,Guild.cssMessage("You got it! Finishing mission..."))
        ref.child('BotCommands').update({'FinishMission':True})

# Resets mission to false
def startMission():
    ref.child('BotCommands').update({'FinishMission':False})

# Display help info
async def showHelp(ch):
    helpMessage = (
        "HELP WINDOW\n\n" +
        "# Ping:\n" +
        "\t[" + Guild.prefix + "ping]\n\n" +
        "# Guild Member Searching:\n" +
        "# To search by a guild members discord or bdo name use:\n" +
        "\t[" + Guild.prefix + "guild search <NAME_GOES_HERE>]\n"
    )
    if Guild.isAuthorizedChannel(ch):
        helpMessage += (
            "# Add [-a] before the name for the above command for\n" + 
            "# something easier to copy for add-and-remove." +
            "\n\nSUPER SECRET OFFICER ONLY COMMANDS\n\n" +
            "# Finish a mission but ONLY IF HERBERT IS AVAILABLE:\n" +
            "\t[" + Guild.prefix + "mission finish]\n" +
            "# To get a list of mismatched named guild members:\n" +
            "\t[" + Guild.prefix + "guild get missing]"
            )
    await client.send_message(ch,Guild.cssMessage(helpMessage))
    return


TOKEN = ""
with open(dir_path + '/token', 'r') as t:
    TOKEN = t.read().replace('\n','')

client.run(TOKEN, bot=True)
