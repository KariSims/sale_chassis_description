import re

from odoo.exceptions import ValidationError


SALE_TYPES = [("retail", "Retail / Détail"), ("wholesale", "Wholesale / Gros")]


def extract_chassis_descriptions(description, standard_description):
    """Read free-text lines of at least 17 characters, preserving colors.

    Automatic product text and optional chassis labels do not count toward the
    minimum. No VIN format, digit, character-set or uniqueness rule is imposed.
    """
    description = (description or "").strip()
    standard = (standard_description or "").strip()
    if standard and description.startswith(standard):
        description = description[len(standard):].strip()
    chassis_descriptions = []
    for row in description.splitlines():
        row = row.strip()
        row = re.sub(r"^(?:Chassis(?: Number)?|Châssis|VIN)\s*:\s*", "", row, flags=re.I).strip()
        if len(row) >= 17:
            chassis_descriptions.append(row)
    return chassis_descriptions


def has_chassis(description, standard_description):
    return bool(extract_chassis_descriptions(description, standard_description))


def validate_descriptions(lines, sale_type, standard_description):
    if not lines:
        return
    if not sale_type:
        raise ValidationError(lines.env._("Choose Retail or Wholesale before confirming this document."))
    if sale_type == "retail":
        for line in lines:
            if not has_chassis(line.name, standard_description(line)):
                raise ValidationError(lines.env._(
                    "%(product)s: enter at least 17 characters on a description line below the product "
                    "(for example, 1GDHK33U25F914022 - Yellow). Colors, spaces and punctuation are allowed. "
                    "The automatic product description does not count toward the minimum.",
                    product=line.product_id.display_name,
                ))
