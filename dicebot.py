#!/usr/bin/env python3

"""Quick and dirty discordbot"""

import discord
import time
import re
import operator
import os
from dice import interpret
from preprocessor import Preprocessor


script_dir = os.path.dirname(__file__)
token = "NjkyMzQxNDU0MzYxNTkxODU4.XntHYA.nim6JKQ3HvYNtqnk5Z9nHpBF5PM"

client = discord.Client()

# a list of bots. these bots will get all messages relayed to them
bots = []

def run_client():
    client.run(token)

@client.event
async def on_ready():
    print("Logged in as")
    print(client.user.name)
    print(client.user.id)
    print("------")

@client.event
async def on_message(message):
    for b in bots:
        await b.handle_message(message)

def init_bot(bot):
    """adds the bot to the message relay"""
    bots.append(bot)

class Bot(object):
    """The Bot controls all interaction with Discord"""
    def __init__(self, name="Dice"):
        # Bot settings
        self.command_prefix = "?"
        self.more_mentions = False  # use more mentions

    def get_mention(self, user):
        """returns mention or name depending on settings

        :param user:
        :return: string (mention or name)
        """
        return user.mention if self.more_mentions else "**{}**".format(user.name)

    def get_current_user(self, user, server):
        """returns the updated version of the user in question"""
        for m in server.members:
            if m == user:
                return m
        print("ERROR no user found")
        return None

    async def print_help(self, author, mentions, channel, text):
        mention = self.get_mention(author)
        lines = [
            "**{}help** prints this text".format(self.command_prefix),
            "**{}x** executes dice command".format(self.command_prefix),
        ]
        await channel.send("\n" + mention + " " + "commands:\n" + ("\n").join(lines))

    async def execute(self, author, mentions, channel, text):
        """executes a snipped of the dice language"""
        mention = self.get_mention(author)

        def prettyfy(input_string):
            if re.search(r"^\{.*\}$", input_string):
                return input_string.replace("{", "```").replace("}", "```").replace(": ", ":\t").replace(", ", "\n")
            return input_string

        # these get output to the user (after prettyfying)
        output_lines = []

        lines = text.split("\n")
        if len(lines) == 1:
            try:
                output_lines.append(prettyfy(str(interpret(text, Preprocessor()))))
            except Exception as e:
                output_lines.append(str(e))
        else:
            # find codeblock
            # match with dotall to get newlines
            match = re.search(r"```(.*?)```", text, re.DOTALL)
            if not match:
                await channel.send("multiline code needs a codeblock")
                return
            code = match.group(1)
            lines = code.split("\n")
            for line in lines:
                try:
                    output_lines.append(prettyfy(str(interpret(line, Preprocessor()))))
                except Exception as e:
                    output_lines.append(str(e))

        # prettyfy output
        # check if dic format then replace commas with new line
        await channel.send("\n" + mention + " " + "commands:\n" + ("\n").join(output_lines))

    async def execute_image(self, author, mentions, channel, text):
        """executes a snipped of the dice language and plots the result. posts the image"""
        mention = self.get_mention(author)

        # these get output to the user (after prettyfying)
        output_lines = []

        lines = text.split("\n")
        if len(lines) == 1:
            try:
                output_lines.append(str(interpret(text, Preprocessor())))
            except Exception as e:
                output_lines.append(str(e))
        else:
            # find codeblock
            # match with dotall to get newlines
            match = re.search(r"```(.*?)```", text, re.DOTALL)
            if not match:
                await channel.send("multiline code needs a codeblock")
                return
            code = match.group(1)
            lines = code.split("\n")
            # common preprocessor for all lines
            preprocessor = Preprocessor()
            for line in lines:
                print("line:", line)
                try:
                    output_lines.append(str(interpret(line, preprocessor)))
                except Exception as e:
                    output_lines.append(str(e))
                print("output:", output_lines[-1])

        # TODO: create a viewer class to avoid this shit
        import viewer

        for line in output_lines:
            viewer.do(line)

        viewer.export("export.png")

        # check if dic format then replace commas with new line
        await channel.send(mention, file=discord.File("export.png"))

    async def handle_message(self, message):
        commands = {
            "help": self.print_help,
            "x": self.execute,
            "p": self.execute_image,
        }

        if message.content.startswith(self.command_prefix):
            author = message.author
            channel = message.channel
            com_list = message.content[len(self.command_prefix):].split()
            if com_list:
                command = com_list[0]
            else:
                return  # just a questionmark
            text = message.content[len(self.command_prefix) + len(command):]
            mentions = message.mentions

            if command in commands:
                await commands[command](author, mentions, channel, text)

if __name__ == "__main__":
    init_bot(Bot())
    run_client()
