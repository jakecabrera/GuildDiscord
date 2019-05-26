import random
import re
import discord
from guild import Guild

class Dungeon(object):
    def __init__(self, *args, **kwargs):
        # patterns
        self.rollPattern = re.compile(r'r\d{1,2}d\d{1,2}')
        self.rollDicePattern = re.compile(r'(?<=\dd)\d{1,2}')
        self.rollCountPattern = re.compile(r'(?<=r)\d*(?=d)')
        self.dicePattern = re.compile(r'(?<!\d)d\d*')
        self.channel = None

    async def parse(self, message):
        ch = message.channel if self.channel == None else self.channel
        if len(message.channel_mentions) > 0:
            ch = message.channel_mentions[0]
        tosses = message.content.split(' ')
        for toss in tosses:
            if len(self.dicePattern.findall(toss)) > 0:
                results = self.dicePattern.findall(toss)
                for result in results:
                    outcome = self.roll(int(result[1:]))
                    await ch.send(Guild.cssMessage(result + ' = '  + str(outcome)))
            if len(self.rollPattern.findall(toss)) > 0:
                results = self.rollPattern.findall(toss)
                for result in results:
                    sides = int(self.rollDicePattern.findall(result)[0])
                    rolls = int(self.rollCountPattern.findall(result)[0])
                    outcomes = list(self.roll(sides) for x in range(rolls))
                    msg = result + ' ='
                    for outcome in outcomes:
                        msg += ' ' + str(outcome) + ','
                    msg = msg[:-1]
                    await ch.send(Guild.cssMessage(msg))
        return

    def roll(self, sides):
        random.seed()
        return random.randint(1,sides)

    def bindToCurrentChannel(self, message):
        self.channel = message.channel
        return

