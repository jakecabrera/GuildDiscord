import random
import re
import discord
from guild import Guild

class Dungeon(object):
    def __init__(self, *args, **kwargs):
        # patterns
        self.rollPattern = re.compile(r'(?:r\d{1,2})?d\d{1,2}(?:[+|-]\d{1,4})?') # ex r23d6-2
        self.rollDicePattern = re.compile(r'(?<=d)\d{1,4}') # ex d20
        self.rollCountPattern = re.compile(r'(?<=r)\d{1,2}(?=d)') # ex r5
        self.dicePattern = re.compile(r'(?<!\d)d\d*(?:[\+-]\d{1,4})?') # ex d7+4
        self.mathPattern = re.compile(r'(?<=\d)[\+-]\d{1,4}') # ex +5
        self.channel = None

    async def parse(self, message):
        ch = message.channel if self.channel == None else self.channel
        if len(message.channel_mentions) > 0:
            ch = message.channel_mentions[0]
        tosses = message.content.split(' ')

        # Perform each roll
        results = self.rollPattern.findall(message.content)
        for result in results:
            # Get parameters
            rollsResults = self.rollCountPattern.findall(result)
            sidesResults = self.rollDicePattern.findall(result)
            mathResults = self.mathPattern.findall(result)
            rolls = int(rollsResults[0]) if len(rollsResults) > 0 else 1
            sides = int(sidesResults[0]) if len(sidesResults) > 0 else 0
            math = mathResults[0] if len(mathResults) > 0 else ''

            # The roll outcomes
            outcomes = list(self.roll(sides) for x in range(rolls))
            value = 0
            outcomeAddString = ''
            for outcome in outcomes:
                value += outcome
                outcomeAddString += str(outcome) + '+'
            outcomeAddString = outcomeAddString[:-1]

            # Do math on result
            if math != '':
                if math[0:1] == '+': value += int(math[1:])
                elif math[0:1] == '-': value -= int(math[1:])
                elif math[0:1] == '*': value *= int(math[1:])
                elif math[0:1] == '/': value /= int(math[1:])

            # Build output message
            msg = result + ' = ' + str(value)
            if math != '' or len(outcomes) > 1:
                msg += ' (' + outcomeAddString + math + ')'

            await ch.send(Guild.cssMessage(msg))

    def roll(self, sides):
        random.seed()
        return random.randint(1,sides)

    def bindToCurrentChannel(self, message):
        self.channel = message.channel
        return

