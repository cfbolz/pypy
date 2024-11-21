#! /usr/bin/env python
"""Module gendfa

Generates finite state automata for recognizing Python tokens.  These are hand
coded versions of the regular expressions originally appearing in Ping's
tokenize module in the Python standard library.

When run from the command line, this should pretty print the DFA machinery.

To regenerate the dfa, run::

    $ python gendfa.py > dfa_generated.py

$Id: genPytokenize.py,v 1.1 2003/10/02 17:37:17 jriehl Exp $
"""

from pypy.interpreter.pyparser.pylexer import *
from pypy.interpreter.pyparser.automata import NonGreedyDFA, DFA, DEFAULT
from pypy.interpreter.pyparser import pygram

def makePyPseudoDFA ():
    import string
    states = []
    labels = {}
    def makeEOL():
        return group(states,
                     newArcPair(states, "\n"),
                     chain(states,
                           newArcPair(states, "\r"),
                           maybe(states, newArcPair(states, "\n"))))
    # ____________________________________________________________
    def makeLineCont ():
        return chain(states,
                     newArcPair(states, "\\"),
                     makeEOL())
    # ____________________________________________________________
    # Ignore stuff
    def makeWhitespace ():
        return any(states, groupStr(states, " \f\t"))
    # ____________________________________________________________
    def makeComment ():
        return chain(states,
                     newArcPair(states, "#"),
                     any(states, notGroupStr(states, "\r\n")))
    # ____________________________________________________________
    # Names
    name = chain(states,
                 groupStr(states, string.letters + "_"),
                 any(states, groupStr(states,
                                      string.letters + string.digits + "_")))
    label(labels, name, "NAME")
    # ____________________________________________________________
    # Digits
    def makeDigits ():
        return groupStr(states, "0123456789")
    # ____________________________________________________________
    # Integer numbers
    hexNumber = chain(states,
                      newArcPair(states, "0"),
                      groupStr(states, "xX"),
                      atleastonce(states,
                                  groupStr(states, "0123456789abcdefABCDEF")),
                      maybe(states, groupStr(states, "lL")))
    octNumber = chain(states,
                      newArcPair(states, "0"),
                      maybe(states,
                            chain(states,
                                  groupStr(states, "oO"),
                                  groupStr(states, "01234567"))),
                      any(states, groupStr(states, "01234567")),
                      maybe(states, groupStr(states, "lL")))
    binNumber = chain(states,
                      newArcPair(states, "0"),
                      groupStr(states, "bB"),
                      atleastonce(states, groupStr(states, "01")),
                      maybe(states, groupStr(states, "lL")))
    decNumber = chain(states,
                      groupStr(states, "123456789"),
                      any(states, makeDigits()),
                      maybe(states, groupStr(states, "lL")))
    intNumber = group(states, hexNumber, octNumber, binNumber, decNumber)
    # ____________________________________________________________
    # Exponents
    def makeExp ():
        return chain(states,
                     groupStr(states, "eE"),
                     maybe(states, groupStr(states, "+-")),
                     atleastonce(states, makeDigits()))
    # ____________________________________________________________
    # Floating point numbers
    def makeFloat ():
        pointFloat = chain(states,
                           group(states,
                                 chain(states,
                                       atleastonce(states, makeDigits()),
                                       newArcPair(states, "."),
                                       any(states, makeDigits())),
                                 chain(states,
                                       newArcPair(states, "."),
                                       atleastonce(states, makeDigits()))),
                           maybe(states, makeExp()))
        expFloat = chain(states,
                         atleastonce(states, makeDigits()),
                         makeExp())
        return group(states, pointFloat, expFloat)
    # ____________________________________________________________
    # Imaginary numbers
    imagNumber = group(states,
                       chain(states,
                             atleastonce(states, makeDigits()),
                             groupStr(states, "jJ")),
                       chain(states,
                             makeFloat(),
                             groupStr(states, "jJ")))
    # ____________________________________________________________
    # Any old number
    number = group(states, imagNumber, makeFloat(), intNumber)
    label(labels, number, "NUMBER")

    # ____________________________________________________________
    # Funny
    # generate from pytoken
    funny = []
    for op in sorted(pygram.python_opmap):
        if op == "$NUM":
            continue
        funny.append(chain(states, chainStr(states, op)))
        label(labels, funny[-1], op)
    revdb_metavar = chain(states,
                          groupStr(states, "$"),
                          atleastonce(states, makeDigits()))
    label(labels, revdb_metavar, "REVDBMETAVAR")
    funny.append(revdb_metavar)
    eol = makeEOL()
    label(labels, eol, "NEWLINE")
    funny.append(eol)
    funny = group(states, *funny)
    # ____________________________________________________________
    def makeStrPrefix ():
        return chain(states,
                     maybe(states, groupStr(states, "uUbB")),
                     maybe(states, groupStr(states, "rR")))
    # ____________________________________________________________
    def makeStr(quote):
        regular_end = newArcPair(states, quote)
        # add a label to the closing quote where a string is finished on one
        # line
        label(labels, regular_end, "STRING")
        continuation_end = makeLineCont()
        label(labels, continuation_end, "TOK_STRING_CONTINUATION")
        return chain(
            states,
            makeStrPrefix(),
            newArcPair(states, quote),
            any(states,
                notGroupStr(states, "\r\n%s\\" % quote)),
            any(states,
                chain(states,
                      newArcPair(states, "\\"),
                      newArcPair(states, DEFAULT),
                      any(states,
                          notGroupStr(states, "\r\n%s\\" % quote)))),
            group(states,
                  regular_end,
                  continuation_end))
    contStr = group(states,
                    makeStr('"'),
                    makeStr("'"))
    triple = chain(states,
                   makeStrPrefix(),
                   group(states,
                         chainStr(states, "'''"),
                         chainStr(states, '"""')))
    label(labels, triple, "TOK_TRIPLE_QUOTE_START")
    comment = makeComment()
    label(labels, comment, "TOK_COMMENT")
    linecont = makeLineCont()
    label(labels, linecont, "TOK_LINECONT")
    pseudoExtras = group(states,
                         linecont,
                         comment,
                         triple)
    pseudoToken = chain(states,
                        makeWhitespace(),
                        group(states,
                              newArcPair(states, EMPTY),
                              pseudoExtras, number, funny, contStr, name))
    label(labels, pseudoToken, "ACCEPT")
    dfaStates, dfaAccepts = nfaToDfa(states, pseudoToken[0], labels)
    #view(dfaStates, dfaAccepts)

    # make accepting states to tokens or -1
    state_to_token = []
    accepts = []
    for i, labels_of_state in enumerate(dfaAccepts):
        accepts.append(len(labels_of_state) != 0)
        tokenid = -2
        if labels_of_state:
            if labels_of_state == frozenset(["ACCEPT"]):
                tokenid = -1
            else:
                rest = labels_of_state - frozenset(["ACCEPT"])
                statelabel, = rest
                tokenid = getattr(pygram.tokens, statelabel, None)
                if tokenid is None:
                    tokenid = pygram.python_opmap[statelabel]
        state_to_token.append(tokenid)
    return DFA(dfaStates, accepts), dfaStates, state_to_token

# ______________________________________________________________________

def makePyEndDFAMap ():
    states = []
    single = chain(states,
                   any(states, notGroupStr(states, "'\\")),
                   any(states,
                       chain(states,
                             newArcPair(states, "\\"),
                             newArcPair(states, DEFAULT),
                             any(states, notGroupStr(states, "'\\")))),
                   newArcPair(states, "'"))
    states, accepts = nfaToDfa(states, *single)
    singleDFA = DFA(states, accepts)
    states_singleDFA = states
    states = []
    double = chain(states,
                   any(states, notGroupStr(states, '"\\')),
                   any(states,
                       chain(states,
                             newArcPair(states, "\\"),
                             newArcPair(states, DEFAULT),
                             any(states, notGroupStr(states, '"\\')))),
                   newArcPair(states, '"'))
    states, accepts = nfaToDfa(states, *double)
    doubleDFA = DFA(states, accepts)
    states_doubleDFA = states
    states = []
    single3 = chain(states,
                    any(states, notGroupStr(states, "'\\")),
                    any(states,
                        chain(states,
                              group(states,
                                    chain(states,
                                          newArcPair(states, "\\"),
                                          newArcPair(states, DEFAULT)),
                                    chain(states,
                                          newArcPair(states, "'"),
                                          notChainStr(states, "''"))),
                              any(states, notGroupStr(states, "'\\")))),
                    chainStr(states, "'''"))
    states, accepts = nfaToDfa(states, *single3)
    single3DFA = NonGreedyDFA(states, accepts)
    states_single3DFA = states
    states = []
    double3 = chain(states,
                    any(states, notGroupStr(states, '"\\')),
                    any(states,
                        chain(states,
                              group(states,
                                    chain(states,
                                          newArcPair(states, "\\"),
                                          newArcPair(states, DEFAULT)),
                                    chain(states,
                                          newArcPair(states, '"'),
                                          notChainStr(states, '""'))),
                              any(states, notGroupStr(states, '"\\')))),
                    chainStr(states, '"""'))
    states, accepts = nfaToDfa(states, *double3)
    double3DFA = NonGreedyDFA(states, accepts)
    states_double3DFA = states
    map = {"'" : (singleDFA, states_singleDFA),
           '"' : (doubleDFA, states_doubleDFA),
           "r" : None,
           "R" : None,
           "u" : None,
           "U" : None,
           "b" : None,
           "B" : None}
    for uniPrefix in ("", "u", "U", "b", "B", ):
        for rawPrefix in ("", "r", "R"):
            prefix = uniPrefix + rawPrefix
            map[prefix + "'''"] = (single3DFA, states_single3DFA)
            map[prefix + '"""'] = (double3DFA, states_double3DFA)
    return map

# ______________________________________________________________________

def output(name, dfa_class, dfa, states, state_to_token=None):
    import textwrap
    lines = []
    i = 0
    for line in textwrap.wrap(repr(dfa.accepts), width = 50):
        if i == 0:
            lines.append("accepts = ")
        else:
            lines.append("           ")
        lines.append(line)
        lines.append("\n")
        i += 1
    import StringIO
    lines.append("states = [\n")
    for numstate, state in enumerate(states):
        lines.append("    # ")
        lines.append(str(numstate))
        if dfa.accepts[numstate]:
            lines.append(" (accepts)")
        lines.append('\n')
        s = StringIO.StringIO()
        i = 0
        for k, v in sorted(state.items()):
            i += 1
            if k == DEFAULT:
                k = "automata.DEFAULT"
            else:
                k = repr(k)
            s.write(k)
            s.write('::')
            s.write(repr(v))
            if i < len(state):
                s.write(', ')
        s.write('},')
        i = 0
        if len(state) <= 4:
            text = [s.getvalue()]
        else:
            text = textwrap.wrap(s.getvalue(), width=36)
        for line in text:
            line = line.replace('::', ': ')
            if i == 0:
                lines.append('    {')
            else:
                lines.append('     ')
            lines.append(line)
            lines.append('\n')
            i += 1
    lines.append("    ]\n")
    lines.append("%s = automata.%s(states, accepts)\n" % (name, dfa_class))
    lines.append("%s.state_to_token = %s\n" % (name, state_to_token))
    return ''.join(lines)

def main ():
    print "# THIS FILE IS AUTOMATICALLY GENERATED BY gendfa.py"
    print "# DO NOT EDIT"
    print "# TO REGENERATE THE FILE, RUN:"
    print "#     python gendfa.py > dfa_generated.py"
    print
    print "from pypy.interpreter.pyparser import automata"
    pseudoDFA, states_pseudoDFA, state_to_token = makePyPseudoDFA()
    print output("pseudoDFA", "DFA", pseudoDFA, states_pseudoDFA, state_to_token)
    endDFAMap = makePyEndDFAMap()
    dfa, states = endDFAMap['"""']
    print output("double3DFA", "NonGreedyDFA", dfa, states)
    dfa, states = endDFAMap["'''"]
    print output("single3DFA", "NonGreedyDFA", dfa, states)
    dfa, states = endDFAMap["'"]
    print output("singleDFA", "DFA", dfa, states)
    dfa, states = endDFAMap['"']
    print output("doubleDFA", "DFA", dfa, states)

# ______________________________________________________________________

if __name__ == "__main__":
    main()
