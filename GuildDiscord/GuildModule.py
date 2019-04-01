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
import MemberModule

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
        closeRef = ref.child(MemberModule.MEMBERS)
        dMem = server.get_member_named(dName)
        if dMem == None:
            await client.send_message(message.channel, cssMessage("#Warning: No user found by name of [" + dName + "] in this server"))
        for key, val in ref.child(MemberModule.MEMBERS).get().items():
            member = Member(val)
            if member.hasAccount(bName):
                print("Member already exists")
                await client.send_message(message.channel, cssMessage("Member already exists with that Family name"))
                return
            elif (dName != "" and member.discord == dName):
                closeRef.child(key).child(MemberModule.ACCOUNTS).push(bName)
                await client.send_message(message.channel, cssMessage("Member already exists with that Discord name." +
                                                         "\nAppending to [" + member.discord + "] as an alternate account"))
                return
        member = closeRef.push()
        member.child(MemberModule.DISCORD).set(dName)
        member.child(MemberModule.ACCOUNTS).push(bName)
        member.child(MemberModule.ADDEDBY).set(adder)
        memID = ''
        if dMem != None:
            memID = dMem.id
        member.child(MemberModule.DISCORD_ID).set(memID)
        member.child(MemberModule.DATE_ADDED).set({".sv": "timestamp"})
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
        for key, val in ref.child(MemberModule.MEMBERS).get().items():
            member = Member(val)
            if member.hasAccount(bName):
                oldDiscord = member.discord
                ref.child(MemberModule.MEMBERS).child(key).update({MemberModule.DISCORD: dName})
                updatedSomeone = True
                await client.send_message(message.channel, cssMessage("Updated [" + bName + "] Discord name from [" + oldDiscord + "] to [" + dName + "]"))
            elif member.discord == dName and member.discord != "":
                if len(member.accounts) == 1:
                    oldName = member.accounts[0]
                    ref.child(MemberModule.MEMBERS).child(key).child(MemberModule.ACCOUNTS).child(list(ref.child(MemberModule.MEMBERS).child(key).child(MemberModule.ACCOUNTS).get().keys()).pop()).set(bName)
                    updatedSomeone = True
                    await client.send_message(message.channel, cssMessage("Updated [" + dName + "] BDO family name from [" + oldName + "] to [" + bName + "]"))
                else:
                    msg = "[" + member.discord + "] has more than one account.\n Which account would you like to update?\n\n"
                    i = 1
                    for account in member.accounts:
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
                            for id, acc in val[MemberModule.ACCOUNTS].items():
                                if acc == member.accounts[choice]:
                                    oldName = member.accounts[choice]
                                    ref.child(MemberModule.MEMBERS).child(key).child(MemberModule.ACCOUNTS).child(id).set(bName)
                                    updatedSomeone = True
                                    await client.send_message(message.channel, cssMessage("Updated [" + dName + "] BDO family name from [" + oldName + "] to [" + bName + "]"))
                                    valid = True
                        except:
                            await client.send_message(message.channel, cssMessage("Please reply with only a number matching one of the options."))
            if updatedSomeone:
                return
        await client.send_message(message.channel, cssMessage("No matching member found in database for:\n\tDiscord: [" + dName + "]\n\tBDO Family: [" + bName + "]"))

    # Search for a member in discord and bdo family
    async def searchMembers(self, search, message, server = None, group = MemberModule.MEMBERS, alt = False):
        client = self.client
        ref = self.ref
        if server == None:
            server = self.server
        print("Searching for guildie through both discord and bdo")
        server = risenServer
        await client.send_typing(message.channel)

        # In case given discriminator
        search = search.split("#")[0]

        # Get current discord names
        discordMembers = {}
        nicks = {}
        for mem in server.members:
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
                    mem = server.get_member(member.id)
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
        members = ref.child(MemberModule.MEMBERS).get()
        guildList = {}
        msg = ""
        for id, m in members.items():
            member = Member(m)
            info = [member.discord]
            dName = server.get_member(member.id)
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
        await client.send_file(message.channel, dir_path + "/guildList.txt")

    # Gets the discrepencies in guild members
    async def getDiscordMissing(self, message, server = None):
        client = self.client
        ref = self.ref
        await client.send_typing(message.channel)
        if server == None:
            server = self.server
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
        for member in server.members:
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
            await client.send_message(message.channel, cssMessage("The following members were found in discord as part of the guild but not in BDO:\n\n" + msg))
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
            await client.send_message(message.channel, cssMessage("The following members were found in BDO as part of the guild but are not a Hooligan:\n\n" + msg))
        if len(bdoMissing) == 0 and len(discordMissing) == 0:
            await client.send_message(message.channel, cssMessage("All members accounted for!"))