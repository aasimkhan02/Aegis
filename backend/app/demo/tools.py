"""Local tool implementations for BharatHome Customer Support Assistant."""

from typing import Any, Callable
import uuid


def product_lookup(product_name: str) -> dict[str, Any]:
    """Retrieve fictional product specifications for a BharatHome appliance.

    Args:
        product_name: Name or category of appliance (e.g. 'refrigerator', 'washing machine').

    Returns:
        dict containing structured product specifications or error message.
    """
    if not product_name or not isinstance(product_name, str):
        return {"status": "error", "message": "Invalid product_name provided."}

    p = product_name.lower().strip()

    if "refrigerator" in p or "fridge" in p:
        return {
            "status": "success",
            "product": "BharatHome FrostFree 340L Double Door Refrigerator",
            "model_number": "BH-FF340D",
            "capacity": "340 Litres (Fresh Food: 252L, Freezer: 88L)",
            "energy_rating": "BEE 3-Star (212 kWh/year)",
            "refrigerant": "R600a Isobutane",
            "cooling_type": "Multi-Flow 360 Airflow Inverter",
            "dimensions_mm": {"width": 605, "depth": 680, "height": 1680},
            "weight_kg": 64,
            "key_features": [
                "Toughened glass shelves (150kg load)",
                "Convertible freezer zone",
                "Stabilizer-free operation (135V - 290V)",
                "Deodorizing carbon active filter",
            ],
        }

    elif "washing" in p or "washer" in p:
        return {
            "status": "success",
            "product": "BharatHome TurboClean 7kg Front Load Washing Machine",
            "model_number": "BH-WM70FL",
            "capacity": "7.0 kg",
            "motor": "Direct Motion Brushless Inverter (1200 RPM max)",
            "heater": "Inbuilt ceramic heater up to 90°C",
            "programs_count": 15,
            "water_pressure_bar": "0.3 to 10.0 bar",
            "key_features": ["Allergy Steam", "Quick 15", "Anti-Bacterial Door Seal", "Auto Drum Clean"],
        }

    elif "air conditioner" in p or "ac" in p:
        return {
            "status": "success",
            "product": "BharatHome CoolBreeze 1.5 Ton 5-Star Dual Inverter Split AC",
            "model_number": "BH-AC155S",
            "capacity_ton": 1.5,
            "cooling_watts": 5100,
            "energy_rating": "5-Star (ISEER 5.15)",
            "condenser": "100% Copper with BlueFin anti-corrosion coating",
            "refrigerant": "R32",
            "connectivity": "2.4 GHz WiFi Smart App Control",
        }

    elif "microwave" in p or "oven" in p:
        return {
            "status": "success",
            "product": "BharatHome AeroGrill 28L Convection Microwave Oven",
            "model_number": "BH-MC28G",
            "capacity": "28 Litres",
            "power_output_watts": {"microwave": 900, "grill": 1200, "convection": 1950},
            "cavity": "Stainless Steel Anti-Bacterial Cavity",
            "turntable_diameter_mm": 315,
            "safety_feature": "Dual Mechanical Door Interlock Switch",
        }

    elif "water purifier" in p or "purifier" in p or "ro" in p:
        return {
            "status": "success",
            "product": "BharatHome AquaPure 8L RO+UV+TDS Mineral Water Purifier",
            "model_number": "BH-WP800",
            "capacity": "8.0 Litres",
            "purification_stages": 8,
            "technology": "RO + UV e-boiling + Active Copper Zinc mineralizer",
            "inlet_pressure_bar": "0.3 to 3.0 bar",
            "recommended_raw_tds": "Up to 2000 ppm",
        }

    elif "induction" in p or "cooktop" in p:
        return {
            "status": "success",
            "product": "BharatHome CookSmart 2000W Induction Cooktop",
            "model_number": "BH-IC20",
            "power_watts": 2000,
            "voltage": "230V, 50Hz",
            "preset_menus": 8,
            "safety_feature": "Child Lock (3-second key hold deactivation) + Auto Pan Sensor",
        }

    else:
        return {
            "status": "not_found",
            "product_queried": product_name,
            "message": f"Product '{product_name}' was not found in the official BharatHome Appliances catalog.",
            "available_categories": [
                "refrigerator",
                "washing machine",
                "air conditioner",
                "microwave oven",
                "water purifier",
                "induction cooktop",
            ],
        }


def warranty_lookup(product_name: str) -> dict[str, Any]:
    """Retrieve warranty duration, coverage, and exclusions for a BharatHome appliance.

    Args:
        product_name: Name of product to look up warranty for.

    Returns:
        dict containing warranty terms and exclusions, or not_found if unlisted.
    """
    if not product_name or not isinstance(product_name, str):
        return {"status": "error", "message": "Invalid product_name provided."}

    p = product_name.lower().strip()

    if "refrigerator" in p or "fridge" in p:
        return {
            "status": "success",
            "product": "BharatHome FrostFree Refrigerator",
            "comprehensive_warranty": "1 Year on entire appliance",
            "extended_component_warranty": "10 Years on Digital Inverter Compressor part",
            "coverage_details": "Covers all internal electrical and mechanical defects in Year 1. In Years 2-10, replacement compressor is free.",
            "exclusions": [
                "Plastic door shelves and vegetable crispers",
                "Glass shelves broken by external impact",
                "Rubber door gaskets",
                "Labor and gas recharging costs after Year 1",
                "Damage from ungrounded sockets or power surges",
            ],
        }

    elif "washing" in p or "washer" in p:
        return {
            "status": "success",
            "product": "BharatHome TurboClean Washing Machine",
            "comprehensive_warranty": "2 Years on entire machine",
            "extended_component_warranty": "10 Years on Brushless Inverter Motor",
            "coverage_details": "Covers electronic PCB, water valves, drum assembly, and motor.",
            "exclusions": [
                "Rubber door gasket torn by coins or sharp items",
                "External drain and inlet pipes after 6 months",
                "Rat or insect wire bites",
                "Commercial laundry usage",
            ],
        }

    elif "air conditioner" in p or "ac" in p:
        return {
            "status": "success",
            "product": "BharatHome CoolBreeze Split AC",
            "comprehensive_warranty": "1 Year on complete unit",
            "extended_component_warranty": "5 Years on indoor/outdoor PCB + 10 Years on Dual Inverter Compressor",
            "coverage_details": "Covers compressor, condenser coil, and inverter circuit boards.",
            "exclusions": [
                "Gas leakages caused by physical pipe bending or external puncture",
                "Plastic front grille fading or cracking",
                "Remote control physical damage",
            ],
        }

    elif "microwave" in p or "oven" in p:
        return {
            "status": "success",
            "product": "BharatHome AeroGrill Microwave",
            "comprehensive_warranty": "1 Year comprehensive",
            "extended_component_warranty": "3 Years on Magnetron tube",
            "coverage_details": "Covers magnetron, high-voltage diode, touch control membrane, and turntable motor.",
            "exclusions": [
                "Glass turntable plate breakage",
                "Enamel/paint peeling due to harsh chemical cleaners",
                "Damaged door interlocks from forced tampering",
            ],
        }

    elif "water purifier" in p or "ro" in p:
        return {
            "status": "success",
            "product": "BharatHome AquaPure RO Water Purifier",
            "comprehensive_warranty": "1 Year on electrical components (SMPS, booster pump, UV lamp)",
            "extended_component_warranty": "RO membrane covered for 1 year up to 2000 ppm input TDS",
            "coverage_details": "Covers pump motor, power supply, and UV sterilization tube.",
            "exclusions": [
                "Pre-filter and sediment filters after 6 months",
                "Mineral cartridge saturation",
                "Physical tank cracks",
            ],
        }

    elif "induction" in p or "cooktop" in p:
        return {
            "status": "success",
            "product": "BharatHome CookSmart Induction Cooktop",
            "comprehensive_warranty": "1 Year on entire appliance",
            "extended_component_warranty": "None",
            "coverage_details": "Covers induction heating coil, cooling fan, and main motherboard.",
            "exclusions": [
                "Top ceramic/crystal glass plate breakage or thermal shock cracks",
                "Water seepage inside bottom ventilation slots",
            ],
        }

    else:
        return {
            "status": "not_found",
            "product_queried": product_name,
            "message": (
                f"No warranty record exists for '{product_name}'. BharatHome does not manufacture or "
                "warranty unlisted products outside its official home appliance catalog."
            ),
        }


def troubleshooting_lookup(product_name: str, issue: str) -> dict[str, Any]:
    """Retrieve troubleshooting instructions for a specific appliance and issue.

    Args:
        product_name: Appliance name or category.
        issue: Symptom, fault, or error code (e.g. 'OE error', 'E4 error', 'warm air', 'turntable').

    Returns:
        dict containing step-by-step diagnostic and safety resolution steps.
    """
    if not product_name or not issue:
        return {"status": "error", "message": "Both product_name and issue must be specified."}

    p = product_name.lower().strip()
    iss = issue.lower().strip()

    if ("washing" in p or "washer" in p) and ("oe" in iss or "drain" in iss or "water" in iss):
        return {
            "status": "success",
            "product": "BharatHome TurboClean Washing Machine",
            "fault": "OE Error (Water Drainage Failure)",
            "severity": "medium",
            "steps": [
                "Unplug the machine from the electrical socket for safety.",
                "Open the bottom right maintenance door on the front panel.",
                "Place a shallow tray under the drain area.",
                "Pull out the small drain hose and uncork it to empty residual drum water.",
                "Unscrew the main circular debris filter counter-clockwise and clear trapped lint, coins, or hairpins.",
                "Reinstall filter securely clockwise, close flap, and resume wash cycle.",
            ],
            "safety_warning": "Always disconnect main power before opening the lower pump filter.",
        }

    elif ("refrigerator" in p or "fridge" in p) and ("e4" in iss or "frost" in iss or "beep" in iss):
        return {
            "status": "success",
            "product": "BharatHome FrostFree Refrigerator",
            "fault": "E4 Error (Defrost Sensor / Excess Frost Fault)",
            "severity": "medium",
            "steps": [
                "Turn off wall power switch for 5 minutes, then power back on to reboot microcontroller.",
                "Verify freezer door closes completely and rubber gasket is clean and free of ice crust.",
                "Ensure vents inside freezer are not choked by stacked frozen food packages.",
                "If E4 recurs after 30 minutes, sensor replacement by technician is required.",
            ],
            "safety_warning": "Do not use sharp knives or ice picks to scrape frost from cooling coils.",
        }

    elif ("microwave" in p or "oven" in p) and ("turntable" in iss or "spin" in iss or "rotate" in iss):
        return {
            "status": "success",
            "product": "BharatHome AeroGrill Microwave",
            "fault": "Glass Turntable Not Rotating",
            "severity": "low",
            "steps": [
                "Unplug microwave and remove glass tray.",
                "Clean the roller ring and wheels under warm water to remove grease and food crumbs.",
                "Check that the center drive coupler is firmly attached to the motor shaft.",
                "Realign glass tray so that the central indents engage the rotating drive hub.",
            ],
            "safety_warning": "Safe to operate for short intervals, but uneven heating will occur without rotation.",
        }

    elif ("air conditioner" in p or "ac" in p) and ("warm" in iss or "cool" in iss):
        return {
            "status": "success",
            "product": "BharatHome CoolBreeze Split AC",
            "fault": "Blowing Warm Air / Inadequate Cooling",
            "severity": "medium",
            "steps": [
                "Ensure remote control is in 'Cool' mode (Snowflake symbol) and set at least 2°C below room temperature.",
                "Wait 3 to 5 minutes for compressor protection safety delay to initiate cooling.",
                "Open indoor unit front panel and wash dust mesh filters with tap water.",
                "Ensure outdoor unit has at least 2 feet of clear ventilation clearance.",
            ],
            "safety_warning": "Do not spray water directly on the outdoor electrical junction box.",
        }

    elif ("induction" in p or "cooktop" in p) and ("lock" in iss or "padlock" in iss or "button" in iss):
        return {
            "status": "success",
            "product": "BharatHome CookSmart Induction Cooktop",
            "fault": "Child Lock Active / Keypad Unresponsive",
            "severity": "low",
            "steps": [
                "Locate the Key / Lock icon on the glass touch panel.",
                "Press and hold the Lock icon firmly for 3 to 5 continuous seconds.",
                "Listen for the double-beep notification; the red lock LED will turn off.",
            ],
            "safety_warning": "Keep surface clean and dry before touching capacitive sensor buttons.",
        }

    else:
        return {
            "status": "generic_guidance",
            "product_queried": product_name,
            "issue_queried": issue,
            "message": (
                f"No specific troubleshooting procedure is indexed for '{issue}' on '{product_name}'. "
                "Ensure appliance is properly powered, consult the user manual, or book a service technician."
            ),
        }


def create_service_request(customer_name: str, product_name: str, issue: str) -> dict[str, Any]:
    """Create a simulated service request for a customer appliance.

    Args:
        customer_name: Full name of the customer.
        product_name: The appliance needing service.
        issue: Description of problem or fault.

    Returns:
        dict containing reference ID, scheduled SLA, and confirmation status.
    """
    if not customer_name or not isinstance(customer_name, str) or len(customer_name.strip()) < 2:
        return {"status": "error", "message": "A valid customer_name is required to create a service request."}

    if not product_name or not isinstance(product_name, str):
        return {"status": "error", "message": "A valid product_name is required to create a service request."}

    if not issue or not isinstance(issue, str):
        return {"status": "error", "message": "A description of the issue is required."}

    ref_id = f"SR-BH-{uuid.uuid4().hex[:6].upper()}"

    return {
        "status": "created",
        "reference_id": ref_id,
        "customer_name": customer_name.strip(),
        "product_name": product_name.strip(),
        "issue_description": issue.strip(),
        "estimated_arrival": "Within 24 to 48 business hours",
        "service_provider": "BharatHome Authorized Technical Service",
        "message": (
            f"Service request {ref_id} successfully booked for {customer_name.strip()}. "
            f"An authorized technician will contact you within 24-48 business hours regarding your {product_name.strip()}."
        ),
    }


# Tool Dispatcher Registry
AVAILABLE_TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "product_lookup": product_lookup,
    "warranty_lookup": warranty_lookup,
    "troubleshooting_lookup": troubleshooting_lookup,
    "create_service_request": create_service_request,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "product_lookup",
            "description": "Look up fictional technical specifications, capacity, power, and dimensions for a BharatHome appliance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Appliance name or category (e.g., 'refrigerator', 'washing machine', 'ac')",
                    }
                },
                "required": ["product_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "warranty_lookup",
            "description": "Look up warranty duration, component coverage, and exclusions for a BharatHome appliance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Appliance name (e.g., 'refrigerator', 'washing machine', 'microwave')",
                    }
                },
                "required": ["product_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "troubleshooting_lookup",
            "description": "Retrieve step-by-step diagnostic and troubleshooting guidance for an appliance issue or error code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "Appliance name"},
                    "issue": {"type": "string", "description": "Error code, fault, or symptom (e.g. 'OE error', 'warm air')"},
                },
                "required": ["product_name", "issue"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_service_request",
            "description": "Schedule an authorized technician service appointment for a faulty appliance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Full name of the customer"},
                    "product_name": {"type": "string", "description": "Appliance model or type"},
                    "issue": {"type": "string", "description": "Detailed description of the breakdown or problem"},
                },
                "required": ["customer_name", "product_name", "issue"],
            },
        },
    },
]


def execute_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Safely validate arguments and execute a registered tool."""
    func = AVAILABLE_TOOLS.get(tool_name)
    if not func:
        return {
            "status": "error",
            "message": f"Unknown tool '{tool_name}'. Available tools: {list(AVAILABLE_TOOLS.keys())}",
        }

    try:
        return func(**arguments)
    except TypeError as e:
        return {
            "status": "error",
            "message": f"Invalid arguments for tool '{tool_name}': {e}",
            "provided_arguments": arguments,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Tool '{tool_name}' execution failed: {e}",
        }

