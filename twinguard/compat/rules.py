"""
TwinGuard Module 3: Compatibility rules.

Checks synthetic, non-weapon test components against platform constraints.
"""


def check_voltage(component, platform):
    """Check whether component voltage is within platform limits."""
    actual = component.get("voltage_v")

    if actual is None:
        return {
            "rule_id": "VOLTAGE-001",
            "requirement": "Component voltage must be specified",
            "actual": "Missing",
        }

    minimum = platform.get("min_voltage_v")
    maximum = platform.get("max_voltage_v")

    if minimum is None or maximum is None:
        return {
            "rule_id": "VOLTAGE-001",
            "requirement": "Platform voltage limits must be specified",
            "actual": f"{actual} V",
        }

    if not minimum <= actual <= maximum:
        return {
            "rule_id": "VOLTAGE-001",
            "requirement": f"Voltage must be between {minimum} V and {maximum} V",
            "actual": f"{actual} V",
        }

    return None


def check_protocol(component, platform):
    """Check whether the communication protocol is supported."""
    required = component.get("protocol")
    supported = platform.get("supported_protocols", [])

    if not required:
        return {
            "rule_id": "PROTOCOL-001",
            "requirement": "Component protocol must be specified",
            "actual": "Missing",
        }

    if required not in supported:
        return {
            "rule_id": "PROTOCOL-001",
            "requirement": f"Protocol must be one of {supported}",
            "actual": required,
        }

    return None


def check_firmware(component, platform):
    """Check firmware compatibility."""
    required = component.get("firmware")
    supported = platform.get("supported_firmware", [])

    if not required:
        return {
            "rule_id": "FIRMWARE-001",
            "requirement": "Component firmware must be specified",
            "actual": "Missing",
        }

    if required not in supported:
        return {
            "rule_id": "FIRMWARE-001",
            "requirement": f"Firmware must be one of {supported}",
            "actual": required,
        }

    return None


def check_interface(component, platform):
    """Check whether the component interface is supported."""
    required = component.get("interface")
    supported = platform.get("supported_interfaces", [])

    if not required:
        return {
            "rule_id": "INTERFACE-001",
            "requirement": "Component interface must be specified",
            "actual": "Missing",
        }

    if required not in supported:
        return {
            "rule_id": "INTERFACE-001",
            "requirement": f"Interface must be one of {supported}",
            "actual": required,
        }

    return None


def check_configuration(component, platform):
    """Check whether the component configuration is approved."""
    required = component.get("configuration")
    supported = platform.get("supported_configurations", [])

    if not required:
        return {
            "rule_id": "CONFIG-001",
            "requirement": "Component configuration must be specified",
            "actual": "Missing",
        }

    if required not in supported:
        return {
            "rule_id": "CONFIG-001",
            "requirement": f"Configuration must be one of {supported}",
            "actual": required,
        }

    return None


def evaluate_rules(component, platform):
    """Run all compatibility rules and return every violation."""
    checks = [
        check_voltage,
        check_protocol,
        check_firmware,
        check_interface,
        check_configuration,
    ]

    violations = []

    for check in checks:
        violation = check(component, platform)

        if violation is not None:
            violations.append(violation)

    return violations