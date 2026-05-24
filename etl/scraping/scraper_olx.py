from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from bs4 import BeautifulSoup
import time
from datetime import datetime
from etl.processing.cleaner import clean_location, clean_price


def scrape_olx():
    rezultate = []
    links = []

    driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()))
    driver.get('https://www.olx.ro/imobiliare/?currency=EUR&search%5Border%5D=created_at:desc')
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, 'lxml')

    anunturi_olx = soup.find_all('a', class_='css-1tqlkj0')
    for a in anunturi_olx:
        href = a.get("href")
        links.append("https://www.olx.ro" + href)
    links = list(set(links))

    for link in links:
        try:
            driver.get(link)
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, 'lxml')

            oras_raw = soup.find('p', class_='css-1g5nan')
            oras_raw = oras_raw.text.strip() if oras_raw else ""

            judete_raw = soup.find_all("p", class_="css-3cz5o2")
            judet_raw = judete_raw[1].text.strip() if len(judete_raw) > 1 else ""

            oras, judet = clean_location(oras_raw, judet_raw)
            if oras is None:
                print(f"Sar anuntul, locatie invalida -> {oras_raw}")
                continue

            suprafata = None
            etaj = None
            perioada_constructie = None
            an_constructie = None
            compartimentare = None
            tip_tranzactie = None
            tip_imobiliar = None
            platforma = "OLX"
            camere = None

            breadcrumb_list = soup.find('ol', class_='css-xv75xi')
            if breadcrumb_list:
                elemente_li = breadcrumb_list.find_all('li', class_='css-7dfllt')

                for li in elemente_li:
                    a_tag = li.find('a', class_='css-tyi2d1')
                    if a_tag:
                        text_a = a_tag.get_text(strip=True).lower()

                        if "vanzare" in text_a:
                            tip_tranzactie = "vanzare"
                        elif "inchiriere" in text_a or "inchiriat" in text_a:
                            tip_tranzactie = "inchiriere"

                        # tipul de imobil
                        if "apartamente" in text_a:
                            tip_imobiliar = "Apartament"
                        elif "case" in text_a:
                            tip_imobiliar = "Casa"
                        elif "terenuri" in text_a:
                            tip_imobiliar = "Teren"

                        if tip_imobiliar == "Apartament":
                            camere = ''.join(c for c in text_a if c.isdigit())

            elemente = soup.find_all('p', class_='css-odhutu')
            for element in elemente:
                text = element.text.strip()

                if text.startswith('Suprafata utila'):
                    suprafata_text = text.split(':', 1)[1].strip()
                    suprafata = int(''.join(c for c in suprafata_text if c in '0123456789'))
                elif text.startswith('Etaj'):
                    etaj = text.split(':', 1)[1].strip()
                elif text.startswith('An constructie'):
                    perioada_constructie = text.split(':', 1)[1].strip()
                elif text.startswith('Compartimentare'):
                    compartimentare = text.split(':', 1)[1].strip()
                if tip_imobiliar == "Casa" and text.startswith('Camere'):
                    camere = text.split(':', 1)[1].strip()

            camere_element = soup.find('p', class_='css-13x8d99')
            if camere_element and camere_element.text.strip().startswith('Camere'):
                camere = camere_element.text.split(':', 1)[1].strip()

            pret_element = soup.find('h3', class_='css-j7prh4')
            pret = clean_price(pret_element.text if pret_element else None)

            # imaginile
            imagini_url = []
            photo_slides = soup.find_all('div', {'data-testid': 'ad-photo'})
            for slide in photo_slides:
                img = slide.find('img', {'data-testid': 'swiper-image-lazy'})
                if img:
                    src = img.get('src', '')
                    if src and 'apollo.olxcdn.com' in src:
                        imagini_url.append(src)
            imagini_url = list(dict.fromkeys(imagini_url))

            data = datetime.today().strftime('%Y-%m-%d')
            processed = False

        except Exception as e:
            print(f"Eroare: {e}")
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

        print(link, judet, oras, suprafata, etaj, perioada_constructie, an_constructie, compartimentare, camere, tip_tranzactie, tip_imobiliar, platforma, pret, data)

    driver.quit()
    return rezultate
