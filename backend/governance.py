"""Pure release decisions. Passing quality alone never authorizes promotion."""
import math
from typing import TypedDict


class GateSet(TypedDict):
    quality: bool
    compatibility: bool
    license: bool
    security: bool


GATE_NAMES = frozenset({'quality', 'compatibility', 'license', 'security'})


def evaluate_gates(macro_f1: float, compatible: bool, license_approved: bool,
                   security_scan_passed: bool) -> GateSet:
    if (isinstance(macro_f1, bool) or not isinstance(macro_f1, (int, float))
            or not 0 <= macro_f1 <= 1 or not math.isfinite(macro_f1)):
        raise ValueError('Quality evidence must be a finite probability')
    if any(type(flag) is not bool for flag in (compatible, license_approved, security_scan_passed)):
        raise ValueError('Release evidence flags must be explicit booleans')
    return {
        'quality': macro_f1 >= 0.85,
        'compatibility': compatible,
        'license': license_approved,
        'security': security_scan_passed,
    }


def eligible(gates: object, authorized: object = False) -> bool:
    # Do not coerce JSON strings/numbers, missing evidence or authorization tokens.
    # This pure predicate does not establish an authenticated actor or perform release.
    return (authorized is True and type(gates) is dict
            and set(gates) == GATE_NAMES
            and all(value is True for value in gates.values()))
