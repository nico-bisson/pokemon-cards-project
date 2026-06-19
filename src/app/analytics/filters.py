def build_filters(series=None, generation=None, mode=None):
    filters = []
    params = []

    CATEGORY_ALIASES = {
        "Pokemon": ("Pokemon", "Pokémon"),
        "Trainer": ("Trainer", "Dresseur"),
        "Energy": ("Energy", "Énergie"),
    }

    def add_category_filter(category):
        values = CATEGORY_ALIASES[category]
        placeholders = ",".join("?" for _ in values)
        filters.append(f"c.category IN ({placeholders})")
        params.extend(values)

    # 👇 groupes virtuels UI (pas en DB)
    # -------------------
    # SERIES
    # -------------------
    if series and series != "All":
        filters.append("s.standard_name = ?")
        params.append(series)

    # -------------------
    # GENERATION
    # -------------------
    if generation and generation != "All":
        filters.append("p.generation_id = ?")
        params.append(generation)

    # -------------------
    # MODE / CATEGORY
    # -------------------
    if mode == "Pokemon":
        add_category_filter("Pokemon")

    elif mode == "Trainer":
        add_category_filter("Trainer")

    elif mode == "Energy":
        add_category_filter("Energy")

    elif mode == "Baby":
        add_category_filter("Pokemon")
        filters.append("p.is_baby = 1")

    elif mode == "Legendary":
        add_category_filter("Pokemon")
        filters.append("p.is_legendary = 1")
        filters.append("p.is_mythical = 0")

    elif mode == "Mythical":
        add_category_filter("Pokemon")
        filters.append("p.is_mythical = 1")

    elif mode == "Legendary + Mythical":
        add_category_filter("Pokemon")
        filters.append("(p.is_legendary = 1 OR p.is_mythical = 1)")

    # -------------------
    # FINAL SQL
    # -------------------
    sql = " AND " + " AND ".join(filters) if filters else ""

    return sql, tuple(params)
