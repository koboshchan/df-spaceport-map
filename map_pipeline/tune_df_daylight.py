"""Apply the spaceport daylight pass to a generated text VMap."""
import argparse
import re
from pathlib import Path

SETTINGS = {
    "env_cubemap_fog": {
        "StartDisabled": "1",
        "cubemapheightfog": "0",
        "cubemapfogmaxopacity": "0.0",
    },
    "post_processing_volume": {
        "exposurecompensation": "0.15",
        "minexposure": "0.85",
        "maxexposure": "1.45",
        "postprocessing": "lighting/postprocessing/de_anubis_prefab/de_anubis_prefab.vpost",
    },
    "light_environment": {
        "color": "255 244 231",
        "brightness": "1.9",
    },
    "light_omni2": {"brightness_legacy": "2.15", "range": "6200"},
    "env_sky": {"brightnessscale": "0.85"},
}
PROPERTIES = re.compile(r'"entity_properties" "EditGameClassProps"\s*\{[^{}]*\}')
FILL_ENTITY = re.compile(
    r'("classname" "string" "light_omni2"(?:(?!"CMapEntity")[\s\S])*?'
    r'"origin" "vector3" "[^"\s]+ [^"\s]+ )[^"\s]+(")'
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    counts = dict.fromkeys(SETTINGS, 0)

    def adjust(match):
        props = match[0]
        classname = re.search(r'"classname" "string" "([^"]+)"', props)
        if not classname or classname[1] not in SETTINGS:
            return props
        name = classname[1]
        counts[name] += 1
        for key, value in SETTINGS[name].items():
            props, changed = re.subn(
                rf'("{key}" "string" )"[^"]*"', rf'\g<1>"{value}"', props
            )
            if changed != 1:
                raise ValueError(f"Unexpected {name}.{key} count: {changed}")
        return props

    result = PROPERTIES.sub(adjust, args.source.read_text(encoding="utf-8-sig"))
    expected = dict.fromkeys(SETTINGS, 1)
    expected["light_omni2"] = 9
    if counts != expected:
        raise ValueError(f"Unexpected scene entity counts: {counts}")
    result, lowered = FILL_ENTITY.subn(r'\g<1>112\2', result)
    if lowered != expected["light_omni2"]:
        raise ValueError(f"Unexpected fill origin count: {lowered}")
    args.output.write_text(result, encoding="utf-8")
    print(counts)


if __name__ == "__main__":
    main()
