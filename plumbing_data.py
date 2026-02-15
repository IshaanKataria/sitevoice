"""
Plumbing materials and pricing database for SiteVoice.
Australian pricing in AUD. Prices are typical retail/trade rates.
"""

PLUMBING_MATERIALS = {
    # Hot Water Systems
    "hot_water": {
        "category": "Hot Water Systems",
        "items": {
            "rheem_250l_electric": {"name": "Rheem 250L Electric HWS", "unit_price": 1150.00, "unit": "each"},
            "rheem_315l_electric": {"name": "Rheem 315L Electric HWS", "unit_price": 1350.00, "unit": "each"},
            "rheem_160l_electric": {"name": "Rheem 160L Electric HWS", "unit_price": 980.00, "unit": "each"},
            "dux_250l_electric": {"name": "Dux 250L Electric HWS", "unit_price": 1100.00, "unit": "each"},
            "rinnai_26l_continuous": {"name": "Rinnai 26L Continuous Flow Gas", "unit_price": 1650.00, "unit": "each"},
            "rinnai_20l_continuous": {"name": "Rinnai 20L Continuous Flow Gas", "unit_price": 1450.00, "unit": "each"},
            "bosch_21l_continuous": {"name": "Bosch 21L Continuous Flow", "unit_price": 1400.00, "unit": "each"},
            "thermann_25l_continuous": {"name": "Thermann 25L Continuous Flow", "unit_price": 1550.00, "unit": "each"},
            "aquamax_250l_electric": {"name": "AquaMAX 250L Electric HWS", "unit_price": 1050.00, "unit": "each"},
            "hws_tempering_valve": {"name": "Tempering Valve", "unit_price": 85.00, "unit": "each"},
            "hws_duo_valve": {"name": "Duo Valve (Pressure/Temp Relief)", "unit_price": 65.00, "unit": "each"},
        }
    },
    # Pipes & Fittings
    "pipes": {
        "category": "Pipes & Fittings",
        "items": {
            "copper_15mm": {"name": "Copper Pipe 15mm (per metre)", "unit_price": 18.00, "unit": "metre"},
            "copper_20mm": {"name": "Copper Pipe 20mm (per metre)", "unit_price": 25.00, "unit": "metre"},
            "copper_25mm": {"name": "Copper Pipe 25mm (per metre)", "unit_price": 35.00, "unit": "metre"},
            "pex_16mm": {"name": "PEX Pipe 16mm (per metre)", "unit_price": 4.50, "unit": "metre"},
            "pex_20mm": {"name": "PEX Pipe 20mm (per metre)", "unit_price": 6.00, "unit": "metre"},
            "pvc_40mm": {"name": "PVC Pipe 40mm (per metre)", "unit_price": 8.00, "unit": "metre"},
            "pvc_50mm": {"name": "PVC Pipe 50mm (per metre)", "unit_price": 10.00, "unit": "metre"},
            "pvc_100mm": {"name": "PVC Pipe 100mm (per metre)", "unit_price": 16.00, "unit": "metre"},
            "copper_elbow_15mm": {"name": "Copper Elbow 15mm", "unit_price": 3.50, "unit": "each"},
            "copper_elbow_20mm": {"name": "Copper Elbow 20mm", "unit_price": 5.00, "unit": "each"},
            "copper_tee_15mm": {"name": "Copper Tee 15mm", "unit_price": 5.50, "unit": "each"},
            "sharkbite_15mm": {"name": "SharkBite Coupling 15mm", "unit_price": 12.00, "unit": "each"},
            "sharkbite_20mm": {"name": "SharkBite Coupling 20mm", "unit_price": 15.00, "unit": "each"},
        }
    },
    # Taps & Mixers
    "taps": {
        "category": "Taps & Mixers",
        "items": {
            "kitchen_mixer": {"name": "Kitchen Sink Mixer", "unit_price": 180.00, "unit": "each"},
            "basin_mixer": {"name": "Basin Mixer Tap", "unit_price": 150.00, "unit": "each"},
            "shower_mixer": {"name": "Shower Mixer Valve", "unit_price": 200.00, "unit": "each"},
            "bath_spout": {"name": "Bath Spout", "unit_price": 120.00, "unit": "each"},
            "laundry_tap_set": {"name": "Laundry Tap Set", "unit_price": 95.00, "unit": "each"},
            "garden_tap": {"name": "Garden Tap (Hose Cock)", "unit_price": 35.00, "unit": "each"},
            "tap_washer_set": {"name": "Tap Washer Repair Kit", "unit_price": 8.00, "unit": "set"},
        }
    },
    # Toilet & Cistern
    "toilet": {
        "category": "Toilet & Cistern",
        "items": {
            "toilet_suite_standard": {"name": "Standard Toilet Suite (S-Trap)", "unit_price": 350.00, "unit": "each"},
            "toilet_suite_wall_faced": {"name": "Wall-Faced Toilet Suite", "unit_price": 550.00, "unit": "each"},
            "cistern_inlet_valve": {"name": "Cistern Inlet Valve", "unit_price": 25.00, "unit": "each"},
            "cistern_outlet_valve": {"name": "Cistern Outlet Valve", "unit_price": 30.00, "unit": "each"},
            "toilet_seat": {"name": "Toilet Seat Replacement", "unit_price": 45.00, "unit": "each"},
            "toilet_connector": {"name": "Toilet Pan Connector", "unit_price": 18.00, "unit": "each"},
            "wax_ring": {"name": "Wax Ring Seal", "unit_price": 12.00, "unit": "each"},
        }
    },
    # Drainage
    "drainage": {
        "category": "Drainage",
        "items": {
            "floor_waste_round": {"name": "Floor Waste Grate (Round)", "unit_price": 35.00, "unit": "each"},
            "floor_waste_square": {"name": "Floor Waste Grate (Square Tile)", "unit_price": 55.00, "unit": "each"},
            "p_trap_40mm": {"name": "P-Trap 40mm", "unit_price": 15.00, "unit": "each"},
            "s_trap_40mm": {"name": "S-Trap 40mm", "unit_price": 15.00, "unit": "each"},
            "overflow_relief_gully": {"name": "Overflow Relief Gully", "unit_price": 65.00, "unit": "each"},
            "inspection_opening": {"name": "Inspection Opening 100mm", "unit_price": 28.00, "unit": "each"},
        }
    },
    # General Consumables
    "consumables": {
        "category": "Consumables & Sundries",
        "items": {
            "solder_lead_free": {"name": "Lead-Free Solder (per roll)", "unit_price": 35.00, "unit": "roll"},
            "flux": {"name": "Soldering Flux", "unit_price": 12.00, "unit": "each"},
            "teflon_tape": {"name": "Teflon Tape (10-pack)", "unit_price": 8.00, "unit": "pack"},
            "silicone_sealant": {"name": "Silicone Sealant Tube", "unit_price": 14.00, "unit": "each"},
            "pipe_cement_pvc": {"name": "PVC Pipe Cement", "unit_price": 16.00, "unit": "each"},
            "pipe_primer": {"name": "PVC Primer", "unit_price": 14.00, "unit": "each"},
            "copper_clips_15mm_10pk": {"name": "Copper Pipe Clips 15mm (10pk)", "unit_price": 6.00, "unit": "pack"},
        }
    },
}

# Labor rates (AUD per hour)
LABOR_RATES = {
    "standard": {"name": "Standard Rate", "rate": 95.00, "description": "Standard business hours (Mon-Fri 7am-5pm)"},
    "after_hours": {"name": "After Hours Rate", "rate": 140.00, "description": "After 5pm weekdays or Saturday"},
    "emergency": {"name": "Emergency/Sunday Rate", "rate": 180.00, "description": "Sunday, public holidays, or emergency callout"},
    "callout": {"name": "Callout Fee", "rate": 80.00, "description": "Standard callout/attendance fee"},
}

# Common job templates with typical time estimates
JOB_TEMPLATES = {
    "hws_replacement_electric": {
        "name": "Hot Water System Replacement (Electric)",
        "typical_hours": 4,
        "typical_materials": ["rheem_250l_electric", "hws_tempering_valve", "hws_duo_valve", "copper_15mm", "copper_elbow_15mm", "teflon_tape"],
        "typical_quantities": {"copper_15mm": 3, "copper_elbow_15mm": 4, "teflon_tape": 1},
    },
    "hws_replacement_gas_continuous": {
        "name": "Hot Water System Replacement (Gas Continuous Flow)",
        "typical_hours": 5,
        "typical_materials": ["rinnai_26l_continuous", "hws_tempering_valve", "copper_15mm", "copper_elbow_15mm", "teflon_tape"],
        "typical_quantities": {"copper_15mm": 4, "copper_elbow_15mm": 6, "teflon_tape": 1},
    },
    "tap_replacement": {
        "name": "Tap/Mixer Replacement",
        "typical_hours": 1,
        "typical_materials": ["basin_mixer", "sharkbite_15mm", "teflon_tape", "silicone_sealant"],
        "typical_quantities": {},
    },
    "toilet_repair": {
        "name": "Toilet Cistern Repair",
        "typical_hours": 1,
        "typical_materials": ["cistern_inlet_valve", "cistern_outlet_valve"],
        "typical_quantities": {},
    },
    "toilet_replacement": {
        "name": "Full Toilet Replacement",
        "typical_hours": 2.5,
        "typical_materials": ["toilet_suite_standard", "toilet_connector", "wax_ring", "silicone_sealant", "teflon_tape"],
        "typical_quantities": {},
    },
    "blocked_drain": {
        "name": "Blocked Drain Clearing",
        "typical_hours": 1.5,
        "typical_materials": [],
        "typical_quantities": {},
    },
    "leaking_pipe_repair": {
        "name": "Leaking Pipe Repair",
        "typical_hours": 1.5,
        "typical_materials": ["copper_15mm", "copper_elbow_15mm", "solder_lead_free", "flux"],
        "typical_quantities": {"copper_15mm": 1, "copper_elbow_15mm": 2},
    },
    "shower_mixer_install": {
        "name": "Shower Mixer Installation",
        "typical_hours": 2,
        "typical_materials": ["shower_mixer", "copper_15mm", "teflon_tape", "silicone_sealant"],
        "typical_quantities": {"copper_15mm": 2},
    },
}


def lookup_material(item_key):
    """Look up a material by its key across all categories."""
    for cat_key, category in PLUMBING_MATERIALS.items():
        if item_key in category["items"]:
            return category["items"][item_key]
    return None


def search_materials(query):
    """Search materials by name. Returns list of (key, item) tuples."""
    query_lower = query.lower()
    results = []
    for cat_key, category in PLUMBING_MATERIALS.items():
        for item_key, item in category["items"].items():
            if query_lower in item["name"].lower() or query_lower in item_key:
                results.append((item_key, item, category["category"]))
    return results


def get_job_template(template_key):
    """Get a job template with full material details and pricing."""
    template = JOB_TEMPLATES.get(template_key)
    if not template:
        return None

    materials_detail = []
    materials_total = 0.0
    for mat_key in template["typical_materials"]:
        mat = lookup_material(mat_key)
        if mat:
            qty = template["typical_quantities"].get(mat_key, 1)
            line_total = mat["unit_price"] * qty
            materials_total += line_total
            materials_detail.append({
                "key": mat_key,
                "name": mat["name"],
                "unit_price": mat["unit_price"],
                "quantity": qty,
                "unit": mat["unit"],
                "line_total": line_total,
            })

    labor_total = template["typical_hours"] * LABOR_RATES["standard"]["rate"]

    return {
        "name": template["name"],
        "hours": template["typical_hours"],
        "labor_rate": LABOR_RATES["standard"]["rate"],
        "labor_total": labor_total,
        "materials": materials_detail,
        "materials_total": materials_total,
        "total": labor_total + materials_total,
    }


def get_all_categories():
    """Return a formatted string of all material categories and items for the AI."""
    result = []
    for cat_key, category in PLUMBING_MATERIALS.items():
        result.append(f"\n### {category['category']}")
        for item_key, item in category["items"].items():
            result.append(f"  - {item_key}: {item['name']} — ${item['unit_price']:.2f}/{item['unit']}")
    return "\n".join(result)


def get_labor_rates_text():
    """Return formatted labor rates for the AI."""
    lines = []
    for key, rate in LABOR_RATES.items():
        lines.append(f"  - {rate['name']}: ${rate['rate']:.2f}/hr ({rate['description']})")
    return "\n".join(lines)
