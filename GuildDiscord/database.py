import re
import os
import io
import collections
import time
import fileinput
from pathlib import Path
from difflib import get_close_matches
from datetime import datetime

import firebase_admin
from member import Member

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

class Database(object):
    def __init__(self, ref):
        #dir_path = os.path.dirname(os.path.realpath(__file__))
        #cred = firebase_admin.credentials.Certificate(dir_path + '/risen-59032-ffc0d0af3cc4.json')
        #default_app = firebase_admin.initialize_app(cred, {'databaseURL': 'https://risen-59032.firebaseio.com/'})
        self.reference = ref #firebase_admin.db.reference('Guild')
        self.members = {k: Member(x) for k, x in ref.child(MEMBERS).get().items()}
        self.alumni = {k: Member(x) for k, x in ref.child(ALUMNI).get().items()}

    @property
    def members(self):
        return self.__members.values()

    @members.setter
    def members(self, members):
        self.__members = members

    @property
    def alumni(self):
        return self.__alumni.values()

    @alumni.setter
    def alumni(self, alumni):
        self.__alumni = alumni

    def listenerCallback(event):
        assert isinstance(event, firebase_admin.db.Event)
        print("Event!")
        return