import re


DIACRITIC_MAP = str.maketrans(
    'ăâîșțşţĂÂÎȘȚŞŢ',
    'aaiststAAISTST'
)


def clean_diacritics(text):
    if not text:
        return text
    return text.translate(DIACRITIC_MAP).strip()


def clean_location(oras_raw, judet_raw):
    if not oras_raw or not judet_raw:
        return None, None

    oras = oras_raw.strip()
    judet = judet_raw.replace("Județul", "").replace("Judetul", "").replace("-", " ").strip()

    # daca orasul are cifre e probabil strada, il sar
    # exceptie: Sector 1..6
    sector_match = re.search(r'Sector(?:ul)?\s*([1-6])', oras, re.IGNORECASE)
    if any(char.isdigit() for char in oras) and not sector_match:
        return None, None

    # il fac "Sector N"
    if sector_match:
        oras = f"Sector {sector_match.group(1)}"

    # "Bucuresti - Ilfov" nu e clar
    if "Ilfov" in judet or "Bucuresti - Ilfov" in judet:
        is_bucuresti = "bucuresti" in oras.lower() or sector_match is not None
        judet = "Bucuresti" if is_bucuresti else "Ilfov"

    # scot "Bucuresti, " din fata cartierelor
    if judet == "Bucuresti":
        oras = re.sub(r'^Bucuresti\s*,\s*', '', oras, flags=re.IGNORECASE).strip()

    # Popesti-Leordeni -> Popesti Leordeni (ca sa se potriveasca)
    if not sector_match:
        oras = re.sub(r'\s+', ' ', oras.replace("-", " ")).strip().title()

    return oras, judet


def clean_price(price_text):
    if not price_text:
        return None
    # preturile in RON/Lei sunt sarite - se pastreaza doar cele in EUR
    # (ca sa nu fie amestecate valute in baza de date si sa iasa statistici aiurea)
    text_lower = price_text.lower()
    if "ron" in text_lower or "lei" in text_lower:
        return None
    # din textul cu pretul se ia doar primul numar
    # ex: "95.000 € - 3.500 €/mp" -> 95000, nu 955003500
    match = re.search(r'\d[\d\s.,]*', price_text)
    if not match:
        return None
    digits = ''.join(c for c in match.group() if c.isdigit())
    return int(digits) if digits else None


def fix_price(pret, tip_imobiliar, tip_tranzactie, suprafata):
    # elimina preturile prea mari sau prea mici (probabil greseli)
    # exceptie la terenuri: daca pretul e pe metru patrat, e inmultit cu suprafata
    if pret is None:
        return None

    # la terenuri, daca pretul e foarte mic, probabil e pretul pe mp si nu total
    # in cazul asta se inmulteste cu suprafata ca sa rezulte pretul total
    # daca nu exista suprafata, anuntul nu poate fi salvat
    if tip_imobiliar == "Teren" and pret < 500:
        if suprafata:
            pret = pret * suprafata
        else:
            return None

    # limite diferite pentru vanzare vs inchiriere
    # ce e in afara intervalului e considerat greseala si se returneaza None
    if tip_tranzactie == "vanzare":
        if pret < 5000 or pret > 10_000_000:
            return None
    elif tip_tranzactie == "inchiriere":
        if pret < 50 or pret > 100_000:
            return None

    return pret


def normalize_tip_imobil(tip_imobiliar):
    if not tip_imobiliar:
        return "Altele"
    tip = tip_imobiliar.lower()
    if "apartament" in tip or "garsonier" in tip:
        return "Apartament"
    if "cas" in tip or "vil" in tip or "duplex" in tip:
        return "Casa"
    if "teren" in tip:
        return "Teren"
    if "spati" in tip or "birou" in tip:
        return "Spatii comerciale"
    return "Altele"


def clean_suprafata(text):
    if not text:
        return None
    match = re.search(r'(\d+[\d.,]*)', text)
    if match:
        try:
            return round(float(match.group(1).replace(',', '.')))
        except (ValueError, TypeError):
            return None
    return None


def clean_etaj(text):
    if text is None:
        return None
    text_lower = str(text).lower().strip()

    # label-uri goale
    if "fara informatii" in text_lower or "fără informații" in text_lower:
        return None
    # doar label, fara valoare
    if text_lower.rstrip(":").strip() in ("etaj", "numar etaje", "număr etaje"):
        return None

    # "un nivel" = casa la parter, il pun 0
    if "un nivel" in text_lower:
        return "0"

    # parter / demisol -> 0
    if "parter" in text_lower or "demisol" in text_lower:
        return "0"
    if "mansarda" in text_lower:
        return "Mansarda"

    # "10 si peste" -> iau primul numar
    if "si peste" in text_lower or "și peste" in text_lower:
        match = re.search(r'\d+', text_lower)
        if match:
            return str(match.group())

    # numar etaje total cladire -> nu e etajul apartamentului
    if "numar etaje" in text_lower or "număr etaje" in text_lower:
        return None

    # iau primul numar, pana la 20 (peste = probabil eroare)
    match = re.search(r'\d+', text_lower)
    if match:
        n = int(match.group())
        if 0 <= n <= 20:
            return str(n)
        return None

    # daca nu are numar, None
    return None


def an_to_perioada(an_constructie):
    if an_constructie is None:
        return None
    try:
        an = int(an_constructie)
    except (ValueError, TypeError):
        return None
    if an < 1977:
        return "inainte de 1977"
    if an < 1990:
        return "1977-1990"
    if an < 2000:
        return "1990-2000"
    return "dupa 2000"


def clean_compartimentare(text):
    if not text:
        return None
    text_lower = text.lower()
    if "semidecomandat" in text_lower:
        return "semidecomandat"
    if "nedecomandat" in text_lower:
        return "nedecomandat"
    if "decomandat" in text_lower:
        return "decomandat"
    if "circular" in text_lower:
        return "circular"
    return None


def build_id_raw(oras, judet, tip_imobiliar, suprafata, etaj, camere,
                 perioada_constructie, tip_tranzactie):
    # normalizez tipul sa iasa acelasi id de pe orice platforma
    tip_clean = normalize_tip_imobil(tip_imobiliar)

    parts = [oras, judet, tip_clean, suprafata, etaj, camere,
             perioada_constructie, tip_tranzactie]
    # lower() la final ca sa nu am duplicate cand un site trimite "Cluj"
    # si altul "cluj" - iese acelasi id_raw
    return "".join(str(x) for x in parts if x is not None).lower()


def validate_listing(anunt):
    has_judet = bool(anunt.get('judet')) and anunt.get('judet') != "N/A"
    has_oras = bool(anunt.get('oras')) and anunt.get('oras') != "N/A"
    has_pret = anunt.get('pret') is not None
    has_id = bool(anunt.get('id_raw'))
    return has_judet and has_oras and has_pret and has_id


def clean_listing(raw):
    # primeste un dict de la scraper si il curata
    anunt = dict(raw)

    # locatie
    oras, judet = clean_location(anunt.get('oras'), anunt.get('judet'))
    anunt['oras'] = clean_diacritics(oras) if oras else None
    anunt['judet'] = clean_diacritics(judet) if judet else None

    pret = anunt.get('pret')
    if isinstance(pret, str):
        anunt['pret'] = clean_price(pret)
    # daca e deja int sau None, il las asa

    anunt['tip_imobiliar'] = normalize_tip_imobil(anunt.get('tip_imobiliar'))

    supra = anunt.get('suprafata')
    if isinstance(supra, str):
        anunt['suprafata'] = clean_suprafata(supra)

    anunt['etaj'] = clean_etaj(anunt.get('etaj'))

    # din an fac perioada
    an = anunt.get('an_constructie')
    if an is not None:
        perioada = an_to_perioada(an)
        if perioada:
            anunt['perioada_constructie'] = perioada

    if anunt.get('compartimentare'):
        anunt['compartimentare'] = clean_compartimentare(anunt['compartimentare'])

    # apel la final, cand tipul si suprafata sunt deja curatate
    # (fix_price are nevoie de ele ca sa decida limitele corecte)
    anunt['pret'] = fix_price(
        anunt.get('pret'),
        anunt.get('tip_imobiliar'),
        anunt.get('tip_tranzactie'),
        anunt.get('suprafata'),
    )

    # refac id_raw cu valorile curatate sa iasa la fel intre site-uri
    anunt['id_raw'] = build_id_raw(
        anunt.get('oras'),
        anunt.get('judet'),
        anunt.get('tip_imobiliar'),
        anunt.get('suprafata'),
        anunt.get('etaj'),
        anunt.get('camere'),
        anunt.get('perioada_constructie'),
        anunt.get('tip_tranzactie'),
    )

    return anunt
