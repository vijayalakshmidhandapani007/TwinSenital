"""
TwinGuard Module 3: Compatibility checker.

Loads component and platform specifications, runs compatibility rules,
and returns the required evidence result.
"""

import json
from pathlib import Path

from compat.rules import evaluate_rules


BASE_DIR = Path(__file__).parent
REGISTRY_FILE = BASE_DIR / "registry" / "components.json"
PLATFORMS_FILE = BASE_DIR / "registry" / "platforms.json"


def load_registry():
    """Load component and platform specifications from JSON."""
    with open(REGISTRY_FILE, "r", encoding="utf-8") as file:
        components_data = json.load(file)

    with open(PLATFORMS_FILE, "r", encoding="utf-8") as file:
        platforms_data = json.load(file)

    return components_data, platforms_data


def check_compatibility(
    module_id: str,
    platform_id: str,
) -> dict:
    """
    Check a component against a platform.

    Returns:
        {
            "evidence_id": str,
            "compatible": bool,
            "violations": [...]
        }
    """
    components_data, platforms_data = load_registry()

    components = components_data.get("components", {})
    platforms = platforms_data.get("platforms", {})

    component = components.get(module_id)
    platform = platforms.get(platform_id)

    if component is None:
        return {
            "evidence_id": f"COMPAT-{module_id}-{platform_id}",
            "compatible": False,
            "violations": [
                {
                    "rule_id": "COMPONENT-404",
                    "requirement": "Component must exist in registry",
                    "actual": module_id,
                }
            ],
        }

    if platform is None:
        return {
            "evidence_id": f"COMPAT-{module_id}-{platform_id}",
            "compatible": False,
            "violations": [
                {
                    "rule_id": "PLATFORM-404",
                    "requirement": "Platform must exist in registry",
                    "actual": platform_id,
                }
            ],
        }

    violations = evaluate_rules(component, platform)

    return {
        "evidence_id": f"COMPAT-{module_id}-{platform_id}",
        "compatible": len(violations) == 0,
        "violations": violations,
    }


if __name__ == "__main__":
    import pprint

    result = check_compatibility(
        module_id="SENSOR-B2",
        platform_id="TEST-PLATFORM-1",
    )

    pprint.pp(result)