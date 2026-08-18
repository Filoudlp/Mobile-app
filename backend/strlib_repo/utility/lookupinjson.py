import json

def get_section(data: dict, name: str) -> dict:
    """
    Récupère une section par son nom en ignorant la ligne des unités.

    :param data: Contenu du JSON chargé
    :param name: Nom de la section ex: "IPE 100"
    :return:     Dictionnaire des propriétés de la section
    """
    sections = [
        s for s in data["sections"]
        if s.get("Name") not in (None, "unit")   # ignore la ligne des unités
    ]

    result = next((s for s in sections if s["Name"] == name), None)

    if result is None:
        available = [s["Name"] for s in sections]
        raise ValueError(
            f"Section '{name}' introuvable.\n"
            f"Sections disponibles : {available}"
        )

    return result


if __name__ == "__main__":
    with open("ressource/IPE.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    ipe100 = get_section(data, "IPE 100")

    print(ipe100)
    print(f"Iz  = {ipe100['Iz']} mm⁴")
    print(f"Iy  = {ipe100['Iy']} mm⁴")
    print(f"A   = {ipe100['A']} mm²")
