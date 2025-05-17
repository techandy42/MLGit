import pytest
from pathlib import Path
from mlgit.core.old_type_validator import validate_type


@pytest.fixture

def basic_sets():
    internal_classes = {'MyClass', 'OtherClass'}
    internal_type_aliases = {'AliasType'}
    external_identifiers = {'ExternalFunc'}
    external_modules = {'extmod', 'requests'}
    return internal_classes, internal_type_aliases, external_identifiers, external_modules


@pytest.mark.parametrize(
    "annotation,expected",
    [
        ('int', True),
        ('float', True),
        ('str', True),
        ('bool', True),
        ('bytes', True),
        ('bytearray', True),
        ('memoryview', True),
        ('Any', True),
        ('None', True),
        ('List[int]', True),
        ('Dict[str,int]', True),
        ('Tuple[int,str,bool]', True),
        ('Set[float]', True),
        ('FrozenSet[MyClass]', True),
        ('Deque[AliasType]', True),
        ('DefaultDict[str,AliasType]', True),
        ('Counter[ExternalFunc]', True),
        ('Iterable[OtherClass]', True),
        ('Mapping[str,OtherClass]', True),
        ('Optional[int]', True),
        ('Union[int,str]', True),
        ('Dict[str,List[int]]', True),
        ('List[List[AliasType]]', True),
        ('MyClass', True),
        ('AliasType', True),
        ('ExternalFunc', True),
        ('extmod.SomeType', True),
        ('requests.Session', True),
        ('UnknownType', False),
        ('List[UnknownType]', False),
        ('List[int', False),
        ('', False),
    ],
)

def test_validate_type(basic_sets, annotation, expected):
    internal_classes, internal_type_aliases, external_identifiers, external_modules = basic_sets
    result = validate_type(
        annotation,
        internal_classes,
        internal_type_aliases,
        external_identifiers,
        external_modules
    )
    assert result == expected
