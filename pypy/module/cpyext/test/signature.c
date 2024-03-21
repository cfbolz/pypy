#include <Python.h>

long wrong_impl(long arg) {
  return arg+1;
}

PyObject* wrong(PyObject* module, PyObject* obj) {
  (void)module;
  long obj_int = PyLong_AsLong(obj);
  if (obj_int == -1 && PyErr_Occurred()) {
    return NULL;
  }
  long result = wrong_impl(obj_int);
  return PyLong_FromLong(result);
}

int wrong_arg_types[] = {100, -1};

PyPyTypedMethodMetadata wrong_sig = {
  .arg_types = wrong_arg_types,
  .ret_type = T_C_LONG,
  .underlying_func = wrong_impl,
  .ml_name = "wrong",
};

double raise_double_impl(double x) {
  if (x == 0.0) {
    PyErr_Format(PyExc_RuntimeError, "got 0. raising");
    return -0.0;
  }
  return x;
}

PyObject* raise_double(PyObject* module, PyObject* obj) {
  (void)module;
  double obj_double = PyFloat_AsDouble(obj);
  if (obj_double == -1 && PyErr_Occurred()) {
    return NULL;
  }
  double result = raise_double_impl(obj_double);
  if (result == -1 && PyErr_Occurred()) {
    return NULL;
  }
  return PyFloat_FromDouble(result);
}

int raise_double_arg_types[] = {T_C_DOUBLE, -1};

PyPyTypedMethodMetadata raise_double_sig = {
  .arg_types = raise_double_arg_types,
  .ret_type = -T_C_DOUBLE,
  .underlying_func = raise_double_impl,
  .ml_name = "raise_double",
};

long takes_object_impl(PyObject* obj, long arg) {
  (void)obj;
  return arg + 1;
}

PyObject* takes_object(PyObject* module, PyObject*const *args, Py_ssize_t nargs) {
  (void)module;
  if (nargs != 2) {
    return PyErr_Format(PyExc_TypeError, "takes_object expected 2 arguments but got %ld", nargs);
  }
  PyObject* obj = args[0];
  assert(obj != NULL);
  long obj_int = PyLong_AsLong(args[1]);
  if (obj_int == -1 && PyErr_Occurred()) {
    return NULL;
  }
  long result = takes_object_impl(obj, obj_int);
  return PyLong_FromLong(result);
}

int takes_object_arg_types[] = {T_PY_OBJECT, T_C_LONG, -1};

PyPyTypedMethodMetadata takes_object_sig = {
  .arg_types = takes_object_arg_types,
  .ret_type = T_C_LONG,
  .underlying_func = takes_object_impl,
  .ml_name = "takes_object",
};

PyObject* takes_only_object_impl(PyObject* arg) {
  Py_INCREF(arg);
  return arg;
}

PyObject* takes_only_object(PyObject* module, PyObject* obj) {
  (void)module;
  return takes_only_object_impl(obj);
}

int takes_only_object_arg_types[] = {T_PY_OBJECT, -1};

PyPyTypedMethodMetadata takes_only_object_sig = {
  .arg_types = takes_only_object_arg_types,
  .ret_type = T_PY_OBJECT,
  .underlying_func = takes_only_object_impl,
  .ml_name = "takes_only_object",
};

static PyMethodDef signature_methods[] = {
    {wrong_sig.ml_name, wrong, METH_O | METH_TYPED, "Have a silly signature"},
    {raise_double_sig.ml_name, raise_double, METH_O | METH_TYPED, "Raise an exception (double)"},
    {takes_object_sig.ml_name, (PyCFunction)(void*)takes_object, METH_FASTCALL | METH_TYPED, "Inc but also takes a PyObject*"},
    {takes_only_object_sig.ml_name, takes_only_object, METH_O | METH_TYPED, "id(x)"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef signature_definition = {
    PyModuleDef_HEAD_INIT, "signature",
    "A C extension module with type information exposed.", -1,
    signature_methods,
    NULL,
    NULL,
    NULL,
    NULL};

PyMODINIT_FUNC PyInit_signature(void) {
  PyObject* result = PyState_FindModule(&signature_definition);
  if (result != NULL) {
    return Py_NewRef(result);
  }
  return PyModule_Create(&signature_definition);
}
