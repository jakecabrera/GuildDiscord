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

import mysql.connector

ACCOUNTS = "Accounts"
ADDEDBY = "AddedBy"
ALUMNI = "Alumni"
DATE_ADDED = "DateAdded"
DATE_REMOVED = "DateRemoved"
DISCORD = "Discord"
DISCORD_ID = "DiscordID"
MEMBERS = "Members"
REMOVED_BY = "RemovedBy"
TIMES_REMOVED = "TimesRemoved"

class Database(object):
    def __init__(self):
        #dir_path = os.path.dirname(os.path.realpath(__file__))
        #creds = {}
        #with open(dir_path + "/dbcred") as f:
        #    creds = f.readlines()
        self.mydb = mysql.connector.connect(
            host="localhost",
            user="risenuser",
            passwd="risenuser",
            database="risen",
            charset="utf8mb4"
            )

        c = self.mydb.cursor(buffered=True)

        c.execute("SELECT D_ID, D_NAME, D_DISCRIMINATOR, G_FAMILY FROM MEMBERS;")
        result = c.fetchall()
        self.members = list(Member(x) for x in result)
        
        c.execute("SELECT D_ID, D_NAME, D_DISCRIMINATOR, G_FAMILY FROM ALUMNI;")
        result = c.fetchall()
        c.close()
        self.alumni = list(Member(x) for x in result)

    def containsFamily(self, family):
        print("checking for family in db")
        for m in self.members:
            if m.account == family:
                return True
        return False

    def containedFamily(self, family):
        for m in self.alumni:
            if m.account == family:
                return True
        return False

    def reinstateGuildie(self, mem, operatorID):
        c = self.mydb.cursor(buffered=True)
        c.execute("UPDATE GUILDIE SET G_CURRENT_MEMBER = 1 WHERE G_FAMILY = %s;", [mem.account])
        c.close()
        self.documentOperation(mem, operatorID, "ADD")
        self.updateMembers()
        self.updateAlumni()

    def insertGuildie(self, mem, operatorID):
        c = self.mydb.cursor(buffered=True)
        sql = "INSERT IGNORE INTO DISCORD VALUES ("
        sql += mem.id + ","
        sql += "%s,"
        sql += "\"" + mem.discord.split("#")[1] + "\");"
        name = mem.discord.split("#")[0]
        c.execute(sql, [name])

        sql = "INSERT INTO GUILDIE(D_ID, G_FAMILY) VALUES("
        sql += mem.id + ","
        sql += "%s);"
        family = mem.account
        c.execute(sql, [family])
        rowCount = c.rowcount
        c.close()

        self.documentOperation(mem, operatorID, "ADD")
        self.updateMembers()
        return rowCount

    def removeGuildie(self, mem, operatorID):
        c = self.mydb.cursor(buffered=True)

        sql = "UPDATE GUILDIE SET G_CURRENT_MEMBER = FALSE WHERE G_FAMILY = %s;"
        c.execute(sql, [mem.account])
        rowCount = c.rowcount

        self.documentOperation(mem, operatorID, "REMOVE")
        self.updateMembers()
        self.updateAlumni()
        c.close()
        return rowCount

    # Fix update of family
    def updateGuildie(self, mem, operatorID):
        c = self.mydb.cursor(buffered=True)

        if self.containsFamily(mem.account):
            # We are updating discord
            
            # First check if the member is attached to a discord account
            sql = "SELECT D_ID FROM GUILDIE WHERE G_FAMILY = \"" + mem.account + "\";"
            c.execute(sql)
            print("looking for discord")
            if c.rowcount > 0:

                print("found")
                result = c.fetchone()
                if result == None and mem.id != None:
                    sql = "INSERT IGNORE INTO DISCORD(D_ID, D_NAME, D_DISCRIMINATOR) VALUES("
                    sql += mem.id + ","
                    sql += "%s,"
                    sql += "\"" + mem.discord.split("#")[1] + "\");"
                    dName = mem.shortDiscord
                print(result[0])

            #sql = "UPDATE GUILDIE SET D_ID = " + id + " WHERE G_FAMILY = \"" + mem.account + "\";"
            #c.execute()
        #else:
            # We are updating family name
            # sql = "UPDATE GUILDIE SET G_FAMILY = \"" + mem.account + "\" WHERE D_ID = " + id + ";"
            # c.execute()


        rowCount = c.rowcount

        #self.documentOperation(mem, operatorID, "UPDATE")
        #self.updateMembers()
        c.close()
        return rowCount

    def updateDiscord(self, mem, operatorID):
        c = self.mydb.cursor(buffered=True)

        sql = "SELECT * FROM DISCORD WHERE D_ID = " + mem.id + ";"
        c.execute(sql)
        result = c.fetchall()
        rowCount = 0
        if len(result) == 0:
            # Enter new discord too
            sql = "INSERT INTO DISCORD VALUES ("
            sql += mem.id + ","
            sql += "%s,"
            sql += "\"" + mem.discord.split("#")[1] + "\");"
            dName = mem.shortDiscord
            c.execute(sql, [dName])
            rowCount += c.rowcount
        else:
            # Enter new discord too
            sql = "UPDATE DISCORD SET D_NAME = %s, D_DISCRIMINATOR = %s WHERE D_ID = " + mem.id + ";"
            c.execute(sql, [mem.shortDiscord, mem.discord.split('#')[1]])
            rowCount += c.rowcount
        
        sql = "UPDATE GUILDIE SET D_ID = " + mem.id + " WHERE G_FAMILY = %s;"
        family = mem.account
        c.execute(sql, [family])
        rowCount += c.rowcount

        self.documentOperation(mem, operatorID, "UPDATE")
        self.updateMembers()
        c.close()
        return rowCount

    def documentOperation(self, mem, operatorID, operation):
        c = self.mydb.cursor(buffered=True)
        sql = "INSERT INTO ADD_AND_REMOVE(G_ID, OPERATION, OPERATOR) VALUES ("
        sql += "(SELECT G_ID FROM GUILDIE WHERE G_FAMILY = \"" + mem.account + "\" LIMIT 1),"
        sql += "\"" + operation + "\","
        sql += "\"" + operatorID + "\");"
        c.execute(sql)
        c.close()
        self.mydb.commit()

    def updateMembers(self):
        c = self.mydb.cursor(buffered=True)

        c.execute("SELECT D_ID, D_NAME, D_DISCRIMINATOR, G_FAMILY FROM MEMBERS;")
        result = c.fetchall()
        c.close()
        self.members = list(Member(x) for x in result)
        
    def updateAlumni(self):
        c = self.mydb.cursor(buffered=True)

        c.execute("SELECT D_ID, D_NAME, D_DISCRIMINATOR, G_FAMILY FROM ALUMNI;")
        result = c.fetchall()
        c.close()
        self.alumni = list(Member(x) for x in result)

    def refresh(self):
        self.updateMembers()
        self.updateAlumni()