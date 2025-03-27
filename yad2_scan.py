import os
import time
import random
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys
print(sys.executable)

CSV_FILE = "vehicles.csv"
import os

# בדיקת URL מותאם אישית
if os.path.exists("custom_url.txt"):
    with open("custom_url.txt", "r") as f:
        base_url = f.read().strip()
else:
    base_url = "https://www.yad2.co.il/vehicles/cars?manufacturer=19,21,48&year=2015-2021&price=24000-44000&km=20000-110000&engineval=1200--1&hand=0-2&topArea=2,19&area=12,52,99&gearBox=102&priceOnly=1&ownerID=1"

# המשך הסקריפט כרגיל (למשל, עם Selenium או BeautifulSoup)
# scraper = Yad2VehicleScraper(base_url)
# scraper.scrape(max_pages=5)


class Yad2VehicleScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.data = []
        self.driver = None

    def init_driver(self):
        options = Options()
        # הפעלת חלון דפדפן רגיל (ללא headless) כדי להמעיט בסיכון לחסימה
        # ניתן להפעיל headless במידת הצורך, אך יש לקחת בחשבון חסימות
        # options.headless = True
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
        options.add_argument("--disable-blink-features=AutomationControlled")
        self.driver = webdriver.Chrome(options=options)

    def build_url(self, page):
        return f"{self.base_url}&page={page}"

    def fetch_page(self, url):
        try:
            self.driver.get(url)
        except Exception as e:
            print(f"תקלה בטעינת הדף {url}: {e}")
            return None

        # השהיה ראשונית של 10 שניות כדי לחקות התנהגות אנושית
        time.sleep(10 + random.uniform(0, 5))

        # בדיקת הודעת חשד בבוטים
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@class='content']//h1[@class='title' and text()='?Are you for real']")
                )
            )
            print(f"הדף {url} חושד בבוטים (זוהתה הודעת '?Are you for real'). מפסיק את התוכנית.")
            self.driver.quit()
            exit()
        except:
            pass

        # המתנה עד שתג ה-<dl> בתוך הסקציה "פרטים נוספים" יופיע
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//section[h2[text()='פרטים נוספים']]//dl"))
            )
        except Exception as e:
            print(f"תקלה בטעינת הדף {url}: {e}")

        return self.driver.page_source

    def parse_listing(self, soup):
        ads = soup.find_all('a', class_='feed-item-base_itemLink__wBfEL')
        listings = []
        for ad in ads:
            # דילוג על מודעות של סוכנויות (אם קיימות)
            if ad.find('span', class_='commercial-item-left-side_agencyName__psfbp'):
                continue

            href = ad.get('href')
            if not href:
                continue
            ad_url = f"https://www.yad2.co.il/vehicles/{href.split('?')[0]}"

            title_tag = ad.find('h2', {'data-nagish': 'feed-item-section-title'})
            make_model = title_tag.find('span',
                                        class_='feed-item-info_heading__k5pVC').text.strip() if title_tag else "לא נמצא"
            details = title_tag.find('span',
                                     class_='feed-item-info_marketingText__eNE4R').text.strip() if title_tag else "לא נמצא"

            year_hand_tag = ad.find('span', class_='feed-item-info_yearAndHandBox___JLbc')
            year_hand = year_hand_tag.text.strip() if year_hand_tag else "לא נמצא"

            price_tag = ad.find('span', class_='price_price__xQt90')
            price = price_tag.text.strip() if price_tag else "לא צוין מחיר"

            listings.append({
                'make_model': make_model,
                'details': details,
                'year_hand': year_hand,
                'price': price,
                'link': ad_url
            })
        return listings

    def parse_ad_details(self, ad_url):
        html_content = self.fetch_page(ad_url)
        if not html_content:
            print(f"לא נטען HTML עבור {ad_url}")
            return {}
        soup = BeautifulSoup(html_content, 'html.parser')

        # חיפוש הסקציה עם הכותרת "פרטים נוספים"
        details_section = None
        for section in soup.find_all('section'):
            h2 = section.find('h2', class_='section-heading_sectionHeading__I5vmn')
            if h2 and h2.text.strip() == "פרטים נוספים":
                details_section = section
                break

        if not details_section:
            print(f"לא נמצאה סקציית 'פרטים נוספים' ב-{ad_url}")
            return {}

        dl = details_section.find('dl')
        if not dl:
            print(f"לא נמצא תג <dl> ב-{ad_url}")
            return {}

        details = {}
        labels = dl.find_all('dd', class_='item-detail_label__FnhAu')
        values = dl.find_all('dt', class_='item-detail_value__QHPml')
        for label, value in zip(labels, values):
            details[label.text.strip()] = value.text.strip()

        # הוספת תאריך הפרסום
        published_date_tag = soup.find('span', class_='report-ad_createdAt__MhAb0')
        published_date = published_date_tag.text.replace('פורסם ב', '').strip() if published_date_tag else "לא נמצא"

        return {
            'km': int(details.get('קילומטראז׳', '0').replace(',', '')) if details.get('קילומטראז׳') else None,
            'color': details.get('צבע'),
            'current_ownership': details.get('בעלות נוכחית'),
            'previous_ownership': details.get('בעלות קודמת'),
            'horsepower': int(details.get('כוח סוס', '0')) if details.get('כוח סוס') else None,
            'engine_capacity': int(details.get('נפח מנוע', '0').replace(',', '')) if details.get('נפח מנוע') else None,
            'fuel_efficiency': float(details.get('צריכת דלק משולבת', '0')) if details.get('צריכת דלק משולבת') else None,
            'published_date': published_date
        }

    def update_csv(self):
        """טוען את קובץ ה-CSV הקיים (אם קיים) ומוסיף את הנתונים החדשים תוך בדיקת כפילויות לפי link."""
        if os.path.exists(CSV_FILE):
            existing_df = pd.read_csv(CSV_FILE)
        else:
            existing_df = pd.DataFrame(columns=["make_model", "details", "year_hand", "price", "link",
                                                "km", "color", "current_ownership", "previous_ownership",
                                                "horsepower", "engine_capacity", "fuel_efficiency", "published_date"])
        new_df = pd.DataFrame(self.data)
        # איחוד הנתונים והסרת כפילויות לפי link
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.drop_duplicates(subset="link", keep="last", inplace=True)
        combined_df.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
        print(f"עודכן קובץ CSV עם {len(combined_df)} מודעות (כולל עדכונים).")

    def scrape(self, max_pages=5):
        self.init_driver()
        page = 1
        while page <= max_pages:
            url = self.build_url(page)
            print(f"מבצע טעינה של הדף {page}: {url}")
            html_content = self.fetch_page(url)
            if not html_content:
                print(f"לא נטען תוכן מהדף {page}.")
                break

            soup = BeautifulSoup(html_content, 'html.parser')
            listings = self.parse_listing(soup)
            if not listings:
                print(f"לא נמצאו מודעות בדף {page}")
                break

            for listing in listings:
                print(f"מבצע שליפת פרטים עבור: {listing['link']}")
                details = self.parse_ad_details(listing['link'])
                combined = {**listing, **details}
                self.data.append(combined)
                # השהיה אקראית בין המודעות
                time.sleep(random.uniform(5, 10))

            print(f"דף {page}: נאספו {len(listings)} מודעות")
            page += 1
            time.sleep(random.uniform(5, 10))
        self.driver.quit()
        self.update_csv()


if __name__ == "__main__":
    scraper = Yad2VehicleScraper(base_url)
    scraper.scrape(max_pages=5)
