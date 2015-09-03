import py, random

from rpython.rlib.debug import debug_print
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper import rclass
from rpython.rtyper.rclass import (
    OBJECT, OBJECT_VTABLE, FieldListAccessor, IR_QUASIIMMUTABLE)

from rpython.jit.backend.llgraph import runner
from rpython.jit.metainterp.history import (TreeLoop, AbstractDescr,
                                            JitCellToken, TargetToken)
from rpython.jit.metainterp.optimizeopt.util import sort_descrs, equaloplists
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.logger import LogOperations
from rpython.jit.tool.oparser import OpParser
from rpython.jit.metainterp.quasiimmut import QuasiImmutDescr
from rpython.jit.metainterp import compile, resume, history
from rpython.jit.metainterp.jitprof import EmptyProfiler
from rpython.jit.metainterp.counter import DeterministicJitCounter
from rpython.config.translationoption import get_combined_translation_config
from rpython.jit.metainterp.resoperation import rop, ResOperation, InputArgRef
from rpython.jit.metainterp.optimizeopt.util import args_dict


def test_sort_descrs():
    class PseudoDescr(AbstractDescr):
        def __init__(self, n):
            self.n = n
        def sort_key(self):
            return self.n
    for i in range(17):
        lst = [PseudoDescr(j) for j in range(i)]
        lst2 = lst[:]
        random.shuffle(lst2)
        sort_descrs(lst2)
        assert lst2 == lst

def test_equaloplists():
    ops = """
    [i0]
    i1 = int_add(i0, 1)
    i2 = int_add(i1, 1)
    guard_true(i1) [i2]
    jump(i1)
    """
    namespace = {}
    loop1 = pure_parse(ops, namespace=namespace)
    loop2 = pure_parse(ops, namespace=namespace)
    loop3 = pure_parse(ops.replace("i2 = int_add", "i2 = int_sub"),
                       namespace=namespace)
    assert equaloplists(loop1.operations, loop2.operations)
    py.test.raises(AssertionError,
                   "equaloplists(loop1.operations, loop3.operations)")

def test_equaloplists_fail_args():
    ops = """
    [i0]
    i1 = int_add(i0, 1)
    i2 = int_add(i1, 1)
    guard_true(i1) [i2, i1]
    jump(i1)
    """
    namespace = {}
    loop1 = pure_parse(ops, namespace=namespace)
    loop2 = pure_parse(ops.replace("[i2, i1]", "[i1, i2]"),
                       namespace=namespace)
    py.test.raises(AssertionError,
                   "equaloplists(loop1.operations, loop2.operations)")
    assert equaloplists(loop1.operations, loop2.operations,
                        strict_fail_args=False)
    loop3 = pure_parse(ops.replace("[i2, i1]", "[i2, i0]"),
                       namespace=namespace)
    py.test.raises(AssertionError,
                   "equaloplists(loop1.operations, loop3.operations)")

# ____________________________________________________________

class LLtypeMixin(object):
    type_system = 'lltype'

    def get_class_of_box(self, box):
        base = box.getref_base()
        return lltype.cast_opaque_ptr(rclass.OBJECTPTR, base).typeptr

    node_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
    node_vtable.name = rclass.alloc_array_name('node')
    node_vtable_adr = llmemory.cast_ptr_to_adr(node_vtable)
    node_vtable2 = lltype.malloc(OBJECT_VTABLE, immortal=True)
    node_vtable2.name = rclass.alloc_array_name('node2')
    node_vtable_adr2 = llmemory.cast_ptr_to_adr(node_vtable2)
    node_vtable3 = lltype.malloc(OBJECT_VTABLE, immortal=True)
    node_vtable3.name = rclass.alloc_array_name('node3')
    node_vtable_adr3 = llmemory.cast_ptr_to_adr(node_vtable3)
    cpu = runner.LLGraphCPU(None)

    NODE = lltype.GcForwardReference()
    S = lltype.GcForwardReference()
    NODE.become(lltype.GcStruct('NODE', ('parent', OBJECT),
                                        ('value', lltype.Signed),
                                        ('floatval', lltype.Float),
                                        ('charval', lltype.Char),
                                        ('nexttuple', lltype.Ptr(S)),
                                        ('next', lltype.Ptr(NODE))))
    S.become(lltype.GcStruct('TUPLE', ('a', lltype.Signed), ('abis', lltype.Signed),
                        ('b', lltype.Ptr(NODE))))
    NODE2 = lltype.GcStruct('NODE2', ('parent', NODE),
                                     ('other', lltype.Ptr(NODE)))

    NODE3 = lltype.GcForwardReference()
    NODE3.become(lltype.GcStruct('NODE3', ('parent', OBJECT),
                            ('value', lltype.Signed),
                            ('next', lltype.Ptr(NODE3)),
                            hints={'immutable': True}))
    
    node = lltype.malloc(NODE)
    node.value = 5
    node.next = node
    node.parent.typeptr = node_vtable
    nodeaddr = lltype.cast_opaque_ptr(llmemory.GCREF, node)
    #nodebox = InputArgRef(lltype.cast_opaque_ptr(llmemory.GCREF, node))
    node2 = lltype.malloc(NODE2)
    node2.parent.parent.typeptr = node_vtable2
    node2addr = lltype.cast_opaque_ptr(llmemory.GCREF, node2)
    myptr = lltype.cast_opaque_ptr(llmemory.GCREF, node)
    mynode2 = lltype.malloc(NODE)
    mynode2.parent.typeptr = node_vtable
    myptr2 = lltype.cast_opaque_ptr(llmemory.GCREF, mynode2)
    nullptr = lltype.nullptr(llmemory.GCREF.TO)
    #nodebox2 = InputArgRef(lltype.cast_opaque_ptr(llmemory.GCREF, node2))
    nodesize = cpu.sizeof(NODE, node_vtable)
    nodesize2 = cpu.sizeof(NODE2, node_vtable2)
    nodesize3 = cpu.sizeof(NODE3, node_vtable3)
    valuedescr = cpu.fielddescrof(NODE, 'value')
    floatdescr = cpu.fielddescrof(NODE, 'floatval')
    chardescr = cpu.fielddescrof(NODE, 'charval')
    nextdescr = cpu.fielddescrof(NODE, 'next')
    nexttupledescr = cpu.fielddescrof(NODE, 'nexttuple')
    otherdescr = cpu.fielddescrof(NODE2, 'other')
    valuedescr3 = cpu.fielddescrof(NODE3, 'value')
    nextdescr3 = cpu.fielddescrof(NODE3, 'next')
    assert valuedescr3.is_always_pure()
    assert nextdescr3.is_always_pure()

    accessor = FieldListAccessor()
    accessor.initialize(None, {'inst_field': IR_QUASIIMMUTABLE})
    QUASI = lltype.GcStruct('QUASIIMMUT', ('inst_field', lltype.Signed),
                            ('mutate_field', rclass.OBJECTPTR),
                            hints={'immutable_fields': accessor})
    quasisize = cpu.sizeof(QUASI, None)
    quasi = lltype.malloc(QUASI, immortal=True)
    quasi.inst_field = -4247
    quasifielddescr = cpu.fielddescrof(QUASI, 'inst_field')
    quasiptr = lltype.cast_opaque_ptr(llmemory.GCREF, quasi)
    quasiimmutdescr = QuasiImmutDescr(cpu, quasiptr, quasifielddescr,
                                      cpu.fielddescrof(QUASI, 'mutate_field'))

    NODEOBJ = lltype.GcStruct('NODEOBJ', ('parent', OBJECT),
                                         ('ref', lltype.Ptr(OBJECT)))
    nodeobj = lltype.malloc(NODEOBJ)
    nodeobjvalue = lltype.cast_opaque_ptr(llmemory.GCREF, nodeobj)
    refdescr = cpu.fielddescrof(NODEOBJ, 'ref')

    INTOBJ_NOIMMUT = lltype.GcStruct('INTOBJ_NOIMMUT', ('parent', OBJECT),
                                                ('intval', lltype.Signed))
    INTOBJ_IMMUT = lltype.GcStruct('INTOBJ_IMMUT', ('parent', OBJECT),
                                            ('intval', lltype.Signed),
                                            hints={'immutable': True})
    intobj_noimmut_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
    intobj_immut_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
    noimmut_intval = cpu.fielddescrof(INTOBJ_NOIMMUT, 'intval')
    immut_intval = cpu.fielddescrof(INTOBJ_IMMUT, 'intval')
    immut = lltype.malloc(INTOBJ_IMMUT, zero=True)
    immutaddr = lltype.cast_opaque_ptr(llmemory.GCREF, immut)
    noimmut_descr = cpu.sizeof(INTOBJ_NOIMMUT, intobj_noimmut_vtable)
    immut_descr = cpu.sizeof(INTOBJ_IMMUT, intobj_immut_vtable)

    PTROBJ_IMMUT = lltype.GcStruct('PTROBJ_IMMUT', ('parent', OBJECT),
                                            ('ptrval', lltype.Ptr(OBJECT)),
                                            hints={'immutable': True})
    ptrobj_immut_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
    ptrobj_immut_descr = cpu.sizeof(PTROBJ_IMMUT, ptrobj_immut_vtable)
    immut_ptrval = cpu.fielddescrof(PTROBJ_IMMUT, 'ptrval')

    arraydescr = cpu.arraydescrof(lltype.GcArray(lltype.Signed))
    array = lltype.malloc(lltype.GcArray(lltype.Signed), 15, zero=True)
    arrayref = lltype.cast_opaque_ptr(llmemory.GCREF, array)
    array2 = lltype.malloc(lltype.GcArray(lltype.Ptr(S)), 15, zero=True)
    array2ref = lltype.cast_opaque_ptr(llmemory.GCREF, array2)
    gcarraydescr = cpu.arraydescrof(lltype.GcArray(llmemory.GCREF))
    gcarraydescr_tid = gcarraydescr.get_type_id()
    floatarraydescr = cpu.arraydescrof(lltype.GcArray(lltype.Float))

    # a GcStruct not inheriting from OBJECT
    tpl = lltype.malloc(S, zero=True)
    tupleaddr = lltype.cast_opaque_ptr(llmemory.GCREF, tpl)
    nodefull2 = lltype.malloc(NODE, zero=True)
    nodefull2addr = lltype.cast_opaque_ptr(llmemory.GCREF, nodefull2)
    ssize = cpu.sizeof(S, None)
    adescr = cpu.fielddescrof(S, 'a')
    abisdescr = cpu.fielddescrof(S, 'abis')
    bdescr = cpu.fielddescrof(S, 'b')
    #sbox = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S)))
    arraydescr2 = cpu.arraydescrof(lltype.GcArray(lltype.Ptr(S)))

    T = lltype.GcStruct('TUPLE',
                        ('c', lltype.Signed),
                        ('d', lltype.Ptr(lltype.GcArray(lltype.Ptr(NODE)))))

    W_ROOT = lltype.GcStruct('W_ROOT', ('parent', OBJECT),
        ('inst_w_seq', llmemory.GCREF), ('inst_index', lltype.Signed),
        ('inst_w_list', llmemory.GCREF), ('inst_length', lltype.Signed),
        ('inst_start', lltype.Signed), ('inst_step', lltype.Signed))
    inst_w_seq = cpu.fielddescrof(W_ROOT, 'inst_w_seq')
    inst_index = cpu.fielddescrof(W_ROOT, 'inst_index')
    inst_length = cpu.fielddescrof(W_ROOT, 'inst_length')
    inst_start = cpu.fielddescrof(W_ROOT, 'inst_start')
    inst_step = cpu.fielddescrof(W_ROOT, 'inst_step')
    inst_w_list = cpu.fielddescrof(W_ROOT, 'inst_w_list')
    w_root_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
    
    tsize = cpu.sizeof(T, None)
    cdescr = cpu.fielddescrof(T, 'c')
    ddescr = cpu.fielddescrof(T, 'd')
    arraydescr3 = cpu.arraydescrof(lltype.GcArray(lltype.Ptr(NODE)))

    U = lltype.GcStruct('U',
                        ('parent', OBJECT),
                        ('one', lltype.Ptr(lltype.GcArray(lltype.Ptr(NODE)))))
    u_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
    u_vtable_adr = llmemory.cast_ptr_to_adr(u_vtable)
    SIMPLE = lltype.GcStruct('simple',
        ('parent', OBJECT),
        ('value', lltype.Signed))
    simplevalue = cpu.fielddescrof(SIMPLE, 'value')
    simple_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
    simpledescr = cpu.sizeof(SIMPLE, simple_vtable)
    simple = lltype.malloc(SIMPLE, zero=True)
    simpleaddr = lltype.cast_opaque_ptr(llmemory.GCREF, simple)
    #usize = cpu.sizeof(U, ...)
    onedescr = cpu.fielddescrof(U, 'one')

    FUNC = lltype.FuncType([lltype.Signed], lltype.Signed)
    plaincalldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                     EffectInfo.MOST_GENERAL)
    elidablecalldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                    EffectInfo([valuedescr], [], [],
                                               [valuedescr], [], [],
                                         EffectInfo.EF_ELIDABLE_CANNOT_RAISE))
    elidable2calldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                    EffectInfo([valuedescr], [], [],
                                               [valuedescr], [], [],
                                         EffectInfo.EF_ELIDABLE_OR_MEMORYERROR))
    elidable3calldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                    EffectInfo([valuedescr], [], [],
                                               [valuedescr], [], [],
                                         EffectInfo.EF_ELIDABLE_CAN_RAISE))
    nonwritedescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                    EffectInfo([], [], [], [], [], []))
    writeadescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                  EffectInfo([], [], [], [adescr], [], []))
    writearraydescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                  EffectInfo([], [], [], [adescr], [arraydescr],
                                             []))
    readadescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                 EffectInfo([adescr], [], [], [], [], []))
    mayforcevirtdescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                 EffectInfo([nextdescr], [], [], [], [], [],
                            EffectInfo.EF_FORCES_VIRTUAL_OR_VIRTUALIZABLE,
                            can_invalidate=True))
    arraycopydescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
             EffectInfo([], [arraydescr], [], [], [arraydescr], [],
                        EffectInfo.EF_CANNOT_RAISE,
                        oopspecindex=EffectInfo.OS_ARRAYCOPY))

    raw_malloc_descr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
             EffectInfo([], [], [], [], [], [],
                        EffectInfo.EF_CAN_RAISE,
                        oopspecindex=EffectInfo.OS_RAW_MALLOC_VARSIZE_CHAR))
    raw_free_descr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
             EffectInfo([], [], [], [], [], [],
                        EffectInfo.EF_CANNOT_RAISE,
                        oopspecindex=EffectInfo.OS_RAW_FREE))

    chararray = lltype.GcArray(lltype.Char)
    chararraydescr = cpu.arraydescrof(chararray)
    u2array = lltype.GcArray(rffi.USHORT)
    u2arraydescr = cpu.arraydescrof(u2array)

    nodefull = lltype.malloc(NODE2, zero=True)
    nodefull.parent.next = lltype.cast_pointer(lltype.Ptr(NODE), nodefull)
    nodefull.parent.nexttuple = tpl
    nodefulladdr = lltype.cast_opaque_ptr(llmemory.GCREF, nodefull)

    # array of structs (complex data)
    complexarray = lltype.GcArray(
        lltype.Struct("complex",
            ("real", lltype.Float),
            ("imag", lltype.Float),
        )
    )
    complexarraydescr = cpu.arraydescrof(complexarray)
    complexrealdescr = cpu.interiorfielddescrof(complexarray, "real")
    compleximagdescr = cpu.interiorfielddescrof(complexarray, "imag")
    complexarraycopydescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
            EffectInfo([], [complexarraydescr], [], [], [complexarraydescr], [],
                       EffectInfo.EF_CANNOT_RAISE,
                       oopspecindex=EffectInfo.OS_ARRAYCOPY))

    rawarraydescr = cpu.arraydescrof(lltype.Array(lltype.Signed,
                                                  hints={'nolength': True}))
    rawarraydescr_char = cpu.arraydescrof(lltype.Array(lltype.Char,
                                                       hints={'nolength': True}))
    rawarraydescr_float = cpu.arraydescrof(lltype.Array(lltype.Float,
                                                        hints={'nolength': True}))

    fc_array = lltype.GcArray(
        lltype.Struct(
            "floatchar", ("float", lltype.Float), ("char", lltype.Char)))
    fc_array_descr = cpu.arraydescrof(fc_array)
    fc_array_floatdescr = cpu.interiorfielddescrof(fc_array, "float")
    fc_array_chardescr = cpu.interiorfielddescrof(fc_array, "char")

    for _name, _os in [
        ('strconcatdescr',               'OS_STR_CONCAT'),
        ('strslicedescr',                'OS_STR_SLICE'),
        ('strequaldescr',                'OS_STR_EQUAL'),
        ('streq_slice_checknull_descr',  'OS_STREQ_SLICE_CHECKNULL'),
        ('streq_slice_nonnull_descr',    'OS_STREQ_SLICE_NONNULL'),
        ('streq_slice_char_descr',       'OS_STREQ_SLICE_CHAR'),
        ('streq_nonnull_descr',          'OS_STREQ_NONNULL'),
        ('streq_nonnull_char_descr',     'OS_STREQ_NONNULL_CHAR'),
        ('streq_checknull_char_descr',   'OS_STREQ_CHECKNULL_CHAR'),
        ('streq_lengthok_descr',         'OS_STREQ_LENGTHOK'),
        ]:
        if _name in ('strconcatdescr', 'strslicedescr'):
            _extra = EffectInfo.EF_ELIDABLE_OR_MEMORYERROR
        else:
            _extra = EffectInfo.EF_ELIDABLE_CANNOT_RAISE
        _oopspecindex = getattr(EffectInfo, _os)
        locals()[_name] = \
            cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                EffectInfo([], [], [], [], [], [], _extra,
                           oopspecindex=_oopspecindex))
        #
        _oopspecindex = getattr(EffectInfo, _os.replace('STR', 'UNI'))
        locals()[_name.replace('str', 'unicode')] = \
            cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                EffectInfo([], [], [], [], [], [], _extra,
                           oopspecindex=_oopspecindex))

    s2u_descr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
            EffectInfo([], [], [], [], [], [], EffectInfo.EF_ELIDABLE_CAN_RAISE,
                       oopspecindex=EffectInfo.OS_STR2UNICODE))
    #

    class LoopToken(AbstractDescr):
        pass
    asmdescr = LoopToken() # it can be whatever, it's not a descr though

    from rpython.jit.metainterp.virtualref import VirtualRefInfo

    class FakeWarmRunnerDesc:
        pass
    FakeWarmRunnerDesc.cpu = cpu
    vrefinfo = VirtualRefInfo(FakeWarmRunnerDesc)
    virtualtokendescr = vrefinfo.descr_virtual_token
    virtualforceddescr = vrefinfo.descr_forced
    FUNC = lltype.FuncType([], lltype.Void)
    ei = EffectInfo([], [], [], [], [], [], EffectInfo.EF_CANNOT_RAISE,
                    can_invalidate=False,
                    oopspecindex=EffectInfo.OS_JIT_FORCE_VIRTUALIZABLE)
    clear_vable = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT, ei)

    jit_virtual_ref_vtable = vrefinfo.jit_virtual_ref_vtable
    jvr_vtable_adr = llmemory.cast_ptr_to_adr(jit_virtual_ref_vtable)
    vref_descr = cpu.sizeof(vrefinfo.JIT_VIRTUAL_REF, jit_virtual_ref_vtable)

    namespace = locals()

# ____________________________________________________________


class Fake(object):
    failargs_limit = 1000
    storedebug = None


class FakeMetaInterpStaticData(object):

    def __init__(self, cpu):
        self.cpu = cpu
        self.profiler = EmptyProfiler()
        self.options = Fake()
        self.globaldata = Fake()
        self.config = get_combined_translation_config(translating=True)

    class logger_noopt:
        @classmethod
        def log_loop(*args):
            pass

    class logger_ops:
        repr_of_resop = repr

    class warmrunnerdesc:
        class memory_manager:
            retrace_limit = 5
            max_retrace_guards = 15
        jitcounter = DeterministicJitCounter()

    def get_name_from_address(self, addr):
        # hack
        try:
            return "".join(addr.ptr.name.chars)
        except AttributeError:
            return ""

class Info(object):
    def __init__(self, preamble, short_preamble=None, virtual_state=None):
        self.preamble = preamble
        self.short_preamble = short_preamble
        self.virtual_state = virtual_state

class Storage(compile.ResumeGuardDescr):
    "for tests."
    def __init__(self, metainterp_sd=None, original_greenkey=None):
        self.metainterp_sd = metainterp_sd
        self.original_greenkey = original_greenkey
    def store_final_boxes(self, op, boxes, metainterp_sd):
        op.setfailargs(boxes)
    def __eq__(self, other):
        return True # screw this
        #return type(self) is type(other)      # xxx obscure

def _sortboxes(boxes):
    _kind2count = {history.INT: 1, history.REF: 2, history.FLOAT: 3}
    return sorted(boxes, key=lambda box: _kind2count[box.type])

final_descr = history.BasicFinalDescr()

class BaseTest(object):

    def parse(self, s, boxkinds=None, want_fail_descr=True, postprocess=None):
        self.oparse = OpParser(s, self.cpu, self.namespace, 'lltype',
                               boxkinds,
                               None, False, postprocess)
        return self.oparse.parse()

    def postprocess(self, op):
        if op.is_guard():
            op.rd_snapshot = resume.Snapshot(None, op.getfailargs())
            op.rd_frame_info_list = resume.FrameInfo(None, "code", 11)

    def add_guard_future_condition(self, res):
        # invent a GUARD_FUTURE_CONDITION to not have to change all tests
        if res.operations[-1].getopnum() == rop.JUMP:
            guard = ResOperation(rop.GUARD_FUTURE_CONDITION, [], None)
            guard.rd_snapshot = resume.Snapshot(None, [])
            res.operations.insert(-1, guard)

    def assert_equal(self, optimized, expected, text_right=None):
        from rpython.jit.metainterp.optimizeopt.util import equaloplists
        assert len(optimized.inputargs) == len(expected.inputargs)
        remap = {}
        for box1, box2 in zip(optimized.inputargs, expected.inputargs):
            assert box1.type == box2.type
            remap[box2] = box1
        assert equaloplists(optimized.operations,
                            expected.operations, False, remap, text_right)

    def _do_optimize_loop(self, compile_data):
        from rpython.jit.metainterp.optimizeopt import optimize_trace
        metainterp_sd = FakeMetaInterpStaticData(self.cpu)
        if hasattr(self, 'vrefinfo'):
            metainterp_sd.virtualref_info = self.vrefinfo
        if hasattr(self, 'callinfocollection'):
            metainterp_sd.callinfocollection = self.callinfocollection
        #
        compile_data.enable_opts = self.enable_opts
        state = optimize_trace(metainterp_sd, None, compile_data)
        return state

    def _convert_call_pure_results(self, d):
        from rpython.jit.metainterp.optimizeopt.util import args_dict

        if d is None:
            return
        call_pure_results = args_dict()
        for k, v in d.items():
            call_pure_results[list(k)] = v
        return call_pure_results

    def unroll_and_optimize(self, loop, call_pure_results=None):
        self.add_guard_future_condition(loop)
        jump_op = loop.operations[-1]
        assert jump_op.getopnum() == rop.JUMP
        ops = loop.operations[:-1]
        jump_op.setdescr(JitCellToken())
        start_label = ResOperation(rop.LABEL, loop.inputargs,
                                   jump_op.getdescr())
        end_label = jump_op.copy_and_change(opnum=rop.LABEL)
        call_pure_results = self._convert_call_pure_results(call_pure_results)
        preamble_data = compile.LoopCompileData(start_label, end_label, ops,
                                                call_pure_results)
        start_state, preamble_ops = self._do_optimize_loop(preamble_data)
        preamble_data.forget_optimization_info()
        loop_data = compile.UnrolledLoopData(start_label, jump_op,
                                             ops, start_state,
                                             call_pure_results)
        loop_info, ops = self._do_optimize_loop(loop_data)
        preamble = TreeLoop('preamble')
        preamble.inputargs = start_state.renamed_inputargs
        start_label = ResOperation(rop.LABEL, start_state.renamed_inputargs)
        preamble.operations = ([start_label] + preamble_ops +
                               loop_info.extra_same_as + [loop_info.label_op])
        loop.inputargs = loop_info.label_op.getarglist()[:]
        loop.operations = [loop_info.label_op] + ops
        return Info(preamble, loop_info.target_token.short_preamble,
                    start_state.virtual_state)

    def set_values(self, ops, jump_values=None):
        jump_op = ops[-1]
        assert jump_op.getopnum() == rop.JUMP
        if jump_values is not None:
            for i, v in enumerate(jump_values):
                if v is not None:
                    jump_op.getarg(i).setref_base(v)
        else:
            for i, box in enumerate(jump_op.getarglist()):
                if box.type == 'r' and not box.is_constant():
                    box.setref_base(self.nodefulladdr)



class FakeDescr(compile.ResumeGuardDescr):
    def clone_if_mutable(self):
        return FakeDescr()
    def __eq__(self, other):
        return isinstance(other, FakeDescr)

def convert_old_style_to_targets(loop, jump):
    newloop = TreeLoop(loop.name)
    newloop.inputargs = loop.inputargs
    newloop.operations = [ResOperation(rop.LABEL, loop.inputargs, descr=FakeDescr())] + \
                      loop.operations
    if not jump:
        assert newloop.operations[-1].getopnum() == rop.JUMP
        newloop.operations[-1] = newloop.operations[-1].copy_and_change(
            rop.LABEL)
    return newloop

# ____________________________________________________________

