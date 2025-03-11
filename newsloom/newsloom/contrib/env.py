import os
from typing import Type, TypeVar, cast, get_args, get_origin


T = TypeVar('T')

_DEFAULT = object()


def convert_to_type(value: str, type_: Type[T]) -> T:
    try:
        if get_origin(type_) is list:
            element_type = get_args(type_)[0]
            items = [item.strip() for item in value.split(',')]

            if element_type == bool:
                return cast(T, [item.lower() in ('true', '1', 'yes', 'y') for item in items])
            return cast(T, [element_type(item) for item in items])

        if type_ == bool:
            return cast(T, value.lower() in ('true', '1', 'yes', 'y'))
        return type_(value)  # type: ignore
    except (ValueError, TypeError) as e:
        raise ValueError(f"Failed to cast value '{value}' to type {type_.__name__}") from e


def get_env_var(name: str, type: Type[T] = str, default: T | None = _DEFAULT) -> T:
    value = os.getenv(name)

    if value is None:
        if default != _DEFAULT:
            return default
        raise ValueError(f"Environment variable {name} not found and no default value specified")

    return convert_to_type(value, type)