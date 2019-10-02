import database
import discord
import math
from guild import Guild

class SAR(object):
    def __init__(self, db, guild):
        self.groups = db.getSARgroups()
        self.page = 1
        self.guild = guild
        self.pageLimit = 10

    async def pickGroup(self, message, client):
        self.page = 1

        # Build choice message
        msg = "Pick a group you want to assign or unassign roles from.\n"
        choice = "[Page " + str(self.page) + "/" + str(math.ceil(len(self.groups)/self.pageLimit)) + "]\n\n"
        optionCount = 1
        groupsList = list(self.groups.keys())
        for group in groupsList:
            choice += str(optionCount) + " : " + group + "\n"
            optionCount += 1
        choice += "c : Cancel"
        def check(m):
            return m.channel == message.channel and m.author == message.author
        await message.channel.send(msg + Guild.cssMessage(choice))
        print(msg + Guild.cssMessage(choice))
        response = await client.wait_for('message', check=check, timeout = 60.0)

        # Get response
        if response.content == 'c': self.cancel()
        else: await self.pickRole(message, client, self.groups[groupsList[int(response.content) - 1]])
        return

    async def pickRole(self, message, client, group):
        self.page = 1

        # Build choice message
        msg = "Pick a role you want to assign or unassign from yourself.\n"
        choice = "[Page " + str(self.page) + "/" + str(math.ceil(len(group)/self.pageLimit)) + "]\n\n"
        optionCount = 1
        rolesList = list(group.keys())
        for role in rolesList:
            choice += str(optionCount) + " : " + role + "\n"
            optionCount += 1
        choice += "c : Cancel"
        def check(m):
            return m.channel == message.channel and m.author == message.author
        await message.channel.send(msg + Guild.cssMessage(choice))
        response = await client.wait_for('message', check=check, timeout = 60.0)

        # Get response
        if response.content == 'c': self.cancel()
        else: await self.applyRole(message, client, group[rolesList[int(response.content) - 1]])
        return

    def cancel(self):
        return

    async def applyRole(self, message, client, role):
        roleToAdd = discord.utils.get(self.guild.roles, id=int(role))
        removedRole = False
        user = self.guild.get_member_named(str(message.author))
        if roleToAdd in user.roles:
            removedRole = True
            await user.remove_roles(roleToAdd)
        else: await user.add_roles(roleToAdd)
        msg = roleToAdd.name + " has been "
        if removedRole: msg += "removed"
        else: msg += "added"
        await message.channel.send(msg)
        return

    def currentPage(self, message, list):
        return

    def nextPage(self, message):
        return

    def prevPage(self, message):
        return

