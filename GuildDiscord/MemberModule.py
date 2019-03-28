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
DATEADDED = 'DateAdded'
DATEREMOVED = 'DateRemoved'
DISCORD = 'Discord'
DISCORDID = 'DiscordID'
MEMBERS = 'Members'
REMOVEDBY = 'RemovedBy'

class Member:
    ACCOUNTS = 'Accounts'
    ADDEDBY = 'AddedBy'
    ALUMNI = 'Alumni'
    DATEADDED = 'DateAdded'
    DATEREMOVED = 'DateRemoved'
    DISCORD = 'Discord'
    DISCORDID = 'DiscordID'
    MEMBERS = 'Members'
    REMOVEDBY = 'RemovedBy'

    def __init__(self, dbMem):
        self.discord = dbMem[DISCORD]
        self.shortDiscord = self.discord.split("#")[0]
        self.accounts = list(dbMem[ACCOUNTS].values())
        self.addedBy = dbMem[ADDEDBY]
        self.dateAddedNumeric = dbMem[DATEADDED] / 1000
        self.dateAdded = datetime.fromtimestamp(self.dateAddedNumeric).strftime('%Y-%m-%d')
        self.id = dbMem[DISCORDID]
        if DATEREMOVED in dbMem:
            self.dateRemovedNumeric = dbMem[DATEREMOVED] / 1000
            self.dateRemoved = datetime.fromtimestamp(self.dateRemovedNumeric).strftime('%Y-%m-%d')
            self.removedBy = dbMem[REMOVEDBY]
        else:
            self.dateRemovedNumeric = None
            self.dateRemoved = None
            self.removedBy = None
    
    def hasAccount(self, account):
        return account.upper() in (x.upper() for x in self.accounts)