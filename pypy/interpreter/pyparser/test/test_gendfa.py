from pypy.interpreter.pyparser.automata import DFA, DEFAULT
from pypy.interpreter.pyparser.gendfa import output
from pypy.interpreter.pyparser.dfa_generated import pseudoDFA
from pypy.interpreter.pyparser.pygram import tokens, python_opmap

def test_states():
    states = [{"\x00": 1}, {"\x01": 0}]
    d = DFA(states[:], [False, True])
    assert output('test', DFA, d, states) == """\
accepts = [False, True]
states = [
    # 0
    {'\\x00': 1},
    # 1 (accepts)
    {'\\x01': 0},
    ]
test = automata.pypy.interpreter.pyparser.automata.DFA(states, accepts)
test.state_to_token = None
"""

def test_number_bug():
    res = pseudoDFA.recognize("0\n", 0)
    assert res == 1
    assert pseudoDFA.state_to_token[pseudoDFA.last_state] == tokens.NUMBER

