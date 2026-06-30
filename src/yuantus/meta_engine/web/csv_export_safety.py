"""CSV export safety helpers."""
from __future__ import annotations

import csv
from typing import Any, Iterable, Mapping


_FORMULA_PREFIXES = ("=", "+", "-", "@")
_CONTROL_PREFIXES = ("\t", "\r", "\n")


def neutralize_csv_formula(value: Any) -> Any:
    """Return a CSV-cell value safe to open in spreadsheet apps.

    Python's csv writer quotes delimiter/newline characters, but spreadsheet apps still
    evaluate quoted cells whose value begins with formula prefixes. Prefix a single quote
    for text that would become a formula after leading whitespace/control trimming.
    """

    if not isinstance(value, str) or not value:
        return value
    stripped = value.lstrip(" \t\r\n")
    if value[0] in _CONTROL_PREFIXES or (stripped and stripped[0] in _FORMULA_PREFIXES):
        return "'" + value
    return value


def _neutralize_row(row: Iterable[Any]) -> list:
    return [neutralize_csv_formula(cell) for cell in row]


class _SafeWriter:
    """``csv.writer``-compatible wrapper that neutralizes every cell against formula injection.

    Only ``writerow``/``writerows`` carry data, so those are the methods we intercept; the
    underlying writer's dialect/behaviour is otherwise unchanged (all constructor kwargs are
    forwarded by :func:`safe_writer`).
    """

    __slots__ = ("_writer",)

    def __init__(self, writer: Any) -> None:
        self._writer = writer

    def writerow(self, row: Iterable[Any]) -> Any:
        return self._writer.writerow(_neutralize_row(row))

    def writerows(self, rows: Iterable[Iterable[Any]]) -> Any:
        return self._writer.writerows([_neutralize_row(r) for r in rows])


class _SafeDictWriter:
    """``csv.DictWriter``-compatible wrapper that neutralizes every VALUE (and header cell).

    Row values are the usual attacker-influenced data. ``writeheader`` is kept SYMMETRIC with
    ``writerow`` -- it routes the field names through the same guard -- so a data-derived
    fieldname (e.g. a user-defined export column) cannot smuggle a formula into the header row
    either. This is a no-op for the developer-constant headers used today.
    """

    __slots__ = ("_writer",)

    def __init__(self, writer: Any) -> None:
        self._writer = writer

    def writeheader(self) -> Any:
        return self.writerow({name: name for name in self._writer.fieldnames})

    def writerow(self, rowdict: Mapping[Any, Any]) -> Any:
        return self._writer.writerow({k: neutralize_csv_formula(v) for k, v in rowdict.items()})

    def writerows(self, rowdicts: Iterable[Mapping[Any, Any]]) -> Any:
        for rowdict in rowdicts:
            self.writerow(rowdict)


def safe_writer(fileobj: Any, **kwargs: Any) -> _SafeWriter:
    """Drop-in replacement for ``csv.writer(...)`` that neutralizes formula injection per cell."""
    return _SafeWriter(csv.writer(fileobj, **kwargs))


def safe_dict_writer(fileobj: Any, fieldnames: Any, **kwargs: Any) -> _SafeDictWriter:
    """Drop-in replacement for ``csv.DictWriter(...)`` that neutralizes formula injection per value."""
    return _SafeDictWriter(csv.DictWriter(fileobj, fieldnames=fieldnames, **kwargs))
