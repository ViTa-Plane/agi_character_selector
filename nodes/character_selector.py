import os
import json
import re
from server import PromptServer

# v 1.3

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
STYLES_ROOT_DIR = os.path.join(CURRENT_DIR, "character_packs")
THUMBNAILS_DIR = os.path.join(STYLES_ROOT_DIR, "thumbnails")

if not os.path.exists(THUMBNAILS_DIR):
    try:
        os.makedirs(THUMBNAILS_DIR)
    except Exception:
        pass

try:
    PromptServer.instance.app.router.add_static(
        '/agi_characters_thumbnails/',
        path=THUMBNAILS_DIR,
        name='agi_characters_thumbnails'
    )
except Exception:
    pass


def load_flat_container_styles():
    styles_inventory = []
    if not os.path.exists(STYLES_ROOT_DIR):
        return []

    try:
        for file in os.listdir(STYLES_ROOT_DIR):
            if file.endswith(".json"):
                json_path = os.path.join(STYLES_ROOT_DIR, file)
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    raw_items = data if isinstance(data, list) else [data]
                    for item in raw_items:
                        if not isinstance(item, dict) or "name" not in item:
                            continue

                        category = item.get("category", "").strip()
                        if category.lower() != "character":
                            continue

                        category = category.capitalize()

                        character = item.get("character")
                        if character is None or str(character).strip() == "":
                            character = "misc"
                        else:
                            character = str(character).strip()

                        nested_params = item.get("params", {})
                        if not isinstance(nested_params, dict):
                            nested_params = {}

                        clothes_dict = {}
                        raw_clothes = item.get("clothes")
                        if isinstance(raw_clothes, dict):
                            clothes_dict = {str(k).strip(): str(v).strip() for k, v in raw_clothes.items()}

                        styles_inventory.append({
                            "name": item.get("name"),
                            "category": category,
                            "character": character,
                            "prompt": item.get("prompt", ""),
                            "negative_prompt": item.get("negative_prompt", ""),
                            "clothes": clothes_dict,
                            "thumbnail": item.get("thumbnail"),
                            "comment": item.get("comment", ""),
                            "seed": item.get("seed", ""),
                            "params": nested_params,
                            "file_name": file
                        })
                except Exception as e:
                    error_msg = str(e)
                    print(f"[Character Selector] Critical Syntax Error parsing container {file}: {error_msg}")

                    styles_inventory.append({
                        "name": f"⚠️ ERROR IN: {file}",
                        "category": "Character",
                        "character": "misc",
                        "prompt": f"JSON syntax error detected inside file: {file}",
                        "negative_prompt": "Fix file syntax to clear this alert flag.",
                        "clothes": {},
                        "thumbnail": None,
                        "comment": f"PARSER REJECTION: {error_msg}",
                        "seed": "ERROR",
                        "params": {},
                        "file_name": file
                    })
    except Exception as e:
        print(f"[Character Selector] Directory access error: {e}")

    styles_inventory.sort(key=lambda x: x["name"].lower())
    return styles_inventory


class CharacterSelector:
    @classmethod
    def INPUT_TYPES(cls):
        all_styles = load_flat_container_styles()
        character_list = [item["name"] for item in all_styles] if all_styles else ["None"]

        all_clothes_keys = set(["none"])
        for item in all_styles:
            clothes_map = item.get("clothes", {})
            if isinstance(clothes_map, dict):
                for k in clothes_map.keys():
                    all_clothes_keys.add(k)

        clothing_list = sorted(list(all_clothes_keys))

        return {
            "required": {
                "select_character": (character_list, {"default": character_list[0] if character_list else "None"}),
                "clothing_type": (clothing_list, {"default": "none"}),
                "lora_strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.05, "display": "number"}),
                "remove_dependencies": ("BOOLEAN", {"default": False, "label_on": "enabled", "label_off": "disabled"}),
                "insert_break": ("BOOLEAN", {"default": True, "label_on": "enabled", "label_off": "disabled"}),
            },
            "optional": {
                "positive": ("STRING", {"forceInput": True}),
                "negative": ("STRING", {"forceInput": True}),
            },
            "hidden": {
                "styles_inventory": ("STRING", {"default": json.dumps(all_styles)})
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("positive", "negative", "character")
    FUNCTION = "apply_style"
    CATEGORY = "agi/Prompt Utility"

    def clean_output_string(self, text):
        if not text:
            return ""
        text = text.replace("{prompt}", "").replace("{weight}", "")
        text = re.sub(r'<lora:[:\s]*>', '', text)
        text = re.sub(r',(?:\s*,)+', ',', text)
        text = text.strip().strip(',')
        return text.strip()

    def clean_all_dependencies(self, text):
        if not text:
            return ""
        text = re.sub(r'<lora:[^>]+>', '', text)
        text = re.sub(r'\(\s*embedding:[^)]+\s*\)', '', text)
        text = re.sub(r'[^a-zA-Z0-9_-]?embedding:[a-zA-Z0-9_.-]+', '', text)
        return self.clean_output_string(text)

    def process_lora_weights(self, text, weight_value):
        if not text:
            return ""

        def parse_individual_lora_tag(tag_match):
            full_tag = tag_match.group(0)
            inner_content = tag_match.group(1)

            if "{weight}" in inner_content:
                inner_content = inner_content.replace("{weight}", f"{weight_value:.2f}")
                parts = inner_content.split(":")
                processed_parts = [parts[0]]

                orig_parts = tag_match.group(1).split(":")
                for idx in range(1, len(parts)):
                    if idx < len(orig_parts) and orig_parts[idx] == "{weight}":
                        processed_parts.append(parts[idx])
                    else:
                        try:
                            processed_parts.append(f"{float(parts[idx]) * weight_value:.2f}")
                        except ValueError:
                            processed_parts.append(parts[idx])
                return f"<lora:{':'.join(processed_parts)}>"

            parts = inner_content.split(":")
            if len(parts) >= 2:
                processed_parts = [parts[0]]
                for num_str in parts[1:]:
                    try:
                        processed_parts.append(f"{float(num_str) * weight_value:.2f}")
                    except ValueError:
                        processed_parts.append(num_str)
                return f"<lora:{':'.join(processed_parts)}>"

            return full_tag

        return re.sub(r'<lora:([^>]+)>', parse_individual_lora_tag, text)

    def apply_style(self, select_character, clothing_type, lora_strength, remove_dependencies, insert_break,
                    positive="", negative=""):
        if "⚠️ ERROR IN" in select_character:
            return (positive, negative, "misc")

        all_styles = load_flat_container_styles()
        style_data = next((item for item in all_styles if item.get("name") == select_character), None)

        if not style_data or select_character == "None":
            res_p, res_n = positive, negative
            character_val = "misc"
        else:
            style_positive = style_data.get("prompt", "{prompt}")
            style_negative = style_data.get("negative_prompt", "")
            character_val = style_data.get("character", "misc")

            # 1. Strip existing legacy BREAKs if insert_break is active
            if insert_break:
                style_positive = re.sub(r'\bBREAK\b', '', style_positive, flags=re.IGNORECASE)
                style_negative = re.sub(r'\bBREAK\b', '', style_negative, flags=re.IGNORECASE)

            # 2. Detect prompt tag positioning
            has_prompt_tag = "{prompt}" in style_positive
            prompt_at_start = style_positive.strip().startswith("{prompt}")

            # 3. Extract clean style base without {prompt}
            clean_style_positive = style_positive.replace("{prompt}", "").strip(" ,")

            # 4. Retrieve clothing string from clothes dict
            clothing_text = ""
            clothes_map = style_data.get("clothes", {})
            if isinstance(clothes_map, dict) and clothing_type != "none":
                clothing_text = clothes_map.get(clothing_type, "")

            if clothing_text:
                clean_style_positive = f"{clean_style_positive}, {clothing_text}" if clean_style_positive else clothing_text

            # 5. Process LoRAs & cleanup
            clean_style_positive = self.process_lora_weights(clean_style_positive, lora_strength)

            if remove_dependencies:
                clean_style_positive = self.clean_all_dependencies(clean_style_positive)
                style_negative = self.clean_all_dependencies(style_negative)

            # 6. Apply BREAK wrapping to character + clothes block
            clean_style_positive = self.clean_output_string(clean_style_positive)
            if insert_break and clean_style_positive:
                wrapped_style = f"BREAK {clean_style_positive} BREAK"
            else:
                wrapped_style = clean_style_positive

            # 7. Build final positive string
            if has_prompt_tag:
                if positive:
                    if prompt_at_start:
                        final_positive = f"{positive}, {wrapped_style}" if wrapped_style else positive
                    else:
                        final_positive = f"{wrapped_style}, {positive}" if wrapped_style else positive
                else:
                    final_positive = wrapped_style
            else:
                if positive:
                    if insert_break:
                        final_positive = f"{wrapped_style}, {positive}" if wrapped_style else positive
                    else:
                        final_positive = f"{positive}, {wrapped_style}" if wrapped_style else positive
                else:
                    final_positive = wrapped_style

            # 8. Apply BREAK to negative prompt
            style_negative = self.clean_output_string(style_negative)
            if insert_break and style_negative:
                style_negative = f"BREAK {style_negative} BREAK"

            final_negative = f"{negative}, {style_negative}" if negative and style_negative else (
                style_negative if style_negative else negative)
            res_p, res_n = final_positive, final_negative

        res_p = self.clean_output_string(res_p)
        res_n = self.clean_output_string(res_n)

        return (res_p, res_n, character_val)


NODE_CLASS_MAPPINGS = {"CharacterSelector": CharacterSelector}
NODE_DISPLAY_NAME_MAPPINGS = {"CharacterSelector": "character selector"}