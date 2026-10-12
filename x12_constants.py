from __future__ import annotations

###############################################################################
# EDI Delimiters
###############################################################################

ELEMENT_SEPARATOR = "*"
SEGMENT_TERMINATOR = "~"
SUBELEMENT_SEPARATOR = ":"

###############################################################################
# X12 Envelope Constants
###############################################################################

ISA_AUTHORIZATION_QUALIFIER = "00"
ISA_AUTHORIZATION_INFORMATION = ""

ISA_SECURITY_QUALIFIER = "00"
ISA_SECURITY_INFORMATION = ""

ISA_SENDER_QUALIFIER = "30"
ISA_RECEIVER_QUALIFIER = "30"

ISA_REPETITION_SEPARATOR = "^"

X12_VERSION = "00501"

IMPLEMENTATION_VERSION = "005010X220A1"

ACKNOWLEDGEMENT_REQUESTED = "0"

COMPONENT_ELEMENT_SEPARATOR = ":"

FUNCTIONAL_IDENTIFIER = "BE"

TRANSACTION_SET_IDENTIFIER = "834"

###############################################################################
# Relationship Codes (INS02 / Loop 2000)
#
# Per companion guide "Relationship Codes" tab. Includes the full code list;
# only a subset have friendly aliases below since census data won't use most
# of these (e.g. court-appointed guardian, annuitant), but the raw codes are
# kept here for reference / validation.
###############################################################################

RELATIONSHIP_CODES = {
    "EMPLOYEE": "18",
    "SELF": "18",

    "SPOUSE": "01",

    "CHILD": "19",
    "SON": "19",
    "DAUGHTER": "19",

    "STEPCHILD": "17",
    "STEPSON": "17",
    "STEPDAUGHTER": "17",

    "ADOPTED CHILD": "09",
    "FOSTER CHILD": "10",
    "WARD": "15",

    "DOMESTIC PARTNER": "53",
    "LIFE PARTNER": "53",

    "OTHER": "G8",
}

# Raw code -> definition, straight from the companion guide, for validation
# and error messages (e.g. edi_834_validator.py can check INS02 against this).
RELATIONSHIP_CODE_DEFINITIONS = {
    "01": "Spouse",
    "03": "Father or Mother",
    "04": "Grandparent (Other)",
    "05": "Grandson or Granddaughter",
    "06": "Uncle or Aunt (Other)",
    "07": "Nephew or Niece",
    "08": "Cousin (Other)",
    "09": "Adopted Child",
    "10": "Foster Child",
    "11": "Son-in-law or Daughter-in-law",
    "12": "Brother-in-law or Sister-in-law",
    "13": "Mother-in-law or Father-in-law",
    "14": "Brother or Sister (Other)",
    "15": "Ward (Other)",
    "16": "Stepparent (Other)",
    "17": "Stepson or Stepdaughter",
    "18": "Employee",
    "19": "Child",
    "23": "Sponsored Dependent (Child)",
    "24": "Dependent of a Minor Dependent (Other)",
    "25": "Ex-Spouse (Other)",
    "26": "Guardian (Other)",
    "31": "Court Appointed Guardian (Other)",
    "38": "Collateral Dependent (Other)",
    "53": "Life Partner or Domestic Partner",
    "60": "Annuitant (Other)",
    "D2": "Trustee (Other)",
    "G8": "Other Relationship - child",
    "G9": "Other Relative - child",
}

###############################################################################
# Gender Codes (DMG03)
###############################################################################

GENDER_CODES = {
    "M": "M",
    "MALE": "M",

    "F": "F",
    "FEMALE": "F",

    "U": "U",
    "UNKNOWN": "U",
}

###############################################################################
# Marital Status (DMG04)
#
# FIX: previous mapping used "S" for SINGLE, but per this companion guide
# "S" = Separated and "I" = Single. Full valid codeset per guide:
#   B = Registered Domestic Partner   D = Divorced   I = Single
#   M = Married   R = Unreported   S = Separated
#   U = Unmarried/Unknown   W = Widowed   X = Legally Separated
###############################################################################

MARITAL_STATUS_CODES = {
    "SINGLE": "I",
    "MARRIED": "M",
    "DIVORCED": "D",
    "WIDOWED": "W",
    "SEPARATED": "S",
    "LEGALLY SEPARATED": "X",
    "DOMESTIC PARTNER": "B",
    "REGISTERED DOMESTIC PARTNER": "B",
    "UNREPORTED": "R",
    "UNKNOWN": "U",
}

###############################################################################
# Insurance Line Codes (HD03)
#
# FIX: guide's confirmed valid values are HLT, DEN, VIS, LTD, STD, FAC.
# STD/LTD must stay as themselves (previously both collapsed to "DIS").
# LIFE uses "FAC" per this guide, not the more common "LIF" — confirm this
# isn't a typo in their guide before going live, but it's what's documented.
#
# ACCIDENT / CRITICAL ILLNESS / HSA / FSA do NOT appear anywhere in this
# companion guide's HD03 list. Mappings are left in below so nothing throws
# a KeyError if the census contains them, but these are UNCONFIRMED — check
# with the trading partner whether these lines are even in scope for this
# feed before relying on them.
###############################################################################

INSURANCE_LINE_CODES = {
    "MEDICAL": "HLT",
    "DENTAL": "DEN",
    "VISION": "VIS",
    "LIFE": "FAC",
    "VOLUNTARY LIFE": "FAC",
    "STD": "STD",
    "LTD": "LTD",

    # --- Unconfirmed against this companion guide, see note above ---
    "ACCIDENT": "ACC",
    "CRITICAL ILLNESS": "CI",
    "HSA": "HSA",
    "FSA": "FSA",
}

###############################################################################
# Maintenance Types (HD01 / INS03)
#
# Both segments share this codeset per the guide:
#   001 = Change   002 = Delete   021 = Addition   024 = Cancellation
#   025 = Reinstatement   026 = Correction   030 = Audit or Compare
#
# IMPORTANT: per the guide, INS03 (2000 loop) has a special rule for full
# files: "If BGN08=2, then INS03 must be 001 (for emp). Dependents can be
# 001, 021, 024, 025." In other words, on a full-file send the EMPLOYEE row
# is always CHANGE (001), never ADD (021) — only dependents may vary. See
# models.py Person.maintenance_type, which now branches on is_employee to
# reflect this.
###############################################################################

MAINTENANCE_TYPES = {
    "CHANGE": "001",
    "DELETE": "002",
    "ADD": "021",
    "TERMINATE": "024",
    "REINSTATE": "025",
    "CORRECTION": "026",
    "AUDIT_COMPARE": "030",
}

# The maintenance type the employee (subscriber) row must carry on a full
# file (BGN08 = 2), per the guide. Kept separate from MAINTENANCE_TYPES so
# call sites can be explicit about *why* they're using "001" here.
FULL_FILE_EMPLOYEE_MAINTENANCE_TYPE = MAINTENANCE_TYPES["CHANGE"]

###############################################################################
# Coverage Tier Codes (HD05)
#
# FIX: previous COVERAGE_TIERS held placeholder/enum-style values (e.g.
# "EMPLOYEE_SPOUSE"), not real EDI codes. Per the guide's "Valid Tier Codes"
# tab, the valid codeset depends on how the *plan* is structured — 2-tier,
# 3-tier, or 4-tier — so this can't be a single flat mapping. Whichever tier
# structure a given plan/group uses needs to come from config (per-plan, not
# global — see config.py), and the segment-builder should look up the code
# from the matching dict below.
#
# There's also a distinct "split family" codeset (DEP/SPO/CHD) used when the
# employee and dependents are billed on separate coverage records rather
# than one combined family record — flagged separately since it's not just
# another tier count, it's a different billing pattern.
###############################################################################

TIER_CODES_2_TIER = {
    "EMPLOYEE": "EMP",
    "EMPLOYEE ONLY": "EMP",
    "DEPENDENT ONLY": "DEP",
    "EMPLOYEE + SPOUSE": "FAM",
    "EMPLOYEE + CHILD": "FAM",
    "FAMILY": "FAM",
}

TIER_CODES_3_TIER = {
    "EMPLOYEE": "EMP",
    "EMPLOYEE ONLY": "EMP",
    "DEPENDENT ONLY": "DEP",
    "EMPLOYEE + SPOUSE": "TWO",
    "EMPLOYEE + CHILD": "E1D",
    "EMPLOYEE + ONE DEPENDENT": "E1D",
    "FAMILY": "FAM",
}

TIER_CODES_4_TIER = {
    "EMPLOYEE": "EMP",
    "EMPLOYEE ONLY": "EMP",
    "DEPENDENT ONLY": "DEP",
    "EMPLOYEE + SPOUSE": "ESP",
    "EMPLOYEE + CHILD": "ECH",
    "FAMILY": "FAM",

    # UMR-specific expanded dependent-count tiers. Guide notes these are
    # "considered family in UMR's system" — confirm whether your plans
    # actually use these before wiring them in, most groups just use FAM.
    "EMPLOYEE + TWO DEPENDENTS": "E2D",
    "EMPLOYEE + THREE DEPENDENTS": "E3D",
    "EMPLOYEE + ONE OR MORE DEPENDENTS": "E5D",
    "EMPLOYEE + TWO OR MORE DEPENDENTS": "E6D",
    "EMPLOYEE + THREE OR MORE DEPENDENTS": "E7D",
    "EMPLOYEE + FOUR OR MORE DEPENDENTS": "E8D",
    "EMPLOYEE + FIVE OR MORE DEPENDENTS": "E9D",
}

SPLIT_FAMILY_TIER_CODES = {
    "DEPENDENT ONLY": "DEP",
    "SPOUSE ONLY": "SPO",
    "CHILD ONLY": "CHD",
}

TIER_STRUCTURES = {
    "2_TIER": TIER_CODES_2_TIER,
    "3_TIER": TIER_CODES_3_TIER,
    "4_TIER": TIER_CODES_4_TIER,
}


import re


def _dependent_count_from_text(text: str) -> int | None:
    """
    Extracts an explicit numeric count from tier text if present, e.g.
    2 from "Employee + Spouse + 2 Children".
    """
    match = re.search(r"(\d+)\s*(CHILD|DEPENDENT)", text)
    return int(match.group(1)) if match else None


def get_tier_code(raw_tier: str, tier_structure: str) -> str:
    """
    Resolves a free-text Coverage Tier value from the census into the
    HD05 code for the given tier structure.

    Tries an exact match against the structure's known literal phrases
    first (e.g. "Employee Only", "Family"). Falls back to a keyword
    parse for combination phrasing the census uses that isn't a literal
    dict key, e.g. "Employee + Spouse + 1 Child".

    Confirmed against the guide's Valid Tier Codes tab: no tier
    structure has a distinct code for "spouse + child(ren) together" --
    ESP/ECH (4-tier) are spouse-ONLY / child-ONLY respectively, so any
    phrase naming both spouse and child collapses to FAM.
    """

    text = (raw_tier or "").strip().upper()

    try:
        codeset = TIER_STRUCTURES[tier_structure]
    except KeyError:
        raise KeyError(
            f"Unknown tier structure {tier_structure!r}; "
            f"expected one of {list(TIER_STRUCTURES)}"
        ) from None

    # 1. Exact match against known literal phrasings for this structure.
    if text in codeset:
        return codeset[text]

    # 2. Unambiguous keyword shortcuts.
    if "FAMILY" in text:
        return codeset.get("FAMILY", "FAM")

    if "DEPENDENT ONLY" in text or text == "DEPENDENT":
        return codeset.get("DEPENDENT ONLY", "DEP")

    if "EMPLOYEE ONLY" in text or text in ("EE ONLY", "EMPLOYEE"):
        return codeset.get("EMPLOYEE ONLY", "EMP")

    # 3. Combination parsing.
    has_spouse = "SPOUSE" in text or "DOMESTIC PARTNER" in text
    has_child = "CHILD" in text

    if has_spouse and has_child:
        return codeset.get("FAMILY", "FAM")

    if has_spouse and not has_child:
        if tier_structure == "4_TIER":
            return "ESP"
        if tier_structure == "3_TIER":
            return "TWO"
        return codeset.get("FAMILY", "FAM")  # 2-tier has no spouse-only code

    if has_child and not has_spouse:
        if tier_structure == "4_TIER":
            return "ECH"
        if tier_structure == "3_TIER":
            return "E1D" if _dependent_count_from_text(text) == 1 else "FAM"
        return codeset.get("FAMILY", "FAM")  # 2-tier has no child-only code

    raise KeyError(
        f"Could not resolve Coverage Tier {raw_tier!r} to a valid HD05 "
        f"code for tier_structure {tier_structure!r} -- this phrasing "
        f"wasn't recognized by the exact-match table or the keyword "
        f"parser. It may need to be added explicitly, or the census "
        f"value may be a typo worth checking."
    )


###############################################################################
# Election Status
###############################################################################

ELECTION_STATUS_CODES = {
    "ENROLLED": "ACTIVE",
    "WAIVED": "WAIVED",
    "TERMINATED": "TERMINATED",
}

###############################################################################
# Boolean Values
###############################################################################

TRUE_VALUES = {
    "Y",
    "YES",
    "TRUE",
    "1",
}

FALSE_VALUES = {
    "N",
    "NO",
    "FALSE",
    "0",
}

###############################################################################
# Supported Input Date Formats
###############################################################################

DATE_FORMATS = (
    "%m/%d/%Y",
    "%m/%d/%y",
    "%Y-%m-%d",
    "%Y%m%d"
)

###############################################################################
# Default Values
###############################################################################

DEFAULT_COUNTRY = "US"

###############################################################################
# Common Plan Types
###############################################################################

PLAN_TYPES = {
    "MEDICAL",
    "DENTAL",
    "VISION",
    "LIFE",
    "VOLUNTARY LIFE",
    "STD",
    "LTD",
    "ACCIDENT",
    "CRITICAL ILLNESS",
    "HSA",
    "FSA",
}

###############################################################################
# Country Codes (2100A/2100B DMG07 and N4 loops — ISO-3166-derived)
#
# Source: companion guide "Country Codes" tab. NA (Namibia) restored --
# Excel/pandas interprets the literal string "NA" as a null and drops it.
# Duplicate codes in the source sheet (AS, KN, LC, VC) were old/new name
# variants for the same country and collapsed to one entry. VI appeared
# twice for two different countries (British vs. U.S. Virgin Islands) --
# almost certainly a copy/paste error in the source, since British Virgin
# Islands already has its own correct code (VG) elsewhere in the sheet.
# Kept VI -> U.S. Virgin Islands, the real ISO-3166 assignment.
###############################################################################

COUNTRY_CODES = {
    "AF": "Afghanistan",
    "AL": "Albania",
    "DZ": "Algeria",
    "AS": "American Samoa",
    "AD": "Andorra",
    "AO": "Angola",
    "AI": "Anguilla",
    "AQ": "Antarctica",
    "AG": "Antigua And Barbuda",
    "AR": "Argentina",
    "AM": "Armenia",
    "AW": "Aruba",
    "AC": "Ascension Island",
    "AU": "Australia",
    "AT": "Austria",
    "AZ": "Azerbaijan",
    "BS": "Bahamas",
    "BH": "Bahrain",
    "BD": "Bangladesh",
    "BB": "Barbados",
    "BY": "Belarus",
    "BE": "Belgium",
    "BZ": "Belize",
    "BJ": "Benin",
    "BM": "Bermuda",
    "BT": "Bhutan",
    "BO": "Bolivia",
    "BA": "Bosnia And Herzegowina",
    "BW": "Botswana",
    "BV": "Bouvet Island",
    "BR": "Brazil",
    "IO": "British Indian Ocean Territory",
    "VG": "British Virgin Islands",
    "BN": "Brunei Darussalam",
    "BG": "Bulgaria",
    "BF": "Burkina Faso",
    "BI": "Burundi",
    "KH": "Cambodia",
    "CM": "Cameroon",
    "CA": "Canada",
    "CV": "Cape Verde",
    "CW": "Curacao",
    "KY": "Cayman Islands",
    "GH": "Ghana",
    "GI": "Gibraltar",
    "GR": "Greece",
    "GL": "Greenland",
    "GD": "Grenada",
    "GP": "Guadeloupe",
    "GU": "Guam",
    "GT": "Guatemala",
    "GG": "Guernsey",
    "GN": "Guinea",
    "GW": "Guinea-Bissau",
    "GY": "Guyana",
    "HT": "Haiti",
    "HM": "Heard And Mc Donald Islands",
    "HN": "Honduras",
    "HK": "Hong Kong",
    "HU": "Hungary",
    "IS": "Iceland",
    "IN": "India",
    "ID": "Indonesia",
    "IR": "Iran (Islamic Republic Of)",
    "IQ": "Iraq",
    "IE": "Ireland",
    "IM": "Isle of Man",
    "IL": "Israel",
    "IT": "Italy",
    "JM": "Jamaica",
    "JP": "Japan",
    "JE": "Jersey",
    "JO": "Jordan",
    "KZ": "Kazakhstan",
    "KE": "Kenya",
    "KI": "Kiribati",
    "KP": "Korea, Dem. Peoples Rep of",
    "KR": "Korea, Republic Of",
    "KW": "Kuwait",
    "KG": "Kyrgyzstan",
    "LA": "Lao People's Democratic Republic",
    "LV": "Latvia",
    "LB": "Lebanon",
    "LS": "Lesotho",
    "LR": "Liberia",
    "LY": "Libyan Arab Jamahiriya",
    "PA": "Panama",
    "PG": "Papua New Guinea",
    "PY": "Paraguay",
    "PE": "Peru",
    "PH": "Philippines",
    "PN": "Pitcairn",
    "PL": "Poland",
    "PT": "Portugal",
    "PR": "Puerto Rico",
    "QA": "Qatar",
    "RE": "Reunion",
    "RO": "Romania",
    "RU": "Russian Federation",
    "RW": "Rwanda",
    "KN": "Saint Kitts And Nevis",
    "LC": "Saint Lucia",
    "VC": "Saint Vincent And The Grenadines",
    "WS": "Samoa",
    "SM": "San Marino",
    "ST": "Sao Tome And Principe",
    "SA": "Saudi Arabia",
    "SN": "Senegal",
    "SP": "Serbia",
    "SC": "Seychelles",
    "SL": "Sierra Leone",
    "SG": "Singapore",
    "SK": "Slovakia (Slovak Republic)",
    "SI": "Slovenia",
    "SB": "Solomon Islands",
    "SO": "Somalia",
    "ZA": "South Africa",
    "GS": "South Georgia And The South Sandwich Islands",
    "SU": "Soviet Union",
    "ES": "Spain",
    "LK": "Sri Lanka",
    "SH": "St. Helena",
    "PM": "St. Pierre And Miquelon",
    "SD": "Sudan",
    "SR": "Suriname",
    "CF": "Central African Republic",
    "TD": "Chad",
    "CL": "Chile",
    "CN": "China",
    "CX": "Christmas Island",
    "CC": "Cocos (Keeling) Islands",
    "CO": "Colombia",
    "KM": "Comoros",
    "CD": "Congo (Democratic Republic)",
    "CG": "Congo (Republic)",
    "CK": "Cook Islands",
    "CR": "Costa Rica",
    "CI": "Cote D'Ivoire",
    "HR": "Croatia (local name: Hrvatska)",
    "CU": "Cuba",
    "CY": "Cyprus",
    "CZ": "Czech Republic",
    "DK": "Denmark",
    "DJ": "Djibouti",
    "DM": "Dominica",
    "DO": "Dominican Republic",
    "TP": "East Timor",
    "EC": "Ecuador",
    "EG": "Egypt",
    "SV": "El Salvador",
    "GQ": "Equatorial Guinea",
    "ER": "Eritrea",
    "EE": "Estonia",
    "ET": "Ethiopia",
    "FK": "Falkland Islands (Malvinas)",
    "FO": "Faroe Islands",
    "FJ": "Fiji",
    "FI": "Finland",
    "FR": "France",
    "FX": "France Metropolitan",
    "GF": "French Guiana",
    "PF": "French Polynesia",
    "TF": "French Southern Territories",
    "GA": "Gabon",
    "GM": "Gambia",
    "GE": "Georgia",
    "DE": "Germany",
    "LI": "Liechtenstein",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "MO": "Macau",
    "MK": "Macedonia, The Former Yugoslav Republic Of",
    "MG": "Madagascar",
    "MW": "Malawi",
    "MY": "Malaysia",
    "MV": "Maldives",
    "ML": "Mali",
    "MT": "Malta",
    "MH": "Marshall Islands",
    "MQ": "Martinique",
    "MR": "Mauritania",
    "MU": "Mauritius",
    "YT": "Mayotte",
    "MX": "Mexico",
    "FM": "Micronesia, Federated States Of",
    "MD": "Moldova, Republic Of",
    "MC": "Monaco",
    "MN": "Mongolia",
    "ME": "Montenegro",
    "MS": "Montserrat",
    "MA": "Morocco",
    "MZ": "Mozambique",
    "MM": "Myanmar",
    "NA": "Namibia",
    "NR": "Nauru",
    "NP": "Nepal",
    "NL": "Netherlands",
    "AN": "Netherlands Antilles",
    "NC": "New Caledonia",
    "NZ": "New Zealand",
    "NI": "Nicaragua",
    "NE": "Niger",
    "NG": "Nigeria",
    "NU": "Niue",
    "NF": "Norfolk Island",
    "MP": "Northern Mariana Islands",
    "NO": "Norway",
    "OM": "Oman",
    "PK": "Pakistan",
    "PW": "Palau",
    "SJ": "Svalbard And Jan Mayen Islands",
    "SZ": "Swaziland",
    "SE": "Sweden",
    "CH": "Switzerland",
    "SY": "Syrian Arab Republic",
    "TW": "Taiwan, Province Of China",
    "TJ": "Tajikistan",
    "TZ": "Tanzania, United Republic Of",
    "TH": "Thailand",
    "TG": "Togo",
    "TK": "Tokelau",
    "TO": "Tonga",
    "TT": "Trinidad And Tobago",
    "TN": "Tunisia",
    "TR": "Turkey",
    "TM": "Turkmenistan",
    "TC": "Turks And Caicos Islands",
    "TV": "Tuvalu",
    "UG": "Uganda",
    "UA": "Ukraine",
    "AE": "United Arab Emirates",
    "GB": "United Kingdom",
    "US": "United States",
    "UM": "United States Minor Outlying Islands",
    "UY": "Uruguay",
    "UZ": "Uzbekistan",
    "VU": "Vanuatu",
    "VA": "Vatican City State (Holy See)",
    "VE": "Venezuela",
    "VN": "Viet Nam",
    "VI": "Virgin Islands (U.S.)",
    "WF": "Wallis And Futuna Islands",
    "EH": "Western Sahara",
    "YE": "Yemen",
    "YU": "Yugoslavia",
    "ZR": "Zaire",
    "ZM": "Zambia",
    "ZW": "Zimbabwe",
}

# Reverse lookup for turning a full country name (as it might appear in a
# census export) into its 2-letter code. Built automatically from the
# table above so it can't drift out of sync.
COUNTRY_NAME_TO_CODE = {
    name.upper(): code for code, name in COUNTRY_CODES.items()
}

###############################################################################
# Logging
###############################################################################

LOGGER_NAME = "834_generator"