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

import discord
import member
from member import Member

import database

dir_path = os.path.dirname(os.path.realpath(__file__))

class Guild:
    def __init__(self, client, ref, server, db):
        self.server = server
        self.client = client
        self.ref = ref
        self.db = db
        assert isinstance(self.db, database.Database)

    prefix = '&'

    AUTHORIZED_CHANNELS = {
        "test": 259049604627169291, # Private test channel
        "ops": 517203484467134484 # ops channel
        }

    DATABASE_CHANNELS = {
        "addAndRemove": 474242123143577610, # Add-and-remove
        "test": 259049604627169291 # Private test channel
        }

    SARGE = 247195865989513217 # That's me!!! o/
    HOOLIGANS = 474236074017685506
    BOY = 513371978816552960
    ALUMNI = 485301856004734988
    SOMEONE = 513371906896953344
    GUILD_ROLES = {
        539836157656301570, # Leadership
        HOOLIGANS,
        474234873763201026, # Senpai Notice Me
        474235266190540800, # Officer
        475010938148225036 # Lead vegan dev
        }

    AUTHORIZED_ROLES = {
        HOOLIGANS,
        539836157656301570, # Leadership
        513372116519878716, # Role from my test server
        474234873763201026, # Senpai notice me
        474235266190540800, # Risen officer
        }

    IMPORTANT_ROLES = {
        474234873763201026, # Senpai notice me
        475010938148225036 # Lead vegan dev
        }

    # Adds an entry to the database
    async def addGuildie(self, dName, bName, adder, message, server = None):
        client = self.client
        await message.channel.trigger_typing()
        if server == None:
            server = self.server
        dName = dName.replace('@', '')
        dMem = server.get_member_named(dName)
        if dMem == None:
            await message.channel.send(Guild.cssMessage("#Error: No user found by name of [" + dName + "] in this server. \n Adding guildie without a discord. Please update with the correct discord name when available."))
            #return

        # Check if member already exists
        if self.db.containsFamily(bName):
            for mem in self.db.members:
                if mem.account == bName:
                    print("Member already exists")
                    await message.channel.send(Guild.cssMessage("Member already exists with that Family name"))
                    return

        # Check if member had been in the guild before (Alumni)
        if self.db.containedFamily(bName):
            print("Welcome back!")
            for alum in self.db.alumni:
                if alum.account == bName:
                    print("Member used to be in guild")
                    self.db.reinstateGuildie(alum, message.author.id)
                    print("Added dName: [" + dName + "]\t[" + bName + "]")
                    await message.channel.send(Guild.cssMessage("Welcome back " + dName + "!\n Added Discord: [" + dName + "]\n\tBdo Family: [" + bName + "]"))
        
        else:
            memID, memName, memDiscrim = 0, '', ''
            if dMem != None:
                memID = dMem.id
                memName = dMem.name
                memDiscrim = dMem.discriminator
            lst = (memID, memName, memDiscrim, bName)
            mem = Member(lst)
            self.db.insertGuildie(mem, message.author.id)

            print("Added dName: [" + dName + "]\t[" + bName + "]")
            await message.channel.send(Guild.cssMessage(" Added Discord: [" + dName + "]\n\tBdo Family: [" + bName + "]"))

        # Roles
        if dMem != None:
            print('changing role')
            role = discord.utils.get(server.roles, id=474236074017685506) #Become a hooligan
            if role == None:
                print('alt')
                role = discord.utils.get(server.roles, id=513371978816552960) #Become a boy
            else:
                print('risen')
            if role != None:
                print('risen')
                await dMem.edit(roles=[role])
                if role in dMem.roles:
                    print('Success')
                else:
                    print('Failure')
        return

    # Removes guildie from database
    async def removeGuildie(self, dName, bName, remover, message, server = None):
        client = self.client
        await message.channel.trigger_typing()
        if server == None:
            server = self.server
        if dName == None:
            dName = ""
        dName = dName.replace('@', '')
        removedSomeone = False
        
        if self.db.containsFamily(bName):
            print('family found')
            dMem = server.get_member_named(dName)
            memID = 0
            if dMem != None:
                memID = dMem.id
            lst = (memID, '', '', bName)
            if dName != "":
                lst = (memID, dName.split('#')[0], dName.split('#')[1], bName)
            mem = Member(lst)
            self.db.removeGuildie(mem, message.author.id)
            await message.channel.send(Guild.cssMessage("Member removed:\n\tDiscord:    [" + dName + "]\n\tBDO Family: [" + bName + "]"))
            removedSomeone = True

        if not removedSomeone:
            await message.channel.send(Guild.cssMessage("No matching member found in database for:\n\tDiscord:    [" + dName + "]\n\tBDO Family: [" + bName + "]"))
        else:
            # Roles
            print('Removing roles')
            dMem = server.get_member_named(dName)
            if dMem != None:
                print('Role change for ' + str(dMem))
                role = discord.utils.get(server.roles, id=485301856004734988) #Become an alumni
                if role == None:
                    role = discord.utils.get(server.roles, id=513371906896953344) #Become a someone
                if role != None:
                    await dMem.edit(roles=[role])
                    if role in dMem.roles:
                        print('Success')
                    else:
                        print('Failure')
            return

    # Update guildie
    async def updateGuildie(self, dName, bName, message, server = None):
        client = self.client
        await message.channel.trigger_typing()
        if server == None:
            server = self.server
        print(dName)
        print(bName)

        dMem = server.get_member_named(dName)
        memID = 0
        if dMem != None:
            memID = dMem.id
        
        lst = (memID, dName.split('#')[0], dName.split('#')[1], bName)
        mem = Member(lst)
        if self.db.updateGuildie(mem, message.author.id) > 0:
            await message.channel.send(Guild.cssMessage("Updated member to the following:\n\tDiscord: [" + dName + "]\n\tBDO Family: [" + bName + "]"))
            return

        await message.channel.send(Guild.cssMessage("No matching member found in database for:\n\tDiscord: [" + dName + "]\n\tBDO Family: [" + bName + "]"))

    async def updateGuildieDiscord(self, bName, dMem, message):
        if not self.db.containsFamily(bName):
            await message.channel.send(Guild.cssMessage('No member found with the family [' + bName + ']. Cancelling operation'))
            return
        lst = (dMem.id, dMem.name, dMem.discriminator, bName)
        mem = Member(lst)
        if self.db.updateDiscord(mem, message.author.id) > 0:
            await message.channel.send(Guild.cssMessage('Updated Discord successfully to [' + str(dMem) + ']'))
        else:
            await message.channel.send(Guild.cssMessage('Somehow nothing happened. That was weird. Hopefully sarge fixes this at somepoint'))

    def getDBMembers(self, group = member.MEMBERS):
        dbMembers = None
        if group == member.MEMBERS:
            dbMembers = self.db.members
        else:
            dbMembers = self.db.alumni
        return dbMembers

    def getDBDiscord(self, group = member.MEMBERS):
        dbMembers = self.getDBMembers(group)
        dbDiscord = list()
        for m in dbMembers:
            if m.shortDiscord != None:
                dbDiscord.append(m.shortDiscord)
        return dbDiscord

    def getDBFamily(self, group = member.MEMBERS):
        dbMembers = self.getDBMembers(group)
        bdoMembers = []
        for mem in dbMembers:
            bdoMembers.append(mem.account.upper())
        return bdoMembers

    def getGuildDiscord(self):
        server = self.server
        discordMembers = {}
        for m in server.members:
            discordMembers[str(m)] = m
        return discordMembers
    
    def getGuildNicks(self):
        server = self.server
        nicks = {}
        for m in server.members:
            if m.nick != None:
                nicks[m.nick.upper()] = m
        return nicks

    def shortSearchDesc(self, mem):
        server = self.server
        disMem = server.get_member(mem.id)
        disPrint = mem.discord if mem.discord != None else ''
        if disMem != None:
            disPrint = disMem.name + "#" + disMem.discriminator
        msg = disPrint + " [" + mem.account + "]"
        return msg

    def longSearchDesc(self, mem):
        server = self.server
        msg = "--------------------------------------------"
        m = server.get_member(mem.id)
        memberDiscord = mem.discord
        if m != None:
            memberDiscord = str(m)
        elif memberDiscord == "" or memberDiscord == None:
            memberDiscord = "NO_DISCORD_NAME_FOUND"
        msg += "\nDiscord:      [" + memberDiscord + "]\n" + "BDO Family:   [" + mem.account + "]"
        if m != None and m.nick != None:
            msg += "\nNickname:     [" + m.nick + "]"
        msg += "\n--------------------------------------------"
        return msg

    # Search for a member in discord and bdo family
    def searchMembers(self, search, group = member.MEMBERS, alt = False, familyOnly = False, expired = False, remove = False):
        client = self.client
        server = self.server
        print("Searching for guildie through both discord and bdo")

        msg = '' 

        if familyOnly == True:
            families = search.split(' ')
            for family in families:
                msg += self.searchMembers(family, alt=alt)
            msg.strip()
            if expired or remove:
                tmp = msg
                msg = ""
                n = 1
                for line in tmp.splitlines():
                    if line == "": continue
                    msg += str(n) + "). " + line + "\n"
                    n += 1
                msg = "\n" + msg
            if alt: msg = "\n" + msg
            return msg

        # Begin output message
        resultFound = False

        # In case given discriminator
        search = search.split("#")[0]

        # Get current discord names
        discordMembers = self.getGuildDiscord()
        nicks = self.getGuildNicks()

        # Get database members
        dbMembers = self.getDBMembers(group)
        dbDiscord = self.getDBDiscord(group)

        # Get db familys
        bdoMembers = self.getDBFamily(group)

        disMatches = []
        # Check for any matches for the name in discord
        discordMatches = get_close_matches(search.upper(), (x.split("#")[0].upper() for x in list(discordMembers.keys())))
        altDiscordMatches = get_close_matches(search.upper(), (x.upper() for x in list(dbDiscord)))
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
        print(altDiscordMatches)

        # Search database against matches
        for mem in dbMembers:
            if mem.id in disMatches or mem.account.upper() in bdoMatches or (mem.shortDiscord != None and mem.shortDiscord.upper() in set(discordMatches).union(set(altDiscordMatches))):
                resultFound = True
                if alt:
                    msg += "\n" + self.shortSearchDesc(mem)
                else:
                    msg += "\n\n" + self.longSearchDesc(mem)

        # Final messages
        if resultFound:            
            print(msg[1:])
            return msg
        else:
            print("[" + search + "] was not found")
            return "\n\n[" + search + "] was not found"

    # Return family names that correspond with the given discord ID
    def getFamilyByID(self, dMemID):
        matches = list()
        for mem in self.db.members:
            if mem.id == dMemID:
                matches.append(mem.account)
        return matches

    def getDiscordByFamily(self, family):
        for m in self.db.members:
            if m.account == family:
                return self.server.get_member(m.id)
        return None

    # Get a list of current guild members!
    async def getGuildList(self, message, server = None):
        if server == None:
            server = self.server
        print("Getting list of guild members!")
        await message.channel.trigger_typing()
        guildList = {}
        msg = ""
        for mem in self.db.members:
            disPrint = mem.discord
            nickPrint = ""
            dName = server.get_member(mem.id)
            if dName != None: 
                disPrint = str(dName)
                if dName.nick != None:
                    nickPrint = dName.nick
            elif disPrint == None or disPrint == "":
                disPrint = "NO_DISCORD_NAME_FOUND"

            info = [disPrint]
            if nickPrint != "":
                info.append(nickPrint)

            guildList[mem.account] = info
        guildList = collections.OrderedDict(sorted(guildList.items()))
        i = 1
        for k, v in guildList.items():
            msg += str(i) + ": Family: " + k + "\r\n    Discord: " + v[0] + "\r\n"
            if len(v) > 1:
                msg += "    Nickname: " + v[1] + "\r\n"
            i += 1
        with io.open(dir_path + "/guildList.txt", "w", encoding="utf-8") as f:
            f.write(msg)
        await message.channel.send(file=discord.File(dir_path + "/guildList.txt"))

    # Gets the discrepencies in guild members
    async def getDiscordMissing(self, message, server = None):
        await message.channel.trigger_typing()
        if server == None:
            server = self.server

        # Get all bdo members from firebase
        dNameMembers = {}
        print("Getting firbase members")
        for mem in self.db.members:
            discordMember = server.get_member(mem.id)
            if not discordMember == None:
                dNameMembers[mem.account] = str(discordMember)
            else:
                dNameMembers[mem.account] = mem.discord

        # Get all hooligans from discord
        hooligans = []
        print("getting discord members")
        for mem in server.members:
            isGuildMember = False
            for mRole in mem.roles:
                if Guild.isGuildRole(mRole):
                    isGuildMember = True
            if isGuildMember:
                hooligans.append(str(mem))

        # Compare hooligans against the bdo members
        discordMissing = []
        print("Comparing")
        for mem in hooligans:
            if not mem in dNameMembers.values():
                discordMissing.append(mem)

        # Compare bdo members against hooligans
        bdoMissing = []
        for mem in dNameMembers.values():
            if not mem in hooligans:
                bdoMissing.append(mem)

        if len(discordMissing) > 0:
            msg = ''
            for mem in discordMissing:
                msg += mem + '\r\n'
            print("Writing")
            with io.open(dir_path + "/guildDiscordMissing.txt", "w", encoding="utf-8") as f:
                f.write(msg)
            await message.channel.send(Guild.cssMessage("The following members were found in discord as part of the guild but not in BDO:\n\n" + msg))
        if len(bdoMissing) > 0:
            print("Bdomissing")
            print(bdoMissing)
            msg = ''
            unnamed = []
            for mem in bdoMissing:
                name = mem
                if name == None or name == "":
                    name = "NO_DISCORD_NAME_FOUND"
                msg += name + '\r\n'
                account = ''
                for a, d in dNameMembers.items():
                    if d == mem and not a in unnamed:
                        account = a
                        unnamed.append(a)
                        break

                msg += '\t\tFamily Name: ' + account + '\r\n'
            print("Writing")
            with io.open(dir_path + "/guildBdoMissing.txt", "w", encoding="utf-8") as f:
                f.write(msg)
            await message.channel.send(Guild.cssMessage("The following members were found in BDO as part of the guild but are not a Hooligan:\n\n" + msg))
        if len(bdoMissing) == 0 and len(discordMissing) == 0:
            await message.channel.send(Guild.cssMessage("All members accounted for!"))
        return

    async def replaceRoles(self, member, targetRole):
        for role in member.roles:
            if role.name != '@everyone' and role.position < self.server.me.top_role.position:
                await member.remove_roles(role)
        await member.add_roles(targetRole)

    def greeting(self, guild, greeting = None):
        if greeting == None:
            print('Retrieving greeting for ' + guild.name)
            return self.db.retrieveGreeting(guild)
        else:
            print('Updating greeting for ' + guild.name)
            self.db.updateGreeting(guild, greeting)
            return

    def greetingChannel(self, guild, channel = None):
        if channel == None:
            print('Getting greeting channel')
            return self.db.retrieveGreeting(guild)[1]
        else:
            print('Setting greeting channel')
            return self.db.updateGreetingChannel(channel, guild)

    def greetingDelay(self, guild, delay = -1):
        if delay < 0:
            print('Getting greeting delay')
            return self.db.retrieveGreeting(guild)[2]
        else:
            print('Setting greeting delay')
            return self.db.updateGreetingDelay(delay, guild)

    
    ########################################################
    #   Class Functions
    ########################################################
    
    # returns a string that is styled in css way for discord
    def cssMessage(msg):
        return "```CSS\n" + msg + "\n```"

    # returns whether the given channel is an authorized channel or not
    def isAuthorizedChannel(ch):
        return ch.id in Guild.AUTHORIZED_CHANNELS.values()

    # Returns whether the given channel is a database channel or not
    def isDatabaseChannel(ch):
        return ch.id in Guild.DATABASE_CHANNELS.values()

    # Returns whether the given role is a role that guild members would have
    def isGuildRole(role):
        return role.id in Guild.GUILD_ROLES

    # Returns whether the given user is a valid user for secret commands
    def isValidUser(user, guild):
        user = guild.get_member(user.id)
        if user != None:
            for role in Guild.AUTHORIZED_ROLES:
                if role in [r.id for r in user.roles]:
                    return True
        return False

    def isImportantUser(user):
        if user.id == Guild.SARGE: 
            return True
        for role in Guild.IMPORTANT_ROLES:
            if role in [r.id for r in user.roles]:
                return True
        return False