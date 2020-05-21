#!/usr/bin/env python3

"""
Introduction
============
This module provides a collection of decorators that makes it easy to
write software using contracts.

Contracts are a debugging and verification tool.  They are declarative
statements about what states a program must be in to be considered
"correct" at runtime.  They are similar to assertions, and are verified
automatically at various well-defined points in the program.  Contracts can
be specified on functions and on classes.

Contracts serve as a form of documentation and a way of formally
specifying program behavior.  Good practice often includes writing all of
the contracts first, with these contract specifying the exact expected
state before and after each function or method call and the things that
should always be true for a given class of object.

Contracts consist of two parts: a description and a condition.  The
description is simply a human-readable string that describes what the
contract is testing, while the condition is a single function that tests
that condition.  The condition is executed automatically and passed certain
arguments (which vary depending on the type of contract), and must return
a boolean value: True if the condition has been met, and False otherwise.

Legacy Python Support
=====================
This module supports versions of Python >= 3.5; that is, versions with
support for "async def" functions.  There is a branch of this module that
is in maintenance mode for versions of Python earlier than 3.5
(including Python 2.7).

The Python 2 and <= 3.5 branch is available at
https://github.com/deadpixi/contracts/tree/python2

This legacy-compatible version is also distributed on PyPI along the 0.5.x
branch; this branch will kept compatible with newer versions to the greatest
extent possible.

That branch is a drop-in replacement for this module and includes most
of the functionality, except support for "async def" functions and a few
other things.

Preconditions and Postconditions
================================
Contracts on functions consist of preconditions and postconditions.
A precondition is declared using the `requires` decorator, and describes
what must be true upon entrance to the function. The condition function
is passed an arguments object, which as as its attributes the arguments
to the decorated function:

    >>> @require("`i` must be an integer", lambda args: isinstance(args.i, int))
    ... @require("`j` must be an integer", lambda args: isinstance(args.j, int))
    ... def add2(i, j):
    ...   return i + j

Note that an arbitrary number of preconditions can be stacked on top of
each other.

These decorators have declared that the types of both arguments must be
integers.  Calling the `add2` function with the correct types of arguments
works:

    >>> add2(1, 2)
    3

But calling with incorrect argument types (violating the contract) fails
with a PreconditionError (a subtype of AssertionError):

    >>> add2("foo", 2)
    Traceback (most recent call last):
    PreconditionError: `i` must be an integer

Functions can also have postconditions, specified using the `ensure`
decorator.  Postconditions describe what must be true after the function
has successfully returned.  Like the `require` decorator, the `ensure`
decorator is passed an argument object.  It is also passed an additional
argument, which is the result of the function invocation.  For example:

    >>> @require("`i` must be a positive integer",
    ...          lambda args: isinstance(args.i, int) and args.i > 0)
    ... @require("`j` must be a positive integer",
    ...          lambda args: isinstance(args.j, int) and args.j > 0)
    ... @ensure("the result must be greater than either `i` or `j`",
    ...         lambda args, result: result > args.i and result > args.j)
    ... def add2(i, j):
    ...     if i == 7:
    ...        i = -7 # intentionally broken for purposes of example
    ...     return i + j

We can now call the function and ensure that everything is working correctly:

    >>> add2(1, 3)
    4

Except that the function is broken in unexpected ways:

    >>> add2(7, 4)
    Traceback (most recent call last):
    PostconditionError: the result must be greater than either `i` or `j`

The function specifying the condition doesn't have to be a lambda; it can be
any function, and pre- and postconditions don't have to actually reference
the arguments or results of the function at all.  They can simply check
the function's environments and effects:

    >>> names = set()
    >>> def exists_in_database(x):
    ...   return x in names
    >>> @require("`name` must be a string", lambda args: isinstance(args.name, str))
    ... @require("`name` must not already be in the database",
    ...          lambda args: not exists_in_database(args.name.strip()))
    ... @ensure("the normalized version of the name must be added to the database",
    ...         lambda args, result: exists_in_database(args.name.strip()))
    ... def add_to_database(name):
    ...     if name not in names and name != "Rob": # intentionally broken
    ...         names.add(name.strip())

    >>> add_to_database("James")
    >>> add_to_database("Marvin")
    >>> add_to_database("Marvin")
    Traceback (most recent call last):
    PreconditionError: `name` must not already be in the database
    >>> add_to_database("Rob")
    Traceback (most recent call last):
    PostconditionError: the normalized version of the name must be added to the database

All of the various calling conventions of Python are supported:

    >>> @require("`a` is an integer", lambda args: isinstance(args.a, int))
    ... @require("`b` is a string", lambda args: isinstance(args.b, str))
    ... @require("every member of `c` should be a boolean",
    ...          lambda args: all(isinstance(x, bool) for x in args.c))
    ... def func(a, b="Foo", *c):
    ...     pass

    >>> func(1, "foo", True, True, False)
    >>> func(b="Foo", a=7)
    >>> args = {"a": 8, "b": "foo"}
    >>> func(**args)
    >>> args = (1, "foo", True, True, False)
    >>> func(*args)
    >>> args = {"a": 9}
    >>> func(**args)
    >>> func(10)

A common contract is to validate the types of arguments. To that end,
there is an additional decorator, `types`, that can be used
to validate arguments' types:

    >>> class ExampleClass:
    ...     pass

    >>> @types(a=int, b=str, c=(type(None), ExampleClass)) # or types.NoneType, if you prefer
    ... @require("a must be nonzero", lambda args: args.a != 0)
    ... def func(a, b, c=38):
    ...     return " ".join(str(x) for x in [a, b])

    >>> func(1, "foo", ExampleClass())
    '1 foo'

    >>> func(1.0, "foo", ExampleClass) # invalid type for `a`
    Traceback (most recent call last):
    PreconditionError: the types of arguments must be valid

    >>> func(1, "foo") # invalid type (the default) for `c`
    Traceback (most recent call last):
    PreconditionError: the types of arguments must be valid

Contracts on Classes
====================
The `require` and `ensure` decorators can be used on class methods too,
not just bare functions:

    >>> class Foo:
    ...     @require("`name` should be nonempty", lambda args: len(args.name) > 0)
    ...     def __init__(self, name):
    ...         self.name = name

    >>> foo = Foo()
    Traceback (most recent call last):
    TypeError: __init__ missing required positional argument: 'name'

    >>> foo = Foo("")
    Traceback (most recent call last):
    PreconditionError: `name` should be nonempty

Classes may also have an additional sort of contract specified over them:
the invariant.  An invariant, created using the `invariant` decorator,
specifies a condition that must always be true for instances of that class.
In this case, "always" means "before invocation of any method and after
its return" -- methods are allowed to violate invariants so long as they
are restored prior to return.

Invariant contracts are passed a single variable, a reference to the
instance of the class. For example:

    >>> @invariant("inner list can never be empty", lambda self: len(self.lst) > 0)
    ... @invariant("inner list must consist only of integers",
    ...            lambda self: all(isinstance(x, int) for x in self.lst))
    ... class NonemptyList:
    ...     @require("initial list must be a list", lambda args: isinstance(args.initial, list))
    ...     @require("initial list cannot be empty", lambda args: len(args.initial) > 0)
    ...     @ensure("the list instance variable is equal to the given argument",
    ...             lambda args, result: args.self.lst == args.initial)
    ...     @ensure("the list instance variable is not an alias to the given argument",
    ...             lambda args, result: args.self.lst is not args.initial)
    ...     def __init__(self, initial):
    ...         self.lst = initial[:]
    ...
    ...     def get(self, i):
    ...         return self.lst[i]
    ...
    ...     def pop(self):
    ...         self.lst.pop()
    ...
    ...     def as_string(self):
    ...         # Build up a string representation using the `get` method,
    ...         # to illustrate methods calling methods with invariants.
    ...         return ",".join(str(self.get(i)) for i in range(0, len(self.lst)))

    >>> nl = NonemptyList([1,2,3])
    >>> nl.pop()
    >>> nl.pop()
    >>> nl.pop()
    Traceback (most recent call last):
    PostconditionError: inner list can never be empty

    >>> nl = NonemptyList(["a", "b", "c"])
    Traceback (most recent call last):
    PostconditionError: inner list must consist only of integers

Violations of invariants are ignored in the following situations:

    - before calls to __init__ and __new__ (since the object is still
      being initialized)

    - before and after calls to any method whose name begins with "__",
      except for methods implementing arithmetic and comparison operations
      and container type emulation (because such methods are private and
      expected to manipulate the object's inner state, plus things get hairy
      with certain applications of `__getattr(ibute)?__`)

    - before and after calls to methods added from outside the initial
      class definition (because invariants are processed only at class
      definition time)

    - before and after calls to classmethods, since they apply to the class
      as a whole and not any particular instance

For example:

    >>> @invariant("`always` should be True", lambda self: self.always)
    ... class Foo:
    ...     always = True
    ...
    ...     def get_always(self):
    ...         return self.always
    ...
    ...     @classmethod
    ...     def break_everything(cls):
    ...         cls.always = False

    >>> x = Foo()
    >>> x.get_always()
    True
    >>> x.break_everything()
    >>> x.get_always()
    Traceback (most recent call last):
    PreconditionError: `always` should be True

Also note that if a method invokes another method on the same object,
all of the invariants will be tested again:

    >>> nl = NonemptyList([1,2,3])
    >>> nl.as_string() == '1,2,3'
    True

Automatically Generated Descriptions
====================================
Some might find that providing a human-readable description for a contract
in addition to a function implementing that contract is a bit too verbose.

For the `require`, `ensure`, and `invariant` decorators, a single-argument
version exists. If only a function is passed in, a description will be
automatically generated based on the code of that function:

    >>> import math
    >>> @require("x must be an integer", lambda args: isinstance(args.x, int))
    ... @require(lambda args: args.x > 0)
    ... @ensure("result must be a float", lambda args, result: isinstance(result, float))
    ... def square_root(x):
    ...     return math.sqrt(x)
    >>> square_root(-1)
    Traceback (most recent call last):
    PreconditionError: @require(lambda args: args.x > 0) failed

This is true for postconditions as well:

    >>> @ensure(lambda args, result: result > 0)
    ... def sub(x, y):
    ...     return x - y
    >>> sub(10, 100)
    Traceback (most recent call last):
    PostconditionError: @ensure(lambda args, result: result > 0) failed

And of course for invariants:

    >>> @invariant(lambda self: self.counter >= 0)
    ... class Counter:
    ...     def __init__(self, initial_value):
    ...         self.counter = initial_value
    ...     def increment(self, value):
    ...         self.counter += value
    >>> counter = Counter(10)
    >>> counter.increment(-100)
    Traceback (most recent call last):
    PostconditionError: @invariant(lambda self: self.counter >= 0) failed

Tests can span more than one line as well:

    >>> @ensure(lambda args, result: result < 1000)
    ... @ensure(lambda args, result: all([
    ...     result > 0]))
    ... @ensure(lambda args, result: isinstance(result, int))
    ... def sub2(x, y):
    ...     return x - y
    >>> sub2(10, 100)
    Traceback (most recent call last):
    PostconditionError: @ensure(lambda args, result: all([
        result > 0])) failed

Preserving Old Values
=====================
Sometimes it's important to be able to compare the results of a function with the
previous state of the program. Earlier states can be preserved using the
`preserve` decorator:

    >>> class Counter:
    ...     def __init__(self, initial_value):
    ...         self.value = initial_value
    ...
    ...     @preserve(lambda args: {"old_value": args.self.value})
    ...     @require("value > 0", lambda args: args.value > 0)
    ...     @ensure("counter is incremented by value",
    ...             lambda args, res, old: args.self.value == old.old_value + args.value)
    ...     def increment(self, value):
    ...         if value == 9:
    ...             self.value += 2 # broken for purposes of example
    ...         self.value += value

    >>> counter = Counter(100)
    >>> counter.increment(10)
    >>> counter.increment(9)
    Traceback (most recent call last):
    PostconditionError: counter is incremented by value

Note that Python's pass-by-reference semantics still apply, so if you need to
preserve an old value, you might have to copy it.

Transforming Data in Contracts
==============================
In general, you should avoid transforming data inside a contract; contracts
themselves are supposed to be side-effect-free.

However, this is not always possible in Python.

Take, for example, iterables passed as arguments. We might want to verify
that a given set of properties hold for every item in the iterable. The
obvious solution would be to do something like this:

    >>> @require("every item in `l` must be > 0", lambda args: all(x > 0 for x in args.l))
    ... def my_func(l):
    ...     return sum(l)

This works well in most situations:

    >>> my_func([1, 2, 3])
    6
    >>> my_func([0, -1, 2])
    Traceback (most recent call last):
    PreconditionError: every item in `l` must be > 0

But it fails in the case of a generator:

    >>> def iota(n):
    ...     for i in range(1, n):
    ...         yield i

    >>> sum(iota(5))
    10
    >>> my_func(iota(5))
    0

The call to `my_func` has a result of 0 because the generator was consumed
inside the `all` call inside the contract. Obviously, this is problematic.

Sadly, there is no generic solution to this problem. In a statically-typed
language, the compiler can verify that some properties of infinite lists
(though not all of them, and what exactly depends on the type system).

We get around that limitation here using an additional decorator, called
`transform` that transforms the arguments to a function, and a function
called `rewrite` that rewrites argument tuples.

For example:

    >>> @transform(lambda args: rewrite(args, l=list(args.l)))
    ... @require("every item in `l` must be > 0", lambda args: all(x > 0 for x in args.l))
    ... def my_func(l):
    ...     return sum(l)
    >>> my_func(iota(5))
    10

Note that this does not completely solve the problem of infinite sequences,
but it does allow for verification of any desired prefix of such a sequence.

This works for class methods too, of course:

    >>> class TestClass:
    ...     @transform(lambda args: rewrite(args, l=list(args.l)))
    ...     @require("every item in `l` must be > 0", lambda args: all(x > 0 for x in args.l))
    ...     def my_func(self, l):
    ...         return sum(l)
    >>> TestClass().my_func(iota(5))
    10

Contracts on Asynchronous Functions (aka coroutine functions)
=============================================================
Contracts can be placed on coroutines (that is, async functions):

    >>> import asyncio
    >>> @require("`a` is an integer", lambda args: isinstance(args.a, int))
    ... @require("`b` is a string", lambda args: isinstance(args.b, str))
    ... @require("every member of `c` should be a boolean",
    ...          lambda args: all(isinstance(x, bool) for x in args.c))
    ... async def func(a, b="Foo", *c):
    ...     await asyncio.sleep(1)

    >>> asyncio.get_event_loop().run_until_complete(
    ...     func( 1, "foo", True, True, False))

Predicates functions themselves cannot be coroutines, as this could
influence the run loop:

    >>> async def coropred_aisint(e):
    ...     await asyncio.sleep(1)
    ...     return isinstance(getattr(e, 'a'), int)
    >>> @require("`a` is an integer", coropred_aisint)
    ... @require("`b` is a string", lambda args: isinstance(args.b, str))
    ... @require("every member of `c` should be a boolean",
    ...          lambda args: all(isinstance(x, bool) for x in args.c))
    ... async def func(a, b="Foo", *c):
    ...     await asyncio.sleep(1)
    Traceback (most recent call last):
    AssertionError: contract predicates cannot be coroutines

Contracts and Debugging
=======================
Contracts are a documentation and testing tool; they are not intended
to be used to validate user input or implement program logic.  Indeed,
running Python with `__debug__` set to False (e.g. by calling the Python
interpreter with the "-O" option) disables contracts.

Testing This Module
===================
This module has embedded doctests that are run with the module is invoked
from the command line.  Simply run the module directly to run the tests.

Contact Information and Licensing
=================================
This module has a home page at `GitHub <https://github.com/deadpixi/contracts>`_.

This module was written by Rob King (jking@deadpixi.com).

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

__all__ = ["ensure", "invariant", "require", "transform", "rewrite",
           "preserve", "PreconditionError", "PostconditionError"]
__author__ = "Rob King"
__copyright__ = "Copyright (C) 2015-2018 Rob King"
__license__ = "LGPL"
__version__ = "$Id$"
__email__ = "jking@deadpixi.com"
__status__ = "Alpha"

from ast import parse
from collections import namedtuple
from functools import wraps
from inspect import isfunction, ismethod, iscoroutinefunction, getfullargspec, getsource
from sys import version_info

if version_info[:2] < (3, 5):
    raise ImportError('dpcontracts >= 0.6 requires Python 3.5 or later.')

class PreconditionError(AssertionError):
    """An AssertionError raised due to violation of a precondition."""

    @property
    def errno(self):
        return self.args[1]

class PostconditionError(AssertionError):
    """An AssertionError raised due to violation of a postcondition."""

def get_function_source(func):
    try:
        source = getsource(func)
        tree = parse(source)
        decorators = tree.body[0].decorator_list
        function = tree.body[0]
        first_line = decorators[0].lineno
        following_line = first_line + 1
        if len(decorators) > 1:
            following_line = decorators[1].lineno
        elif len(function.body) > 0:
            following_line = function.body[0].lineno - 1
        return "\n".join(source.split("\n")[first_line - 1:following_line - first_line]) + " failed"

    except (SyntaxError, OSError):
        return str(func)

def get_wrapped_func(func):
    while hasattr(func, '__contract_wrapped_func__'):
        func = func.__contract_wrapped_func__
    return func

def build_call(func, *args, **kwargs):
    """
    Build an argument dictionary suitable for passing via `**` expansion given
    function `f`, positional arguments `args`, and keyword arguments `kwargs`.
    """

    func = get_wrapped_func(func)
    named, vargs, _, defs, kwonly, kwonlydefs, _ = getfullargspec(func)

    nonce = object()
    actual = dict((name, nonce) for name in named)

    defs = defs or ()
    kwonlydefs = kwonlydefs or {}

    actual.update(kwonlydefs)
    actual.update(dict(zip(reversed(named), reversed(defs))))
    actual.update(dict(zip(named, args)))

    if vargs:
        actual[vargs] = tuple(args[len(named):])

    actual.update(kwargs)

    for name, value in actual.items():
        if value is nonce:
            raise TypeError("%s missing required positional argument: '%s'" % (func.__name__, name))

    return tuple_of_dict(actual)

def tuple_of_dict(dictionary, name="Args"):
    assert isinstance(dictionary, dict), "dictionary must be a dict instance"
    return namedtuple(name, dictionary.keys())(**dictionary)

def arg_count(func):
    named, vargs, _, defs, kwonly, kwonlydefs, _ = getfullargspec(func)
    return len(named) + len(kwonly) + (1 if vargs else 0)

def condition(description, predicate, precondition=False, postcondition=False, instance=False,
        errno=0, clean_up=None):
    assert isinstance(description, str), "contract descriptions must be strings"
    assert len(description) > 0, "contracts must have nonempty descriptions"
    assert isfunction(predicate), "contract predicates must be functions"
    assert not iscoroutinefunction(predicate), "contract predicates cannot be coroutines"
    assert precondition or postcondition, "contracts must be at least one of pre- or post-conditional"
    if instance or precondition:
        assert arg_count(predicate) == 1, "invariant predicates must take one argument"
    elif postcondition:
        assert arg_count(predicate) in (2, 3), "postcondition predicates must take two or three arguments"

    def require(f):
        wrapped = get_wrapped_func(f)

        if iscoroutinefunction(f):
            @wraps(f)
            async def inner(*args, **kwargs):
                rargs = build_call(f, *args, **kwargs) if not instance else args[0]

                if precondition and not predicate(rargs):
                    raise PreconditionError(description, errno)

                preserved_values = {}
                for preserver in getattr(wrapped, "__contract_preserver__", [lambda x: {}]):
                    preserved_values.update(preserver(rargs))
                result = await f(*args, **kwargs)

                if instance:
                    if not predicate(rargs):
                        if clean_up:
                            try:
                                clean_up(*args, **kwargs)
                            except Exception as e:
                                raise PostconditionError(f"{description}. Clean up failed: {e}", errno)
                        raise PostconditionError(description, errno)
                elif postcondition:
                    check = None
                    if arg_count(predicate) == 3:
                        check = predicate(rargs, result, tuple_of_dict(preserved_values))
                    else:
                        check = predicate(rargs, result)
                    if not check:
                        if clean_up:
                            try:
                                clean_up(*args, **kwargs)
                            except Exception as e:
                                raise PostconditionError(f"{description}. Clean up failed: {e}", errno)
                        raise PostconditionError(description, errno)

                return result

        elif isfunction(f):
            @wraps(f)
            def inner(*args, **kwargs):
                rargs = build_call(f, *args, **kwargs) if not instance else args[0]

                if precondition and not predicate(rargs):
                    raise PreconditionError(description, errno)

                preserved_values = {}
                for preserver in getattr(wrapped, "__contract_preserver__", [lambda x: {}]):
                    preserved_values.update(preserver(rargs))
                result = f(*args, **kwargs)

                if instance:
                    if not predicate(rargs):
                        if clean_up:
                            try:
                                clean_up(*args, **kwargs)
                            except Exception as e:
                                raise PostconditionError(f"{description}. Clean up failed: {e}", errno)
                        raise PostconditionError(description, errno)
                elif postcondition:
                    check = None
                    if arg_count(predicate) == 3:
                        check = predicate(rargs, result, tuple_of_dict(preserved_values))
                    else:
                        check = predicate(rargs, result)
                    if not check:
                        if clean_up:
                            try:
                                clean_up(*args, **kwargs)
                            except Exception as e:
                                raise PostconditionError(f"{description}. Clean up failed: {e}", errno)
                        raise PostconditionError(description, errno)

                return result

        else:
            raise NotImplementedError

        inner.__contract_wrapped_func__ = wrapped
        return inner
    return require

def require(arg1, arg2=None, arg3=None):
    """
    Specify a precondition described by `description` and tested by
    `predicate`, raising an error `errno` on failure.
    """

    assert any([
        (isinstance(arg1, str) and isfunction(arg2) and arg3 is None), # desc, pred
        (isfunction(arg1) and arg2 is None and arg3 is None), # pred
        (isfunction(arg1) and isinstance(arg2, int) and arg3 is None), # pred, errno
        (isinstance(arg1, str) and isfunction(arg2) and isinstance(arg3, int)) # desc, pred, errno
    ])

    description = ""
    predicate = lambda x: x
    errno = 0

    if isinstance(arg1, str):
        description = arg1
        predicate = arg2
        errno = errno or arg3
    else:
        description = get_function_source(arg1)
        predicate = arg1
        errno = errno or arg2

    return condition(description, predicate, True, False, errno=errno)

def rewrite(args, **kwargs):
    return args._replace(**kwargs)

def preserve(preserver):
    assert isfunction(preserver), "preservers must be functions"
    assert arg_count(preserver) == 1, "preservers can only take a single argument"

    def func(f):
        wrapped = get_wrapped_func(f)
        @wraps(f)
        def inner(*args, **kwargs):
            return f(*args, **kwargs)
        if not hasattr(wrapped, "__contract_preserver__"):
            wrapped.__contract_preserver__ = []
        wrapped.__contract_preserver__.append(preserver)
        return inner
    return func
            
def transform(transformer):
    assert isfunction(transformer), "transformers must be functions"
    assert arg_count(transformer) == 1, "transformers can only take a single argument"

    def func(f):
        @wraps(f)
        def inner(*args, **kwargs):
            rargs = transformer(build_call(f, *args, **kwargs))
            return f(**(rargs._asdict()))
        return inner
    return func

def types(**requirements):
    """
    Specify a precondition based on the types of the function's
    arguments.
    """

    def predicate(args):
        for name, kind in sorted(requirements.items()):
            assert hasattr(args, name), "missing required argument `%s`" % name

            if not isinstance(kind, tuple):
                kind = (kind,)

            if not any(isinstance(getattr(args, name), k) for k in kind):
                return False

        return True

    return condition("the types of arguments must be valid", predicate, True)

def ensure(arg1, arg2=None, arg3=None, arg4=None):
    """
    Specify a precondition described by `description` and tested by
    `predicate`, raising an error with `errno` and calling `clean_up` on failure.
    """

    assert any([
        (isinstance(arg1, str) and isfunction(arg2) and arg3 is None and arg4 is None), # desc, pred
        (isfunction(arg1) and arg2 is None and arg3 is None and arg4 is None), # pred
        (isfunction(arg1) and isinstance(arg2, int) and arg3 is None and arg4 is None), # pred, errno
        (isinstance(arg1, str) and isfunction(arg2) and isinstance(arg3, int) and arg4 is None), # desc, pred, errno
        (isinstance(arg1, str) and isfunction(arg2) and isfunction(arg3) and arg4 is None), # desc, pred, clean
        (isfunction(arg1) and isfunction(arg2) and arg3 is None and arg4 is None), # pred, clean
        (isfunction(arg1) and isinstance(arg2, int) and isfunction(arg3) and arg4 is None), # pred, errno, clean
        (isinstance(arg1, str) and isfunction(arg2) and isinstance(arg3, int) and isfunction(arg4)), # desc, pred, errno, clean
    ])

    description = ""
    predicate = lambda x: x
    errno = 0
    clean_up = None

    if isinstance(arg1, str):
        description = arg1
        predicate = arg2
        errno = arg3 or errno
        clean_up = arg4 or clean_up
    else:
        description = get_function_source(arg1)
        predicate = arg1
        errno = arg2 or errno
        clean_up = arg3 or clean_up

    return condition(description, predicate, False, True, errno=errno, clean_up=clean_up)

def invariant(arg1, arg2=None):
    """
    Specify a class invariant described by `description` and tested
    by `predicate`.
    """

    desc = ""
    predicate = lambda x: x

    if isinstance(arg1, str):
        desc = arg1
        predicate = arg2
    else:
        desc = get_function_source(arg1)
        predicate = arg1

    def invariant(c):
        def check(name, func):
            exceptions = ("__getitem__", "__setitem__", "__lt__", "__le__", "__eq__",
                          "__ne__", "__gt__", "__ge__", "__init__")

            if name.startswith("__") and name.endswith("__") and name not in exceptions:
                return False

            if not ismethod(func) and not isfunction(func):
                return False

            if getattr(func, "__self__", None) is c:
                return False

            return True

        class InvariantContractor(c):
            pass

        for name, value in [(name, getattr(c, name)) for name in dir(c)]:
            if check(name, value):
                setattr(InvariantContractor, name,
                        condition(desc, predicate, name != "__init__", True, True)(value))
        return InvariantContractor
    return invariant

if not __debug__:
    def require(description, predicate):
        def func(f):
            return f
        return func

    def ensure(description, predicate):
        def func(f):
            return f
        return func

    def invariant(description, predicate):
        def func(c):
            return c
        return func

    def transform(transformer):
        def func(c):
            return c
        return func

    def preserve(preserver):
        def func(c):
            return c
        return func

if __name__ == "__main__":
    import doctest
    doctest.testmod()
