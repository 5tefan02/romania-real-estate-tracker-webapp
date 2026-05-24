from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from bs4 import BeautifulSoup
import time
from datetime import datetime
import re
from etl.processing.cleaner import clean_location, clean_price, clean_suprafata, clean_etaj, an_to_perioada


def scrape_imobiliarero(url_start, tip_tranzactie):
    rezultate = []
    links = []

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)
    driver.get(url_start)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'lxml')
    anunturi_imobiliare = soup.find_all('a', {'data-cy': 'listing-information-link'})

    for a in anunturi_imobiliare:
        href = a.get("href")
        links.append("https://www.imobiliare.ro" + href)
    links = list(set(links))

    for link in links:
        try:
            driver.get(link)
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, 'lxml')

            oras = None
            judet = None
            tip_imobiliar = None
            suprafata = None
            camere = None

            nav = soup.find('nav', {'data-cy': 'breadcrumbs'})

            if nav:
                breadcrumb_links = nav.find_all('a')

                text_links = [l.get_text(strip=True) for l in breadcrumb_links if l.get_text(strip=True)]

                if len(text_links) >= 2:
                    raw_judet = text_links[2]
                    raw_oras = text_links[3]
                    raw_tip_imobiliar = text_links[1]

                    tip_imobiliar = raw_tip_imobiliar.strip()
                    oras, judet = clean_location(raw_oras, raw_judet)
                    if oras is None:
                        print(f"Locatie invalida: {raw_oras}, {raw_judet}")
                        continue
                    if judet == "Bucuresti" and "Bucuresti" not in oras:
                        oras = f"Bucuresti, {oras}"

                    print(f" Judet: {judet}, Oras: {oras}")

            label_suprafata = soup.find('span', string=re.compile(r'Suprafe|Sup\.', re.IGNORECASE))

            if not label_suprafata:
                label_suprafata = soup.find(lambda tag: tag.name == "span" and "utila" in tag.text.lower())

            if label_suprafata:
                container = label_suprafata.find_parent('div', class_='swiper-item') or label_suprafata.find_parent('div')

                valoare_span = container.find(lambda tag: tag.name == "span" and "mp" in tag.text.lower())

                if valoare_span:
                    suprafata = clean_suprafata(valoare_span.get_text(strip=True))

            label_etaj = soup.find('span', string=re.compile(r'Etaj', re.IGNORECASE))
            etaj = None

            if label_etaj:
                container_etaj = label_etaj.find_parent('div')
                if container_etaj:
                    valoare_etaj_span = container_etaj.find('span', class_='font-semibold')

                    if valoare_etaj_span:
                        etaj = clean_etaj(valoare_etaj_span.get_text(strip=True))

            an_constructie = None
            label_an_constructie = soup.find('span', string=re.compile(r'An constr.', re.IGNORECASE))

            if label_an_constructie:
                container_an = label_an_constructie.find_parent('div')
                valoare_an_span = container_an.find('span', class_='font-semibold')

                if valoare_an_span:
                    match = re.search(r"(\d{4})", valoare_an_span.get_text(strip=True))
                    if match:
                        try:
                            an_constructie = int(match.group(1))
                        except ValueError:
                            an_constructie = None

            perioada_constructie = an_to_perioada(an_constructie)

            compartimentare = None

            label_compartimentare = soup.find('section', {'data-cy': 'listing-amenities-excerpt-component'})

            if label_compartimentare:
                spans = label_compartimentare.find_all('span', class_='text-md')

                cuvinte_cheie = ["decomandat", "semidecomandat", "nedecomandat", "circular"]

                for s in spans:
                    text_span = s.get_text(strip=True).lower()

                    if any(keyword in text_span for keyword in cuvinte_cheie):
                        compartimentare = s.get_text(strip=True)
                        break

            label_camere = soup.find('span', string=re.compile(r'Nr. cam.', re.IGNORECASE))
            if label_camere:
                container_camere = label_camere.find_parent('div')
                valoare_camere_span = container_camere.find('span', class_='font-semibold')

                if valoare_camere_span:
                    text_camere = valoare_camere_span.get_text(strip=True)
                    camere = text_camere.strip()

                    try:
                        camere = int(camere)
                    except ValueError:
                        camere = camere

            # imaginile
            imagini_url = []
            gallery = soup.find('div', class_=re.compile(r'gallery\b'))
            if gallery:
                img_tags = gallery.find_all('img', src=re.compile(r'roamcdn\.net.*gallery-main'))
                for img in img_tags:
                    src = img.get('src', '')
                    if src and 'object-cover' not in (img.get('class') or []):
                        imagini_url.append(src)
            imagini_url = list(dict.fromkeys(imagini_url))

            label_pret = soup.find('div', {'aria-label': 'price'})
            pret = clean_price(label_pret.text if label_pret else None)

            platforma = "imobiliare.ro"

            data = datetime.today().strftime('%Y-%m-%d')

            processed = False

        except Exception as e:
            print(f"Eroare la link-ul {link}: {e}")
            continue

        rezultate.append({
            'URL_anunt': link,
            'judet': judet,
            'oras': oras,
            'suprafata': suprafata,
            'etaj': etaj,
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
            'imagini_url': '|'.join(imagini_url) if imagini_url else ''})

        print(f"Gata {link}, Oras: {oras}, Judet: {judet}, Pret: {pret}")
    driver.quit()
    return rezultate
