"""
Estrattore AVANZATO di rifugi e bivacchi da escursionismo.it
Versione per 30 rifugi per ogni regione italiana
Utilizzo: python RifugiScraper.py
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import re
from urllib.parse import urljoin, urlparse
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from collections import defaultdict

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class RifugioInfo:
    """Struttura dati per le informazioni del rifugio"""
    url: str
    nome: str
    quota_altitudine: str
    luogo: str
    tipo: str
    proprietà: str
    nazione: str
    regione: str
    valle: str
    area_montuosa: str
    periodo_apertura: str
    posti_letto: str
    coordinate_lat: str
    coordinate_lon: str
    servizi: List[str]
    accesso: Dict[str, str]
    telefono: str
    email: str
    sito_web: str
    immagine_url: str
    descrizione: str
    gestore: str
    altre_dotazioni: str

class RifugiScraperRegioni:
    def __init__(self):
        self.base_url = "https://www.escursionismo.it"
        self.rifugi_url = "https://www.escursionismo.it/rifugi-bivacchi/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.rifugi_data = []
        self.processed_urls = set()
        
        # Contatore per regione
        self.rifugi_per_regione = defaultdict(int)
        self.MAX_RIFUGI_PER_REGIONE = 30
        
        # Regioni italiane
        self.regioni_italiane = {
            'piemonte', 'valle d\'aosta', 'aosta', 'lombardia', 'trentino', 'alto adige', 
            'trentino-alto adige', 'veneto', 'friuli', 'friuli-venezia giulia', 'liguria', 
            'emilia-romagna', 'emilia', 'romagna', 'toscana', 'umbria', 'marche', 
            'lazio', 'abruzzo', 'molise', 'campania', 'puglia', 'basilicata', 
            'calabria', 'sicilia', 'sardegna'
        }
        
        # Mapping per i servizi
        self.servizi_mapping = {
            'riscaldamento': '🔥 Riscaldamento',
            'wc': '🚽 WC',
            'acqua_fredda': '❄️ Acqua fredda',
            'acqua_calda': '🔥 Acqua calda',
            'docce': '🚿 Docce',
            'ristorante': '🍽️ Ristorante',
            'cucina': '👨‍🍳 Possibilità di cucinare',
            'luce': '💡 Luce elettrica',
            'carte_credito': '💳 Carte di credito',
            'sconti_cai': '🎒 Sconti associati CAI'
        }

    def get_page(self, url, retries=3):
        """Ottiene il contenuto di una pagina con retry logic"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Tentativo {attempt + 1} fallito per {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"Impossibile ottenere {url} dopo {retries} tentativi")
                    return None

    def is_rifugio_page(self, url):
        """Verifica se l'URL è una pagina di un singolo rifugio"""
        if any(keyword in url.lower() for keyword in ['page/', '?page=', 'rifugi-bivacchi/?', 'rifugi-bivacchi/#']):
            return False
        
        if 'rifugi-bivacchi/' in url and url != self.rifugi_url:
            after_rifugi = url.split('rifugi-bivacchi/')[-1].strip('/')
            if after_rifugi and len(after_rifugi) > 2:
                return True
        return False

    def normalize_regione(self, regione_text):
        """Normalizza il nome della regione"""
        if not regione_text:
            return ""
        
        regione_lower = regione_text.lower().strip()
        
        # Mapping specifici per normalizzare le varianti
        regione_mapping = {
            'valle d\'aosta': 'valle d\'aosta',
            'aosta': 'valle d\'aosta',
            'trentino': 'trentino-alto adige',
            'alto adige': 'trentino-alto adige',
            'trentino-alto adige': 'trentino-alto adige',
            'friuli': 'friuli-venezia giulia',
            'friuli-venezia giulia': 'friuli-venezia giulia',
            'emilia': 'emilia-romagna',
            'romagna': 'emilia-romagna',
            'emilia-romagna': 'emilia-romagna'
        }
        
        # Cerca corrispondenza esatta
        if regione_lower in regione_mapping:
            return regione_mapping[regione_lower]
        
        # Cerca corrispondenza parziale
        for regione_std in self.regioni_italiane:
            if regione_std in regione_lower or regione_lower in regione_std:
                return regione_std
        
        return regione_lower if regione_lower in self.regioni_italiane else ""

    def is_regione_italiana(self, regione):
        """Verifica se la regione è italiana"""
        if not regione:
            return False
        
        regione_normalized = self.normalize_regione(regione)
        return regione_normalized in self.regioni_italiane

    def regione_needs_more_rifugi(self, regione):
        """Verifica se la regione ha bisogno di più rifugi"""
        if not regione:
            return False
        
        regione_normalized = self.normalize_regione(regione)
        if not regione_normalized:
            return False
        
        current_count = self.rifugi_per_regione[regione_normalized]
        return current_count < self.MAX_RIFUGI_PER_REGIONE

    def extract_rifugio_urls_from_page(self, page_url):
        """Estrae gli URL dei rifugi da una pagina di lista"""
        print(f"\n🔍 Analizzando pagina: {page_url}")
        
        response = self.get_page(page_url)
        if not response:
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        urls = []
        
        # Cerca tutti i link nella pagina
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link['href']
            full_url = urljoin(self.base_url, href)
            
            if self.is_rifugio_page(full_url) and full_url not in self.processed_urls:
                urls.append(full_url)
                self.processed_urls.add(full_url)
                
                link_text = link.get_text().strip()
                print(f"    ✅ TROVATO: {link_text[:50]} -> {href}")
        
        return urls

    def extract_rifugio_urls(self, max_pages=50):
        """Estrae tutti gli URL dei rifugi dalla pagina principale e successive"""
        logger.info("Estrazione URL rifugi...")
        
        all_urls = []
        
        # Prima pagina
        urls_page1 = self.extract_rifugio_urls_from_page(self.rifugi_url)
        all_urls.extend(urls_page1)
        
        # Pagine successive
        for page_num in range(2, max_pages + 1):
            page_url = f"{self.rifugi_url}page/{page_num}/"
            urls_page = self.extract_rifugio_urls_from_page(page_url)
            all_urls.extend(urls_page)
            
            if not urls_page:
                break
            
            time.sleep(1)
        
        print(f"\n📊 TOTALE URL RIFUGI TROVATI: {len(all_urls)}")
        return all_urls

    def extract_table_info(self, soup):
        """Estrae informazioni dalla tabella informativa del rifugio"""
        info_data = {}
        
        # Cerca diverse strutture di tabelle possibili
        table_selectors = [
            'table.info-table',
            'table',
            '.info-table',
            '.rifugio-info',
            '.dettagli-rifugio'
        ]
        
        table = None
        for selector in table_selectors:
            table = soup.select_one(selector)
            if table:
                break
        
        if table:
            # Estrae dati dalla tabella
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text().strip().lower()
                    value = cells[1].get_text().strip()
                    
                    # Normalizza le chiavi
                    if 'proprietà' in key or 'proprieta' in key:
                        info_data['proprietà'] = value
                    elif 'nazione' in key:
                        info_data['nazione'] = value
                    elif 'regione' in key:
                        info_data['regione'] = value
                    elif 'quota' in key or 'altitudine' in key:
                        info_data['quota_altitudine'] = value
                    elif 'periodo' in key and 'apertura' in key:
                        info_data['periodo_apertura'] = value
                    elif 'valle' in key:
                        info_data['valle'] = value
                    elif 'area' in key and 'montuosa' in key:
                        info_data['area_montuosa'] = value
                    elif 'posti' in key and 'letto' in key:
                        info_data['posti_letto'] = value
                    elif 'coordinate' in key:
                        info_data['coordinate'] = value
                    elif 'dotazioni' in key:
                        info_data['altre_dotazioni'] = value
        
        return info_data

    def extract_coordinates(self, soup, page_text):
        """Estrae le coordinate del rifugio"""
        lat, lon = "", ""
        
        # Pattern per coordinate
        coord_patterns = [
            r'Lat[:\s]*([0-9.]+)[,\s]*Long?[:\s]*([0-9.]+)',
            r'([0-9]{2}\.[0-9]+)[,\s]+([0-9]{1,2}\.[0-9]+)',
            r'Coordinate[:\s]*([0-9.]+)[,\s]+([0-9.]+)',
        ]
        
        for pattern in coord_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                lat, lon = match.groups()
                break
        
        # Cerca anche nei tag script per mappe
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                coord_match = re.search(r'lat[:\s]*([0-9.]+)[,\s]*lng[:\s]*([0-9.]+)', script.string, re.IGNORECASE)
                if coord_match:
                    lat, lon = coord_match.groups()
                    break
        
        return lat, lon

    def extract_servizi(self, soup):
        """Estrae i servizi disponibili nel rifugio"""
        servizi = []
        
        # Cerca nella sezione servizi
        servizi_section = soup.find('div', class_='servizi') or soup.find('section', class_='servizi')
        
        if servizi_section:
            # Cerca icone o testi dei servizi
            for servizio_key, servizio_nome in self.servizi_mapping.items():
                if servizio_key.replace('_', ' ') in servizi_section.get_text().lower():
                    servizi.append(servizio_nome)
        
        # Cerca anche nel testo generale della pagina
        page_text = soup.get_text().lower()
        for servizio_key, servizio_nome in self.servizi_mapping.items():
            search_terms = servizio_key.replace('_', ' ')
            if search_terms in page_text and servizio_nome not in servizi:
                servizi.append(servizio_nome)
        
        return servizi

    def extract_accesso_info(self, soup):
        """Estrae informazioni sull'accesso al rifugio"""
        accesso = {
            'localita_partenza': '',
            'dislivello': '',
            'tempo_percorrenza': '',
            'difficolta': '',
            'descrizione': ''
        }
        
        # Cerca sezione accesso
        accesso_section = soup.find('div', class_='accesso') or soup.find('section', class_='accesso')
        
        if accesso_section:
            accesso_text = accesso_section.get_text()
        else:
            # Cerca nel testo generale
            accesso_text = soup.get_text()
        
        # Pattern per le informazioni di accesso
        patterns = {
            'localita_partenza': r'Località di partenza[:\s]*([^\n]+)',
            'dislivello': r'Dislivello[:\s]*([0-9]+\s*m)',
            'tempo_percorrenza': r'Tempo di percorrenza[:\s]*([0-9,\s]+h)',
            'difficolta': r'Difficoltà[:\s]*([EF]+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, accesso_text, re.IGNORECASE)
            if match:
                accesso[key] = match.group(1).strip()
        
        # Descrizione dell'accesso
        if accesso_section:
            accesso['descrizione'] = accesso_section.get_text().strip()[:500]
        
        return accesso
    
    def extract_contacts_improved(self, soup, page_text):
        """Estrae contatti migliorati (telefono, email, sito web)"""
        telefono = ""
        email = ""
        sito_web = ""
        
        # TELEFONO - Pattern più specifici ed esclusioni
        phone_patterns = [
            r'Tel\.?\s*:?\s*(\+?[\d\s\-\.\(\)]{8,15})',
            r'Telefono\s*:?\s*(\+?[\d\s\-\.\(\)]{8,15})',
            r'Phone\s*:?\s*(\+?[\d\s\-\.\(\)]{8,15})',
            r'Cellulare\s*:?\s*(\+?[\d\s\-\.\(\)]{8,15})',
            r'Mobile\s*:?\s*(\+?[\d\s\-\.\(\)]{8,15})'
        ]
        
        for pattern in phone_patterns:
            matches = re.finditer(pattern, page_text, re.IGNORECASE)
            for match in matches:
                potential_phone = match.group(1).strip()
                # Esclude coordinate (che hanno punti decimali)
                if '.' not in potential_phone and len(potential_phone) >= 8:
                    # Rimuove spazi e caratteri non numerici per validazione
                    clean_phone = re.sub(r'[^\d]', '', potential_phone)
                    if 8 <= len(clean_phone) <= 15:  # Lunghezza ragionevole per telefono
                        telefono = potential_phone
                        break
            if telefono:
                break
        
        # Se non trova con pattern specifici, cerca in modo più generale ma con esclusioni
        if not telefono:
            general_phone_pattern = r'(\+?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{0,4})'
            matches = re.finditer(general_phone_pattern, page_text)
            for match in matches:
                potential_phone = match.group(1)
                # Esclude se sembra una coordinata (contiene punto decimale nel formato coordinate)
                if not re.match(r'\d{2}\.\d+', potential_phone):
                    clean_phone = re.sub(r'[^\d]', '', potential_phone)
                    if 8 <= len(clean_phone) <= 15:
                        telefono = potential_phone
                        break
        
        # EMAIL
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, page_text)
        if email_match:
            email = email_match.group(0)
        
        # SITO WEB - cerca link esterni
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('http') and 'escursionismo.it' not in href:
                # Verifica se sembra un sito web del rifugio
                link_text = link.get_text().lower()
                if any(word in link_text for word in ['sito', 'website', 'web', 'homepage']) or \
                   any(word in href.lower() for word in ['refugio', 'rifugi', 'huette', 'cabane']):
                    sito_web = href
                    break
        
        return telefono, email, sito_web

    def extract_image_url(self, soup):
        """Estrae l'URL dell'immagine principale del rifugio"""
        img_selectors = [
            # Immagine principale del rifugio
            '.rifugio-image img',
            '.main-image img', 
            '.hero-image img',
            '.rifugio-photo img',
            
            # Contenitori di immagini
            '.image-container img',
            '.photo-container img',
            '.gallery img:first-child',
            
            # Immagini con attributi specifici
            'img[alt*="rifugio" i]',
            'img[alt*="bivacco" i]',
            'img[alt*="cabana" i]',
            'img[alt*="hutte" i]',
            'img[src*="rifugi" i]',
            'img[src*="bivac" i]',
            
            # Immagini nelle prime sezioni della pagina
            'article img:first-of-type',
            '.content img:first-of-type',
            'main img:first-of-type',
            
            # Fallback generico
            'img[src*="upload"]',
            'img[src*="images"]'
        ]
            
        for selector in img_selectors:
            img = soup.select_one(selector)
            if img and img.get('src'):
                src = img['src']
                # Verifica che non sia un'icona o immagine troppo piccola
                if not any(skip in src.lower() for skip in ['icon', 'logo', 'favicon', 'sprite']):
                    full_url = urljoin(self.base_url, src)
                    return full_url
        
        # Approccio alternativo: cerca immagini per dimensione o contesto
        all_images = soup.find_all('img', src=True)
        
        for i, img in enumerate(all_images):
            src = img['src']
            alt = img.get('alt', '').lower()
            
            # Scoring system per scegliere l'immagine migliore
            score = 0
            
            # Bonus per parole chiave nell'alt text
            if any(word in alt for word in ['rifugio', 'bivacco', 'mountain', 'mont', 'alp', 'cabana', 'hutte']):
                score += 10
                
            # Bonus per path dell'immagine
            if any(word in src.lower() for word in ['rifugi', 'bivac', 'mountain', 'alp', 'photo', 'image']):
                score += 5
                
            # Malus per icone e loghi
            if any(word in src.lower() for word in ['icon', 'logo', 'favicon', 'sprite', 'button']):
                score -= 10
                
            # Malus per immagini molto piccole (probabilmente icone)
            width = img.get('width')
            height = img.get('height')
            if width and height:
                try:
                    w, h = int(width), int(height)
                    if w < 100 or h < 100:
                        score -= 5
                    elif w > 300 and h > 200:
                        score += 3
                except:
                    pass
            
            if score >= 5:  # Soglia minima
                full_url = urljoin(self.base_url, src)
                return full_url
        
        return ""

    def extract_rifugio_info(self, url):
        """Estrae informazioni complete di un singolo rifugio"""
        print(f"\n🏔️  ESTRAZIONE COMPLETA DA: {url}")
        
        response = self.get_page(url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        page_text = soup.get_text()
        
        # Inizializza struttura dati
        rifugio_info = RifugioInfo(
            url=url,
            nome="",
            quota_altitudine="",
            luogo="",
            tipo="",
            proprietà="",
            nazione="",
            regione="",
            valle="",
            area_montuosa="",
            periodo_apertura="",
            posti_letto="",
            coordinate_lat="",
            coordinate_lon="",
            servizi=[],
            accesso={},
            telefono="",
            email="",
            sito_web="",
            immagine_url="",
            descrizione="",
            gestore="",
            altre_dotazioni=""
        )
        
        # ESTRAZIONE NOME
        nome_candidates = []
        
        if soup.title:
            title_text = soup.title.text.strip()
            clean_title = re.sub(r'\s*-\s*escursionismo\.it.*', '', title_text, flags=re.IGNORECASE)
            if clean_title:
                nome_candidates.append(clean_title)
        
        for tag in ['h1', 'h2']:
            for header in soup.find_all(tag):
                text = header.get_text().strip()
                if text and len(text) > 3:
                    nome_candidates.append(text)
        
        # Seleziona il nome migliore
        for candidate in nome_candidates:
            clean_name = re.sub(r'\s*-\s*escursionismo\.it.*', '', candidate, flags=re.IGNORECASE)
            clean_name = clean_name.strip()
            
            if clean_name and len(clean_name) >= 3:
                generic_terms = ['cerca', 'escursion', 'homepage', 'rifugi e bivacchi']
                if not any(term.lower() in clean_name.lower() for term in generic_terms):
                    rifugio_info.nome = clean_name
                    break
        
        if not rifugio_info.nome:
            rifugio_info.nome = url.split('/')[-1].replace('-', ' ').title()
        
        # ESTRAZIONE INFORMAZIONI DALLA TABELLA
        table_info = self.extract_table_info(soup)
        
        if table_info:
            rifugio_info.proprietà = table_info.get('proprietà', '')
            rifugio_info.nazione = table_info.get('nazione', '')
            rifugio_info.regione = table_info.get('regione', '')
            rifugio_info.quota_altitudine = table_info.get('quota_altitudine', '')
            rifugio_info.periodo_apertura = table_info.get('periodo_apertura', '')
            rifugio_info.valle = table_info.get('valle', '')
            rifugio_info.area_montuosa = table_info.get('area_montuosa', '')
            rifugio_info.posti_letto = table_info.get('posti_letto', '')
            rifugio_info.altre_dotazioni = table_info.get('altre_dotazioni', '')
        
        # ESTRAZIONE REGIONE DAL TESTO SE NON TROVATA NELLA TABELLA
        if not rifugio_info.regione:
            # Cerca nel luogo o nel testo della pagina
            luogo_text = page_text.lower()
            for regione in self.regioni_italiane:
                if regione in luogo_text:
                    rifugio_info.regione = regione.title()
                    break
        
        # TIPO (Rifugio/Bivacco)
        page_text_lower = page_text.lower()
        url_lower = url.lower()
        nome_lower = rifugio_info.nome.lower()
        
        if any(word in page_text_lower or word in url_lower or word in nome_lower 
               for word in ['bivacco', 'bivac', 'biwak']):
            rifugio_info.tipo = 'Bivacco'
        elif any(word in page_text_lower or word in url_lower or word in nome_lower 
                 for word in ['rifugio', 'hütte', 'capanna', 'baita', 'cabane']):
            rifugio_info.tipo = 'Rifugio'
        else:
            rifugio_info.tipo = 'Non specificato'
        
        # QUOTA (se non trovata nella tabella)
        if not rifugio_info.quota_altitudine:
            quota_text = rifugio_info.nome + ' ' + page_text
            quota_patterns = [
                r'(\d{3,4})\s*m(?:etri|t)?(?:\s|$|\.|,)',
                r'(\d{3,4})\s*s\.l\.m',
                r'(\d{3,4})\s*mslm'
            ]
            
            for pattern in quota_patterns:
                match = re.search(pattern, quota_text, re.IGNORECASE)
                if match:
                    quota = match.group(1)
                    if 200 <= int(quota) <= 5000:
                        rifugio_info.quota_altitudine = f"{quota}m"
                        break
        
        # COORDINATE
        lat, lon = self.extract_coordinates(soup, page_text)
        rifugio_info.coordinate_lat = lat
        rifugio_info.coordinate_lon = lon
        
        # SERVIZI
        rifugio_info.servizi = self.extract_servizi(soup)
        
        # ACCESSO
        rifugio_info.accesso = self.extract_accesso_info(soup)
        
        # CONTATTI
        telefono, email, sito_web = self.extract_contacts_improved(soup, page_text)
        rifugio_info.telefono = telefono
        rifugio_info.email = email
        rifugio_info.sito_web = sito_web
        
        # IMMAGINE
        rifugio_info.immagine_url = self.extract_image_url(soup)
        
        # LUOGO (combinazione di informazioni geografiche)
        luogo_parts = []
        if rifugio_info.valle:
            luogo_parts.append(rifugio_info.valle)
        if rifugio_info.area_montuosa:
            luogo_parts.append(rifugio_info.area_montuosa)
        if rifugio_info.regione:
            luogo_parts.append(rifugio_info.regione)
        if rifugio_info.nazione:
            luogo_parts.append(rifugio_info.nazione)
        
        rifugio_info.luogo = ", ".join(luogo_parts)
        
        # VERIFICA SE È ITALIANO E SE LA REGIONE HA BISOGNO DI PIÙ RIFUGI
        if rifugio_info.nazione.lower() != 'italia' and not self.is_regione_italiana(rifugio_info.regione):
            print(f"❌ SCARTATO: Non italiano - {rifugio_info.nome}")
            return None
        
        # Normalizza la regione
        regione_normalized = self.normalize_regione(rifugio_info.regione)
        if not regione_normalized:
            print(f"❌ SCARTATO: Regione non riconosciuta - {rifugio_info.nome} ({rifugio_info.regione})")
            return None
        
        # Verifica se la regione ha già abbastanza rifugi
        if not self.regione_needs_more_rifugi(rifugio_info.regione):
            print(f"❌ SCARTATO: {regione_normalized.title()} ha già {self.MAX_RIFUGI_PER_REGIONE} rifugi")
            return None
        
        print(f"✅ ACCETTATO: {rifugio_info.nome}")
        return rifugio_info
        
    def scrape_all_rifugi(self, max_rifugi=100, delay=2):
        """Esegue lo scraping completo di tutti i rifugi"""
        logger.info(f"Inizio scraping di massimo {max_rifugi} rifugi con delay di {delay}s")
        
        # Ottieni tutti gli URL dei rifugi
        rifugi_urls = self.extract_rifugio_urls()
        
        if not rifugi_urls:
            logger.error("Nessun URL di rifugio trovato!")
            return
        
        print(f"\n🎯 INIZIO ESTRAZIONE DETTAGLIATA")
        print(f"📋 {len(rifugi_urls)} rifugi da processare")
        print(f"🎯 Obiettivo: {self.MAX_RIFUGI_PER_REGIONE} rifugi per regione italiana")
        
        processed_count = 0
        
        for i, url in enumerate(rifugi_urls, 1):
            if processed_count >= max_rifugi:
                print(f"\n🛑 LIMITE RAGGIUNTO: {max_rifugi} rifugi processati")
                break
            
            print(f"\n📍 [{i}/{len(rifugi_urls)}] Processando: {url}")
            
            try:
                rifugio_info = self.extract_rifugio_info(url)
                
                if rifugio_info:
                    # Incrementa il contatore per la regione
                    regione_norm = self.normalize_regione(rifugio_info.regione)
                    self.rifugi_per_regione[regione_norm] += 1
                    
                    # Converti in dizionario e aggiungi ai dati
                    rifugio_dict = asdict(rifugio_info)
                    self.rifugi_data.append(rifugio_dict)
                    processed_count += 1
                    
                    print(f"✅ AGGIUNTO: {rifugio_info.nome}")
                    print(f"   📍 {rifugio_info.luogo}")
                    print(f"   🗺️ {regione_norm.title()}: {self.rifugi_per_regione[regione_norm]}/{self.MAX_RIFUGI_PER_REGIONE}")
                    
                    # Mostra statistiche intermedie ogni 10 rifugi
                    if processed_count % 10 == 0:
                        self.print_statistics()
                else:
                    print(f"❌ SCARTATO: {url}")
                
                # Pausa per non sovraccaricare il server
                if delay > 0:
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Errore nell'estrazione di {url}: {e}")
                continue
        
        print(f"\n🏁 SCRAPING COMPLETATO!")
        print(f"📊 Rifugi processati: {processed_count}")
        print(f"📈 Rifugi salvati: {len(self.rifugi_data)}")
        
        # Statistiche finali
        self.print_final_statistics()

    def print_statistics(self):
        """Stampa statistiche intermedie per regione"""
        print(f"\n📊 STATISTICHE CORRENTI:")
        for regione, count in sorted(self.rifugi_per_regione.items()):
            progress = (count / self.MAX_RIFUGI_PER_REGIONE) * 100
            bar = "█" * int(progress / 10) + "░" * (10 - int(progress / 10))
            print(f"   {regione.title():20} [{bar}] {count:2}/{self.MAX_RIFUGI_PER_REGIONE} ({progress:3.0f}%)")

    def print_final_statistics(self):
        """Stampa statistiche finali dettagliate"""
        print(f"\n🎯 STATISTICHE FINALI:")
        print(f"=" * 60)
        
        total_rifugi = len(self.rifugi_data)
        total_regioni = len(self.rifugi_per_regione)
        
        print(f"📊 TOTALI:")
        print(f"   • Rifugi raccolti: {total_rifugi}")
        print(f"   • Regioni coperte: {total_regioni}")
        print(f"   • Media per regione: {total_rifugi/total_regioni:.1f}")
        
        print(f"\n🗺️ DETTAGLIO PER REGIONE:")
        for regione, count in sorted(self.rifugi_per_regione.items()):
            progress = (count / self.MAX_RIFUGI_PER_REGIONE) * 100
            status = "✅ COMPLETO" if count >= self.MAX_RIFUGI_PER_REGIONE else "⏳ In corso"
            print(f"   {regione.title():20} {count:2}/{self.MAX_RIFUGI_PER_REGIONE} rifugi ({progress:3.0f}%) {status}")
        
        # Conteggio per tipologia
        tipi = {}
        for rifugio in self.rifugi_data:
            tipo = rifugio.get('tipo', 'Non specificato')
            tipi[tipo] = tipi.get(tipo, 0) + 1
        
        print(f"\n🏔️ TIPOLOGIE:")
        for tipo, count in sorted(tipi.items()):
            percentage = (count / total_rifugi) * 100
            print(f"   {tipo:15} {count:3} ({percentage:4.1f}%)")
        
        # Conteggio con servizi
        rifugi_con_servizi = sum(1 for r in self.rifugi_data if r.get('servizi'))
        rifugi_con_telefono = sum(1 for r in self.rifugi_data if r.get('telefono'))
        rifugi_con_email = sum(1 for r in self.rifugi_data if r.get('email'))
        rifugi_con_coordinate = sum(1 for r in self.rifugi_data if r.get('coordinate_lat') and r.get('coordinate_lon'))
        
        print(f"\n📋 COMPLETEZZA DATI:")
        print(f"   Con servizi:    {rifugi_con_servizi:3}/{total_rifugi} ({(rifugi_con_servizi/total_rifugi)*100:4.1f}%)")
        print(f"   Con telefono:   {rifugi_con_telefono:3}/{total_rifugi} ({(rifugi_con_telefono/total_rifugi)*100:4.1f}%)")
        print(f"   Con email:      {rifugi_con_email:3}/{total_rifugi} ({(rifugi_con_email/total_rifugi)*100:4.1f}%)")
        print(f"   Con coordinate: {rifugi_con_coordinate:3}/{total_rifugi} ({(rifugi_con_coordinate/total_rifugi)*100:4.1f}%)")

    def save_to_json(self, filename):
        """Salva i dati dei rifugi in formato JSON"""
        try:
            # Crea il metadata del file
            metadata = {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_rifugi": len(self.rifugi_data),
                "total_regioni": len(self.rifugi_per_regione),
                "regioni_statistiche": dict(self.rifugi_per_regione),
                "source": "escursionismo.it",
                "scraper_version": "2.0"
            }
            
            # Struttura finale del JSON
            output_data = {
                "metadata": metadata,
                "rifugi": self.rifugi_data
            }
            
            # Salva il file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Dati salvati in {filename}")
            print(f"💾 File salvato: {filename}")
            
            # Informazioni sul file
            import os
            file_size = os.path.getsize(filename)
            print(f"📁 Dimensione file: {file_size/1024:.1f} KB")
            
        except Exception as e:
            logger.error(f"Errore nel salvataggio: {e}")
            print(f"❌ ERRORE nel salvataggio: {e}")

def main():
    """Funzione principale che esegue lo scraping completo"""
    scraper = RifugiScraperRegioni()

    try:
        # Parametri configurabili
        MAX_RIFUGI = 300  # Aumenta per produzione completa (30 rifugi x ~20 regioni)
        DELAY_SECONDS = 2  # Rispetta il server
        
        print("🚀 AVVIO SCRAPING RIFUGI - VERSIONE COMPLETA")
        print("=" * 60)
        print(f"🎯 Obiettivo: {scraper.MAX_RIFUGI_PER_REGIONE} rifugi per ogni regione italiana")
        print(f"📊 Limite totale: {MAX_RIFUGI} rifugi")
        print(f"⏱️ Pausa tra richieste: {DELAY_SECONDS} secondi")
        print(f"🌐 Fonte: {scraper.base_url}")
        print("=" * 60)
        
        # Esegui lo scraping principale
        scraper.scrape_all_rifugi(max_rifugi=MAX_RIFUGI, delay=DELAY_SECONDS)
        
        # Salva i risultati se ci sono dati
        if scraper.rifugi_data:
            print(f"\n💾 SALVATAGGIO FILES...")
            
            # Salva JSON (formato principale)
            json_filename = "C:/Users/righi/Desktop/Progetti/Web Scraper/Rifugi_bivacchi.json"
            scraper.save_to_json(json_filename)
            
            print(f"\n✅ SUCCESS! Files creati:")
            print(f"    📄 JSON: {json_filename} ({len(scraper.rifugi_data)} rifugi)")
            
            # Mostra un riassunto dei primi 10 rifugi trovati
            print(f"\n📋 ANTEPRIMA PRIMI 10 RIFUGI:")
            print("-" * 60)
            
            for i, rifugio in enumerate(scraper.rifugi_data[:10], 1):
                nome = rifugio.get('nome', 'Nome non disponibile')
                tipo = rifugio.get('tipo', '?')
                luogo = rifugio.get('luogo', 'Luogo non disponibile')
                quota = rifugio.get('quota_altitudine', '?')
                posti = rifugio.get('posti_letto', '?')
                
                print(f"  {i:2}. {nome} ({tipo})")
                print(f"      📍 {luogo}")
                if quota != '?':
                    print(f"      📏 {quota}")
                if posti != '?':
                    print(f"      🛏️ {posti} posti letto")
                
                # Mostra alcuni servizi se disponibili
                servizi = rifugio.get('servizi', [])
                if servizi:
                    servizi_text = ', '.join(servizi[:3])  # Solo primi 3
                    if len(servizi) > 3:
                        servizi_text += f" + altri {len(servizi)-3}"
                    print(f"      🛠️ {servizi_text}")
                print()
            
            if len(scraper.rifugi_data) > 10:
                print(f"      ... e altri {len(scraper.rifugi_data)-10} rifugi")
            
            print(f"\n🎉 SCRAPING COMPLETATO CON SUCCESSO!")
            print(f"📈 Controlla i file per tutti i dettagli")
            
        else:
            print("\n❌ NESSUN DATO RACCOLTO")
            print("💡 Possibili cause:")
            print("   • Problemi di connessione")
            print("   • Struttura del sito cambiata")
            print("   • Filtri troppo restrittivi")

    except KeyboardInterrupt:
        print(f"\n\n⏹️ SCRAPING INTERROTTO DALL'UTENTE")
        if scraper.rifugi_data:
            print(f"💾 Salvataggio dati parziali ({len(scraper.rifugi_data)} rifugi)...")
            try:
                scraper.save_to_json("Rifugi_bivacchi_PARZIALE.json")
                print("✅ Dati parziali salvati")
            except:
                print("❌ Errore nel salvataggio dati parziali")
    
    except Exception as e:
        logger.error(f"Errore critico durante l'estrazione: {e}")
        print(f"\n❌ ERRORE CRITICO: {e}")
        
        # Stampa traceback completo per debug
        import traceback
        print("\n🔍 DETTAGLI ERRORE:")
        traceback.print_exc()
        
        # Prova comunque a salvare eventuali dati raccolti
        if hasattr(scraper, 'rifugi_data') and scraper.rifugi_data:
            print(f"\n💾 Tentativo salvataggio dati parziali ({len(scraper.rifugi_data)} rifugi)...")
            try:
                scraper.save_to_json("Rifugi_bivacchi_ERRORE.json")
                print("✅ Dati parziali salvati nonostante l'errore")
            except Exception as save_error:
                print(f"❌ Impossibile salvare: {save_error}")

if __name__ == "__main__":
    main()