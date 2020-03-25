#!/usr/bin/env python3

"""Interactive interpreter"""

import sys

from interpreter import Interpreter
from parser import DiceParser
from lexer import Lexer

while True:
    text = input("dice> ")
    if text == "exit":
        break
    try:
        result = Interpreter(DiceParser(Lexer(text)).expr()).interpret()
        print(result)
    except Exception as e:
        print(e)
