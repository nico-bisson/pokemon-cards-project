ROMAN = {
    1: "I",
    2: "II",
    3: "III",
    4: "IV",
    5: "V",
    6: "VI",
    7: "VII",
    8: "VIII",
    9: "IX",
}


def format_generation(gen_id: int) -> str:
    return f"Generation {ROMAN.get(gen_id, gen_id)}"
