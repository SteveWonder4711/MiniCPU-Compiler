use regex::Regex;
use std::fmt;

#[allow(dead_code)]
struct EbnfRule<'a> {
    name: &'a str,
    rule: EbnfStatement<'a>,
}

struct EbnfParser<'a, 'b> {
    input: &'b str,
    currentline: i32,
    currentcolumn: i32,
    rules: Vec<EbnfRule<'a>>,
    charnum: i64,
}

struct EbnfPartial<'a> {
    starttoken: i64,
    currenttoken: i64,
    statement: EbnfStatement<'a>,
    isterminal: bool,
}

enum EbnfStatement<'a> {
    StringTerminal {
        string: &'a str,
    },
    RegexTerminal {
        string: &'a str,
    },
    DefinedRule {
        rulename: &'a str,
    },
    Concatenation {
        rules: Vec<Box<EbnfStatement<'a>>>,
    },
    Optional {
        rule: Box<EbnfStatement<'a>>,
    },
    OneOrMore {
        rule: Box<EbnfStatement<'a>>,
    },
    ZeroOrMore {
        rule: Box<EbnfStatement<'a>>,
    },
    /*Repetition {
        rule: Box<EbnfStatement<'a>>,
        minamount: i32,
        maxamount: i32,
    },*/
    Or {
        left: Box<EbnfStatement<'a>>,
        right: Box<EbnfStatement<'a>>,
    },
}

struct ParseEbnfError {
    line: i32,
    column: i32,
    errtype: ParseEbnfErrorType,
}

enum ParseEbnfErrorType {
    UnclosedString,
    UnclosedParen,
    UnexpectedCharacter(char),
    EmptyRule,
}

impl fmt::Display for ParseEbnfError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let errtype = &self.errtype;
        let line = self.line;
        let column = self.column;
        match errtype {
            ParseEbnfErrorType::UnclosedString => {
                write!(
                    f,
                    "Unclosed String, expected '\"' at line {line}, column {column}!"
                )
            }
            ParseEbnfErrorType::UnexpectedCharacter(character) => {
                write!(
                    f,
                    "Unexpected '{character}' at line {line}, column {column}!"
                )
            }
            ParseEbnfErrorType::EmptyRule => {
                write!(f, "Empty rule in line {line}, column {column}!")
            }
            ParseEbnfErrorType::UnclosedParen => {
                write!(f, "Unclosed Parentheses, expected ')' at ")
            }
        }
    }
}

impl fmt::Debug for ParseEbnfError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{self}")
    }
}

impl<'a> fmt::Display for EbnfStatement<'a> {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            EbnfStatement::StringTerminal { string } => write!(f, "\"{string}\""),
            EbnfStatement::RegexTerminal { string } => write!(f, "/{string}/"),
            EbnfStatement::DefinedRule { rulename } => write!(f, "{rulename}"),
            EbnfStatement::Concatenation { rules } => write!(
                f,
                "Concatenation: ({})",
                rules.into_iter().fold(String::new(), |string, rule| string
                    + " "
                    + &(*rule.to_string()))
            ),
            EbnfStatement::Optional { rule } => write!(f, "Optional: {}", rule),
            /*EbnfStatement::Repetition {
                rule,
                minamount,
                maxamount,
            } => write!(f, "{rule}{{{minamount},{maxamount}}}"),*/
            EbnfStatement::Or { left, right } => write!(f, "{left} | {right}"),
            EbnfStatement::OneOrMore { rule } => write!(f, "{rule}+"),
            EbnfStatement::ZeroOrMore { rule } => write!(f, "{rule}*"),
        }
    }
}

impl<'a> fmt::Display for EbnfPartial<'a> {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let statement = &self.statement;
        if let EbnfStatement::Concatenation { rules } = statement {
            let mut out = String::new();
            for (i, rule) in rules.iter().enumerate() {
                if i as i64 == self.currenttoken {
                    out += "°";
                }
                out.push_str(format!("{rule} ").as_str());
            }
            write!(f, "{out}")
        } else {
            let statement = &self.statement;
            if self.currenttoken == 0 {
                write!(f, "° {statement}")
            } else {
                write!(f, "{statement}°")
            }
        }
    }
}

impl<'a> EbnfStatement<'a> {
    fn new(s: &'a str, startline: i32, startcolumn: i32) -> Result<Self, ParseEbnfError> {
        let mut parsedrules: Vec<EbnfStatement> = Vec::new();
        let characters = s.chars();
        let mut matchstart = 0;
        let mut currentcolumn: i32 = startcolumn;
        let mut currentline: i32 = startline;
        let mut stringparse = false;
        let mut escaped = false;
        let mut bracketparse = false;
        let mut bracketlevel = 0;
        let mut regexparse = false;

        for (i, char) in characters.enumerate() {
            //parsing strings
            if escaped {
                escaped = false;
            } else if stringparse {
                if char == '"' {
                    stringparse = false;
                    parsedrules.push(EbnfStatement::StringTerminal {
                        string: &s[matchstart + 1..i],
                    });
                    matchstart = i + 1;
                } else if char == '\n' {
                    return Err(ParseEbnfError {
                        line: currentline,
                        column: currentcolumn,
                        errtype: ParseEbnfErrorType::UnexpectedCharacter(char.to_owned()),
                    });
                } else if char == '\\' {
                    escaped = true;
                }
            }
            //parsing brackets
            else if bracketparse {
                if char == '(' {
                    bracketlevel += 1;
                }
                if char == ')' {
                    bracketlevel -= 1;
                    if bracketlevel == 0 {
                        bracketparse = false;
                        parsedrules.push(EbnfStatement::new(
                            &s[matchstart + 1..i],
                            currentline,
                            currentcolumn,
                        )?);
                        matchstart = i + 1;
                    }
                }
            }
            //parsing regex
            else if regexparse {
                if char == '/' {
                    regexparse = false;
                    parsedrules.push(EbnfStatement::RegexTerminal {
                        string: &s[matchstart + 1..i],
                    });
                    matchstart = i + 1;
                }
            }
            //parsing regular rule names, split by space, newline or tab
            else if [' ', '\n', '\t'].contains(&char) {
                if matchstart != i {
                    parsedrules.push(EbnfStatement::DefinedRule {
                        rulename: &s[matchstart..i],
                    });
                }
                matchstart = i + 1;
            } else if char == '"' {
                stringparse = true;
            } else if char == '(' {
                bracketparse = true;
                bracketlevel = 1;
            } else if char == '/' {
                regexparse = true;
            } else if char == '?' {
                if parsedrules.len() == 0 {
                    return Err(ParseEbnfError {
                        line: currentline,
                        column: currentcolumn,
                        errtype: ParseEbnfErrorType::EmptyRule,
                    });
                }
                let lastrule = parsedrules.pop().expect("");

                parsedrules.push(EbnfStatement::Optional {
                    rule: Box::new(lastrule),
                });
                matchstart = i + 1;
            } else if char == '*' {
                if parsedrules.len() == 0 {
                    return Err(ParseEbnfError {
                        line: currentline,
                        column: currentcolumn,
                        errtype: ParseEbnfErrorType::EmptyRule,
                    });
                }
                let lastrule = parsedrules.pop().expect("");

                parsedrules.push(EbnfStatement::ZeroOrMore {
                    rule: Box::new(lastrule),
                });
                matchstart = i + 1;
            } else if char == '+' {
                if parsedrules.len() == 0 {
                    return Err(ParseEbnfError {
                        line: currentline,
                        column: currentcolumn,
                        errtype: ParseEbnfErrorType::EmptyRule,
                    });
                }
                let lastrule = parsedrules.pop().expect("");

                parsedrules.push(EbnfStatement::OneOrMore {
                    rule: Box::new(lastrule),
                });
                matchstart = i + 1;
            } else if char == '|' {
                let left: Box<EbnfStatement> = match parsedrules.len() {
                    0 => {
                        return Err(ParseEbnfError {
                            line: currentline,
                            column: currentcolumn,
                            errtype: ParseEbnfErrorType::EmptyRule,
                        });
                    }
                    1 => Box::new(parsedrules.pop().expect("")),
                    _ => {
                        let mut concatrules: Vec<Box<EbnfStatement>> = Vec::new();
                        while parsedrules.len() > 0 {
                            concatrules.push(Box::new(parsedrules.remove(0)));
                        }
                        Box::new(EbnfStatement::Concatenation { rules: concatrules })
                    }
                };
                let right: Box<EbnfStatement> = Box::new(EbnfStatement::new(
                    &s[i + 1..],
                    currentline,
                    currentcolumn + 1,
                )?);
                return Ok(EbnfStatement::Or {
                    left: left,
                    right: right,
                });
            }

            if char == '\n' {
                currentcolumn = 0;
                currentline += 1;
            }

            currentcolumn += 1;
        }

        if stringparse {
            return Err(ParseEbnfError {
                line: currentline,
                column: currentcolumn,
                errtype: ParseEbnfErrorType::UnclosedString,
            });
        }

        if bracketparse {
            return Err(ParseEbnfError {
                line: currentline,
                column: currentcolumn,
                errtype: ParseEbnfErrorType::UnclosedParen,
            });
        }

        if matchstart < s.len() {
            parsedrules.push(EbnfStatement::DefinedRule {
                rulename: &s[matchstart..],
            });
        }

        if parsedrules.len() == 1 {
            let rule = parsedrules.pop();
            return Ok(rule.expect("This is not supposed to happen"));
        } else if parsedrules.len() > 0 {
            let mut concatrules: Vec<Box<EbnfStatement>> = Vec::new();
            while parsedrules.len() > 0 {
                concatrules.push(Box::new(parsedrules.remove(0)));
            }
            return Ok(EbnfStatement::Concatenation { rules: concatrules });
        } else {
            return Err(ParseEbnfError {
                line: currentline,
                column: currentcolumn,
                errtype: ParseEbnfErrorType::EmptyRule,
            });
        }
    }
}

impl<'a, 'b> EbnfParser<'a, 'b> {
    fn from_str(s: &'a str) -> Result<Self, ParseEbnfError> {
        let mut parsename = false;
        let mut parsebody = false;
        let mut matchstart = 0;
        let mut currentline = 0;
        let mut currentcolumn = 0;
        let mut rulename = "";
        let mut parsedstatements: Vec<EbnfRule<'a>> = Vec::new();
        let mut i = 0;

        for char in s.chars() {
            if parsename {
                if char == ':' {
                    rulename = &s[matchstart..i];
                    parsename = false;
                    parsebody = true;
                    matchstart = i + 1;
                } else if !char.is_alphanumeric() {
                    return Err(ParseEbnfError {
                        line: currentline,
                        column: currentcolumn,
                        errtype: ParseEbnfErrorType::UnexpectedCharacter(char),
                    });
                }
                currentcolumn += 1;
            } else if parsebody {
                let parserule = {
                    let mut parsedrules: Vec<EbnfStatement> = Vec::new();
                    let mut stringparse = false;
                    let mut escaped = false;
                    let mut bracketparse = false;
                    let mut bracketlevel = 0;
                    let mut regexparse = false;
                    let mut out: Option<EbnfStatement> = None;
                    let mut outfound = false;
                    let parsestart = matchstart;

                    for (x, char) in s[matchstart..].chars().enumerate() {
                        let i = x + parsestart;
                        //parsing strings
                        if escaped {
                            escaped = false;
                        } else if stringparse {
                            if char == '"' {
                                stringparse = false;
                                parsedrules.push(EbnfStatement::StringTerminal {
                                    string: &s[matchstart + 1..i],
                                });
                                matchstart = i + 1;
                            } else if char == '\n' {
                                return Err(ParseEbnfError {
                                    line: currentline,
                                    column: currentcolumn,
                                    errtype: ParseEbnfErrorType::UnexpectedCharacter(
                                        char.to_owned(),
                                    ),
                                });
                            } else if char == '\\' {
                                escaped = true;
                            }
                        }
                        //parsing brackets
                        else if bracketparse {
                            if char == '(' {
                                bracketlevel += 1;
                            }
                            if char == ')' {
                                bracketlevel -= 1;
                                if bracketlevel == 0 {
                                    bracketparse = false;
                                    parsedrules.push(EbnfStatement::new(
                                        &s[matchstart + 1..i],
                                        currentline,
                                        currentcolumn,
                                    )?);
                                    matchstart = i + 1;
                                }
                            }
                        }
                        //parsing regex
                        else if regexparse {
                            if char == '/' {
                                regexparse = false;
                                parsedrules.push(EbnfStatement::RegexTerminal {
                                    string: &s[matchstart + 1..i],
                                });
                                matchstart = i + 1;
                            }
                        }
                        //parsing regular rule names, split by space, newline or tab
                        else if [' ', '\n', '\t'].contains(&char) {
                            if matchstart != i {
                                parsedrules.push(EbnfStatement::DefinedRule {
                                    rulename: &s[matchstart..i],
                                });
                            }
                            matchstart = i + 1;
                        } else if char == '"' {
                            stringparse = true;
                        } else if char == '(' {
                            bracketparse = true;
                            bracketlevel = 1;
                        } else if char == '/' {
                            regexparse = true;
                        } else if char == '?' {
                            if parsedrules.len() == 0 {
                                return Err(ParseEbnfError {
                                    line: currentline,
                                    column: currentcolumn,
                                    errtype: ParseEbnfErrorType::EmptyRule,
                                });
                            }
                            let lastrule = parsedrules.pop().expect("");

                            parsedrules.push(EbnfStatement::Optional {
                                rule: Box::new(lastrule),
                            });
                            matchstart = i + 1;
                        } else if char == '*' {
                            if parsedrules.len() == 0 {
                                return Err(ParseEbnfError {
                                    line: currentline,
                                    column: currentcolumn,
                                    errtype: ParseEbnfErrorType::EmptyRule,
                                });
                            }
                            let lastrule = parsedrules.pop().expect("");

                            parsedrules.push(EbnfStatement::ZeroOrMore {
                                rule: Box::new(lastrule),
                            });
                            matchstart = i + 1;
                        } else if char == '+' {
                            if parsedrules.len() == 0 {
                                return Err(ParseEbnfError {
                                    line: currentline,
                                    column: currentcolumn,
                                    errtype: ParseEbnfErrorType::EmptyRule,
                                });
                            }
                            let lastrule = parsedrules.pop().expect("");

                            parsedrules.push(EbnfStatement::OneOrMore {
                                rule: Box::new(lastrule),
                            });
                            matchstart = i + 1;
                        } else if char == '|' {
                            let left: Box<EbnfStatement> = match parsedrules.len() {
                                0 => {
                                    return Err(ParseEbnfError {
                                        line: currentline,
                                        column: currentcolumn,
                                        errtype: ParseEbnfErrorType::EmptyRule,
                                    });
                                }
                                1 => Box::new(parsedrules.pop().expect("")),
                                _ => {
                                    let mut concatrules: Vec<Box<EbnfStatement>> = Vec::new();
                                    while parsedrules.len() > 0 {
                                        concatrules.push(Box::new(parsedrules.remove(0)));
                                    }
                                    Box::new(EbnfStatement::Concatenation { rules: concatrules })
                                }
                            };
                            let right: Box<EbnfStatement> = Box::new(EbnfStatement::new(
                                &s[i + 1..],
                                currentline,
                                currentcolumn + 1,
                            )?);
                            out = Some(EbnfStatement::Or {
                                left: left,
                                right: right,
                            });
                            outfound = true;
                        } else if char == ';' {
                            break;
                        }

                        if char == '\n' {
                            println!("linebreak");
                            currentcolumn = 0;
                            currentline += 1;
                        }

                        currentcolumn += 1;
                    }

                    if stringparse {
                        return Err(ParseEbnfError {
                            line: currentline,
                            column: currentcolumn,
                            errtype: ParseEbnfErrorType::UnclosedString,
                        });
                    }

                    if bracketparse {
                        return Err(ParseEbnfError {
                            line: currentline,
                            column: currentcolumn,
                            errtype: ParseEbnfErrorType::UnclosedParen,
                        });
                    }

                    if outfound {
                    } else if parsedrules.len() == 1 {
                        let rule = parsedrules.pop();
                        out = Some(rule.expect("This is not supposed to happen"));
                    } else if parsedrules.len() > 0 {
                        let mut concatrules: Vec<Box<EbnfStatement>> = Vec::new();
                        while parsedrules.len() > 0 {
                            concatrules.push(Box::new(parsedrules.remove(0)));
                        }
                        out = Some(EbnfStatement::Concatenation { rules: concatrules });
                    } else {
                        return Err(ParseEbnfError {
                            line: currentline,
                            column: currentcolumn,
                            errtype: ParseEbnfErrorType::EmptyRule,
                        });
                    }
                    parsebody = false;
                    match out {
                        Some(rule) => Ok(rule),
                        None => Err(ParseEbnfError {
                            line: currentline,
                            column: currentcolumn,
                            errtype: ParseEbnfErrorType::EmptyRule,
                        }),
                    }
                }?;
                println!("{rulename}, {parserule}");
                parsedstatements.push(EbnfRule {
                    name: rulename,
                    rule: parserule,
                });
            } else {
                if char.is_alphanumeric() {
                    println!("found a rule start at line {currentline}, column {currentcolumn}");
                    matchstart = i;
                    parsename = true;
                }
                currentcolumn += 1;
            }
            if char == '\n' {
                println!("Linebreak");
                currentline += 1;
                currentcolumn = 0;
            }
            i += 1;
        }

        Ok(EbnfParser {
            input: "",
            currentline: 0,
            currentcolumn: 0,
            rules: parsedstatements,
            charnum: 0,
        })
    }
}

fn main() {
    println!();

    let parser = EbnfParser::from_str("test: \"haiiii :3\";\n woof: test ;");

    match parser {
        Err(err) => println!("{err}"),
        _ => {}
    }
}
