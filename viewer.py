#!/usr/bin/env python3

"""Visualizes results from dice using Matplotlib"""

# TODO: make this viewer work with internal dice engine objects!

import fileinput
import re
import sys

import matplotlib.pyplot as plt

from diceengine import ResultList, Distrib

def show():
    """Opens window to show final result"""
    plt.show()

def export(path):
    """Export current figure to path"""
    plt.savefig(path)

def visualize(data, legend):
    """Visualizes data"""
    print("data", data, legend)
    if isinstance(data, dict):
        x = list(data.keys())
        y = list(data.values())
        plt.plot(x, y, label=legend)
        print(legend)
        plt.legend()

def string_to_number(string):
    """Returns number if string can be converted else returns string"""
    try:
        a = float(string)
        if a.is_integer():
            a = int(a)
        return a
    except ValueError:
        return string

def parse(text):
    # print(text)
    """Parses text to create data"""
    # re recognising python dictionaries
    #
    # NOTE: currently only one item per row is allowed
    # serach for dict:
    match = re.search(r"\{.*?: .*?(?:, .*?: .*?)*\}", text)
    if match:
        items = []
        for item in match.group(0)[1:-1].split(", "):
            a, b = item.split(" ")
            a = string_to_number(a)
            b = string_to_number(b)
            items.append([a, b])
        return dict(items)

def label(string):
    do.label.append(string)

def xlabel(string):
    plt.xlabel(string)

def ylabel(string):
    plt.ylabel(string)

def plot(string):
    print("input: ", string, "type: ", type(string))
    visualize(parse(string), "\n".join(do.label))
    do.label = []

def do(input_string):
    """Does action according to input string"""
    if input_string.startswith("#label "):
        do.label.append(input_string[len("#label "):].strip())
        return
    if input_string.startswith("#xlabel"):
        plt.xlabel(input_string[len("#xlabel "):].strip())
    if input_string.startswith("#ylabel"):
        plt.ylabel(input_string[len("#ylabel "):].strip())
    if input_string.startswith("#grid fine"):
        plt.minorticks_on()
        plt.grid(which='minor')
        plt.grid(color='#666666')
    elif input_string.startswith("#grid"):
        plt.grid(color='#666666')
    if input_string.startswith("#title "):
        plt.title(input_string[len("#title "):].strip())
    if input_string.startswith("#"):
        # just a print statement
        return

    # actual information
    visualize(parse(input_string), "\n".join(do.label))
    do.label = []
# static stores lines for the next label
do.label = []

def main(args):
    args = args[1:]
    input_lines = fileinput.input(args)
    # collects label data until distribution is visualized
    for line in input_lines:
        # lines starting with # contain information for this script (either lables or commands)
        do(line)
    show()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
