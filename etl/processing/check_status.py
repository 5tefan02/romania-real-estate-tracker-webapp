from bs4 import BeautifulSoup
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from etl.processing.cleaner import clean_price


def verificare_status(driver, url, platforma):
    try:
        driver.get(url)

        # olx
        if platforma == "OLX":
            try:
                WebDriverWait(driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="ad-price-container"]')),
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-cy="500-page"]'))
                    )
                )
            except:
                pass

            soup = BeautifulSoup(driver.page_source, 'lxml')

            if soup.find('p', {'data-cy': '500-page'}):
                print(f"[Inactiv - OLX] Pagina 500: {url}")
                return None

            pret_element = soup.find(attrs={'data-testid': 'ad-price-container'})

        # imobiliare.ro
        elif platforma == "imobiliare.ro":
            time.sleep(2)

            # caz 1: anuntul a fost scos de tot - URL-ul redirecteaza catre alta pagina
            if driver.current_url != url:
                print(f"[Inactiv - imobiliare.ro] Redirect: {url}")
                return None

            try:
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="price"]'))
                )
            except:
                pass

            soup = BeautifulSoup(driver.page_source, 'lxml')

            # caz 2: anuntul e inchis (nu mai primeste cereri) - URL-ul ramane acelasi
            # dar pe pagina apare un banner role="alert" cu textul:
            # "In acest moment, nu se primesc cereri pentru aceasta proprietate..."
            alert = soup.find('div', {'role': 'alert'})
            if alert and "nu se primesc cereri" in alert.get_text().lower():
                print(f"[Inactiv - imobiliare.ro] Banner 'nu se primesc cereri': {url}")
                return None

            pret_element = soup.find(attrs={'aria-label': 'price'})

        # storia
        elif platforma == "Storia":
            try:
                WebDriverWait(driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'strong[data-cy="adPageHeaderPrice"]')),
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-cy="redirectedFromInactiveAd"]'))
                    )
                )
            except:
                pass

            soup = BeautifulSoup(driver.page_source, 'lxml')

            if soup.find(attrs={'data-cy': 'redirectedFromInactiveAd'}):
                print(f"[Inactiv - Storia] Banner: {url}")
                return None

            pret_element = soup.find('strong', {'data-cy': 'adPageHeaderPrice'})

        # citesc pretul
        if pret_element:
            pret = clean_price(pret_element.get_text(strip=True))
            if pret:
                return pret

        print(f"[Activ fara pret clar] {url}")
        return 0

    except Exception as e:
        print(f"[Eroare] {platforma} | {url} | {e}")
        return None
