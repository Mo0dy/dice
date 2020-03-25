#!/usr/bin/env python3

class AST(object):
    """The baseclass for all AST nodes"""

class BinOp(AST):
    """Node for all binary operators"""
    def __init__(self, left, op, right):
        self.left = left
        self.token = self.op = op
        self.right = right

    def __repr__(self):
        result = "BinOp: {}".format(self.op)
        left_node = str(self.left)
        right_node = str(self.right)
        result += '\t|'.join(('\n' + "left: " + str(self.left).lstrip()).splitlines(True))
        result += '\t|'.join(('\n' + "right: " + str(self.right).lstrip()).splitlines(True))
        return result

class TenOp(AST):
    """Node for all tenary operators"""
    def __init__(self, left, op, middle, op2, right):
        self.left = left
        self.middle = middle
        self.right = right
        self.token1 = self.op1 = op
        self.token2 = self.op2 = op2

    def __repr__(self):
        # NOTE: copyied from BinOp
        result = "TenOp: {}, {}".format(self.op1, self.op2)
        left_node = str(self.left)
        middle_node = str(self.middle)
        right_node = str(self.right)
        result += '\t|'.join(('\n' + "left: " + str(self.left).lstrip()).splitlines(True))
        result += '\t|'.join(('\n' + "middle " + str(self.middle).lstrip()).splitlines(True))
        result += '\t|'.join(('\n' + "right: " + str(self.right).lstrip()).splitlines(True))
        return result

class Val(AST):
    """Value end node"""
    def __init__(self, token):
        self.token = token
        self.value = token.value

    def __repr__(self):
        return "Val: {}".format(self.value)
