#!/usr/bin/env python3

"""Preprocesses input (lines) for dice"""

# In addition to comments this is pretty much just a HACK y solution to emulate what functions can do

import re

class Definition(object):
    """Basically a macro (c)"""
    def __init__(self, statement):
        """parse definition and extract information"""
        regex = r"^([a-zA-Z]\w*)(?:\(([a-zA-Z]\w*(?: *, *[a-zA-A]\w*)*)\))? *(.*)$"
        match = re.search(regex, statement)
        if not match:
            raise Exception("Definition exception. Could not parse: {}".format(statement))
        self.name = match.group(1)
        self.attributes = []
        if match.group(2):
            # collect attributes from inside the attribute group e.g.: (a, b, c)
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
            # concatinate regexes to match every argument with its own group
            attr_regex = " *, *".join(['(".*?"|.*?)'] * len(self.attributes))
            regex = r"{name}\({attributes}\)".format(name=self.name, attributes=attr_regex)

            # space for the newly generated line
            new_line = line

            # find every place where the definition can be applied
            match = re.search(regex, new_line)
            while match:
                # NOTE: this can be an endless loop with a carefully chosen #definition
                # TODO: matches are in order so maybe only view part of the string for future matches?
                groups = match.groups()
                replacement = self.body
                # add attributes to own body for replacement
                for attribute, value in zip(self.attributes, groups):
                    replacement = re.sub(attribute, value, replacement)
                # sub in body
                new_line = re.sub(regex, replacement, new_line, count=1)
                # see if there are any more matches
                match = re.search(regex, new_line)
            return new_line
        else:
            # no attributes just replace every occurence of self.name with self.body
            regex = r"{name}".format(name=self.name)
            return re.sub(regex, self.body, line)

class Preprocessor(object):
    """Preprocesses line of code for the dice language

    // : gets ignored as comment
    !define : gets added as definition
    also applies existing definitions (macros) to line."""

    def __init__(self):
        self.definitions = []

    def define(self, line):
        """Defines a preprocessor statement (replace) similar to c #define"""
        self.definitions.append(Definition(line))

    def preprocess(self, line):
        """Preprocesses line"""
        # ignore comments and whitespace only
        if line.startswith("//") or line.strip() == "":
            return ""

        # apply definitions
        ret_line = line
        for d in self.definitions:
            ret_line = d.parse(ret_line)

        if line.startswith("!define"):
            self.define(ret_line[len("!define"):].strip())
            return ""

        return ret_line
