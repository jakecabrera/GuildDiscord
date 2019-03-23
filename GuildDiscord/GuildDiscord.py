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
        await client.send_message(message.channel,cssMessage(msg))

    elif m.startswith("=PAT"):
        time.sleep(2)
        await client.send_message(message.channel, "There there")

    elif m.startswith(prefix + "SPOILER"):
        c = message.content.split(" ")[1:]
        c = list(map(lambda x: "||" + x + "||", c))
        msg = " ".join(c)
        await client.send_message(message.channel, msg)

    # Guildie Tracker
    # Check if adding guildie
    if len(addPattern.findall(m)) > 0 and message.channel.id in databaseChannels:
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
            await addGuildie(dName, bName, message.channel, message.server, adder)

    # Check if removing guildie
    if len(removePattern.findall(m)) > 0 and message.channel.id in databaseChannels:
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
            await removeGuildie(dName, bName, message.channel, message.server, remover)
            
    # Check if updating guildie
    if len(updatePattern.findall(m)) > 0 and message.channel.id in databaseChannels:
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
            await updateGuildie(dName, bName, message.channel)

    # Guild operations
    if m.startswith(prefix + "GUILD"):
        i = len(prefix + "GUILD ")
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
            await searchMembers(mesg[i:], message.channel, message.server, alt)
        if m.startswith("LIST"):
            await getGuildList(message.channel, message.server)
        if m.startswith("GET MISSING"):
            await getDiscordMissing(message.channel, message.server)

    # Alumni operations
    if m.startswith(prefix + "ALUMNI"):
        i = len(prefix + "ALUMNI ")
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
            await searchMembers(mesg[i:], message.channel, message.server, alt, "Alumni")

    else:
        return


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
        "# Ping:\n" +
        "\t[" + prefix + "ping]\n\n" +
        "# Guild Member Searching:\n" +
        "# To search by a guild members discord or bdo name use:\n" +
        "\t[" + prefix + "guild search <NAME_GOES_HERE>]\n"
    )
    if ch.id in authorizedChannels:
        helpMessage += (
            "# Add [-a] before the name for the above command for\n" + 
            "# something easier to copy for add-and-remove." +
            "\n\nSUPER SECRET OFFICER ONLY COMMANDS\n\n" +
            "# Finish a mission but ONLY IF HERBERT IS AVAILABLE:\n" +
            "\t[" + prefix + "mission finish]\n" +
            "# To get a list of mismatched named guild members:\n" +
            "\t[" + prefix + "guild get missing]"
            )
    await client.send_message(ch, cssMessage(helpMessage))
    return

# Adds an entry to the database
async def addGuildie(dName, bName, ch, ser, adder):
    dName = dName.replace('@', '')
    members = ref.child('Members').get()
    dMem = ser.get_member_named(dName)
    if dMem == None:
        await client.send_message(ch, cssMessage("#Warning: No user found by name of [" + dName + "] in this server"))
    for member in members:
        m = members[member]
        if m['Family'].upper() == bName.upper():
            print("Member already exists")
            await client.send_message(ch, cssMessage("Member already exists with that Family name"))
            return
        elif (dName != "" and m['Discord'] == dName):
            alt = ref.child('Members').child(member).child('Alts').push(bName)
            #alt.set(bName)
            await client.send_message(ch, cssMessage("Member already exists with that Discord name." +
                                                     "\nAppending to [" + m['Discord'] + "] as an alternate account"))
            return
    member = ref.child('Members').push()
    member.child("Discord").set(dName)
    member.child("Family").set(bName)
    member.child("AddedBy").set(adder)
    member.child("DateAdded").set({".sv": "timestamp"})
    print("Added dName: [" + dName + "]\t[" + bName + "]")
    await client.send_message(ch, cssMessage(" Added Discord: [" + dName + "]\n\tBdo Family: [" + bName + "]"))

    # Roles
    try:
        dMem = ser.get_member_named(dName)
        if dMem != None:
            role = discord.utils.get(ser.roles, id="474236074017685506") #Become a hooligan
            altRole = discord.utils.get(ser.roles, id="513371978816552960") #Become a boy
            if role != None:
                await client.replace_roles(dMem, role)
            if altRole != None:
                await client.replace_roles(dMem, altRole)
    except:
        print("Could not edit roles")
    if True:
        return
    else:
        return

# Removes guildie from database
async def removeGuildie(dName, bName, ch, ser, remover):
    if dName == None:
        dName = ""
    dName = dName.replace('@', '')
    members = ref.child('Members').get()
    removedSomeone = False
    for member in members:
        if members[member]['Family'].upper() == bName.upper() or (dName != "" and members[member]['Discord'].upper() == dName.upper()):
            print("Removing [" + bName + "] = [" + members[member]['Discord'] + "]")
            dName = members[member]['Discord']
            bName = members[member]['Family']
            ref.child('Alumni').child(member).set(ref.child('Members').child(member).get())
            ref.child('Alumni').child(member).child('RemovedBy').set(remover)    
            ref.child('Alumni').child(member).child("DateRemoved").set({".sv": "timestamp"})
            ref.child('Members').child(member).delete()
            removedSomeone = True
            await client.send_message(ch, cssMessage("Removed Discord: [" + dName + "]\n\t BDO Family: [" + bName + "]"))
        if removedSomeone:
            break
    # Roles
    try:
        dMem = ser.get_member_named(dName)
        if dMem != None:
            role = discord.utils.get(ser.roles, id="485301856004734988") #Become an alumni
            altRole = discord.utils.get(ser.roles, id="513371906896953344") #Become a someone
            if role != None:
                await client.replace_roles(dMem, role)
            if altRole != None:
                await client.replace_roles(dMem, altRole)
    except:
        print("Could not edit roles")
    if not removedSomeone:
        await client.send_message(ch, cssMessage("No matching member found in database for:\n\tDiscord:    [" + dName + "]\n\tBDO Family: [" + bName + "]"))
    else:
        return

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
        elif members[member]['Discord'] == dName and members[member]['Discord'] != "":
            oldFamily = members[member]['Family']
            ref.child('Members').child(member).update({'Family': bName})
            updatedSomeone = True
            await client.send_message(ch, cssMessage("Updated [" + dName + "] BDO family name from [" + oldFamily + "] to [" + bName + "]"))
        if updatedSomeone:
            return
    await client.send_message(ch, cssMessage("No matching member found in database for:\n\tDiscord: [" + dName + "]\n\tBDO Family: [" + bName + "]"))

# Search for a member in discord and bdo family
async def searchMembers(search, ch, ser, alt=False, group="Members"):
    print("Searching for guildie through both discord and bdo")
    await client.send_typing(ch)

    # In case given discriminator
    search = search.split("#")[0]

    # Get current discord names
    discordMembers = []
    nicks = []
    for mem in ser.members:
        discordMembers.append(mem.name.upper())
        if mem.nick != None:
            nicks.append(mem.nick)

    # Get database members
    dbMembers = ref.child(group).get()
    bdoMembers = []
    for mem in dbMembers:
        bdoMembers.append(dbMembers[mem]['Family'])

    matches = []
    # Check for any matches for the name in discord
    discordMatches = get_close_matches(search.upper(), discordMembers) 
    for match in get_close_matches(search, nicks):
        dis = ser.get_member_named(match)
        if dis != None and not dis.name.upper() in discordMatches:
            discordMatches.append(dis.name.upper())
    matches.extend(discordMatches)

    # Check for any matches for the name in bdo
    bdoMatches = get_close_matches(search.upper(), bdoMembers)
    matches.extend(bdoMatches)

    # Base case
    if not search.upper() in matches:
        matches.append(search.upper())

    # Begin output message
    msg = "Results for  [" + search + "]:"
    resultFound = False

    # Search database against matches
    for member in dbMembers:
        dis = dbMembers[member]['Discord']
        bdo = dbMembers[member]['Family']
        if dis.split("#")[0].upper() in matches or bdo.upper() in matches:
            resultFound = True
            msg += "\n\n--------------------------------------------\n"
            if alt:
                msg += dis + " [" + bdo + "]"
            else:
                msg += "Discord:      [" + dis + "]\n" + "BDO Family:   [" + bdo + "]"
                mem = ser.get_member_named(dis.split("#")[0])
                if mem != None and mem.nick != None:
                    msg += "\nNickname:     [" + mem.nick + "]"
                if group == "Members":
                    adder = None
                    try:
                        adder = dbMembers[member]['AddedBy']
                    except:
                        print("No Adder")
                    dateAdded = dbMembers[member]['DateAdded']
                    dateAdded /= 1000
                    if not adder == None:
                        msg += "\nAdded By:     [" + adder + "]"
                    if not dateAdded == None:
                        msg += "\nDate Added:   [" + datetime.fromtimestamp(dateAdded).strftime('%Y-%m-%d') + "]"
                elif group == "Alumni":
                    remover = dbMembers[member]['RemovedBy']
                    dateRemoved = dbMembers[member]['DateRemoved']
                    dateRemoved /= 1000
                    msg += "\nRemoved By:   [" + remover + "]"
                    msg += "\nDate Removed: [" + datetime.fromtimestamp(dateRemoved).strftime('%Y-%m-%d') + "]"
            msg += "\n--------------------------------------------"

    # Final messages
    if resultFound:            
        print(msg)
        await client.send_message(ch, cssMessage(msg))
    else:
        print("[" + search + "] was not found")
        await client.send_message(ch, cssMessage("[" + search + "] was not found"))

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
    else:
        return

# returns a string that is styled in css way for discord
def cssMessage(msg):
    return "```CSS\n" + msg + "\n```"


TOKEN = ""
with open(dir_path + '/token', 'r') as t:
    TOKEN = t.read().replace('\n','')

client.run(TOKEN, bot=True)
