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

import MemberModule
from MemberModule import Member

dir_path = os.path.dirname(os.path.realpath(__file__))
stateFileExists = Path(dir_path + '/state').is_file()

client = discord.Client()
cred = credentials.Certificate(dir_path + '/risen-59032-ffc0d0af3cc4.json')
default_app = firebase_admin.initialize_app(cred, {'databaseURL': 'https://risen-59032.firebaseio.com/'})
ref = db.reference('Guild')
prefix = '&'
risenServer = None

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
    global risenServer
    print("The bot is ready!")
    await client.send_message(client.get_channel("259049604627169291"), "Online!")
    risenServer = client.get_server('474229539636248596')
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
        #await client.send_message(client.get_channel("259049604627169291"), str(message.server.id))
        await client.send_message(message.channel, "pong!")

    #elif m.startswith(prefix + "FIX DATABASE"):
    #    for k, v in ref.child('Members').get().items():
    #        ref.child('Members').child(k).child('discordID').delete()
    #    for k, v in ref.child('Alumni').get().items():
    #        ref.child('Alumni').child(k).child('discordID').delete()
    #    return

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
            await updateGuildie(dName, bName, message.channel, message.author)

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
        print("End Guild Ops")

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
            await searchMembers(mesg[i:], message.channel, message.server, alt, MemberModule.ALUMNI)

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
    ser = risenServer
    dName = dName.replace('@', '')
    closeRef = ref.child(MemberModule.MEMBERS)
    dMem = ser.get_member_named(dName)
    if dMem == None:
        await client.send_message(ch, cssMessage("#Warning: No user found by name of [" + dName + "] in this server"))
    for key, val in ref.child(MemberModule.MEMBERS).get().items():
        member = Member(val)
        if member.hasAccount(bName):
            print("Member already exists")
            await client.send_message(ch, cssMessage("Member already exists with that Family name"))
            return
        elif (dName != "" and member.discord == dName):
            closeRef.child(key).child(MemberModule.ACCOUNTS).push(bName)
            await client.send_message(ch, cssMessage("Member already exists with that Discord name." +
                                                     "\nAppending to [" + member.discord + "] as an alternate account"))
            return
    member = closeRef.push()
    member.child(MemberModule.DISCORD).set(dName)
    member.child(MemberModule.ACCOUNTS).push(bName)
    member.child(MemberModule.ADDEDBY).set(adder)
    memID = ''
    if dMem != None:
        memID = dMem.id
    member.child(MemberModule.DISCORDID).set(memID)
    member.child(MemberModule.DATEADDED).set({".sv": "timestamp"})
    print("Added dName: [" + dName + "]\t[" + bName + "]")
    await client.send_message(ch, cssMessage(" Added Discord: [" + dName + "]\n\tBdo Family: [" + bName + "]"))

    # Roles
    try:
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
    removedSomeone = False
    for key, val in ref.child(MemberModule.MEMBERS).get().items():
        member = Member(val)
        if member.hasAccount(bName) or (dName != "" and member.discord.upper() == dName.upper()):
            print("Removing [" + bName + "] = [" + member.discord + "]")
            dName = member.discord
            bNames = member.accounts
            ref.child(MemberModule.ALUMNI).child(key).set(ref.child('Members').child(key).get())
            ref.child(MemberModule.ALUMNI).child(key).child('RemovedBy').set(remover)    
            ref.child(MemberModule.ALUMNI).child(key).child("DateRemoved").set({".sv": "timestamp"})
            ref.child(MemberModule.MEMBERS).child(key).delete()
            removedSomeone = True
            removeMsg = "Removed Discord: [" + dName + "]\n\t BDO Family: [" + bNames.pop() + "]"
            for n in bNames:
                removeMsg += "\n\t             [" + n + "]"
            await client.send_message(ch, cssMessage(removeMsg))
        if removedSomeone:
            break
    if not removedSomeone:
        await client.send_message(ch, cssMessage("No matching member found in database for:\n\tDiscord:    [" + dName + "]\n\tBDO Family: [" + bName + "]"))
    else:
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
        return

# Update guildie
async def updateGuildie(dName, bName, ch, sender):
    print(dName)
    print(bName)
    updatedSomeone = False
    for key, val in ref.child(MemberModule.MEMBERS).get().items():
        member = Member(val)
        if member.hasAccount(bName):
            oldDiscord = member.discord
            ref.child(MemberModule.MEMBERS).child(key).update({MemberModule.DISCORD: dName})
            updatedSomeone = True
            await client.send_message(ch, cssMessage("Updated [" + bName + "] Discord name from [" + oldDiscord + "] to [" + dName + "]"))
        elif member.discord == dName and member.discord != "":
            if len(member.accounts) == 1:
                oldName = member.accounts[0]
                ref.child(MemberModule.MEMBERS).child(key).child(MemberModule.ACCOUNTS).child(list(ref.child(MemberModule.MEMBERS).child(key).child(MemberModule.ACCOUNTS).get().keys()).pop()).set(bName)
                updatedSomeone = True
                await client.send_message(ch, cssMessage("Updated [" + dName + "] BDO family name from [" + oldName + "] to [" + bName + "]"))
            else:
                msg = "[" + member.discord + "] has more than one account.\n Which account would you like to update?\n\n"
                i = 1
                for account in member.accounts:
                    msg += str(i) + ".)\t " + account + "\n"
                    i += 1
                msg += "99.)\tCancel\n\n Please reply with the number of your choice."
                await client.send_message(ch, cssMessage(msg))
                valid = False
                def check(m):
                    return not (m.content.startswith(prefix) or m.content.startswith("<"))
                while not valid:
                    reply = await client.wait_for_message(author=sender, channel=ch, check=check)
                    if reply == None:
                        await client.send_message(ch, cssMessage("Cancelling update operation."))
                        return
                    try:
                        choice = int(reply.content)
                        if choice == 99:
                            await client.send_message(ch, cssMessage("Cancelling update operation."))
                            return
                        choice -= 1
                        for id, acc in val[MemberModule.ACCOUNTS].items():
                            if acc == member.accounts[choice]:
                                oldName = member.accounts[choice]
                                ref.child(MemberModule.MEMBERS).child(key).child(MemberModule.ACCOUNTS).child(id).set(bName)
                                updatedSomeone = True
                                await client.send_message(ch, cssMessage("Updated [" + dName + "] BDO family name from [" + oldName + "] to [" + bName + "]"))
                                valid = True
                    except:
                        await client.send_message(ch, cssMessage("Please reply with only a number matching one of the options."))
        if updatedSomeone:
            return
    await client.send_message(ch, cssMessage("No matching member found in database for:\n\tDiscord: [" + dName + "]\n\tBDO Family: [" + bName + "]"))

# Search for a member in discord and bdo family
async def searchMembers(search, ch, ser, alt=False, group=MemberModule.MEMBERS):
    print("Searching for guildie through both discord and bdo")
    ser = risenServer
    await client.send_typing(ch)

    # In case given discriminator
    search = search.split("#")[0]

    # Get current discord names
    discordMembers = {}
    nicks = {}
    for mem in ser.members:
        discordMembers[mem.name.upper() + "#" + mem.discriminator] = mem
        if mem.nick != None:
            nicks[mem.nick.upper()] = mem

    # Get database members
    dbMembers = ref.child(group).get()
    bdoMembers = []
    for key, val in dbMembers.items():
        member = Member(val)
        bdoMembers += (x.upper() for x in member.accounts)

    disMatches = []
    # Check for any matches for the name in discord
    discordMatches = get_close_matches(search.upper(), (x.split("#")[0] for x in list(discordMembers.keys())))
    nickMatches = get_close_matches(search.upper(), list(nicks.keys()))
    for k, v in discordMembers.items():
        if k.split('#')[0] in discordMatches:
            disMatches.append(v.id)
    for k, v in nicks.items():
        if k in nickMatches and not v.id in disMatches:
            disMatches.append(v.id)

    # Check for any matches for the name in bdo
    bdoMatches = get_close_matches(search.upper(), bdoMembers)
    print(disMatches)
    print(bdoMatches)

    ## Base case
    #if not search.upper() in matches:
    #    matches.append(search.upper())

    # Begin output message
    msg = "Results for  [" + search + "]:"
    resultFound = False

    # Search database against matches
    for key, val in dbMembers.items():
        member = Member(val)
        upperAccounts = (x.upper() for x in member.accounts)
        matchedAccounts = set(upperAccounts) & set(bdoMatches)
        if member.id in disMatches or matchedAccounts or member.shortDiscord.upper() in discordMatches:
            resultFound = True
            msg += "\n\n--------------------------------------------"
            if alt:
                for match in matchedAccounts:
                    matchedAccount = ""
                    for a in member.accounts:
                        if a.upper() == match:
                            matchedAccount = a
                    msg += "\n" + member.discord + " [" + matchedAccount + "]"
            else:
                accounts = member.accounts
                mem = ser.get_member(member.id)
                memberDiscord = member.discord
                if mem != None:
                    memberDiscord = mem.name + '#' + mem.discriminator
                msg += "\nDiscord:      [" + memberDiscord + "]\n" + "BDO Family:   [" + accounts.pop() + "]"
                for match in accounts:
                    msg += "\n              [" + match + "]"
                if mem != None and mem.nick != None:
                    msg += "\nNickname:     [" + mem.nick + "]"
                msg += "\nAdded By:     [" + member.addedBy + "]"
                msg += "\nDate Added:   [" + member.dateAdded + "]"
                if group == "Alumni":
                    msg += "\nRemoved By:   [" + member.removedBy + "]"
                    msg += "\nDate Removed: [" + member.dateRemoved + "]"
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
    ser = risenServer
    print("Getting list of guild members!")
    members = ref.child(MemberModule.MEMBERS).get()
    guildList = {}
    msg = ""
    for id, m in members.items():
        member = Member(m)
        info = [member.discord]
        dName = ser.get_member(member.id)
        if dName != None and dName.nick != None:
            info.append(dName.nick)
        for account in member.accounts:
            guildList[account] = info
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
    ser = risenServer
    members = ref.child(MemberModule.MEMBERS).get()

    # Get all bdo members from firebase
    dNameMembers = {}
    print("Getting firbase members")
    for id, m in members.items():
        member = Member(m)
        dNameMembers[member.discord] = member.accounts

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
            name = member
            if name == "":
                name = "NO_DISCORD_NAME_FOUND"
            msg += name + '\r\n'
            accounts = dNameMembers[member]
            msg += '\t\tFamily Name: ' + accounts.pop() + '\r\n'
            for account in accounts:
                msg += '\t\t             ' + account + '\r\n'
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
