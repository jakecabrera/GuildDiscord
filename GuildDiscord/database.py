import re
import os
import io
import collections
import time
import fileinput
import pyodbc
from pathlib import Path
from difflib import get_close_matches
from datetime import datetime

from member import Member

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
        print('Initializing database object')
        #with open(dir_path + "/dbcred") as f:
        #    content = f.readlines()
        #    for line in content:
        #        if line != '' or not line.startswith('#'):
        #            creds[line.split('=')[0].strip()] = line.split('=')[1].strip()
        #self.creds = creds

        self.mydb = pyodbc.connect(
            "Driver={SQL Server Native Client 11.0};"
            "Server=localhost;"
            "Database=test;"
            "Trusted_Connection=yes;"
            )

        c = self.cursor()

        c.execute("SELECT D_ID, D_NAME, D_DISCRIMINATOR, G_FAMILY FROM MEMBERS;")
        result = c.fetchall()
        self.members = list(Member(x) for x in result)
        
        c.execute("SELECT D_ID, D_NAME, D_DISCRIMINATOR, G_FAMILY FROM ALUMNI;")
        result = c.fetchall()
        self.alumni = list(Member(x) for x in result)
        print(len(self.alumni))

        c.execute("SELECT M_VALUE FROM MESSAGES WHERE M_NAME = 'HELP_OFFICER'")
        self.__helpMessageOfficer = c.fetchall()[0][0]

        c.execute("SELECT M_VALUE FROM MESSAGES WHERE M_NAME = 'HELP_MAIN\'")
        self.__helpMessageMain = c.fetchall()[0][0]

        c.execute("SELECT M_VALUE FROM MESSAGES WHERE M_NAME = 'HELP_AAR'")
        self.__helpMessageAAR = c.fetchall()[0][0]
        c.close()
    
    @property
    def helpMessageOfficer(self):
        return self.__helpMessageOfficer

    @helpMessageOfficer.setter
    def helpMessageOfficer(self, val):
        c = self.cursor()
        sql = "UPDATE MESSAGES SET M_VALUE = ? WHERE M_NAME = 'HELP_OFFICER';"
        c.execute(sql, [val])
        print('rowcount: ' + str(c.rowcount))
        c.close()
        self.mydb.commit()
        self.mydb.close()
        self.__helpMessageOfficer = val

    @property
    def helpMessageMain(self):
        return self.__helpMessageMain

    @helpMessageMain.setter
    def helpMessageMain(self, val):
        c = self.cursor()
        sql = "UPDATE MESSAGES SET M_VALUE = ? WHERE M_NAME = 'HELP_MAIN';"
        c.execute(sql, [val])
        print('rowcount: ' + str(c.rowcount))
        c.close()
        self.mydb.commit()
        self.mydb.close()
        self.__helpMessageMain = val

    @property
    def helpMessageAAR(self):
        return self.__helpMessageAAR

    @helpMessageAAR.setter
    def helpMessageAAR(self, val):
        c = self.cursor()
        sql = "UPDATE MESSAGES SET M_VALUE = ? WHERE M_NAME = 'HELP_AAR';"
        c.execute(sql, [val])
        print('rowcount: ' + str(c.rowcount))
        c.close()
        self.mydb.commit()
        self.mydb.close()
        self.__helpMessageAAR = val

    def getSARgroups(self): 
        c = self.cursor()
        c.execute("SELECT GROUP_NAME FROM SELF_ASSIGNABLE_ROLES_GROUPS")
        groups = set()
        for result in c.fetchall(): groups.add(result[0])
        c.execute("SELECT ROLE_ID, ROLE_NAME, GROUP_NAME FROM SELF_ASSIGNABLE_ROLES NATURAL JOIN SELF_ASSIGNABLE_ROLES_GROUPS;")
        sars = dict()
        for result in c.fetchall():
            if result[2] in sars:
                sars[result[2]][result[1]] = result[0]
            else:
                sars[result[2]] = dict()
                sars[result[2]][result[1]] = result[0]
        return sars
       
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
        c = self.cursor()
        c.execute("UPDATE GUILDIE SET G_CURRENT_MEMBER = 1 WHERE G_FAMILY = ?;", [mem.account])
        c.close()
        self.documentOperation(mem, operatorID, "ADD")
        self.updateMembers()
        self.updateAlumni()

    def insertGuildie(self, mem, operatorID):
        c = self.cursor()
        sql = ""
        if mem.id != None and mem.id != 0:
            try:
                sql = "INSERT INTO DISCORD VALUES ("
                sql += str(mem.id) + ","
                sql += "?,"
                sql += "\"" + mem.discord.split("#")[1] + "\") "
                name = mem.discord.split("#")[0]
                c.execute(sql, [name])
            except:
                print('Something went wrong with entering discord into db')

            sql = "INSERT INTO GUILDIE(D_ID, G_FAMILY) VALUES("
            sql += str(mem.id) + ","
            sql += "?);"
        else:
            sql = "INSERT INTO GUILDIE(G_FAMILY) VALUES(?);"
        family = mem.account
        c.execute(sql, [family])
        rowCount = c.rowcount
        c.close()

        self.documentOperation(mem, operatorID, "ADD")
        self.updateMembers()
        return rowCount

    def removeGuildie(self, mem, operatorID):
        c = self.cursor()

        sql = "UPDATE GUILDIE SET G_CURRENT_MEMBER = 0 WHERE G_FAMILY = ?;"
        c.execute(sql, [mem.account])
        rowCount = c.rowcount

        self.documentOperation(mem, operatorID, "REMOVE")
        self.updateMembers()
        self.updateAlumni()
        c.close()
        return rowCount

    def updateGreeting(self, server, message):
        c = self.cursor()

        # Make sure server exists
        sql = 'SELECT * FROM SERVER WHERE SERVER_ID = ' + str(server.id) + ';'
        c.execute(sql)
        if c.rowcount == 0:
            sql = 'INSERT IGNORE INTO SERVER(SERVER_ID, SERVER_NAME) VALUES (' + str(server.id) + ',?);'
            c.execute(sql, [server.name])

        # update or add GREETING
        sql = 'SELECT * FROM GREETING WHERE SERVER_ID = ' + str(server.id) + ';'
        c.execute(sql)
        if c.rowcount == 0:
            sql = 'INSERT IGNORE INTO GREETING(SERVER_ID, MESSAGE) VALUES (' + str(server.id) + ',?);'
            c.execute(sql, [message])
        else:
            sql = 'UPDATE GREETING SET MESSAGE = ? WHERE SERVER_ID = ' + str(server.id) + ';'
            c.execute(sql, [message])

        rowCount = c.rowcount
        c.close()
        self.mydb.commit()
        return rowCount

    def retrieveGreeting(self, server):
        sql = 'SELECT MESSAGE, CHANNEL_ID, DELAY FROM GREETING WHERE SERVER_ID = ' + str(server.id) + ';'
        result = self.executeCommit(sql, results = True)
        if result != None and len(result) > 0:
            return result[0]
        else:
            return None

    def updateGreetingChannel(self, channel, server):
        sql = 'UPDATE GREETING SET CHANNEL_ID = ' + str(channel.id) + ' WHERE SERVER_ID = ' + str(server.id) + ';'
        return self.executeCommit(sql)

    def updateGreetingDelay(self, n, server):
        if n > 60 or n < 0:
            return -1
        sql = 'UPDATE GREETING SET DELAY = ' + str(n) + ' WHERE SERVER_ID = ' + str(server.id) + ';'
        return self.executeCommit(sql)

    # Fix update of family
    def updateGuildie(self, mem, operatorID):
        c = self.cursor()

        if self.containsFamily(mem.account):
            # We are updating discord
            
            # First check if the member is attached to a discord account
            sql = "SELECT D_ID FROM GUILDIE WHERE G_FAMILY = \"" + mem.account + "\";"
            c.execute(sql)
            print("looking for discord")
            if c.rowcount > 0:

                print("found")
                result = c.fetchone()
                if result == None and mem.id != None and mem.id != 0:
                    sql = "INSERT IGNORE INTO DISCORD(D_ID, D_NAME, D_DISCRIMINATOR) VALUES("
                    sql += str(mem.id) + ","
                    sql += "?,"
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
        c = self.cursor()

        sql = "SELECT * FROM DISCORD WHERE D_ID = " + str(mem.id) + ";"
        c.execute(sql)
        result = c.fetchall()
        rowCount = 0
        if len(result) == 0:
            # Enter new discord too
            sql = "INSERT INTO DISCORD([D_ID], [D_NAME], [D_DISCRIMINATOR]) VALUES ("
            sql += str(mem.id) + ","
            sql += "?,"
            sql += "'" + mem.discord.split("#")[1] + "');"
            dName = mem.shortDiscord
            c.execute(sql, [dName])
            rowCount += c.rowcount
        else:
            # Enter new discord too
            sql = "UPDATE DISCORD SET D_NAME = ?, D_DISCRIMINATOR = ? WHERE D_ID = " + str(mem.id) + ";"
            c.execute(sql, [mem.shortDiscord, mem.discord.split('#')[1]])
            rowCount += c.rowcount
        
        sql = "UPDATE GUILDIE SET D_ID = " + str(mem.id) + " WHERE G_FAMILY = ?;"
        family = mem.account
        c.execute(sql, [family])
        rowCount += c.rowcount

        self.documentOperation(mem, operatorID, "UPDATE")
        self.updateMembers()
        c.close()
        return rowCount

    def documentOperation(self, mem, operatorID, operation):
        c = self.cursor()
        sql = "INSERT INTO [ADD_AND_REMOVE](G_ID, OPERATION, OPERATOR) VALUES ("
        sql += "(SELECT TOP 1 G_ID FROM GUILDIE WHERE G_FAMILY = '" + mem.account + "'),"
        sql += "'" + operation + "',"
        sql += str(operatorID) + ");"
        c.execute(sql)
        c.close()
        self.mydb.commit()

    def updateMembers(self):
        print("updating members")
        c = self.cursor()
        c.execute("SELECT D_ID, D_NAME, D_DISCRIMINATOR, G_FAMILY FROM MEMBERS;")
        result = c.fetchall()
        c.close()
        print('members before: ' + str(len(self.members)))
        self.members = list(Member(x) for x in result)
        print('members after:  ' + str(len(self.members)))
        
    def updateAlumni(self):
        c = self.cursor()

        c.execute("SELECT D_ID, D_NAME, D_DISCRIMINATOR, G_FAMILY FROM ALUMNI;")
        result = c.fetchall()
        c.close()
        self.alumni = list(Member(x) for x in result)

    def refresh(self):
        self.mydb.reconnect()
        self.updateMembers()
        self.updateAlumni()

    def cursor(self):
        #if not self.mydb.is_connected():
        #    self.mydb = mysql.connector.connect(
        #        host = self.creds['host'],
        #        user = self.creds['user'],
        #        passwd = self.creds['passwd'],
        #        database = self.creds['database'],
        #        charset = self.creds['charset']
        #        )
        #return self.mydb.cursor(buffered=True)
        return self.mydb.cursor()

    def executeCommit(self, sql, lst = None, results = False):
        c = self.cursor()

        if lst != None:
            c.execute(sql, lst)
        else:
            c.execute(sql)

        output = None
        if results == True:
            output = c.fetchall()
        else:
            output = c.rowcount

        c.close()
        self.mydb.commit()
        return output