import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import urllib.parse

def scrape_jugend_forscht():
    base_url = "https://www.jugend-forscht.de"
    search_url = f"{base_url}/projektdatenbank.html"
    
    # Fachgebiete laut HTML: 
    # 2 = Mathe/Informatik, 3 = Physik, 5 = Geo/Raum, 6 = Technik
    target_specialisms = {
        "3": "Physik",
        "6": "Technik",
        "2": "Mathematik/Informatik",
        "5": "Geo- und Raumwissenschaften"
    }
    
    # Die letzten 5 Jahre (2021 bis 2025)
    target_years =["2025", "2024", "2023", "2022", "2021"]
    
    # Session starten, um Cookies und Tokens über Anfragen hinweg zu behalten
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    })
    
    all_projects =[]
    
    for year in target_years:
        for spec_id, spec_name in target_specialisms.items():
            print(f"\n-> Starte Scraping für Jahr: {year}, Fachgebiet: {spec_name}")
            
            # 1. Initiale Suchseite aufrufen um die Formular-Tokens (cHash etc.) zu erhalten
            response = session.get(search_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            form = soup.find('form', {'name': 'projectFilter'})
            if not form:
                print("FEHLER: Suchformular auf der Startseite nicht gefunden.")
                continue
                
            # Formularziel-URL (enthält den wichtigen cHash-Parameter)
            action_url = form.get('action')
            if not action_url.startswith("http"):
                action_url = urllib.parse.urljoin(base_url, action_url)
                
            # Alle Hidden-Inputs (Sicherheitstokens) einsammeln
            form_data = {}
            for hidden in form.find_all('input', type='hidden'):
                name = hidden.get('name')
                value = hidden.get('value', '')
                if name:
                    form_data[name] = value
                    
            # 2. Unsere gewünschten Filter-Optionen überschreiben
            form_data['tx_smsjufoprojects_smsjufprojectdb[filter][year]'] = year
            form_data['tx_smsjufoprojects_smsjufprojectdb[filter][area]'] = "0"
            form_data['tx_smsjufoprojects_smsjufprojectdb[filter][specialism]'] = spec_id
            form_data['tx_smsjufoprojects_smsjufprojectdb[filter][awardcategory]'] = "0"
            form_data['tx_smsjufoprojects_smsjufprojectdb[filter][searchWord]'] = ""
            
            # 3. Formular absenden (POST-Request)
            post_resp = session.post(action_url, data=form_data)
            current_soup = BeautifulSoup(post_resp.text, 'html.parser')
            
            page_count = 1
            while True:
                print(f"   Lese Seite {page_count}...")
                
                # Projekte auf der aktuellen Seite extrahieren
                project_divs = current_soup.find_all('div', class_='project')
                
                for pdiv in project_divs:
                    info_div = pdiv.find('div', class_='info')
                    if not info_div:
                        continue
                        
                    # Metadaten aus der Liste lesen (z.B. "2025 | Arbeitswelt | Thüringen")
                    meta_text = ""
                    for child in info_div.children:
                        if child.name == 'h2': # Stop vor dem Titel
                            break
                        if isinstance(child, str) and child.strip():
                            meta_text += child.strip()
                    
                    # Titel und Detail-Link
                    h2 = info_div.find('h2')
                    title = h2.text.strip() if h2 else ""
                    a_tag = h2.find('a') if h2 else None
                    link = ""
                    if a_tag and a_tag.get('href'):
                        link = urllib.parse.urljoin(base_url, a_tag.get('href'))
                        
                    # Teilnehmende (stehen im Suchergebnis meist direkt unter dem Titel im <p>-Tag)
                    p_tag = info_div.find('p')
                    participants = p_tag.text.strip() if p_tag else ""
                    
                    # 4. Detailseite scrapen für die Beschreibung und Platzierungen/Preise
                    description_and_prizes = ""
                    if link:
                        try:
                            # Kurze Pause, um den Server nicht zu blockieren (Fair Use)
                            time.sleep(0.5) 
                            detail_resp = session.get(link)
                            detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                            
                            # Typischerweise liegt der Content im Container mit der ID "content"
                            content_div = detail_soup.find('div', id='content')
                            if content_div:
                                # Da sich Preise und Beschreibungen oft in verschiedenen Tags (p, li, h3) befinden,
                                # holen wir zur Sicherheit den gesamten Text-Inhalt dieser Container:
                                text_blocks =[]
                                for tag in content_div.find_all(['p', 'h3', 'li']):
                                    text = tag.get_text(strip=True)
                                    if text and text not in text_blocks:
                                        text_blocks.append(text)
                                description_and_prizes = "\n".join(text_blocks)
                        except Exception as e:
                            print(f"Fehler beim Aufruf der Detailseite {link}: {e}")
                            
                    all_projects.append({
                        "Jahr": year,
                        "Fachgebiet": spec_name,
                        "Meta_Infos": meta_text,
                        "Titel": title,
                        "Teilnehmende": participants,
                        "Beschreibung_und_Preise": description_and_prizes,
                        "Link": link
                    })
                    
                # 5. Nach Paginierung "Nächste" schauen
                next_li = current_soup.find('li', class_='next')
                if next_li and next_li.find('a'):
                    next_url = next_li.find('a').get('href')
                    next_url = urllib.parse.urljoin(base_url, next_url)
                    
                    time.sleep(1) # Kurze Pause vor Seitenwechsel
                    next_resp = session.get(next_url)
                    current_soup = BeautifulSoup(next_resp.text, 'html.parser')
                    page_count += 1
                else:
                    break # Keine weiteren Seiten für dieses Fachgebiet/Jahr

    # 6. Als Pandas DataFrame in CSV und Excel speichern
    print("\nScraping abgeschlossen! Exportiere Daten...")
    df = pd.DataFrame(all_projects)
    
    # Optional: Die Meta-Infos (Jahr | Fachgebiet | Bundesland) in einzelne Spalten splitten
    if not df.empty:
        try:
            meta_split = df['Meta_Infos'].str.split('|', expand=True)
            df['Jahr_Meta'] = meta_split[0].str.strip()
            df['Fachgebiet_Meta'] = meta_split[1].str.strip()
            df['Bundesland'] = meta_split[2].str.strip()
        except:
            pass # Falls das Format irgendwo abweicht, ignorieren wir das Splitting

    df.to_csv("jugend_forscht_projekte.csv", index=False, encoding="utf-8-sig")
    df.to_excel("jugend_forscht_projekte.xlsx", index=False)
    print("Fertig! Die Dateien 'jugend_forscht_projekte.csv' und '.xlsx' wurden erstellt.")

if __name__ == "__main__":
    scrape_jugend_forscht()