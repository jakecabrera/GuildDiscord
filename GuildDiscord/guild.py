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

import discord
import member
from member import Member

dir_path = os.path.dirname(os.path.realpath(__file__))

AUTHORIZED_CHANNELS = {
    "259049604627169291", # Private test channel
    "517203484467134484" # ops channel
    }

DATABASE_CHANNELS = {
    "474242123143577610", # Add-and-remove
    "259049604627169291" # Private test channel
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

class Guild:
    def __init__(self, client, ref, server):
        self.server = server
        self.client = client
        self.ref = ref

    # Adds an entry to the database
    async def addGuildie(self, dName, bName, adder, message, server = None):
        ref = self.ref
        client = self.client
        if server == None:
            server = self.server
        dName = dName.replace('@', '')
        closeRef = ref.child(member.MEMBERS)
        dMem = server.get_member_named(dName)
        if dMem == None:
            await client.send_message(message.channel, cssMessage("#Warning: No user found by name of [" + dName + "] in this server"))
        for key, val in ref.child(member.MEMBERS).get().items():
            member = Member(val)
            if member.hasAccount(bName):
                print("Member already exists")
                await client.send_message(message.channel, cssMessage("Member already exists with that Family name"))
                return
            elif (dName != "" and member.discord == dName):
                closeRef.child(key).child(member.ACCOUNTS).push(bName)
                await client.send_message(message.channel, cssMessage("Member already exists with that Discord name." +
                                                         "\nAppending to [" + member.discord + "] as an alternate account"))
                return
        member = closeRef.push()
        member.child(member.DISCORD).set(dName)
        member.child(member.ACCOUNTS).push(bName)
        member.child(member.ADDEDBY).set(adder)
        memID = ''
        if dMem != None:
            memID = dMem.id
        member.child(member.DISCORD_ID).set(memID)
        member.child(member.DATE_ADDED).set({".sv": "timestamp"})
        print("Added dName: [" + dName + "]\t[" + bName + "]")
        await client.send_message(message.channel, cssMessage(" Added Discord: [" + dName + "]\n\tBdo Family: [" + bName + "]"))

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
        ref = self.ref
        if server == None:
            server = self.server
        if dName == None:
            dName = ""
        dName = dName.replace('@', '')
        removedSomeone = False
        for key, val in ref.child(member.MEMBERS).get().items():
            member = Member(val)
            if member.hasAccount(bName) or (dName != "" and member.discord.upper() == dName.upper()):
                print("Removing [" + bName + "] = [" + member.discord + "]")
                dName = member.discord
                bNames = member.accounts
                ref.child(member.ALUMNI).child(key).set(ref.child('Members').child(key).get())
                ref.child(member.ALUMNI).child(key).child('RemovedBy').set(remover)    
                ref.child(member.ALUMNI).child(key).child("DateRemoved").set({".sv": "timestamp"})
                ref.child(member.MEMBERS).child(key).delete()
                removedSomeone = True
                removeMsg = "Removed Discord: [" + dName + "]\n\t BDO Family: [" + bNames.pop() + "]"
                for n in bNames:
                    removeMsg += "\n\t             [" + n + "]"
                await client.send_message(message.channel, cssMessage(removeMsg))
            if removedSomeone:
                break
        if not removedSomeone:
            await client.send_message(message.channel, cssMessage("No matching member found in database for:\n\tDiscord:    [" + dName + "]\n\tBDO Family: [" + bName + "]"))
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
        ref = self.ref
        if server == None:
            server = self.server
        print(dName)
        print(bName)
        updatedSomeone = False
        for key, val in ref.child(member.MEMBERS).get().items():
            mem = Member(val)
            if mem.hasAccount(bName):
                oldDiscord = mem.discord
                ref.child(member.MEMBERS).child(key).update({member.DISCORD: dName})
                updatedSomeone = True
                await client.send_message(message.channel, cssMessage("Updated [" + bName + "] Discord name from [" + oldDiscord + "] to [" + dName + "]"))
            elif mem.discord == dName and mem.discord != "":
                if len(mem.accounts) == 1:
                    oldName = mem.accounts[0]
                    ref.child(member.MEMBERS).child(key).child(member.ACCOUNTS).child(list(ref.child(member.MEMBERS).child(key).child(member.ACCOUNTS).get().keys()).pop()).set(bName)
                    updatedSomeone = True
                    await client.send_message(message.channel, cssMessage("Updated [" + dName + "] BDO family name from [" + oldName + "] to [" + bName + "]"))
                else:
                    msg = "[" + mem.discord + "] has more than one account.\n Which account would you like to update?\n\n"
                    i = 1
                    for account in mem.accounts:
                        msg += str(i) + ".)\t " + account + "\n"
                        i += 1
                    msg += "99.)\tCancel\n\n Please reply with the number of your choice."
                    await client.send_message(message.channel, cssMessage(msg))
                    valid = False
                    def check(m):
                        return not (m.content.startswith(prefix) or m.content.startswith("<"))
                    while not valid:
                        reply = await client.wait_for_message(author=message.author, channel=message.channel, check=check)
                        if reply == None:
                            await client.send_message(message.channel, cssMessage("Cancelling update operation."))
                            return
                        try:
                            choice = int(reply.content)
                            if choice == 99:
                                await client.send_message(message.channel, cssMessage("Cancelling update operation."))
                                return
                            choice -= 1
                            for id, acc in val[member.ACCOUNTS].items():
                                if acc == mem.accounts[choice]:
                                    oldName = mem.accounts[choice]
                                    ref.child(member.MEMBERS).child(key).child(member.ACCOUNTS).child(id).set(bName)
                                    updatedSomeone = True
                                    await client.send_message(message.channel, cssMessage("Updated [" + dName + "] BDO family name from [" + oldName + "] to [" + bName + "]"))
                                    valid = True
                        except:
                            await client.send_message(message.channel, cssMessage("Please reply with only a number matching one of the options."))
            if updatedSomeone:
                return
        await client.send_message(message.channel, cssMessage("No matching member found in database for:\n\tDiscord: [" + dName + "]\n\tBDO Family: [" + bName + "]"))

    # Search for a member in discord and bdo family
    async def searchMembers(self, search, message, server = None, group = member.MEMBERS, alt = False):
        client = self.client
        ref = self.ref
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
            discordMembers[m.name.upper() + "#" + m.discriminator] = m
            if m.nick != None:
                nicks[m.nick.upper()] = m

        # Get database members
        dbMembers = ref.child(group).get()
        bdoMembers = []
        for key, val in dbMembers.items():
            mem = Member(val)
            bdoMembers += (x.upper() for x in mem.accounts)

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

        # Begin output message
        msg = "Results for  [" + search + "]:"
        resultFound = False

        # Search database against matches
        for key, val in dbMembers.items():
            mem = Member(val)
            upperAccounts = (x.upper() for x in mem.accounts)
            matchedAccounts = set(upperAccounts) & set(bdoMatches)
            if mem.id in disMatches or matchedAccounts or mem.shortDiscord.upper() in discordMatches:
                resultFound = True
                msg += "\n\n--------------------------------------------"
                if alt:
                    # Get discord name
                    disMem = server.get_member(mem.id)
                    disPrint = mem.discord
                    if disMem != None:
                        disPrint = disMem.name + "#" + disMem.discriminator

                    # Get account to print
                    if len(matchedAccounts) > 0:
                        for match in matchedAccounts:
                            matchedAccount = ""
                            for a in mem.accounts:
                                if a.upper() == match:
                                    matchedAccount = a
                            msg += "\n" + disPrint + " [" + matchedAccount + "]"

                    # If no accounts matched and we are here, that means it was the discord that matched.
                    # Print all the accounts for that discord
                    else:
                        for account in mem.accounts:
                            msg += "\n" + disPrint + " [" + account + "]"
                else:
                    accounts = mem.accounts
                    m = server.get_member(mem.id)
                    memberDiscord = mem.discord
                    if m != None:
                        memberDiscord = m.name + '#' + m.discriminator
                    elif memberDiscord == "":
                        memberDiscord = "NO_DISCORD_NAME_FOUND"
                    msg += "\nDiscord:      [" + memberDiscord + "]\n" + "BDO Family:   [" + accounts.pop() + "]"
                    for match in accounts:
                        msg += "\n              [" + match + "]"
                    if m != None and m.nick != None:
                        msg += "\nNickname:     [" + m.nick + "]"
                    msg += "\nAdded By:     [" + mem.addedBy + "]"
                    msg += "\nDate Added:   [" + mem.dateAdded + "]"
                    if group == member.ALUMNI:
                        msg += "\nRemoved By:   [" + mem.removedBy + "]"
                        msg += "\nDate Removed: [" + mem.dateRemoved + "]"
                msg += "\n--------------------------------------------"

        # Final messages
        if resultFound:            
            print(msg)
            await client.send_message(message.channel, cssMessage(msg))
        else:
            print("[" + search + "] was not found")
            await client.send_message(message.channel, cssMessage("[" + search + "] was not found"))

    # Get a list of current guild members!
    async def getGuildList(self, message, server = None):
        client = self.client
        ref = self.ref
        if server == None:
            server = self.server
        print("Getting list of guild members!")
        await client.send_typing(message.channel)
        members = ref.child(member.MEMBERS).get()
        guildList = {}
        msg = ""
        for id, m in members.items():
            mem = Member(m)
            disPrint = mem.discord
            nickPrint = ""
            dName = server.get_member(mem.id)
            if dName != None: 
                disPrint = dName.name + "#" + dName.discriminator
                if dName.nick != None:
                    nickPrint = dName.nick
            elif disPrint == "":
                disPrint = "NO_DISCORD_NAME_FOUND"

            info = [disPrint]
            if nickPrint != "":
                info.append(nickPrint)

            for account in mem.accounts:
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
        await client.send_file(message.channel, dir_path + "/guildList.txt")

    # Gets the discrepencies in guild members
    async def getDiscordMissing(self, message, server = None):
        client = self.client
        ref = self.ref
        await client.send_typing(message.channel)
        if server == None:
            server = self.server
        members = ref.child(member.MEMBERS).get()

        # Get all bdo members from firebase
        dNameMembers = {}
        print("Getting firbase members")
        for id, m in members.items():
            mem = Member(m)
            dNameMembers[mem.discord] = mem.accounts

        # Get all hooligans from discord
        hooligans = []
        print("getting discord members")
        for mem in server.members:
            isGuildMember = False
            for mRole in mem.roles:
                if isGuildRole(mRole):
                    isGuildMember = True
            if isGuildMember:
                hooligans.append(mem.name + '#' + mem.discriminator)

        # Compare hooligans against the bdo members
        discordMissing = []
        print("Comparing")
        for mem in hooligans:
            if not mem in dNameMembers:
                discordMissing.append(mem)

        # Compare bdo members against hooligans
        bdoMissing = []
        for mem in dNameMembers.keys():
            if not mem in hooligans:
                bdoMissing.append(mem)

        if len(discordMissing) > 0:
            msg = ''
            for mem in discordMissing:
                msg += mem + '\r\n'
            print("Writing")
            with io.open(dir_path + "/guildDiscordMissing.txt", "w", encoding="utf-8") as f:
                f.write(msg)
            await client.send_message(message.channel, cssMessage("The following members were found in discord as part of the guild but not in BDO:\n\n" + msg))
        if len(bdoMissing) > 0:
            msg = ''
            for mem in bdoMissing:
                name = mem
                if name == "":
                    name = "NO_DISCORD_NAME_FOUND"
                msg += name + '\r\n'
                accounts = dNameMembers[mem]
                msg += '\t\tFamily Name: ' + accounts.pop() + '\r\n'
                for account in accounts:
                    msg += '\t\t             ' + account + '\r\n'
            print("Writing")
            with io.open(dir_path + "/guildBdoMissing.txt", "w", encoding="utf-8") as f:
                f.write(msg)
            await client.send_message(message.channel, cssMessage("The following members were found in BDO as part of the guild but are not a Hooligan:\n\n" + msg))
        if len(bdoMissing) == 0 and len(discordMissing) == 0:
            await client.send_message(message.channel, cssMessage("All members accounted for!"))
        return

# returns a string that is styled in css way for discord
def cssMessage(msg):
    return "```CSS\n" + msg + "\n```"

# returns whether the given channel is an authorized channel or not
def isAuthorizedChannel(ch):
    return ch.id in AUTHORIZED_CHANNELS

# Returns whether the given channel is a database channel or not
def isDatabaseChannel(ch):
    return ch.id in DATABASE_CHANNELS

# Returns whether the given role is a role that guild members would have
def isGuildRole(role):
    return role.id in GUILD_ROLES

# Returns whether the given user is a valid user for secret commands
def isValidUser(user):
    for role in AUTHORIZED_ROLES:
        if role in [r.id for r in user.roles]:
            return True
    return False