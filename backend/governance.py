"""Pure release decisions. Passing quality alone never authorizes promotion."""


def evaluate_gates(macro_f1, compatible, license_approved, security_scan_passed):
    return {
        "quality": bool(macro_f1 >= 0.85),
        "compatibility": bool(compatible),
        "license": bool(license_approved),
        "security": bool(security_scan_passed),
    }


def eligible(gates, authorized=False):
    return (
        authorized
        and set(gates) == {"quality", "compatibility", "license", "security"}
        and all(gates.values())
    )
