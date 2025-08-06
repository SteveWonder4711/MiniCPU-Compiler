import logging
from lark import Lark, logger, visitors

logger.setLevel(logging.WARN)

operatorcodes = {
    "+": "add",
    "-": "sub",
    "*": "call mul 2",
    "/": "call div 2",
    "%": "call mod 2",
    ">>": "call shr 2",
    "<<": "call shl 2",
    "&": "and",
    "^": "call xor 2",
    "|": "or",
    "==": "eq",
    "!=": "ne",
    ">": "gt",
    ">=": "ge",
    "<": "lt",
    "<=": "le"
}

unaryoperatorcodes = {
    "-": "neg",
    "~": "not"
}


class ParseState:
    def __init__(self):
        self.ifnum = 0
        self.symboltable = []

class ConvertAST(visitors.Transformer_InPlaceRecursive):
    def body(self, tree):
        statements = tree
        return Body(statements)
   
    def statement(self, tree):
        return Statement(tree[0])

    def ifclause(self, tree):
        ifbranch = None
        elifbranches = []
        elsebranch = None
        for child in tree:
            if type(child) == If:
                ifbranch = child
            elif type(child) == Elif:
                elifbranches.append(child)
            else:
                elsebranch = child
        return IfClause(ifbranch, elifbranches, elsebranch)

    def ifbranch(self, tree):
        expression = tree[0]
        body = tree[1]
        return If(expression, body)

    def elifbranch(self, tree):
        expression = tree[0]
        body = tree[1]
        return Elif(expression, body)

    def elsebranch(self, tree):
        body = tree[0]
        return Else(body)

    def assignment(self, tree):
        assignvar = tree[0].value
        operator = tree[1].value
        expression = tree[2]
        return Assignment(assignvar, expression, operator)

    def number(self, tree):
        number = tree[0]
        return Number(number)

    def identifier(self, tree):
        value = tree[0]
        return Identifier(value)

    def binaryop(self, tree):
        left = tree[0]
        operator = tree[1].value
        right = tree[2]
        return BinaryOp(left, right, operator)

    def unaryop(self, tree):
        operator = tree[0]
        right = tree[1]
        return UnaryOp(right, operator)


class Body:
    def __init__(self, statements):
        self.statements = statements

    def eval(self, state):
        out = ""
        for statement in self.statements:
            out += f"{statement.eval(state)}\n"
        return out

class Statement:
    def __init__(self, statement):
        self.statement = statement

    def eval(self, state):
        return self.statement.eval(state)

class IfClause:
    def __init__(self, ifbranch, elifbranches, elsebranch):
        self.ifbranch = ifbranch
        self.elifbranches = elifbranches
        self.elsebranch = elsebranch

    def eval(self, state):
        ifnum = state.ifnum
        state.ifnum += 1
        localnum = 0
        out = ""
        out += f"{self.ifbranch.expression.eval(state)}\nnot\nifgoto if{ifnum}_{localnum}\n"
        out += f"{self.ifbranch.body.eval(state)}\ngoto if{ifnum}_end\n@ if{ifnum}_{localnum}\n"
        localnum += 1
        for branch in self.elifbranches:
            out += f"{branch.expression.eval(state)}\nnot\nifgoto if{ifnum}_{localnum}\n"
            out += f"{branch.body.eval(state)}\ngoto if{ifnum}_end\n@ if{ifnum}_{localnum}\n"
        if self.elsebranch is not None:
            out += f"{self.elsebranch.body.eval(state)}\n"
        out += f"@ if{ifnum}_end\n"
        return out


#if, elif and else evals are done in class IfClause
class If:
    def __init__(self, expression, body):
        self.expression = expression
        self.body = body

class Elif:
    def __init__(self, expression, body):
        self.expression = expression
        self.body = body

class Else:
    def __init__(self, body):
        self.body = body


class Assignment:
    def __init__(self, assignvar, expression, operator):
        self.assignvar = assignvar
        self.expression = expression
        self.operator = operator

    def eval(self, state):
        if self.assignvar not in state.symboltable:
            state.symboltable.append(self.assignvar)
        index = state.symboltable.index(self.assignvar)
        if self.operator == "=":
            return f"{self.expression.eval(state)}\npopvar {index}\n"
        else:
            return f"pushvar {index}\n{self.expression.eval(state)}\n{operatorcodes[self.operator]}\npopvar {index}\n"


class BinaryOp:
    def __init__(self, left, right, operator):
        self.left = left
        self.right = right
        self.operator = operator

    def eval(self, state):
        return f"{self.left.eval(state)}\n{self.right.eval(state)}\n{operatorcodes[self.operator]}\n"

class UnaryOp:
    def __init__(self, right, operator):
        self.right = right
        self.operator = operator

    def eval(self, state):
        return f"{self.right.eval(state)}\n{unaryoperatorcodes[self.operator]}\n"


class Identifier:
    def __init__(self, value):
        self.value = value

    def eval(self, state):
        if self.value in state.symboltable:
            return f"pushvar {state.symboltable.index(self.value)}"
        raise NameError(f"name {self.value} not defined")


class Number:
    def __init__(self, value):
        self.value = value

    def eval(self, state):
        return f"pushvalue {self.value}"


with open("larksyntax.lark") as syntaxfile:
    syntax = syntaxfile.read()

with open("code") as codefile:
    code = codefile.read()

p = Lark(syntax, start="start")

parsestate = ParseState()

parsed = p.parse(code)
print(parsed.pretty())

ConvertAST().transform(parsed)

converted = parsed.children[0]

print(converted.eval(parsestate))
