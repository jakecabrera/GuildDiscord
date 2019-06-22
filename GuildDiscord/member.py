import re
import os
import io
import collections
import time
import fileinput
from pathlib import Path
from difflib import get_close_matches
from datetime import datetime

ACCOUNTS = 'Accounts'
ADDEDBY = 'AddedBy'
ALUMNI = 'Alumni'
DATE_ADDED = 'DateAdded'
DATE_REMOVED = 'DateRemoved'
DISCORD = 'Discord'
DISCORD_ID = 'DiscordID'
MEMBERS = 'Members'
REMOVED_BY = 'RemovedBy'
TIMES_REMOVED = 'TimesRemoved'

class Member:
    def __init__(self, x):
        if x[0] != None:
            self.id = x[0]
        else:
            self.id = None
        if x[1] != None and x[2] != None:
            self.discord = x[1] + '#' + x[2]
            self.shortDiscord = x[1]
        else:
            self.discord = None
            self.shortDiscord = None
        self.account = x[3]
    
    def hasAccount(self, account):
        return account.upper() in (x.upper() for x in self.accounts)

    # Converts a discord member to a risen member
    def m2m(mem, account):
        id = mem.id
        discordName = mem.name
        discriminator = mem.discriminator
        return Member([id, discordName, discriminator, account])