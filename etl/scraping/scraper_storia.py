from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from bs4 import BeautifulSoup
import time
from datetime import datetime
import re
from etl.processing.cleaner import clean_diacritics, clean_location, clean_price, clean_suprafata, clean_etaj, an_to_perioada, clean_compartimentare, build_id_raw


def scrape_storia(url_start, tip_tranzactie, tip_imobiliar):
    rezultate = []
    links = []

    # headless ca sa fie mai rapid
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.page_load_strategy = 'eager'

    print("Pornesc driverul pentru Storia...")
    driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)

    driver.get(url_start)
    time.sleep(5)

    # iau link-urile de pe pagina principala
    soup = BeautifulSoup(driver.page_source, 'lxml')
    anunturi_imobiliare = soup.find_all('a', {'data-cy': 'listing-item-link'})

    for a in anunturi_imobiliare:
        href = a.get("href")
        if href:
            links.append("https://www.storia.ro" + href)

    links = list(set(links))
    print(f"Am gasit {len(links)} link-uri.")

    # intru pe fiecare anunt
    for link in links:
        try:
            driver.get(link)
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, 'lxml')

            oras = None
            judet = None
            suprafata = None
            etaj_final = None
            an_constructie = None
            perioada_constructie = None
            camere = None
            compartimentare = None
            pret = None

            # locatie
            location_element = soup.find('a', {'data-sentry-source-file': 'MapLink.tsx'})

            if location_element:
                text_locatie = clean_diacritics(location_element.get_text(strip=True))
                parti = [p.strip() for p in text_locatie.split(',')]

                oras_raw = parti[-2] if len(parti) >= 2 else parti[0]
                judet_raw = parti[-1] if len(parti) >= 1 else None

                oras, judet = clean_location(oras_raw, judet_raw)

                # la Bucuresti vreau sa am sectorul
                if judet == "Bucuresti":
                    sector_gasit = next((p.strip() for p in parti if "Sector" in p), None)
                    oras = f"Bucuresti, {sector_gasit}" if sector_gasit else "Bucuresti"

            # suprafata
            detalii_items = soup.find_all('div', class_=re.compile(r'e178zspo0|css-1okys8k'))
            for item in detalii_items:
                text_item = item.get_text(separator=" ", strip=True)
                if "m²" in text_item or "Suprafata" in text_item:
                    suprafata = clean_suprafata(text_item)
                    if suprafata:
                        break

            # etaj / an / camere
            containere_detalii = soup.find_all('div', {'data-sentry-element': 'ItemGridContainer'})
            if not containere_detalii:
                containere_detalii = soup.find_all('div', class_=re.compile(r'css-1xw0jqp|efdvw050'))

            for container in containere_detalii:
                text_complet = container.get_text(separator=" ", strip=True).lower()

                if "etaj" in text_complet or "parter" in text_complet or "demisol" in text_complet:
                    etaj_final = clean_etaj(text_complet)

                elif "anul construc" in text_complet or "an construc" in text_complet:
                    match = re.search(r'\d{4}', text_complet)
                    if match:
                        an_constructie = int(match.group())
                        perioada_constructie = an_to_perioada(an_constructie)

                elif "camere" in text_complet:
                    match = re.search(r'\d+', text_complet)
                    if match:
                        camere = int(match.group())

            # compartimentarea o iau din descriere
            container_descriere = soup.find('div', {'data-cy': 'ad_description'})
            if not container_descriere:
                container_descriere = soup.find('div', class_='css-fl29zg')

            if container_descriere:
                text_descriere = container_descriere.get_text(separator=" ", strip=True)
                compartimentare = clean_compartimentare(text_descriere)

            # imaginile
            imagini_url = []
            gallery = soup.find('div', {'data-cy': 'mosaic-gallery-main-view'})
            if gallery:
                img_tags = gallery.find_all('img', class_=re.compile(r'el1rdii3'))
                for img in img_tags:
                    src = img.get('src', '')
                    if src and 'apollo.olxcdn.com' in src:
                        imagini_url.append(src)
            imagini_url = list(dict.fromkeys(imagini_url))

            pret_element = soup.find('strong', {'data-cy': 'adPageHeaderPrice'})
            pret = clean_price(pret_element.get_text(strip=True) if pret_element else None)

            platforma = "Storia"
            data = datetime.today().strftime('%Y-%m-%d')
            processed = False

            id_raw = build_id_raw(
                oras, judet, tip_imobiliar, suprafata, etaj_final,
                camere, perioada_constructie, tip_tranzactie
            )

            rezultate.append({
                'id_raw': id_raw,
                'URL_anunt': link,
                'judet': judet,
                'oras': oras,
                'suprafata': suprafata,
                'etaj': etaj_final,
                'perioada_constructie': perioada_constructie,
                'an_constructie': an_constructie,
                'compartimentare': compartimentare,
                'camere': camere,
                'pret': pret,
                'tip_tranzactie': tip_tranzactie,
                'tip_imobiliar': tip_imobiliar,
                'platforma': platforma,
                'data': data,
                'processed': processed,
                'imagini_url': '|'.join(imagini_url) if imagini_url else ''
            })

            print(f"Gata {link}, Oras: {oras}, Pret: {pret}")

        except Exception as e:
            print(f"Eroare la {link}: {e}")
            continue

    driver.quit()
    return rezultate
