# typedload
# Copyright (C) 2018-2021 Salvo "LtWorf" Tomaselli
#
# typedload is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# author Salvo "LtWorf" Tomaselli <tiposchi@tiscali.it>

from enum import Enum
from typing import Dict, List, NamedTuple, Optional, Set, Tuple, Union
import unittest

from attr import attrs, attrib

from typedload import load, dump, exceptions, typechecks
from typedload import datadumper


class Hair(Enum):
    BROWN = 'brown'
    BLACK = 'black'
    BLONDE = 'blonde'
    WHITE = 'white'


@attrs
class Person:
    name = attrib(default='Turiddu', type=str)
    address = attrib(type=Optional[str], default=None)


@attrs
class DetailedPerson(Person):
    hair = attrib(type=Hair, default=Hair.BLACK)


@attrs
class Students:
    course = attrib(type=str)
    students = attrib(type=List[Person])

@attrs
class Mangle:
    value = attrib(type=int, metadata={'name': 'va.lue'})

class TestAttrDump(unittest.TestCase):

    def test_basicdump(self):
        assert dump(Person()) == {}
        assert dump(Person('Alfio')) == {'name': 'Alfio'}
        assert dump(Person('Alfio', '33')) == {'name': 'Alfio', 'address': '33'}

    def test_norepr(self):
        @attrs
        class A:
            i = attrib(type=int)
            j = attrib(type=int, repr=False)
        assert dump(A(1,1)) == {'i': 1}

    def test_dumpdefault(self):
        dumper = datadumper.Dumper()
        dumper.hidedefault = False
        assert dumper.dump(Person()) == {'name': 'Turiddu', 'address': None}

    def test_factory_dump(self):
        @attrs
        class A:
            a = attrib(factory=list, metadata={'ciao': 'ciao'}, type=List[int])

        assert dump(A()) == {}
        assert dump(A(), hidedefault=False) == {'a': []}

    def test_nesteddump(self):
        assert dump(
            Students('advanced coursing', [
            Person('Alfio'),
            Person('Carmelo', 'via mulino'),
        ])) == {
            'course': 'advanced coursing',
            'students': [
                {'name': 'Alfio'},
                {'name': 'Carmelo', 'address': 'via mulino'},
            ]
        }


class TestAttrload(unittest.TestCase):

    def test_condition(self):
        assert typechecks.is_attrs(Person)
        assert typechecks.is_attrs(Students)
        assert typechecks.is_attrs(Mangle)
        assert typechecks.is_attrs(DetailedPerson)
        assert not typechecks.is_attrs(int)
        assert not typechecks.is_attrs(List[int])
        assert not typechecks.is_attrs(Union[str, int])
        assert not typechecks.is_attrs(Tuple[str, int])

    def test_basicload(self):
        assert load({'name': 'gino'}, Person) == Person('gino')
        assert load({}, Person) == Person('Turiddu')

    def test_nestenum(self):
        assert load({'hair': 'white'}, DetailedPerson) == DetailedPerson(hair=Hair.WHITE)

    def test_nested(self):
        assert load(
            {
                'course': 'advanced coursing',
                'students': [
                    {'name': 'Alfio'},
                    {'name': 'Carmelo', 'address': 'via mulino'},
                ]
            },
            Students,
        ) == Students('advanced coursing', [
            Person('Alfio'),
            Person('Carmelo', 'via mulino'),
        ])

    def test_uuid(self):
        import uuid

        @attrs
        class A:
            a = attrib(type=int)
            uuid_value = attrib(type=str, init=False)

            def __attrs_post_init__(self):
                self.uuid_value = str(uuid.uuid4())

        assert type(load({'a': 1}, A).uuid_value) == str
        assert load({'a': 1}, A) != load({'a': 1}, A)


class TestMangling(unittest.TestCase):

    def test_load_metanames(self):
        a = {'va.lue': 12}
        b = a.copy()
        assert load(a, Mangle) == Mangle(12)
        assert a == b

    def test_dump_metanames(self):
        assert dump(Mangle(12)) == {'va.lue': 12}

    def test_mangle_rename(self):
        @attrs
        class Mangle:
            a = attrib(type=int, metadata={'name': 'b'})
            b = attrib(type=str, metadata={'name': 'a'})
        assert load({'b': 1, 'a': 'ciao'}, Mangle) == Mangle(1, 'ciao')
        assert dump(Mangle(1, 'ciao')) == {'b': 1, 'a': 'ciao'}

    def test_weird_mangle(self):
        @attrs
        class Mangle:
            a = attrib(type=int, metadata={'name': 'b', 'alt': 'q'})
            b = attrib(type=str, metadata={'name': 'a'})
        assert load({'b': 1, 'a': 'ciao'}, Mangle) == Mangle(1, 'ciao')
        assert load({'q': 1, 'b': 'ciao'}, Mangle, mangle_key='alt') == Mangle(1, 'ciao')
        assert dump(Mangle(1, 'ciao')) == {'b': 1, 'a': 'ciao'}
        assert dump(Mangle(1, 'ciao'), mangle_key='alt') == {'q': 1, 'b': 'ciao'}


class TestAttrExceptions(unittest.TestCase):

    def test_wrongtype(self):
        try:
            load(3, Person)
        except exceptions.TypedloadTypeError:
            pass

        data = {
            'course': 'how to be a corsair',
            'students': [
                {'name': 'Alfio'},
                3
            ]
        }
        try:
            load(data, Students)
        except exceptions.TypedloadTypeError as e:
            assert e.trace[-1].annotation[1] == 1

    def test_index(self):
        try:
            load(
                {
                    'course': 'advanced coursing',
                    'students': [
                        {'name': 'Alfio'},
                        {'name': 'Carmelo', 'address': 'via mulino'},
                        [],
                    ]
                },
                Students,
            )
        except Exception as e:
            assert e.trace[-2].annotation[1] == 'students'
            assert e.trace[-1].annotation[1] == 2
