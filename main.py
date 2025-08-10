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
    "<=": "le",
    "&&": "and",
    "||": "or"
}

unaryoperatorcodes = {
    "-": "neg",
    "~": "not"
}


class ParseState:
    def __init__(self):
        self.ifnum = 0
        self.whilenum = 0
        self.fornum = 0
        self.currentfunction = "global"
        self.functions = {"global": {
                "arguments": {},
                "locals": {}
            }
        }

class ConvertAST(visitors.Transformer_InPlaceRecursive):
    def codebody(self, tree):
        statements = tree
        return CodeBody(statements)

    def body(self, tree):
        statements = tree
        return Body(statements)
   
    def statement(self, tree):
        return Statement(tree[0])

    def function(self, tree):
        returntype = "void"
        hastype = type(tree[-2]) == Type
        name = tree[0].value
        arguments = {}
        for i in range(1,len(tree)-1-hastype,2):
            argname = tree[i].value
            argtype = tree[i+1].value
            arguments[argname] = {"type": argtype}
        body = tree[-1]
        if hastype: returntype = tree[-2].value
        return Function(name, arguments, body, returntype)

    def callnoret(self, tree):
        return CallNoRet(tree[0])

    def call(self, tree):
        name = tree[0].value
        arguments = []
        for i in range(1,len(tree)):
            arguments.append(tree[i])
        return Call(name, arguments)

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

    def whilestatement(self, tree):
        expression = tree[0]
        body = tree[1]
        return While(expression, body)

    def forstatement(self, tree):
        startstatement = tree[0]
        condition = tree[1]
        loopstatement = tree[2]
        body = tree[3]
        return For(startstatement, condition, loopstatement, body)

    def assignment(self, tree):
        assignvar = tree[0].value
        i = 1
        vartype = None
        if type(tree[2]) == Type:
            vartype = tree[2].value
            i = 3
        operator = tree[i].value
        expression = tree[i+1]
        return Assignment(assignvar, vartype, expression, operator)

    def returnstatement(self, tree):
        expression = tree[0]
        return Return(expression)

    def number(self, tree):
        number = tree[0]
        return Number(number)

    def identifier(self, tree):
        value = tree[0].value
        return Identifier(value)

    def vartype(self, tree):
        value = tree[0].value
        return Type(value)

    def binaryop(self, tree):
        left = tree[0]
        operator = tree[1].value
        right = tree[2]
        return BinaryOp(left, right, operator)

    def unaryop(self, tree):
        operator = tree[0]
        right = tree[1]
        return UnaryOp(right, operator)



class CodeBody:
    def __init__(self, statements):
        self.statements = statements

    def eval(self, state):
        out = ""
        for statement in self.statements:
            out += f"{statement.eval(state)}\n"
        return out

class Body:
    def __init__(self, statements):
        self.statements = statements

    def eval(self, state):
        out = ""
        for statement in self.statements:
            out += f"{statement.eval(state)}\n"
        return out.strip("\n")

class Statement:
    def __init__(self, statement):
        self.statement = statement

    def eval(self, state):
        return self.statement.eval(state)

class Function:
    def __init__(self, name, arguments, body, returntype):
        self.name = name
        self.arguments = arguments
        self.body = body
        self.returntype = returntype

    def eval(self, state):
        state.currentfunction = self.name
        state.functions[self.name] = {"returntype": self.returntype, "arguments": self.arguments, "locals": {}}
        bodyout = self.body.eval(state)
        localscount = len(state.functions[self.name]["locals"])
        state.currentfunction = "global"
        return f"@ {self.name}\nfunction {localscount}\n{bodyout}"


class CallNoRet:
    def __init__(self, call):
        self.call = call

    def eval(self, state):
        return f"{self.call.eval(state)}\npopa"


class Call:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

    def eval(self, state):
        out = ""
        for expression in self.arguments:
            out += f"{expression.eval(state)}\n"
        return out + f"call {self.name} {len(self.arguments)}"


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
        out += f"@ if{ifnum}_end"
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

class While:
    def __init__(self, expression, body):
        self.expression = expression
        self.body = body
    
    def eval(self, state):
        whilenum = state.whilenum
        state.whilenum += 1
        expression = self.expression.eval(state)
        body = self.body.eval(state)
        return f"@while{whilenum}_loop\n{expression}\nnot\nifgoto while{whilenum}_end\n{body}\ngoto while{whilenum}_loop\n@while{whilenum}_end"

class For:
    def __init__(self, startstatement, condition, loopstatement, body):
        self.startstatement = startstatement
        self.condition = condition
        self.loopstatement = loopstatement
        self.body = body

    def eval(self, state):
        fornum = state.fornum
        state.fornum += 1
        startstatement = self.startstatement.eval(state)
        condition = self.condition.eval(state)
        loopstatement = self.loopstatement.eval(state)
        body = self.body.eval(state)
        return f"{startstatement}\n@ for{fornum}_loop\n{condition}\nnot\nifgoto for{fornum}_end\n{body}\n{loopstatement}\ngoto for{fornum}_loop\n@ for{fornum}_end"



class Assignment:
    def __init__(self, assignvar, vartype, expression, operator):
        self.assignvar = assignvar
        self.expression = expression
        self.operator = operator
        self.vartype = vartype

    def eval(self, state):
        expression = self.expression.eval(state)

        currentfunction = state.currentfunction
        if self.assignvar not in state.functions[currentfunction]["locals"]:
            if self.vartype is None:
                raise TypeError(f"assignment to {self.assignvar} is missing a type")
            state.functions[currentfunction]["locals"][self.assignvar] = {"type": self.vartype}
        index = list(state.functions[currentfunction]["locals"]).index(self.assignvar)
        if self.operator == "=":
            return f"{expression}\npopvar {index}"
        else:
            return f"pushvar {index}\n{self.expression.eval(state)}\n{operatorcodes[self.operator.replace("=", "")]}\npopvar {index}"

class Return:
    def __init__(self, expression):
        self.expression = expression

    def eval(self, state):
        return f"{self.expression.eval(state)}\nret"


class BinaryOp:
    def __init__(self, left, right, operator):
        self.left = left
        self.right = right
        self.operator = operator

    def eval(self, state):
        return f"{self.left.eval(state)}\n{self.right.eval(state)}\n{operatorcodes[self.operator]}"

class UnaryOp:
    def __init__(self, right, operator):
        self.right = right
        self.operator = operator

    def eval(self, state):
        return f"{self.right.eval(state)}\n{unaryoperatorcodes[self.operator]}"

class Type:
    def __init__(self, value):
        self.value = value

class Identifier:
    def __init__(self, value):
        self.value = value

    def eval(self, state):
        symboltable = state.functions[state.currentfunction]
        if self.value in symboltable["locals"]:
            return f"pushvar {list(symboltable["locals"]).index(self.value)}"
        elif self.value in symboltable["arguments"]:
            return f"pusharg {list(symboltable["arguments"]).index(self.value)}"

        raise NameError(f"name {self.value} referenced before assignment")


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

ConvertAST().transform(parsed)

converted = parsed.children[0]

print(converted.eval(parsestate))

print(parsestate.functions)
