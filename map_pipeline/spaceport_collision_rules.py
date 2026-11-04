"""Classify map objects for supplemental collision without loading Blender."""

import re


COLLISION_NAME_RE = re.compile(
    r"ground|floor|terrain|road|walkway|stair|escalator|curb|ramp|"
    r"wall|building|dock|column|pillar|rock|cliff|platform|ceiling|"
    r"roof|truss|silo",
    re.I,
)
NO_COLLISION = re.compile(
    r"decal|sticker|emissive|light(?:ing|fixture|_0)|lamp|label|poster|paper|litter|"
    r"foliage|leaf|leaves|grass|branch|bullet|brokenglass|shatter|cable|wire_0|"
    r"cushion|pillow|tarp|cloth|"
    r"shadow|helper|_fx_|pipeline_ring|_trim|_sign",
    re.I,
)
COVER = re.compile(
    r"container|supplybox|packingbox|plasticbox|crate|cabinet|locker|shel[ffv]|"
    r"(?<!t)rack|tools_box|servercabinet|generator|machinery|oxygencylinder|centrifuge|"
    r"vehicle|truck|forklift|helicopter|trolley|"
    r"guardrail|railing|fence|barrier|ladder|"
    r"door|table|desk|bench|chair|sofa|bed|dumpster|ventilation|tank",
    re.I,
)


def collision_candidate(record):
    name = record["name"]
    if record["type"] != "MESH" or not record.get("bounds") or NO_COLLISION.search(name):
        return False
    structure = COLLISION_NAME_RE.search(name)
    if not (structure or COVER.search(name)):
        return False
    materials = record["materials"]
    if materials and all(material and NO_COLLISION.search(material) for material in materials):
        return False
    x, y, z = record["bounds"]["size"]
    return max(x, y) >= 0.35 and (z >= 0.22 or (structure is not None and min(x, y) >= 0.30))
