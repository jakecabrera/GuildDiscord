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

    def __init__(self, dbMem):
        self.discord = dbMem[DISCORD]
        self.shortDiscord = self.discord.split("#")[0]
        self.accounts = list(dbMem[ACCOUNTS].values())
        self.addedBy = dbMem[ADDEDBY]
        self.dateAddedNumeric = dbMem[DATE_ADDED] / 1000
        self.dateAdded = datetime.fromtimestamp(self.dateAddedNumeric).strftime('%Y-%m-%d')
        self.id = dbMem[DISCORD_ID]
        if DATE_REMOVED in dbMem:
            self.dateRemovedNumeric = dbMem[DATE_REMOVED] / 1000
            self.dateRemoved = datetime.fromtimestamp(self.dateRemovedNumeric).strftime('%Y-%m-%d')
            self.removedBy = dbMem[REMOVED_BY]
            self.timesRemoved = dbMem[TIMES_REMOVED]
        else:
            self.dateRemovedNumeric = None
            self.dateRemoved = None
            self.removedBy = None
    
    def hasAccount(self, account):
        return account.upper() in (x.upper() for x in self.accounts)