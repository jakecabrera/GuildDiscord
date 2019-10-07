import re
import os
import io
import collections
import time
import fileinput
from pathlib import Path
from difflib import get_close_matches
from datetime import datetime
from pytz import timezone

import discord
from discord.ext import commands

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

import database
import member
import guild
from guild import Guild
from dungeon import Dungeon
from sar import SAR

dir_path = os.path.dirname(os.path.realpath(__file__))
stateFileExists = Path(dir_path + '/state').is_file()

client = discord.Client()
cred = credentials.Certificate(dir_path + '/risen-59032-ffc0d0af3cc4.json')
default_app = firebase_admin.initialize_app(cred, {'databaseURL': 'https://risen-59032.firebaseio.com/'})
ref = db.reference('Guild')
risenServer = None
risenGuild = None
datab = None
dungeon = Dungeon()

removePattern = re.compile(r'<(?:REMOVED|LEFT).*>.*\[.*\]')
updatePattern = re.compile(r'<UPDATE[D]?.*>.*\[.*\]')
namesPattern = re.compile(r'(?<=> )[ ]?.*]')
discordNamePattern = re.compile(r'.*#\d{4}')
bdoNamePattern = re.compile(r'(?<=\[)[A-z0-9]*(?=\])')
addPattern = re.compile(r'<ADDED>.*\[.*\]')


timezones = {
    'EST': 'US/Eastern',
    'EDT': 'US/Eastern',
    'MST': 'US/Arizona',
    'PST': 'US/Pacific',
    'PDT': 'US/Pacific'
    }

# File to check if still available to complete missions or not
if not stateFileExists:
    with open(dir_path + '/state', 'x') as f:
        f.write("Available: False\n")

state = {}
with open(dir_path + '/state') as f:
    content = f.readlines()
    for line in content:
        if line != '' or not line.startswith('#'):
            state[line.split(':')[0].strip()] = line.split(':')[1].strip()
okToRun = state['Available'] == 'True'

@client.event
async def on_ready():
    global risenServer
    global risenGuild
    global datab
    datab = database.Database()

    print("The bot is ready!")
    testChannel = client.get_channel(int(Guild.AUTHORIZED_CHANNELS['test']))
    print(testChannel)
    await testChannel.send("Online!")
    risenServer = client.get_guild(474229539636248596)
    risenGuild = Guild(client, ref, risenServer, datab)
    if not okToRun:
        await client.change_presence(activity=discord.Game(name="Unavailable"))
    else:
        await client.change_presence(activity=discord.Game(name="Available"))

    print("The bot is really ready!")

@client.event
async def on_member_remove(discordMember):
    if not risenServer.id == discordMember.guild.id:
        return
    msg = discordMember.top_role.name + " [" + str(discordMember) + "] has left the server."
    msg = msg.replace('@everyone ', '')
    print('Bye bye ' + str(discordMember))
    if discordMember.top_role.id in Guild.GUILD_ROLES:
        accounts = risenGuild.getFamilyByID(discordMember.id)
        if len(accounts) > 0:
            datab.updateDiscord(member.Member.m2m(discordMember, accounts[0]), discordMember.guild.me.id)
        for account in accounts:
            msg += '\nBDO Family: [' + account + ']'
    print(msg)
    await client.get_channel(Guild.DATABASE_CHANNELS['addAndRemove']).send(Guild.cssMessage(msg))

@client.event
async def on_user_update(before, after):    
    if str(before) == str(after): return
    if not Guild.isValidUser(before, risenServer): return
    msg = str(before) + " changed their username to " + str(after)
    print(msg)
    await client.get_channel(Guild.DATABASE_CHANNELS['addAndRemove']).send(Guild.cssMessage(msg))
    return

@client.event
async def on_member_join(discordMember):
    print('Welcome to ' + discordMember.guild.name + ' user ' + str(discordMember))
    greeting = risenGuild.greeting(discordMember.guild)
    if greeting == None or None in greeting or '' in greeting:
        return

    channel = client.get_channel(greeting[1])
    greetingMsg = greeting[0]
    # Mention the new player
    greetingMsg = greetingMsg.replace('{{mention}}', discordMember.mention)
    # Set up role mentions
    greetingMsg = greetingMsg.replace('[[role=', '<@')
    greetingMsg = greetingMsg.replace(']]', '>')
    
    time.sleep(greeting[2])
    await channel.send(greetingMsg)

@client.event
async def on_message(message):
    global okToRun

    # Return if the message is from unauthorized user
    if message.author == client.user or not Guild.isValidUser(message.author, message.guild):
        return

    m = message.content.upper()
    
    # Set State
    if message.author.id == Guild.SARGE and m.startswith(Guild.prefix + "STATE") and Guild.isAuthorizedChannel(message.channel):
        args = m.split(" ")
        if args[1] == 'STOP' or args[1] == 'PAUSE':
            okToRun = False
            with fileinput.FileInput(dir_path + '/state', inplace=True, backup='.bak') as f:
                for line in f:
                    print(line.replace('Available: True', 'Available: False'), end='')
            await message.channel.send(Guild.cssMessage("Commands are no longer available"))
            await client.change_presence(game=discord.Game(name="Unavailable"))
        elif args[1] == 'CONTINUE' or args[1] == 'START':
            okToRun = True
            with fileinput.FileInput(dir_path + '/state', inplace=True, backup='.bak') as f:
                for line in f:
                    print(line.replace('Available: False', 'Available: True'), end='')
            await message.channel.send(Guild.cssMessage("Commands are now available"))
            await client.change_presence(game=discord.Game(name="Available"))
        print("okToRun changed to [" + str(okToRun) + "]")

    elif message.author.id == Guild.SARGE and m.startswith(Guild.prefix + "DATABASE") and Guild.isAuthorizedChannel(message.channel):
        datab.refresh()
        await message.channel.send( Guild.cssMessage('Refreshing'))

    # Mission Commands
    elif (m.startswith(Guild.prefix + "MISSION") or m.startswith(Guild.prefix + "MISSIONS")) and Guild.isAuthorizedChannel(message.channel) and okToRun:    
        botOnline = ref.child('BotCommands').child('Online').get()
        if not botOnline:
            await message.channel.send(Guild.cssMessage("The bot responsible for handling this request is not online right now."))
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
        roles = message.guild.roles
        msg = ""
        for role in roles:
            msg += str(role.id) + ":\t" + role.name + "\n"
        await client.get_channel(259049604627169291).send(msg)
        channels = message.guild.channels
        msg = ""
        for channel in channels:
            msg += str(channel.id) + ":\t" + channel.name + "\n"
        await client.get_channel(259049604627169291).send(msg)
        await client.get_channel(259049604627169291).send(str(message.guild.id))
        await message.channel.send( "pong!")

    elif m.startswith(Guild.prefix + "GET ROLE IDS"):
        print("Getting role ids")
        roles = message.guild.roles
        msg = ""
        for role in roles:
            msg += str(role.id) + ":\t" + role.name + "\n"
        await client.get_channel(259049604627169291).send(msg)

    # Help!
    elif m.startswith(Guild.prefix + "HELP"):
        print("Displaying Help Message...")
        helpmsg = datab.helpMessageMain
        if Guild.isAuthorizedChannel(message.channel): helpmsg += datab.helpMessageOfficer
        await message.channel.send(helpmsg)

    elif m.startswith("<HELP>") and Guild.isDatabaseChannel(message.channel):
        print("Moxie? Is that you?")
        await message.channel.send(datab.helpMessageAAR)

    elif m.startswith(Guild.prefix + "UPDATE HELP "):
        m = m[len(Guild.prefix + "UPDATE HELP "):]
        helpMessage = '\n'.join(message.content.splitlines()[1:])
        if m.startswith('OFFICER'): 
            print('officer help updated')
            datab.helpMessageOfficer = helpMessage
        elif m.startswith('MAIN'): 
            print('main help updated')
            datab.helpMessageMain = helpMessage
        elif m.startswith('AAR'):
            print('aar help updated')
            datab.helpMessageAAR = helpMessage
        await message.channel.send(Guild.cssMessage('Updated help message!'))
        return
        
    elif m.startswith(Guild.prefix + 'CUDDLE'):
        # current time
        dateToConvert = datetime.now()
        
        # if a time was actually specified...
        if len(m[7:]) > 0:
            # Patterns to extract essential info
            timezonePattern = re.compile(r'(?i)[a-zA-Z]*$')
            hourPattern = re.compile(r'(?i)(?<=cuddle )\d{1,2}')
            dayHalfPattern = re.compile(r'(?i)(?<=\d)(?:AM|PM)(?= )')
            minutePattern = re.compile(r'(?i)(?<=:)\d{2}')
            
            # Extract the time
            tzResult = timezonePattern.findall(m)[0]
            hours = int(hourPattern.findall(m)[0])
            dayHalf = dayHalfPattern.findall(m)[0]
            minutesResults = minutePattern.findall(m)

            # Check if minutes were specified
            minutes = 0
            if len(minutesResults) > 0:
                minutes = int(minutesResults[0])

            # Check which half of the day we are using
            if dayHalf == 'PM':
                hours += 12

            # If a timezone is specified then convert the current datetime to that timezone
            # and set the time for that timezone
            if tzResult in timezones:
                dateToConvert = datetime.now(timezones[tzResult])
                dateToConvert = dateToConvert.replace(hour=hours, minute=minutes)
            else:
                return

        # Convert whatever time we specify into cuddle time
        dateToConvert = dateToConvert.astimezone(timezone('Australia/Adelaide'))
        timeFormat = dateToConvert.strftime('%I:%M%p %Z')

        await message.channel.send(timeFormat)

    elif m.startswith("=PAT"):
        time.sleep(1)
        await message.channel.send( "There there")

    elif m.startswith(Guild.prefix + "SPOILER") and Guild.isImportantUser(message.author):
        c = message.content.split(" ")[1:]
        c = list(map(lambda x: "||" + x + "||", c))
        msg = " ".join(c)
        await message.channel.send( msg)
        await message.delete()

    elif m.startswith(Guild.prefix + "GREETING CHANNEL") and Guild.isImportantUser(message.author):
        channels = message.channel_mentions
        if len(channels) > 0:
            result = risenGuild.greetingChannel(message.guild, channel=channels[0])
            if result > 0:
                await message.channel.send('Set channel for greeting output to <#' + str(channels[0].id) + '>')
            else:
                await message.channel.send('Set the greeting message first before choosing a channel')
        else:
            ch = client.get_channel(risenGuild.greetingChannel(message.guild))
            msg = 'No bound channel'
            if ch != None:
                msg = 'Greeting messages are bound to <#' + str(ch.id) + '>'
            await message.channel.send(msg)

    elif m.startswith(Guild.prefix + "GREETING DELAY") and Guild.isImportantUser(message.author):
        val = message.content[len(Guild.prefix + "GREETING DELAY"):].strip()
        if len(val) > 0:
            try:
                delay = int(val)
                print('delay = ' + str(delay))
                if delay >= 0:
                    result = risenGuild.greetingDelay(message.guild, delay)
                    print('result = ' + str(result))
                    if result > 0:
                        await message.channel.send('Set greeting delay to ' + str(delay) + ' seconds.')
                        return
            except:
                print('Cant fit val into an int')
            await message.channel.send('Please use an integer value 0-60 (represented as seconds) that is not what the delay is already set to.')
        else:
            delay = risenGuild.greetingDelay(message.guild)
            msg = 'Greeting is set to delay for ' + str(delay) + ' seconds.'
            await message.channel.send(msg)

    elif m.startswith(Guild.prefix + "GREETING") and Guild.isImportantUser(message.author):
        if len(m[len(Guild.prefix + "GREETING"):].strip()) > 0:
            # setting greeting
            msg = '\n'.join(message.content.splitlines()[1:])
            risenGuild.greeting(message.guild, greeting=msg)
            await message.channel.send(Guild.cssMessage('Updated!'))
        else:
            # getting greeting
            greeting = risenGuild.greeting(message.guild)
            if greeting == None or None in greeting:
                greeting = Guild.cssMessage('The greeting message has not yet been set')
            elif m.startswith(Guild.prefix + "GREETING NO MENTION"):
                greeting = Guild.cssMessage(greeting)
            await message.channel.send(greeting[0])


    # Guildie Tracker
    # Check if adding guildie
    if len(addPattern.findall(m)) > 0 and Guild.isDatabaseChannel(message.channel):
        mesg = message.content
        for mention in message.mentions:
            mesg = mesg.replace("<@" + str(mention.id) + ">", mention.name + "#" + mention.discriminator)
            mesg = mesg.replace("<@!" + str(mention.id) + ">", mention.name + "#" + mention.discriminator)
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
            bdoResults = bdoNamePattern.findall(x)
            if not len(bdoResults) == 0:
                bName = bdoResults[-1]
            adder = message.author.name + "#" + message.author.discriminator
            await risenGuild.addGuildie(dName, bName, adder, message)

    # Check if removing guildie
    if len(removePattern.findall(m)) > 0 and Guild.isDatabaseChannel(message.channel):
        mesg = message.content
        for mention in message.mentions:
            mesg = mesg.replace("<@" + str(mention.id) + ">", mention.name + "#" + mention.discriminator)
            mesg = mesg.replace("<@!" + str(mention.id) + ">", mention.name + "#" + mention.discriminator)
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
            bdoResults = bdoNamePattern.findall(x)
            if not len(bdoResults) == 0:
                bName = bdoResults[-1]
            print("bName: " + bName)
            print("dName: " + dName)
            await risenGuild.removeGuildie(dName, bName, remover, message)
            
    # Check if updating guildie
    if len(updatePattern.findall(m)) > 0 and Guild.isDatabaseChannel(message.channel):
        print("Updating!")
        mesg = message.content
        for mention in message.mentions:
            mesg = mesg.replace("<@" + str(mention.id) + ">", mention.name + "#" + mention.discriminator)
            mesg = mesg.replace("<@!" + str(mention.id) + ">", mention.name + "#" + mention.discriminator)
        a = updatePattern.findall(mesg)
        c = '\n'.join(a)
        b = namesPattern.findall(c)
        for x in b:
            args = x.lstrip().split(" ")
            dName = discordNamePattern.search(x.lstrip()).group()
            bName = bdoNamePattern.findall(x)[-1]
            await risenGuild.updateGuildie(dName, bName, message)

    # Guild operations
    if m.startswith(Guild.prefix + "GUILD "):
        i = len(Guild.prefix + "GUILD ")
        m = m[i:]
        if m.startswith("SEARCH "):
            mesg = message.content
            for mention in message.mentions:
                mesg = mesg.replace("<@" + str(mention.id) + ">", mention.name + "#" + mention.discriminator)
                mesg = mesg.replace("<@!" + str(mention.id) + ">", mention.name + "#" + mention.discriminator)
            m = m[len(m.split(" ")[0]) + 1:]
            i += len("SEARCH ")
            optionPattern = re.compile(r'(?i)(?<=\s-)(?:a|f|x|r)(?=\s)')
            optionResults = optionPattern.findall(mesg)
            options = set()
            for result in optionResults:
                options.add(result.upper())
            expired = 'X' in options
            remove = 'R' in options and not expired
            alt = 'A' in options or expired or remove
            familyOnly = 'F' in options or expired or remove
            print('Options: ' + str(options))
            print("alt?: " + str(alt))
            i += 3 * len(options)
            print('Message:')
            print(mesg[i:])
            results = "Results for  [" + mesg[i:] + "]:"
            results += risenGuild.searchMembers(mesg[i:], alt=alt, familyOnly=familyOnly, expired = expired, remove=remove)
            await message.channel.send(Guild.cssMessage(results))
            if not Guild.isValidUser(message.author, message.guild) or not Guild.isDatabaseChannel(message.channel): return
            if expired or remove:
                msg = ""
                if expired:
                    msg = "Please enter the numbers of the results separated by spaces that you wish to add the expired role to."
                if remove:
                    msg = "Please enter the numbers of the results separated by spaces that you wish to remove from the guild."
                await message.channel.send(Guild.cssMessage(msg))
                def check(m):
                    return m.channel == message.channel and m.author == message.author
                response = await client.wait_for('message', check=check, timeout = 60.0)
                choices = list((a + ")." for a in response.content.split(' ')))
                selections = results.splitlines()[2:]
                msg = ""
                for selection in selections:
                    for choice in choices:
                        if selection.startswith(choice):
                            print(selection.replace(choice + " ",''))
                            familyPattern = re.compile(r'(?<=\[)[A-z0-9]*(?=\])')
                            familyResults = familyPattern.findall(selection)
                            family = familyResults[-1]
                            dMem = risenGuild.getDiscordByFamily(family)
                            if dMem != None:
                                if expired:
                                    role = discord.utils.get(risenServer.roles, id=597253708711067658)
                                    await dMem.add_roles(role)
                                    msg += "Role added for " + str(dMem) + '\n'
                                    print('role added')
                                if remove:
                                    await risenGuild.removeGuildie(str(dMem), family, message.author, message)
                            elif family != None:
                                print("No discord found for " + family)
                                if expired:
                                    msg += "No roled added to family [" + family + "] because there was no discord found\n"
                                if remove:
                                    await risenGuild.removeGuildie('', family, message.author, message)
                if not remove: 
                    await message.channel.send(Guild.cssMessage(msg))
        elif m.startswith("LIST"):
            await risenGuild.getGuildList(message)
        elif m.startswith("GET MISSING"):
            await risenGuild.getDiscordMissing(message)
        elif m.startswith('UPDATE '):
            mesg = message.content
            for mention in message.mentions:
                mesg = mesg.replace('<@' + str(mention.id) + '>', str(mention))
                mesg = mesg.replace('<@!' + str(mention.id) + '>', str(mention))
                mesg = mesg.replace(Guild.prefix + 'GUILD UPDATE ', '')
            m = m[len(m.split(" ")[0]) + 1:]
            i += len("UPDATE ")
            if m.startswith('DISCORD '):
                m = mesg[i:]
                bName = m.split(' ')[1]
                dMem = risenServer.get_member_named(' '.join(m.split(' ')[2:]))
                if dMem == None:
                    msg = 'No discord member found in this server as [' + ' '.join(m.split(' ')[2:]) + ']'
                    await message.channel.send(Guild.cssMessage(msg))
                else:
                    await risenGuild.updateGuildieDiscord(bName, dMem, message)
        print("End Guild Ops")

    # Alumni operations
    if m.startswith(Guild.prefix + "ALUMNI"):
        i = len(Guild.prefix + "ALUMNI ")
        m = m[i:]
        if m.startswith("SEARCH"):
            mesg = message.content
            for mention in message.mentions:
                mesg = mesg.replace("<@" + str(mention.id) + ">", mention.name + "#" + mention.discriminator)
                mesg = mesg.replace("<@!" + str(mention.id) + ">", mention.name + "#" + mention.discriminator)
            m = m[len(m.split(" ")[0]) + 1:]
            i += len("SEARCH ")
            alt = m.startswith("-A ")
            if alt:
                i += len(m.split(" ")[0]) + 1
            print("alt?: " + str(alt))
            await message.channel.trigger_typing()
            results = "Results for  [" + mesg[i:] + "]:\n\n"
            results += risenGuild.searchMembers(mesg[i:], group=member.ALUMNI, alt=alt)
            await message.channel.send(Guild.cssMessage(results))
    
    if m.startswith(Guild.prefix):
        await dungeon.parse(message)

    if m.startswith(Guild.prefix + "WHO HAS "):
        print("who has?")
        msgs = list()
        role = None
        if len(message.role_mentions) == 0:
            print("no role mentions")
            roleId = int(message.content[len(Guild.prefix + "WHO HAS "):])
            role = risenServer.get_role(roleId)
            print(role)
        else:
            print("found the first mentioned role")
            role = message.role_mentions[0]

        if role == None:
            print("Could not find the role you wanted")
            msgs.append("Did you forget to mention a role?")
        else:
            msg = ''
            for mem in risenServer.members:
                if role in mem.roles:
                    addStr = str(mem) + "\n"
                    if len(Guild.cssMessage(msg + addStr)) > 2000:
                        msgs.append(msg)
                        msg = ''
                    msg += addStr
            msgs.append(msg)
        for msg in msgs:
            await message.channel.send(Guild.cssMessage(msg))


    # SAR
    if m.startswith("=RANK"):
        print("SAR")
        sar = SAR(datab, risenServer)
        await sar.pickGroup(message, client)

# Sends a signal to voice attack to turn in the mission
async def finishMission(channel):
    alreadyQueued = ref.child('BotCommands').child('FinishMission').get()

    if alreadyQueued:
        await channel.send(Guild.cssMessage("Already working on it!"))
    else:
        await channel.send(Guild.cssMessage("You got it! Finishing mission..."))
        ref.child('BotCommands').update({'FinishMission':True})

# Resets mission to false
def startMission():
    ref.child('BotCommands').update({'FinishMission':False})


TOKEN = ""
with open(dir_path + '/token', 'r') as t:
    TOKEN = t.read().replace('\n','')

client.run(TOKEN, bot=True)
