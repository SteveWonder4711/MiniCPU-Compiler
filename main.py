from rply import LexerGenerator, ParserGenerator
from rply.token import BaseBox

keywords = ["function", "return"]

lg = LexerGenerator()

lg.add('NUMBER', r'(0[XxOoBb])?\d+')
lg.add('IDENTIFIER', r'[A-Za-z][A-Za-z0-9_-]*')
lg.add('PLUS', r'\+')
lg.add('MINUS', r'\-')
lg.add('MUL', r'\*')
lg.add('DIV', r'\/')
lg.add('ASSIGN', r'=')
lg.add('OPEN_PARENS', r'\(')
lg.add('CLOSE_PARENS', r'\)')
lg.add('SEMICOLON', r'\;')
for keyword in keywords:
    lg.add(keyword.upper(), keyword)

lg.ignore(r'\s+')

lexer = lg.build()


class ParseState(object):
    def __init__(self):
        self.symboltable = []

class Identifier(BaseBox):
    def __init__(self, name):
        self.name = name

    def eval(self, state):
        if self.name in state.symboltable:
            return f"pushvar {state.symboltable.index(self.name)}"
        else:
            raise NameError(f"name {self.name} not defined")

class Code(BaseBox):
    def __init__(self, statements):
        self.statements = statements

    def eval(self, state):
        out = ""
        for statement in self.statements:
            out += statement.eval(state) + "\n"
        return out

class Number(BaseBox):
    def __init__(self, value):
        self.value = f"pushvalue {value}" 

    def eval(self, state):
        return self.value

class BinaryOp(BaseBox):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class UnaryOp(BaseBox):
    def __init__(self, right):
        self.right = right

class Assign(BaseBox):
    def __init__(self, assignvar, expression, parsestate):
        self.assignvar = assignvar
        self.expression = expression
        if assignvar not in parsestate.symboltable:
            parsestate.symboltable.append(assignvar)
        self.assignindex = parsestate.symboltable.index(assignvar)


    def eval(self, state):
        return f"{self.expression.eval(state)}\npopvar {self.assignindex}"


class Add(BinaryOp):
    def eval(self, state):
        return f"{self.left.eval(state)}\n{self.right.eval(state)}\nadd"

class Sub(BinaryOp):
    def eval(self, state):
        return f"{self.left.eval(state)}\n{self.right.eval(state)}\nsub"

class Mul(BinaryOp):
    def eval(self, state):
        return f"{self.left.eval(state)}\n{self.right.eval(state)}\ncall mul 2"

class Div(BinaryOp):
    def eval(self, state):
        return f"{self.left.eval(state)}\n{self.right.eval(state)}\ncall mul 2"

class Neg(UnaryOp):
    def eval(self, state):
        return f"{self.right.eval(state)}\nneg"




pg = ParserGenerator(
    #All token Names
    ["NUMBER", "PLUS", "MINUS", "MUL", "DIV", "OPEN_PARENS", "CLOSE_PARENS", "IDENTIFIER", "ASSIGN", "SEMICOLON"] + [keyword.upper() for keyword in keywords],
    
    precedence=[
        ('left', ["PLUS", "MINUS"]),
        ('left', ["MUL", "DIV"])
    ]
)


@pg.production('code : statements')
def parsecode(state, p):
    return Code(p[0])
        

@pg.production('statements : statement')
def singlestatement(state, p):
    return [p[0]]


@pg.production('statements : statements statement')
def statements(state, p):
    outlist = []
    for statement in p[0]:
        outlist.append(statement)
    outlist.append(p[1])
    print(outlist)
    return outlist



@pg.production('statement : assignment SEMICOLON')
def statement(state, p):
    return p[0]


@pg.production('assignment : IDENTIFIER ASSIGN expression')
def assignment(state, p):
    varname = p[0].getstr()
    right = p[2]
    return Assign(varname, right, state)



@pg.production('expression : IDENTIFIER')
def expression_identifier(state, p):
    return Identifier(p[0].getstr())

@pg.production('expression : NUMBER')
def expression_number(state, p):
    return Number(p[0].getstr())

@pg.production('expression : OPEN_PARENS expression CLOSE_PARENS')
def expression_parens(state, p):
    return p[1]

@pg.production('expression : expression PLUS expression')
@pg.production('expression : expression MINUS expression')
@pg.production('expression : expression MUL expression')
@pg.production('expression : expression DIV expression')
def expression_binop(state, p):
    left = p[0]
    right = p[2]
    operator = p[1].gettokentype()
    match operator:
        case "PLUS":
            return Add(left, right)
        case "MINUS":
            return Sub(left, right)
        case "MUL":
            return Mul(left, right)
        case "DIV":
            return Div(left, right)
        case _:
            raise AssertionError("Invalid Operator!")

@pg.production('expression : MINUS expression')
def expression_unop(state, p):
    right = p[1]
    operator = p[0].gettokentype()
    match operator:
        case "MINUS":
            return Neg(right)
        case _:
            raise AssertionError("Invalid Operator!")




parser = pg.build()

string = """a = -1;
b = a + 2;
"""



state = ParseState()

lexed = lexer.lex(string)
#while True:
#    token = lexed.next()
#    if token is not None:
#        print(token)
#    else:
#        break
parsed = parser.parse(lexed, state=state)
print(parsed.eval(state))
