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

import database
import member
import guild
from guild import Guild
from dungeon import Dungeon

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
namesPattern = re.compile(r'(?<=>)[ ]?.*]')
discordNamePattern = re.compile(r'.*#\d{4}')
bdoNamePattern = re.compile(r'(?<=\[).*(?=\])')
addPattern = re.compile(r'<ADDED>.*\[.*\]')

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
async def on_member_join(discordMember):
    print('Welcome to ' + discordMember.guild.name + ' user ' + str(discordMember))
    greeting = risenGuild.greeting(discordMember.guild)
    if greeting == None or None in greeting or '' in greeting:
        return

    channel = client.get_channel(greeting[1])
    time.sleep(greeting[2])
    greetingMsg = greeting[0]
    # Mention the new player
    greetingMsg = greetingMsg.replace('{{mention}}', discordMember.mention)
    # Set up role mentions
    greetingMsg = greetingMsg.replace('[[role=', '<@')
    greetingMsg = greetingMsg.replace(']]', '>')

    await channel.send(greeting[0])

@client.event
async def on_message(message):
    global okToRun

    # Return if the message is from unauthorized user
    if message.author == client.user or not Guild.isValidUser(message.author):
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
        

    elif m.startswith("=PAT"):
        time.sleep(1)
        await message.channel.send( "There there")

    elif m.startswith(Guild.prefix + "SPOILER") and Guild.isImportantUser(message.author):
        c = message.content.split(" ")[1:]
        c = list(map(lambda x: "||" + x + "||", c))
        msg = " ".join(c)
        await message.edit(content=msg)
        # await message.channel.send( msg)

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
            bdoResults = bdoNamePattern.search(x)
            if not bdoResults == None:
                bName = bdoResults.group()
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
            bdoResults = bdoNamePattern.search(x)
            if not bdoResults == None:
                bName = bdoResults.group()
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
            bName = bdoNamePattern.search(x).group()
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
            optionPattern = re.compile(r'(?i)(?<=\s-)(?:a|f)(?=\s)')
            optionResults = optionPattern.findall(mesg)
            options = set()
            for result in optionResults:
                options.add(result.upper())
            alt = 'A' in options
            familyOnly = 'F' in options
            print('Options: ' + str(options))
            print("alt?: " + str(alt))
            i += 3 * len(options)
            print('Message:')
            print(mesg[i:])
            await risenGuild.searchMembers(mesg[i:], message, alt=alt, familyOnly=familyOnly)
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
            await risenGuild.searchMembers(mesg[i:], message, group=member.ALUMNI, alt=alt)
    
    if m.startswith(Guild.prefix):
        await dungeon.parse(message)

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
