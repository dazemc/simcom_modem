import sys
from typing import ClassVar


def py_version_check() -> bool:
    """Return ``True`` when running on Python 3.13 or newer."""
    if sys.version_info < (3, 13):  # noqa: UP036
        print("Python version must be 3.13 or greater")
        print("\nExiting...")
        return False
    return True


class SingletonMeta(type):
    """
    This metaclass ensures that only one instance of any class using it exists.
    """

    _instances: ClassVar[dict[type, object]] = {}

    def __call__(cls, *args, **kwargs):
        """
        If an instance of cls doesn't exist, create one and store it in _instances.
        Otherwise, return the existing instance.
        """
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
