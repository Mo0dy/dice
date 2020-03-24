#!/usr/bin/env python3

from parser import DiceParser
from lexer import Lexer, PLUS, ROLL, INTEGER, IF_THEN, EOF, GREATER_THEN
from diceengine import Diceprop

class NodeVisitor(object):
    def visit(self, node):
        """Calls method with name visit_NodeName for every ast node visited.
        Does Depthfirst search."""
        method_name = 'visit_' + type(node).__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """Gets calles if no proper visit methods exists"""
        raise Exception('No visit_{} method'.format(type(node).__name__))


class Interpreter(NodeVisitor):
    """Implements the language from an abstract syntax tree."""
    def __init__(self, ast):
        self.ast = ast;

    def visit_BinOp(self, node):
        if node.op.type == PLUS:
            return Diceprop.add(self.visit(node.left), self.visit(node.right))
        if node.op.type == ROLL:
            return Diceprop(self.visit(node.left), self.visit(node.right))
        if node.op.type == GREATER_THEN:
            return Diceprop.greaterorequal(self.visit(node.left), self.visit(node.right))

    def visit_Val(self, node):
        return node.value

    def interpret(self):
        """Interprets AST"""
        return self.visit(self.ast)

if __name__ == "__main__":
    input_text = "1d20 + 16 >= 17"
    ast = DiceParser(Lexer(input_text)).expr()
    interpreter = Interpreter(ast)
    result = interpreter.interpret()
    print(result)
