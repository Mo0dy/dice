#!/usr/bin/env python3

"""Interactive interpreter"""

import sys
import fileinput
import re

from interpreter import Interpreter
from diceengine import ResultList, Distrib
from parser import DiceParser
from lexer import Lexer

def interpret(text):
    try:
        result = Interpreter(DiceParser(Lexer(text)).expr()).interpret()
        # round and prettyfy
        if isinstance(result, ResultList) or isinstance(result, Distrib):
            for k, v in result.items():
                result[k] = round(v, 2)
        return result
    except Exception as e:
        return str(e)

def runinteractive():
    while True:
        text = input("dice> ")
        if text == "exit":
            return 0
        print(interpret(text))
    return 2

class Definition(object):
    def __init__(self, statement):
        """parse definition and extract information"""
        regex = r"^([a-zA-Z]\w*)(?:\(([a-zA-Z]\w*(?: *, *[a-zA-A]\w*)*)\))? *(.*)$"
        match = re.search(regex, statement)
        if not match:
            raise Exception("Definition exception. Could not parse: {}".format(statement))
        self.name = match.group(1)
        self.attributes = []
        if match.group(2):
            self.attributes = [x.strip() for x in match.group(2).split(",")]
        if not match.group(3):
            raise Exception("Definition needs a definition body could not parse: {}".format(statement))
        self.body = match.group(3).strip()
        self.statement = statement

    def __repr__(self):
        return "Definition: {}".format(self.statement)

    def parse(self, line):
        """Parses a line and applies itself wherever possible"""
        # It's a lot simpler if I make two regexes out of this one with and one without attributes
        if self.attributes:
            attr_regex = " *, *".join(['"(.*?)"'] * len(self.attributes))
            regex = r"{name}\({attributes}\)".format(name=self.name, attributes=attr_regex)

            # less strict (no " needed)
            attr_regex2 = ",".join(['(.*?)'] * len(self.attributes))
            regex2 = r"{name}\({attributes}\)".format(name=self.name, attributes=attr_regex2)
            new_line = line

            # HACK: This should be a lot cleaner!
            match = re.search(regex, new_line)
            # stores which match is used
            match1 = True
            if not match:
                match1 = False
                match = re.search(regex2, new_line)
            while match:
                # NOTE: this can be an endless loop with a carefully chosen #definition
                groups = match.groups()
                replacement = self.body
                for attribute, value in zip(self.attributes, groups):
                    replacement = re.sub(attribute, value, replacement)
                new_line = re.sub(regex if match1 else regex2, replacement, new_line, count=1)
                match = re.search(regex, new_line)
                if not match:
                    match = re.search(regex2, new_line)
            return new_line
        else:
            regex = r"{name}".format(name=self.name)
            return re.sub(regex, self.body, line)

def define(line, definitions):
    """Defines a preprocessor statement (replace) similar to c #define"""
    definitions.append(Definition(line))

def main(args):
    definitions = []

    if len(args) > 1:
        if args[1] in ["-i", "--interactive"]:
            return runinteractive()
        elif args[1] in ["-e", "--execute"] and len(args) > 1:
            sys.stdout.write(interpret(args[2]))
            return 0

    input_lines = fileinput.input()
    for line in input_lines:
        if line == "\n" or line[0] in '!#':
            if line.startswith("!define"):
                define(line[len("!define"):].strip(), definitions)
            if line[0] == '#':
                sys.stdout.write(line)
        else:
            # apply definitions:
            for d in definitions:
                line = d.parse(line)
            result = str(interpret(line))
            if result:
                sys.stdout.write("dice> " + line)
                sys.stdout.write(str(result) + "\n\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
