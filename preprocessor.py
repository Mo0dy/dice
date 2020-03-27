#!/usr/bin/env python3

"""Preprocesses input (lines) for dice"""

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
            attr_regex = " *, *".join(['(".*?"|.*?)'] * len(self.attributes))
            regex = r"{name}\({attributes}\)".format(name=self.name, attributes=attr_regex)
            new_line = line
            match = re.search(regex, new_line)
            while match:
                # NOTE: this can be an endless loop with a carefully chosen #definition
                groups = match.groups()
                replacement = self.body
                for attribute, value in zip(self.attributes, groups):
                    replacement = re.sub(attribute, value, replacement)
                new_line = re.sub(regex, replacement, new_line, count=1)
                match = re.search(regex, new_line)
            return new_line
        else:
            regex = r"{name}".format(name=self.name)
            return re.sub(regex, self.body, line)

class Preprocessor(object):
    def __init__(self):
        self.definitions = []

    def define(self, line):
        """Defines a preprocessor statement (replace) similar to c #define"""
        self.definitions.append(Definition(line))

    def preprocess(self, line):
        ret_line = line
        for d in self.definitions:
            ret_line = d.parse(ret_line)
        return ret_line
