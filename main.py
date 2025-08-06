import logging
from lark import Lark, logger, Visitor

logger.setLevel(logging.WARN)

class ConvertAST(Visitor):
    def body(self, tree):
        statements = tree.children
        tree = Body(statements)
    
    def ifclause(self, tree):
        ifbranch = None
        elifbranches = []
        elsebranch = None
        for child in tree.children:
            if type(child) == If:
                ifbranch = child
            elif type(child) == Elif:
                elifbranches.append(child)
            else:
                elsebranch = child
        tree = IfClause(ifbranch, elifbranches, elsebranch)

    def if(self, tree):
        expression = tree.children[0]
        body = tree.children[1]
        tree = If(expression, body)

    def elif(self, tree):
        expression = tree.children[0]
        body = tree.children[1]
        tree = Elif(expression, body)

    def else(self, tree):
        body = tree.children[0]
        tree = Else(body)

    def assignment(self, tree):
        assignvar = tree.children[0].value
        expression = tree.children[1]
        tree = Assignment(assignvar, expression)

    def number(self, tree):
        number = tree.children[0]
        tree = Number(number)

    def binaryop(self, tree):
        left = tree.children[0]
        operator = tree.children[1]
        right = tree.children[2]
        tree = BinaryOp(left, right, operator)

    def unaryop(self, tree):
        operator = tree.children[0]
        right = tree.children[1]
        tree = UnaryOp(right, operator)


class Body:
    def __init__(self, statements):
        self.statements = statements

    def eval(self, state):
        out = ""
        for statement in self.statements:
            out += f"{statement.eval(state)}\n"
        return out

class IfClause:
    def __init__(self, ifbranch, elifbranches, elsebranch):
        self.ifbranch = ifbranch
        self.elifbranches = elifbranches
        self.elsebranch = elsebranch

    def eval(self, state): #TODO: CURRENTLY WORKING ON THIS
        ifnum = state.ifnum
        state.ifnum += 1
        localnum = 0
        out = ""
        out += f"{self.ifbranch.expression.eval(state)}\nnot\nifgoto if{ifnum}_{localnum}\n"
        out += f"{self.ifbranch.body.eval(state)}\ngoto if{ifnum}_end\n@ if{ifnum}_{localnum}\n"
        localnum += 1
        for branch in self.elifbranches:
            out += f"{branch.eval(state)}\n"

        

with open("larksyntax.lark") as syntaxfile:
    syntax = syntaxfile.read()

with open("code") as codefile:
    code = codefile.read()

p = Lark(syntax, start="body")

parsed = p.parse(code)
print(parsed.pretty())

ConvertAST().visit(parsed)

