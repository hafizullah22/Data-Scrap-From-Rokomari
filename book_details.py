import csv
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver

def scroll_page(driver, pause_time=0.5, max_attempts=10):
    last_height = driver.execute_script("return document.body.scrollHeight")
    attempts = 0
    while attempts < max_attempts:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        attempts += 1


def collect_author_links(pages=3, save_csv=True, csv_file='authors.csv'):
    driver = get_driver()
    wait = WebDriverWait(driver, 10)
    author_data = []
    base_url = 'https://www.rokomari.com/book/authors/?page={}'

    for page_num in range(1, pages + 1):
        try:
            url = base_url.format(page_num)
            print(f"🔄 Loading author page {page_num}")
            driver.get(url)
            wait.until(EC.presence_of_element_located((By.ID, 'author-list')))
            time.sleep(1)

            authors = driver.find_elements(By.XPATH, '//*[@id="author-list"]/div[3]/section/div[2]/div/a')
            for a in authors:
                href = a.get_attribute('href')
                name = a.text.strip()
                if href and name:
                    author_id = href.rstrip('/').split('/')[-1]
                    author_data.append({
                        'author_id': author_id,
                        'author_name': name,
                        'author_url': href
                    })

            print(f"✅ Page {page_num} done | Total: {len(author_data)} authors collected so far")

        except Exception as e:
            print(f"⚠️ Error on page {page_num}: {e}")
            continue

    driver.quit()

    if save_csv:
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['author_id', 'author_name', 'author_url'])
            writer.writeheader()
            for row in author_data:
                writer.writerow(row)
        print(f"💾 Saved {len(author_data)} authors to {csv_file}")

    return [item['author_url'] for item in author_data]  # returning only links for further scraping


def scrape_books_from_author(author_url):
    books = set()
    try:
        driver = get_driver()
        driver.get(author_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'book-list-wrapper')))
        scroll_page(driver)
        book_elems = driver.find_elements(By.CSS_SELECTOR, '.book-list-wrapper a')
        for elem in book_elems:
            href = elem.get_attribute('href')
            if href:
                books.add(href)
    except Exception as e:
        print(f"❌ Failed author: {author_url} | {e}")
    finally:
        driver.quit()
    return list(books)

def scrape_book_details(book_url, retries=2):
    for attempt in range(retries):
        try:
            driver = get_driver()
            wait = WebDriverWait(driver, 10)
            driver.get(book_url)
            scroll_page(driver)

            # Title and price
            title = driver.find_element(By.XPATH, '//*[@id="ts--desktop-details-book-main-info"]/div[1]/h1').text.strip()
            price = driver.find_element(By.CLASS_NAME, 'sell-price').text.strip()

            # Summary
            try:
                summary = driver.find_element(By.CSS_SELECTOR, '.product-synopsis p').text.strip()
            except:
                summary = 'N/A'

            # Comments
            comments = []
            try:
                comment_elements = driver.find_elements(By.CSS_SELECTOR, '#book-review-section .review-details')
                comments = [c.text.strip() for c in comment_elements if c.text.strip()]
            except:
                comments = []

            # Q&A
            qas = []
            try:
                qa_elements = driver.find_elements(By.CSS_SELECTOR, '#ts--common-ques-ans-card .ts--question-ans-card')
                qas = [q.text.strip() for q in qa_elements if q.text.strip()]
            except:
                qas = []

            return {
                'url': book_url,
                'title': title,
                'price': price,
                'summary': summary,
                'comments': comments,
                'qa': qas
            }

        except Exception as e:
            print(f"⚠️ Retry {attempt+1} for {book_url} failed: {e}")
        finally:
            try:
                driver.quit()
            except:
                pass
    return None


def multithread_scrape_books(author_links, max_author_threads=2, max_book_threads=2):
    all_books = []
    seen_urls = set()

    print("🔁 Scraping authors (multithreaded)...")
    with ThreadPoolExecutor(max_workers=max_author_threads) as author_executor:
        author_futures = {author_executor.submit(scrape_books_from_author, link): link for link in author_links}

        for future in as_completed(author_futures):
            author_url = author_futures[future]
            try:
                book_urls = future.result()
                author_name = author_url.rstrip('/').split('/')[-1]

                print(f"📘 {len(book_urls)} books by {author_name}")

                with ThreadPoolExecutor(max_workers=max_book_threads) as book_executor:
                    book_futures = {
                        book_executor.submit(scrape_book_details, book_url): book_url
                        for book_url in book_urls if book_url not in seen_urls
                    }

                    for b_future in as_completed(book_futures):
                        book_url = book_futures[b_future]
                        seen_urls.add(book_url)
                        book_data = b_future.result()
                        if book_data:
                            book_data['author'] = author_name
                            all_books.append(book_data)

            except Exception as e:
                print(f"❌ Author processing failed: {author_url} | {e}")

    return all_books

def save_books_to_csv(book_data_list, filename='books_data.csv'):
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'author', 'title', 'price', 'summary', 'comments', 'qa', 'url'
        ])
        writer.writeheader()
        for book in book_data_list:
            writer.writerow({
                'author': book.get('author', ''),
                'title': book.get('title', ''),
                'price': book.get('price', ''),
                'summary': book.get('summary', ''),
                'comments': ' ||| '.join(book.get('comments', [])),
                'qa': ' ||| '.join(book.get('qa', [])),
                'url': book.get('url', '')
            })
    print(f"✅ Saved {len(book_data_list)} books to {filename}")

# ==== MAIN ====
if __name__ == "__main__":
    print("🚀 Step 1: Collecting author links...")
    author_links = collect_author_links(pages=2)  # keep original logic

    print("🧠 Step 2: Scraping all book details (fast)...")
    books_data = multithread_scrape_books(author_links[:2], max_author_threads=2, max_book_threads=2)

    print("💾 Step 3: Saving data to CSV...")
    save_books_to_csv(books_data)
