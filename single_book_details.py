from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def scrape_rokomari_book(url):
    # Setup driver options
    options = Options()
    options.add_argument('--headless')  # Comment out to see browser
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    wait = WebDriverWait(driver, 10)

    # Initialize variables
    title = price = summary = 'N/A'
    comments = []
    qas = []

    try:
        # Extract book title
        title = wait.until(EC.presence_of_element_located(
            (By.XPATH, '//*[@id="ts--desktop-details-book-main-info"]/div[1]/h1'))
        ).text.strip()

        # Extract price
        price = wait.until(EC.presence_of_element_located(
            (By.CLASS_NAME, 'sell-price'))
        ).text.strip()

        # Extract summary
        try:
            summary = driver.find_element(
                By.XPATH, '//*[@id="rokomariBody"]/div[3]/div[5]/div[2]/div[1]/div'
            ).text.strip()
        except:
            summary = 'N/A'

        # Scroll to load comments
        height = driver.execute_script('return document.body.scrollHeight')
        for i in range(0, height + 300, 60):
            driver.execute_script(f'window.scrollTo(0,{i});')
            time.sleep(0.5)

        # Extract comments
        for j in range(2, 15):  # Increase range for more comments
            try:
                comment_xpath = f'//*[@id="rokomariBody"]/div[3]/div[6]/div[2]/div/div/div/div[{j}]/div[2]/div/div'
                comment_elements = driver.find_elements(By.XPATH, comment_xpath)
                for c in comment_elements:
                    text = c.text.strip()
                    if text:
                        comments.append(text)
            except:
                continue

        # Extract Questions & Answers (Optional)
        try:
            qa_cards = driver.find_elements(By.ID, 'ts--common-ques-ans-card')
            for card in qa_cards:
                qa_text = card.text.strip()
                if qa_text:
                    qas.append(qa_text)
        except:
            pass

    except Exception as e:
        print(f"❌ Error scraping: {e}")

    finally:
        driver.quit()

    return title, price, summary, comments, qas

# Example usage
url = 'https://www.rokomari.com/book/195175/bela-furabar-age'
title, price, summary, comments, qas = scrape_rokomari_book(url)

# Output
print("📘 Title:", title)
print("💰 Price:", price)
print("📝 Summary:", summary)
print(f"💬 Comments ({len(comments)}):")
for i, c in enumerate(comments, 1):
    print(f"{i}. {c}")
print(f"\n❓ Q&A ({len(qas)}):")
for i, qa in enumerate(qas, 1):
    print(f"{i}. {qa}")


