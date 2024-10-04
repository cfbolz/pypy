# Generated by ruleopt/generate.py, don't edit!

from rpython.jit.metainterp.history import ConstInt
from rpython.jit.metainterp.optimizeopt.util import (
    get_box_replacement)
from rpython.jit.metainterp.resoperation import rop

from rpython.rlib.rarithmetic import LONG_BIT, r_uint, intmask, ovfcheck, uint_mul_high

class OptIntAutoGenerated(object):
    _all_rules_fired = []
    _rule_names_int_add = ['add_zero', 'add_reassoc_consts']
    _rule_fired_int_add = [0] * 2
    _all_rules_fired.append((_rule_names_int_add, _rule_fired_int_add))
    def optimize_INT_ADD(self, op):
        arg_0 = get_box_replacement(op.getarg(0))
        b_arg_0 = self.getintbound(arg_0)
        arg_1 = get_box_replacement(op.getarg(1))
        b_arg_1 = self.getintbound(arg_1)
        # add_zero: int_add(x, 0) => x
        if b_arg_1.known_eq_const(0):
            self.make_equal_to(op, arg_0)
            self._rule_fired_int_add[0] += 1
            return
        # add_zero: int_add(0, x) => x
        if b_arg_0.known_eq_const(0):
            self.make_equal_to(op, arg_1)
            self._rule_fired_int_add[0] += 1
            return
        # add_reassoc_consts: int_add(int_add(x, C1), C2) => int_add(x, C)
        arg_0_int_add = self.optimizer.as_operation(arg_0, rop.INT_ADD)
        if arg_0_int_add is not None:
            arg_0_int_add_0 = get_box_replacement(arg_0.getarg(0))
            b_arg_0_int_add_0 = self.getintbound(arg_0_int_add_0)
            arg_0_int_add_1 = get_box_replacement(arg_0.getarg(1))
            b_arg_0_int_add_1 = self.getintbound(arg_0_int_add_1)
            if b_arg_0_int_add_1.is_constant():
                C_arg_0_int_add_1 = b_arg_0_int_add_1.get_constant_int()
                if b_arg_1.is_constant():
                    C_arg_1 = b_arg_1.get_constant_int()
                    C = intmask(r_uint(C_arg_0_int_add_1) + r_uint(C_arg_1))
                    newop = self.replace_op_with(op, rop.INT_ADD, args=[arg_0_int_add_0, ConstInt(C)])
                    self.optimizer.send_extra_operation(newop)
                    self._rule_fired_int_add[1] += 1
                    return
        # add_reassoc_consts: int_add(C2, int_add(x, C1)) => int_add(x, C)
        if b_arg_0.is_constant():
            C_arg_0 = b_arg_0.get_constant_int()
            arg_1_int_add = self.optimizer.as_operation(arg_1, rop.INT_ADD)
            if arg_1_int_add is not None:
                arg_1_int_add_0 = get_box_replacement(arg_1.getarg(0))
                b_arg_1_int_add_0 = self.getintbound(arg_1_int_add_0)
                arg_1_int_add_1 = get_box_replacement(arg_1.getarg(1))
                b_arg_1_int_add_1 = self.getintbound(arg_1_int_add_1)
                if b_arg_1_int_add_1.is_constant():
                    C_arg_1_int_add_1 = b_arg_1_int_add_1.get_constant_int()
                    C = intmask(r_uint(C_arg_1_int_add_1) + r_uint(C_arg_0))
                    newop = self.replace_op_with(op, rop.INT_ADD, args=[arg_1_int_add_0, ConstInt(C)])
                    self.optimizer.send_extra_operation(newop)
                    self._rule_fired_int_add[1] += 1
                    return
        # add_reassoc_consts: int_add(int_add(C1, x), C2) => int_add(x, C)
        arg_0_int_add = self.optimizer.as_operation(arg_0, rop.INT_ADD)
        if arg_0_int_add is not None:
            arg_0_int_add_0 = get_box_replacement(arg_0.getarg(0))
            b_arg_0_int_add_0 = self.getintbound(arg_0_int_add_0)
            arg_0_int_add_1 = get_box_replacement(arg_0.getarg(1))
            b_arg_0_int_add_1 = self.getintbound(arg_0_int_add_1)
            if b_arg_0_int_add_0.is_constant():
                C_arg_0_int_add_0 = b_arg_0_int_add_0.get_constant_int()
                if b_arg_1.is_constant():
                    C_arg_1 = b_arg_1.get_constant_int()
                    C = intmask(r_uint(C_arg_0_int_add_0) + r_uint(C_arg_1))
                    newop = self.replace_op_with(op, rop.INT_ADD, args=[arg_0_int_add_1, ConstInt(C)])
                    self.optimizer.send_extra_operation(newop)
                    self._rule_fired_int_add[1] += 1
                    return
        # add_reassoc_consts: int_add(C2, int_add(C1, x)) => int_add(x, C)
        if b_arg_0.is_constant():
            C_arg_0 = b_arg_0.get_constant_int()
            arg_1_int_add = self.optimizer.as_operation(arg_1, rop.INT_ADD)
            if arg_1_int_add is not None:
                arg_1_int_add_0 = get_box_replacement(arg_1.getarg(0))
                b_arg_1_int_add_0 = self.getintbound(arg_1_int_add_0)
                arg_1_int_add_1 = get_box_replacement(arg_1.getarg(1))
                b_arg_1_int_add_1 = self.getintbound(arg_1_int_add_1)
                if b_arg_1_int_add_0.is_constant():
                    C_arg_1_int_add_0 = b_arg_1_int_add_0.get_constant_int()
                    C = intmask(r_uint(C_arg_1_int_add_0) + r_uint(C_arg_0))
                    newop = self.replace_op_with(op, rop.INT_ADD, args=[arg_1_int_add_1, ConstInt(C)])
                    self.optimizer.send_extra_operation(newop)
                    self._rule_fired_int_add[1] += 1
                    return
        return self.emit(op)
    _rule_names_int_eq = ['eq_different_knownbits', 'eq_same', 'eq_one', 'eq_zero']
    _rule_fired_int_eq = [0] * 4
    _all_rules_fired.append((_rule_names_int_eq, _rule_fired_int_eq))
    def optimize_INT_EQ(self, op):
        arg_0 = get_box_replacement(op.getarg(0))
        b_arg_0 = self.getintbound(arg_0)
        arg_1 = get_box_replacement(op.getarg(1))
        b_arg_1 = self.getintbound(arg_1)
        # eq_different_knownbits: int_eq(x, y) => 0
        if b_arg_0.known_ne(b_arg_1):
            self.make_constant_int(op, 0)
            self._rule_fired_int_eq[0] += 1
            return
        # eq_different_knownbits: int_eq(y, x) => 0
        if b_arg_1.known_ne(b_arg_0):
            self.make_constant_int(op, 0)
            self._rule_fired_int_eq[0] += 1
            return
        # eq_same: int_eq(x, x) => 1
        if arg_1 is arg_0:
            self.make_constant_int(op, 1)
            self._rule_fired_int_eq[1] += 1
            return
        # eq_same: int_eq(x, x) => 1
        if arg_1 is arg_0:
            self.make_constant_int(op, 1)
            self._rule_fired_int_eq[1] += 1
            return
        # eq_one: int_eq(x, 1) => x
        if b_arg_1.known_eq_const(1):
            if b_arg_0.is_bool():
                self.make_equal_to(op, arg_0)
                self._rule_fired_int_eq[2] += 1
                return
        # eq_one: int_eq(1, x) => x
        if b_arg_0.known_eq_const(1):
            if b_arg_1.is_bool():
                self.make_equal_to(op, arg_1)
                self._rule_fired_int_eq[2] += 1
                return
        # eq_zero: int_eq(x, 0) => int_is_zero(x)
        if b_arg_1.known_eq_const(0):
            newop = self.replace_op_with(op, rop.INT_IS_ZERO, args=[arg_0])
            self.optimizer.send_extra_operation(newop)
            self._rule_fired_int_eq[3] += 1
            return
        # eq_zero: int_eq(0, x) => int_is_zero(x)
        if b_arg_0.known_eq_const(0):
            newop = self.replace_op_with(op, rop.INT_IS_ZERO, args=[arg_1])
            self.optimizer.send_extra_operation(newop)
            self._rule_fired_int_eq[3] += 1
            return
        return self.emit(op)
    _rule_names_int_ne = ['ne_same', 'ne_different_knownbits', 'ne_zero']
    _rule_fired_int_ne = [0] * 3
    _all_rules_fired.append((_rule_names_int_ne, _rule_fired_int_ne))
    def optimize_INT_NE(self, op):
        arg_0 = get_box_replacement(op.getarg(0))
        b_arg_0 = self.getintbound(arg_0)
        arg_1 = get_box_replacement(op.getarg(1))
        b_arg_1 = self.getintbound(arg_1)
        # ne_same: int_ne(x, x) => 0
        if arg_1 is arg_0:
            self.make_constant_int(op, 0)
            self._rule_fired_int_ne[0] += 1
            return
        # ne_same: int_ne(x, x) => 0
        if arg_1 is arg_0:
            self.make_constant_int(op, 0)
            self._rule_fired_int_ne[0] += 1
            return
        # ne_different_knownbits: int_ne(x, y) => 1
        if b_arg_0.known_ne(b_arg_1):
            self.make_constant_int(op, 1)
            self._rule_fired_int_ne[1] += 1
            return
        # ne_different_knownbits: int_ne(y, x) => 1
        if b_arg_1.known_ne(b_arg_0):
            self.make_constant_int(op, 1)
            self._rule_fired_int_ne[1] += 1
            return
        # ne_zero: int_ne(x, 0) => int_is_true(x)
        if b_arg_1.known_eq_const(0):
            newop = self.replace_op_with(op, rop.INT_IS_TRUE, args=[arg_0])
            self.optimizer.send_extra_operation(newop)
            self._rule_fired_int_ne[2] += 1
            return
        # ne_zero: int_ne(0, x) => int_is_true(x)
        if b_arg_0.known_eq_const(0):
            newop = self.replace_op_with(op, rop.INT_IS_TRUE, args=[arg_1])
            self.optimizer.send_extra_operation(newop)
            self._rule_fired_int_ne[2] += 1
            return
        return self.emit(op)
    _rule_names_int_force_ge_zero = ['force_ge_zero_neg', 'force_ge_zero_pos']
    _rule_fired_int_force_ge_zero = [0] * 2
    _all_rules_fired.append((_rule_names_int_force_ge_zero, _rule_fired_int_force_ge_zero))
    def optimize_INT_FORCE_GE_ZERO(self, op):
        arg_0 = get_box_replacement(op.getarg(0))
        b_arg_0 = self.getintbound(arg_0)
        # force_ge_zero_neg: int_force_ge_zero(x) => 0
        if b_arg_0.known_lt_const(0):
            self.make_constant_int(op, 0)
            self._rule_fired_int_force_ge_zero[0] += 1
            return
        # force_ge_zero_pos: int_force_ge_zero(x) => x
        if b_arg_0.known_nonnegative():
            self.make_equal_to(op, arg_0)
            self._rule_fired_int_force_ge_zero[1] += 1
            return
        return self.emit(op)