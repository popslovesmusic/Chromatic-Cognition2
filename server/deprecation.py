"""
Deprecation utilities for Soundlab + D-ASE
Feature 026 (FR-004): API deprecation warnings and tracking

This module provides decorators and utilities for marking APIs as deprecated,
issuing warnings, and tracking deprecated functionality for eventual removal.
"""

import functools
import warnings
from typing import Optional, Callable, Any


class DeprecationInfo:
    """Store information about a deprecated item"""

    def __init__(
        self,
        name: str,
        deprecated_in: str,
        remove_in: str,
        reason: Optional[str] = None,
        alternative: Optional[str] = None,
    ):
        self.name = name
        self.deprecated_in = deprecated_in
        self.remove_in = remove_in
        self.reason = reason
        self.alternative = alternative

    def __str__(self) -> str:
        msg = f"{self.name} is deprecated since v{self.deprecated_in} and will be removed in v{self.remove_in}."
        if self.reason:
            msg += f" Reason: {self.reason}."
        if self.alternative:
            msg += f" Use {self.alternative} instead."
        return msg


# Registry of all deprecated items
_DEPRECATION_REGISTRY = {}


def deprecated(
    deprecated_in: str,
    remove_in: str,
    reason: Optional[str] = None,
    alternative: Optional[str] = None,
) -> Callable:
    """
    Decorator to mark a function, method, or class as deprecated.

    Args:
        deprecated_in: Version when the item was deprecated (e.g., "1.1.0")
        remove_in: Version when the item will be removed (e.g., "2.0.0")
        reason: Optional reason for deprecation
        alternative: Optional alternative API to use

    Example:
        @deprecated(
            deprecated_in="1.1.0",
            remove_in="2.0.0",
            reason="Replaced by optimized implementation",
            alternative="new_function()"
        )
        def old_function():
            pass
    """

    def decorator(obj: Any) -> Any:
        # Determine the name
        if hasattr(obj, "__name__"):
            name = obj.__name__
        elif hasattr(obj, "__class__"):
            name = obj.__class__.__name__
        else:
            name = str(obj)

        # Create deprecation info
        info = DeprecationInfo(
            name=name,
            deprecated_in=deprecated_in,
            remove_in=remove_in,
            reason=reason,
            alternative=alternative,
        )

        # Register the deprecation
        _DEPRECATION_REGISTRY[name] = info

        # If it's a class, wrap its __init__
        if isinstance(obj, type):
            original_init = obj.__init__

            @functools.wraps(original_init)
            def new_init(self, *args, **kwargs):
                warnings.warn(
                    str(info),
                    category=DeprecationWarning,
                    stacklevel=2,
                )
                return original_init(self, *args, **kwargs)

            obj.__init__ = new_init
            return obj

        # If it's a function or method, wrap it
        @functools.wraps(obj)
        def wrapper(*args, **kwargs):
            warnings.warn(
                str(info),
                category=DeprecationWarning,
                stacklevel=2,
            )
            return obj(*args, **kwargs)

        return wrapper

    return decorator


def deprecated_parameter(
    param_name: str,
    deprecated_in: str,
    remove_in: str,
    reason: Optional[str] = None,
    alternative: Optional[str] = None,
) -> Callable:
    """
    Decorator to mark a function parameter as deprecated.

    Args:
        param_name: Name of the deprecated parameter
        deprecated_in: Version when the parameter was deprecated
        remove_in: Version when the parameter will be removed
        reason: Optional reason for deprecation
        alternative: Optional alternative parameter to use

    Example:
        @deprecated_parameter(
            "old_param",
            deprecated_in="1.1.0",
            remove_in="2.0.0",
            alternative="new_param"
        )
        def my_function(new_param=None, old_param=None):
            pass
    """

    def decorator(func: Callable) -> Callable:
        info = DeprecationInfo(
            name=f"{func.__name__}.{param_name}",
            deprecated_in=deprecated_in,
            remove_in=remove_in,
            reason=reason,
            alternative=alternative,
        )

        _DEPRECATION_REGISTRY[f"{func.__name__}.{param_name}"] = info

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if param_name in kwargs:
                warnings.warn(
                    f"Parameter '{param_name}' of {func.__name__}() {info}",
                    category=DeprecationWarning,
                    stacklevel=2,
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator


def deprecated_alias(
    old_name: str,
    new_name: str,
    deprecated_in: str,
    remove_in: str,
) -> Callable:
    """
    Create a deprecated alias for a function or class.

    Args:
        old_name: Name of the deprecated alias
        new_name: Name of the new function/class
        deprecated_in: Version when the alias was deprecated
        remove_in: Version when the alias will be removed

    Returns:
        A wrapped version of the new function that issues a deprecation warning

    Example:
        def new_function():
            pass

        old_function = deprecated_alias(
            "old_function",
            "new_function",
            deprecated_in="1.1.0",
            remove_in="2.0.0"
        )(new_function)
    """

    def decorator(obj: Any) -> Any:
        info = DeprecationInfo(
            name=old_name,
            deprecated_in=deprecated_in,
            remove_in=remove_in,
            reason=f"Use {new_name} instead",
            alternative=new_name,
        )

        _DEPRECATION_REGISTRY[old_name] = info

        if isinstance(obj, type):
            # For classes, create a new class that warns on instantiation
            class DeprecatedClass(obj):
                def __init__(self, *args, **kwargs):
                    warnings.warn(
                        str(info),
                        category=DeprecationWarning,
                        stacklevel=2,
                    )
                    super().__init__(*args, **kwargs)

            DeprecatedClass.__name__ = old_name
            return DeprecatedClass

        # For functions
        @functools.wraps(obj)
        def wrapper(*args, **kwargs):
            warnings.warn(
                str(info),
                category=DeprecationWarning,
                stacklevel=2,
            )
            return obj(*args, **kwargs)

        wrapper.__name__ = old_name
        return wrapper

    return decorator


def get_deprecations() -> dict:
    """
    Get all registered deprecations.

    Returns:
        Dictionary mapping deprecated item names to DeprecationInfo objects
    """
    return _DEPRECATION_REGISTRY.copy()


def get_deprecations_by_version(remove_in: str) -> dict:
    """
    Get deprecations scheduled for removal in a specific version.

    Args:
        remove_in: Version to filter by (e.g., "2.0.0")

    Returns:
        Dictionary of deprecations scheduled for removal in that version
    """
    return {
        name: info
        for name, info in _DEPRECATION_REGISTRY.items()
        if info.remove_in == remove_in
    }


def print_deprecation_report():
    """Print a formatted report of all deprecations."""
    print("=" * 80)
    print("Soundlab + D-ASE Deprecation Report")
    print("=" * 80)
    print()

    if not _DEPRECATION_REGISTRY:
        print("No deprecated items.")
        return

    # Group by removal version
    by_version = {}
    for name, info in _DEPRECATION_REGISTRY.items():
        if info.remove_in not in by_version:
            by_version[info.remove_in] = []
        by_version[info.remove_in].append(info)

    for version in sorted(by_version.keys()):
        print(f"Scheduled for removal in v{version}:")
        print("-" * 80)
        for info in by_version[version]:
            print(f"  • {info.name}")
            print(f"    Deprecated in: v{info.deprecated_in}")
            if info.reason:
                print(f"    Reason: {info.reason}")
            if info.alternative:
                print(f"    Alternative: {info.alternative}")
            print()
        print()


# Example usage and tests
if __name__ == "__main__":
    # Example 1: Deprecated function
    @deprecated(
        deprecated_in="1.1.0",
        remove_in="2.0.0",
        reason="Replaced by optimized implementation",
        alternative="fast_process()",
    )
    def slow_process(data):
        """Old slow processing function."""
        return data

    # Example 2: Deprecated class
    @deprecated(
        deprecated_in="1.1.0",
        remove_in="2.0.0",
        reason="Use the new PhiProcessor class",
        alternative="PhiProcessor",
    )
    class OldProcessor:
        """Old processor class."""

        def __init__(self):
            pass

    # Example 3: Deprecated parameter
    @deprecated_parameter(
        "old_format",
        deprecated_in="1.1.0",
        remove_in="2.0.0",
        alternative="output_format",
    )
    def export_data(data, output_format="json", old_format=None):
        """Export data in various formats."""
        if old_format:
            output_format = old_format
        return f"Exporting as {output_format}"

    # Print report
    print_deprecation_report()

    # Test the decorators (these will issue warnings)
    print("Testing deprecated items (warnings expected):")
    print("-" * 80)

    # This will warn
    result = slow_process([1, 2, 3])
    print(f"Result: {result}")

    # This will warn
    processor = OldProcessor()
    print(f"Processor: {processor}")

    # This will warn
    output = export_data([1, 2, 3], old_format="csv")
    print(f"Output: {output}")
