#!/usr/bin/env python3

from diceparser import DiceParser
from lexer import Lexer, INTEGER, ROLL, GREATER_OR_EQUAL, LESS_OR_EQUAL, LESS, GREATER, EQUAL, PLUS, MINUS, MUL, DIV, RES, ELSE, EOF, COLON, ADV, DIS, ELSEDIV, HIGH, LOW, LBRACK
from diceengine import Diceengine

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

    def exception(self, message=""):
        raise Exception("Interpreter exception: {}".format(message))

    def visit_VarOp(self, node):
        if node.op.type == LBRACK:
            # construct list from subnodes in node.nodes
            ret_val = []
            for node in node.nodes:
                new_val = self.visit(node)
                if type(new_val) != int:
                    self.exception("Constructing list expected int got: {}".format(type(new_val)))
                ret_val.append(new_val)
            return ret_val
        self.exception("{} not implemented".format(node))

    def visit_TenOp(self, node):
        if node.op1.type == RES and node.op2.type == ELSE:
            return Diceengine.reselse(self.visit(node.left), self.visit(node.middle), self.visit(node.right))
        elif node.op1.type == ROLL:
            if node.op2.type == HIGH:
                return Diceengine.rollhigh(self.visit(node.left), self.visit(node.middle), self.visit(node.right))
            elif node.op2.type == LOW:
                return Diceengine.rolllow(self.visit(node.left), self.visit(node.middle), self.visit(node.right))
        self.exception("{} not implemented".format(node))

    def visit_BinOp(self, node):
        # TODO: should I add typeguards here?
       
        if node.op.type == PLUS:
            return Diceengine.add(self.visit(node.left), self.visit(node.right))
        if node.op.type == MINUS:
            return Diceengine.sub(self.visit(node.left), self.visit(node.right))
        if node.op.type == MUL:
            return Diceengine.mul(self.visit(node.left), self.visit(node.right))
        if node.op.type == DIV:
            return Diceengine.div(self.visit(node.left), self.visit(node.right))
        if node.op.type == ROLL:
            return Diceengine.roll(self.visit(node.left), self.visit(node.right))
        if node.op.type == GREATER_OR_EQUAL:
            return Diceengine.greaterorequal(self.visit(node.left), self.visit(node.right))
        if node.op.type == LESS_OR_EQUAL:
            return Diceengine.lessorequal(self.visit(node.left), self.visit(node.right))
        if node.op.type == GREATER:
            return Diceengine.greater(self.visit(node.left), self.visit(node.right))
        if node.op.type == LESS:
            return Diceengine.less(self.visit(node.left), self.visit(node.right))
        if node.op.type == EQUAL:
            return Diceengine.equal(self.visit(node.left), self.visit(node.right))
        if node.op.type == RES:
            return Diceengine.res(self.visit(node.left), self.visit(node.right))
        if node.op.type == ELSEDIV:
            return Diceengine.reselsediv(self.visit(node.left), self.visit(node.right))
        if node.op.type == COLON:
            val1 = self.visit(node.left)
            if type(val1) != int:
                self.exception("Expected int got {}".format(type(val1)))
            val2 = self.visit(node.right)
            if type(val2) != int:
                self.exception("Expected int got {}".format(type(val2)))
            return [x for x in range(val1, val2 + 1)]
        if node.op.type == LBRACK:
            return Diceengine.choose(self.visit(node.left), self.visit(node.right))

        self.exception("{} not implemented".format(node))

    def visit_UnOp(self, node):
        if node.op.type == ROLL:
            return Diceengine.rollsingle(self.visit(node.value))
        elif node.op.type == ADV:
            return Diceengine.rolladvantage(self.visit(node.value))
        elif node.op.type == DIS:
            return Diceengine.rolldisadvantage(self.visit(node.value))
        elif node.op.type == RES:
            return Diceengine.resunary(self.visit(node.value))
        self.exception("{} not implemented".format(node))

    def visit_Val(self, node):
        return node.value

    def interpret(self):
        """Interprets AST"""
        return self.visit(self.ast)

if __name__ == "__main__":
    input_text = "d20 < 10"
    ast = DiceParser(Lexer(input_text)).expr()
    interpreter = Interpreter(ast)
    result = interpreter.interpret()
    print(result)
