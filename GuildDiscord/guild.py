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
        "test": "259049604627169291", # Private test channel
        "ops": "517203484467134484" # ops channel
        }

    DATABASE_CHANNELS = {
        "addAndRemove": "474242123143577610", # Add-and-remove
        "test": "259049604627169291" # Private test channel
        }

    AUTHORIZED_ROLES = {
        "539836157656301570", # Leadership
        "513372116519878716", # Role from my test server
        "474234873763201026", # Senpai notice me
        "474235266190540800", # Risen officer
        }

    SARGE = "247195865989513217" # That's me!!! o/
    HOOLIGANS = "474236074017685506"
    GUILD_ROLES = {
        "539836157656301570", # Leadership
        HOOLIGANS,
        "474234873763201026", # Senpai Notice Me
        "474235266190540800", # Officer
        "475010938148225036" # Lead vegan dev
        }

    # Adds an entry to the database
    async def addGuildie(self, dName, bName, adder, message, server = None):
        client = self.client
        await client.send_typing(message.channel)
        if server == None:
            server = self.server
        dName = dName.replace('@', '')
        dMem = server.get_member_named(dName)
        if dMem == None:
            await client.send_message(message.channel, Guild.cssMessage("#Error: No user found by name of [" + dName + "] in this server. \n Cancelling operation"))
            return

        # Check if member already exists
        if self.db.containsFamily(bName):
            for mem in self.db.members:
                if mem.account == bName:
                    print("Member already exists")
                    await client.send_message(message.channel, Guild.cssMessage("Member already exists with that Family name"))
                    return

        # Check if member had been in the guild before (Alumni)
        if self.db.containedFamily(bName):
            print("Welcome back!")
            for alum in self.db.alumni:
                if alum.account == bName:
                    print("Member used to be in guild")
                    self.db.reinstateGuildie(alum, message.author.id)
                    print("Added dName: [" + dName + "]\t[" + bName + "]")
                    await client.send_message(message.channel, Guild.cssMessage("Welcome back " + dName + "!\n Added Discord: [" + dName + "]\n\tBdo Family: [" + bName + "]"))
                    return

        memID = ''
        if dMem != None:
            memID = dMem.id
        lst = (memID, dMem.name, dMem.discriminator, bName)
        mem = Member(lst)
        self.db.insertGuildie(mem, message.author.id)

        print("Added dName: [" + dName + "]\t[" + bName + "]")
        await client.send_message(message.channel, Guild.cssMessage(" Added Discord: [" + dName + "]\n\tBdo Family: [" + bName + "]"))

        # Roles
        try:
            if dMem != None:
                role = discord.utils.get(server.roles, id="474236074017685506") #Become a hooligan
                altRole = discord.utils.get(server.roles, id="513371978816552960") #Become a boy
                if role != None:
                    await client.replace_roles(dMem, role)
                if altRole != None:
                    await client.replace_roles(dMem, altRole)
        except:
            print("Could not edit roles")
        return

    # Removes guildie from database
    async def removeGuildie(self, dName, bName, remover, message, server = None):
        client = self.client
        await client.send_typing(message.channel)
        if server == None:
            server = self.server
        if dName == None:
            dName = ""
        dName = dName.replace('@', '')
        removedSomeone = False
        
        if self.db.containsFamily(bName):
            print('family found')
            dMem = server.get_member_named(dName)
            memID = ''
            if dMem != None:
                memID = dMem.id
            lst = (memID, dName.split('#')[0], dName.split('#')[1], bName)
            mem = Member(lst)
            self.db.removeGuildie(mem, message.author.id)
            await client.send_message(message.channel, Guild.cssMessage("Member removed:\n\tDiscord:    [" + dName + "]\n\tBDO Family: [" + bName + "]"))
            removedSomeone = True

        if not removedSomeone:
            await client.send_message(message.channel, Guild.cssMessage("No matching member found in database for:\n\tDiscord:    [" + dName + "]\n\tBDO Family: [" + bName + "]"))
        else:
            # Roles
            try:
                dMem = server.get_member_named(dName)
                if dMem != None:
                    role = discord.utils.get(server.roles, id="485301856004734988") #Become an alumni
                    altRole = discord.utils.get(server.roles, id="513371906896953344") #Become a someone
                    if role != None:
                        await client.replace_roles(dMem, role)
                    if altRole != None:
                        await client.replace_roles(dMem, altRole)
            except:
                print("Could not edit roles")
            return

    # Update guildie
    async def updateGuildie(self, dName, bName, message, server = None):
        client = self.client
        await client.send_typing(message.channel)
        if server == None:
            server = self.server
        print(dName)
        print(bName)

        dMem = server.get_member_named(dName)
        memID = ''
        if dMem != None:
            memID = dMem.id
        
        lst = (memID, dName.split('#')[0], dName.split('#')[1], bName)
        mem = Member(lst)
        if self.db.updateGuildie(mem, message.author.id) > 0:
            await client.send_message(message.channel, Guild.cssMessage("Updated member to the following:\n\tDiscord: [" + dName + "]\n\tBDO Family: [" + bName + "]"))
            return

        await client.send_message(message.channel, Guild.cssMessage("No matching member found in database for:\n\tDiscord: [" + dName + "]\n\tBDO Family: [" + bName + "]"))

    async def updateGuildieDiscord(self, bName, dMem, message):
        if not self.db.containsFamily(bName):
            await self.client.send_message(message.channel, Guild.cssMessage('No member found with the family [' + bName + ']. Cancelling operation'))
            return
        lst = (dMem.id, dMem.name, dMem.discriminator, bName)
        mem = Member(lst)
        if self.db.updateDiscord(mem, message.author.id) > 0:
            await self.client.send_message(message.channel, Guild.cssMessage('Updated Discord successfully to [' + str(dMem) + ']'))
        else:
            await self.client.send_message(message.channel, Guild.cssMessage('Somehow nothing happened. That was weird. Hopefully sarge fixes this at somepoint'))

    # Search for a member in discord and bdo family
    async def searchMembers(self, search, message, server = None, group = member.MEMBERS, alt = False):
        client = self.client
        if server == None:
            server = self.server
        print("Searching for guildie through both discord and bdo")
        await client.send_typing(message.channel)

        # In case given discriminator
        search = search.split("#")[0]

        # Get current discord names
        discordMembers = {}
        nicks = {}
        for m in server.members:
            discordMembers[str(m)] = m
            if m.nick != None:
                nicks[m.nick.upper()] = m

        # Get database members
        dbMembers = None
        if group == member.MEMBERS:
            print('Looking for a current member')
            dbMembers = self.db.members
        else:
            print('Looking for an alumni')
            dbMembers = self.db.alumni

        # Get db familys
        bdoMembers = []
        for mem in dbMembers:
            bdoMembers.append(mem.account.upper())

        disMatches = []
        # Check for any matches for the name in discord
        discordMatches = get_close_matches(search.upper(), (x.split("#")[0].upper() for x in list(discordMembers.keys())))
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

        # Begin output message
        msg = "Results for  [" + search + "]:"
        resultFound = False

        # Search database against matches
        for mem in dbMembers:
            if mem.id in disMatches or mem.account.upper() in bdoMatches or (mem.shortDiscord != None and mem.shortDiscord.upper() in discordMatches):
                resultFound = True
                msg += "\n\n--------------------------------------------"
                if alt:
                    # Get discord name
                    disMem = server.get_member(mem.id)
                    disPrint = mem.discord if mem.discord != None else ''
                    if disMem != None:
                        disPrint = disMem.name + "#" + disMem.discriminator

                    msg += "\n" + disPrint + " [" + mem.account + "]"
                else:
                    m = server.get_member(mem.id)
                    memberDiscord = mem.discord
                    if m != None:
                        memberDiscord = str(m)
                    elif memberDiscord == "" or memberDiscord == None:
                        memberDiscord = "NO_DISCORD_NAME_FOUND"
                    msg += "\nDiscord:      [" + memberDiscord + "]\n" + "BDO Family:   [" + mem.account + "]"
                    if m != None and m.nick != None:
                        msg += "\nNickname:     [" + m.nick + "]"
                    #msg += "\nAdded By:     [" + mem.addedBy + "]"
                    #msg += "\nDate Added:   [" + mem.dateAdded + "]"
                    #if group == member.ALUMNI:
                    #    msg += "\nRemoved By:   [" + mem.removedBy + "]"
                    #    msg += "\nDate Removed: [" + mem.dateRemoved + "]"
                msg += "\n--------------------------------------------"

        # Final messages
        if resultFound:            
            print(msg)
            await client.send_message(message.channel, Guild.cssMessage(msg))
        else:
            print("[" + search + "] was not found")
            await client.send_message(message.channel, Guild.cssMessage("[" + search + "] was not found"))

    # Get a list of current guild members!
    async def getGuildList(self, message, server = None):
        if server == None:
            server = self.server
        print("Getting list of guild members!")
        await self.client.send_typing(message.channel)
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
            elif disPrint == "":
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
        await self.client.send_file(message.channel, dir_path + "/guildList.txt")

    # Gets the discrepencies in guild members
    async def getDiscordMissing(self, message, server = None):
        await self.client.send_typing(message.channel)
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
            if not mem in dNameMembers:
                discordMissing.append(mem)

        # Compare bdo members against hooligans
        bdoMissing = []
        for mem in dNameMembers:
            if not mem in hooligans:
                bdoMissing.append(mem)

        if len(discordMissing) > 0:
            msg = ''
            for mem in discordMissing:
                msg += mem + '\r\n'
            print("Writing")
            with io.open(dir_path + "/guildDiscordMissing.txt", "w", encoding="utf-8") as f:
                f.write(msg)
            await self.client.send_message(message.channel, Guild.cssMessage("The following members were found in discord as part of the guild but not in BDO:\n\n" + msg))
        if len(bdoMissing) > 0:
            msg = ''
            for mem in bdoMissing:
                name = mem
                if name == "":
                    name = "NO_DISCORD_NAME_FOUND"
                msg += name + '\r\n'
                account = ''
                for a, d in dNameMembers:
                    if d == mem:
                        account = a
                        break

                msg += '\t\tFamily Name: ' + account + '\r\n'
            print("Writing")
            with io.open(dir_path + "/guildBdoMissing.txt", "w", encoding="utf-8") as f:
                f.write(msg)
            await self.client.send_message(message.channel, Guild.cssMessage("The following members were found in BDO as part of the guild but are not a Hooligan:\n\n" + msg))
        if len(bdoMissing) == 0 and len(discordMissing) == 0:
            await self.client.send_message(message.channel, Guild.cssMessage("All members accounted for!"))
        return
    
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
    def isValidUser(user):
        for role in Guild.AUTHORIZED_ROLES:
            if role in [r.id for r in user.roles]:
                return True
        return False