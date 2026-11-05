"""Fictional knowledge base and retrieval helper for BharatHome Appliances."""

from typing import Any


BHARATHOME_KNOWLEDGE_BASE: list[dict[str, Any]] = [
    {
        "id": "kb_refrigerator_specs",
        "category": "product_specs",
        "title": "BharatHome FrostFree 340L Double Door Refrigerator Specifications",
        "product": "BharatHome FrostFree 340L Refrigerator",
        "keywords": ["refrigerator", "fridge", "frostfree", "specifications", "specs", "capacity", "dimensions"],
        "content": (
            "Model: BharatHome FrostFree 340L Double Door (Model BH-FF340D).\n"
            "Capacity: 340 Litres (Fresh Food: 252L, Freezer: 88L).\n"
            "Cooling Technology: Digital Inverter Multi-Flow 360 Airflow with intelligent frost sensor.\n"
            "Energy Efficiency: BEE 3-Star (Annual consumption: 212 kWh).\n"
            "Refrigerant: Eco-friendly R600a (Isobutane).\n"
            "Features: Toughened glass adjustable shelves (up to 150kg load), deodorizing carbon filter, "
            "convertible freezer zone, stabilizer-free operation (135V - 290V).\n"
            "Dimensions: 605 mm (W) x 680 mm (D) x 1680 mm (H). Weight: 64 kg."
        ),
    },
    {
        "id": "kb_refrigerator_warranty",
        "category": "warranty",
        "title": "BharatHome Refrigerator Warranty Terms and Exclusions",
        "product": "BharatHome FrostFree 340L Refrigerator",
        "keywords": ["refrigerator", "fridge", "warranty", "guarantee", "compressor", "exclusions"],
        "content": (
            "Warranty Period: 1-Year Comprehensive Warranty on the entire appliance, plus a 10-Year Warranty "
            "specifically covering the Digital Inverter Compressor.\n"
            "What is Covered: All mechanical, electrical, and electronic parts in Year 1. In Years 2 to 10, "
            "the compressor replacement part is free (labor, transit, and gas recharging fees are payable by customer).\n"
            "Exclusions: Plastic crispers, door shelves, glass racks, rubber door gaskets, cosmetic dents/scratches, "
            "and damages caused by ungrounded power outlets or unauthorized technician tampering."
        ),
    },
    {
        "id": "kb_refrigerator_troubleshooting",
        "category": "troubleshooting",
        "title": "BharatHome Refrigerator Troubleshooting Guide - Error Codes E4 and Frost Buildup",
        "product": "BharatHome FrostFree 340L Refrigerator",
        "keywords": ["refrigerator", "fridge", "error e4", "e4", "beeping", "frost", "cooling"],
        "content": (
            "Error Code E4 indicates a defrost sensor malfunction or excessive frost buildup blocking airflow.\n"
            "Troubleshooting Steps:\n"
            "1. Turn off the main power switch for 5 minutes and restart the unit to reboot the control board.\n"
            "2. Inspect the freezer door gasket for gaps or food obstructions preventing full closure.\n"
            "3. If error code E4 reappears after 30 minutes, book an authorized BharatHome technician to replace "
            "the defrost thermal sensor."
        ),
    },
    {
        "id": "kb_washing_machine_specs",
        "category": "product_specs",
        "title": "BharatHome TurboClean 7kg Front Load Washing Machine Specifications",
        "product": "BharatHome TurboClean 7kg Washing Machine",
        "keywords": ["washing machine", "washer", "turboclean", "specifications", "specs", "capacity"],
        "content": (
            "Model: BharatHome TurboClean 7kg Front Load (Model BH-WM70FL).\n"
            "Capacity: 7.0 kg dry linen capacity, ideal for families of 3-4.\n"
            "Motor: Direct Motion Brushless Inverter Motor with 1200 RPM maximum spin speed.\n"
            "Programs: 15 wash cycles including Allergy Steam, Quick 15, Cotton Eco, and Woolmark Care.\n"
            "Features: Inbuilt ceramic heater (up to 90°C), Anti-Bacterial Door Seal (ABT), Child Lock, "
            "Auto Drum Clean reminder, rat-mesh base protection.\n"
            "Water Pressure Requirement: 0.3 bar to 10 bar."
        ),
    },
    {
        "id": "kb_washing_machine_warranty",
        "category": "warranty",
        "title": "BharatHome Washing Machine Warranty Terms",
        "product": "BharatHome TurboClean 7kg Washing Machine",
        "keywords": ["washing machine", "washer", "warranty", "motor", "exclusions"],
        "content": (
            "Warranty Period: 2-Year Comprehensive Warranty on complete machine + 10-Year Warranty on the Inverter Motor.\n"
            "Coverage: Drum, internal electronic PCB board, water inlet valves, and motor.\n"
            "Exclusions: Rubber door bellows damaged by sharp objects, lint filter physical breakage, external water "
            "hoses after 6 months, and insect/rodent infestation damage."
        ),
    },
    {
        "id": "kb_washing_machine_oe_error",
        "category": "troubleshooting",
        "title": "BharatHome Washing Machine OE Error Drainage Troubleshooting",
        "product": "BharatHome TurboClean 7kg Washing Machine",
        "keywords": ["washing machine", "washer", "oe error", "oe", "drain", "water stuck", "filter"],
        "content": (
            "Error Code OE indicates that the washing machine cannot drain water within the scheduled time.\n"
            "Step-by-step Resolution:\n"
            "1. Unplug the washing machine from the electrical socket for safety.\n"
            "2. Locate the maintenance flap at the bottom right corner of the front panel and open it.\n"
            "3. Place a shallow tray or towel underneath the drain area.\n"
            "4. Uncap the small emergency drain hose to drain out residual water.\n"
            "5. Turn the main circular debris filter counter-clockwise to remove it. Rinse away trapped coins, "
            "pins, and lint under running water.\n"
            "6. Reinsert the filter firmly clockwise, close the flap, and restart the cycle."
        ),
    },
    {
        "id": "kb_water_purifier_specs_install",
        "category": "installation",
        "title": "BharatHome AquaPure RO Water Purifier Installation & Specifications",
        "product": "BharatHome AquaPure RO Water Purifier",
        "keywords": ["water purifier", "aquapure", "ro", "install", "installation", "specs", "pressure"],
        "content": (
            "Model: BharatHome AquaPure 8L RO+UV+TDS Mineral Water Purifier (Model BH-WP800).\n"
            "Purification: 8-stage RO + UV e-boiling + Active Copper & Zinc alkaline cartridge.\n"
            "Storage Capacity: 8.0 Litres food-grade ABS storage tank.\n"
            "Installation Instructions & Pre-requisites:\n"
            "1. Water Inlet Pressure: Requires 0.3 bar (4.3 psi) to 3.0 bar (43.5 psi).\n"
            "2. If customer lives on high floors with pressure < 0.3 bar, a BharatHome Pressure Booster Pump kit "
            "is installed by the technician for a subsidized fee of Rs. 600.\n"
            "3. Mount unit within 3 feet of a 230V 3-pin plug and 5 feet of raw water tap connection.\n"
            "4. Standard installation is free within 48 hours of product delivery."
        ),
    },
    {
        "id": "kb_water_purifier_warranty",
        "category": "warranty",
        "title": "BharatHome AquaPure Water Purifier Warranty & Filter Terms",
        "product": "BharatHome AquaPure RO Water Purifier",
        "keywords": ["water purifier", "ro", "warranty", "filters", "membrane"],
        "content": (
            "Warranty Period: 1-Year Comprehensive Warranty covering electronic SMPS, booster pump, and UV assembly.\n"
            "Consumables Warranty: Sediment filter and carbon blocks covered for first 6 months. RO membrane covered "
            "for 1 year up to 2000 ppm input TDS."
        ),
    },
    {
        "id": "kb_microwave_specs_safety",
        "category": "safety",
        "title": "BharatHome AeroGrill 28L Convection Microwave Specifications and Safety Door Mechanism",
        "product": "BharatHome AeroGrill 28L Microwave",
        "keywords": ["microwave", "aerogrill", "safety", "door switch", "bypass", "interlock", "radiation"],
        "content": (
            "Model: BharatHome AeroGrill 28L Convection Microwave (Model BH-MC28G).\n"
            "Capacity & Power: 28 Litres, 900W Microwave power, 1200W Quartz Grill, 1950W Convection.\n"
            "CRITICAL SAFETY WARNING - DOOR SAFETY INTERLOCK MECHANISM:\n"
            "BharatHome microwaves feature a dual primary and secondary mechanical safety interlock switch. "
            "It is strictly FORBIDDEN and DANGEROUS to bypass, tamper with, or override the door safety mechanism. "
            "Operating a microwave with a bypassed door latch releases dangerous microwave radiation, causing "
            "severe thermal burns, eye damage, and fire hazard. Never insert pins, tape, or wires to defeat the switch. "
            "If the door latch is broken, the appliance must remain powered off until repaired by an authorized technician."
        ),
    },
    {
        "id": "kb_air_conditioner_specs_troubleshooting",
        "category": "product_specs",
        "title": "BharatHome CoolBreeze 1.5 Ton Inverter AC Specs and Warm Air Troubleshooting",
        "product": "BharatHome CoolBreeze 1.5 Ton Inverter AC",
        "keywords": ["ac", "air conditioner", "coolbreeze", "warm air", "cooling", "specifications"],
        "content": (
            "Model: BharatHome CoolBreeze 1.5 Ton 5-Star Dual Inverter Split AC (Model BH-AC155S).\n"
            "Cooling Capacity: 5100 Watts; ISEER: 5.15 (High Energy Saving); 100% Copper Condenser with BlueFin coating.\n"
            "Warm Air Troubleshooting:\n"
            "1. Verify remote is set to 'Cool' mode (snowflake icon), not 'Fan' or 'Dry'.\n"
            "2. Note the 3-minute compressor safety startup delay.\n"
            "3. Wash the indoor unit air filters under lukewarm water if clogged with dust."
        ),
    },
    {
        "id": "kb_induction_cooktop_specs_child_lock",
        "category": "troubleshooting",
        "title": "BharatHome CookSmart 2000W Induction Cooktop & Child Lock Feature",
        "product": "BharatHome CookSmart 2000W Induction Cooktop",
        "keywords": ["induction", "cooktop", "child lock", "padlock", "specs", "cooksmart"],
        "content": (
            "Model: BharatHome CookSmart 2000W Induction Cooktop (Model BH-IC20).\n"
            "Power: 2000 Watts with 8 Indian auto-cook menu presets.\n"
            "Child Lock Deactivation: Press and hold the Key/Lock symbol on the touch panel continuously for "
            "3 to 5 seconds until a double beep sounds and the padlock LED turns off."
        ),
    },
    {
        "id": "kb_general_support_policies",
        "category": "support_policy",
        "title": "BharatHome General Customer Support Policies, Unlisted Products, and Service Requests",
        "product": "BharatHome General Policies",
        "keywords": ["policy", "unlisted", "unknown product", "service request", "refund", "returns", "installation"],
        "content": (
            "Unlisted Products Policy: BharatHome only manufactures and services appliances in its official catalog "
            "(Refrigerators, Washing Machines, Air Conditioners, Microwave Ovens, Water Purifiers, Induction Cooktops). "
            "BharatHome does NOT sell or service unlisted appliances such as televisions, laptops, mobile phones, or "
            "third-party electronics. Representatives must inform customers that BharatHome does not carry warranty or service for unlisted goods.\n"
            "Service Requests: Service appointments can be registered by providing customer name, appliance model, and issue description. "
            "Technicians visit within 24 to 48 hours.\n"
            "Payments: All service and spare part payments must be made digitally through official BharatHome SMS payment links or technician app QR code. Cash payments are strictly prohibited."
        ),
    },
]


def search_knowledge_base(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Retrieve the top matching knowledge base articles based on keyword similarity."""
    query_terms = set(query.lower().replace("?", "").replace(",", "").replace(".", "").split())

    scored_entries = []
    for entry in BHARATHOME_KNOWLEDGE_BASE:
        score = 0
        keywords = [k.lower() for k in entry["keywords"]]
        title_words = entry["title"].lower().split()
        product_words = entry["product"].lower().split()

        for term in query_terms:
            if len(term) < 2:
                continue
            if any(term in kw for kw in keywords):
                score += 3
            if any(term in tw for tw in title_words):
                score += 2
            if any(term in pw for pw in product_words):
                score += 2
            if term in entry["content"].lower():
                score += 1

        if score > 0:
            scored_entries.append((score, entry))

    scored_entries.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored_entries[:top_k]]

