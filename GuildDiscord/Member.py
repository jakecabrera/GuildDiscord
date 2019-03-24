import re
import os
import io
import collections
import time
import fileinput
from pathlib import Path
from difflib import get_close_matches
from datetime import datetime

class Member:
    def __init__(self, dbMem):
        self.discord = dbMem['Discord']
        self.shortDiscord = self.discord.split("#")[0]
        self.accounts = list(dbMem['Accounts'].values())
        self.addedBy = dbMem['AddedBy']
        self.dateAddedNumeric = dbMem['DateAdded'] / 1000
        self.dateAdded = datetime.fromtimestamp(self.dateAddedNumeric).strftime('%Y-%m-%d')
        if 'DateRemoved' in dbMem:
            self.dateRemovedNumeric = dbMem['DateRemoved'] / 1000
            self.dateRemoved = datetime.fromtimestamp(self.dateRemovedNumeric).strftime('%Y-%m-%d')
            self.removedBy = dbMem['RemovedBy']
        else:
            self.dateRemovedNumeric = None
            self.dateRemoved = None
            self.removedBy = None
    
    def hasAccount(self, account):
        return account.upper() in (x.upper() for x in self.accounts)