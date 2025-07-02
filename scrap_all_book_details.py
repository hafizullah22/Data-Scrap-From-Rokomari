import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Headless optimized Chrome driver setup
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')
    chrome_options.page_load_strategy = 'eager'
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(15)
    return driver

def smooth_scroll(driver, increment=300, delay=0.05, max_attempts=5):
    last_height = driver.execute_script("return document.body.scrollHeight")
    attempts = 0
    while attempts < max_attempts:
        driver.execute_script(f"window.scrollBy(0, {increment});")
        time.sleep(delay)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            attempts += 1
        else:
            attempts = 0
            last_height = new_height

# Step 1: Collect Author Links
def collect_author_links(pages=2, save_csv=True, csv_file='authors.csv'):
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

            print(f"✅ Page {page_num} done | Total: {len(author_data)} authors")

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

    return [item['author_url'] for item in author_data]

# Step 2: Scrape books from one author page
def scrape_books_from_author(author_url):
    books = set()
    try:
        driver = get_driver()
        driver.get(author_url)
        smooth_scroll(driver)
        time.sleep(1)

        book_elems = driver.find_elements(By.CSS_SELECTOR, '.book-list-wrapper a')
        for elem in book_elems:
            href = elem.get_attribute('href')
            if href and '/book/' in href:
                books.add(href)

    except Exception as e:
        print(f"❌ Failed author: {author_url} | {e}")
    finally:
        driver.quit()

    return list(books)

# Multithread scrape book URLs
def multithread_scrape_books(author_links, max_author_threads=2):
    all_books = set()

    def scrape_author_books(url):
        try:
            books = scrape_books_from_author(url)
            print(f"📚 {len(books)} books found from {url}")
            return books
        except Exception as e:
            print(f"❌ Error in thread for {url}: {e}")
            return []

    with ThreadPoolExecutor(max_workers=max_author_threads) as executor:
        futures = [executor.submit(scrape_author_books, link) for link in author_links]
        for f in as_completed(futures):
            try:
                books = f.result()
                all_books.update(books)
            except Exception as e:
                print(f"❗ Error getting result from future: {e}")

    print(f"✅ Total unique books collected: {len(all_books)}")
    return list(all_books)

# Save just book URLs to CSV with Status column
def save_book_urls_to_csv(book_urls, filename="book_urls.csv"):
    with open(filename, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(["Book URL", "Status"])
        for url in book_urls:
            writer.writerow([url, "Pending"])
    print(f"💾 Saved {len(book_urls)} book URLs to {filename}")

# Load book URLs and status from CSV, only Pending or empty status
def load_book_urls_with_status(filename='book_urls.csv'):
    urls = []
    try:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            print(f"CSV Headers: {reader.fieldnames}")

            for row in reader:
                url = row['Book URL'].strip()
                status = row.get('Status', '').strip()
                if url and status.lower() != 'completed':
                    urls.append(url)
    except Exception as e:
        print(f"❌ Failed to read from {filename}: {e}")
    return urls

# Update the CSV to mark scraped URLs as Completed
def mark_urls_as_completed(scraped_urls, filename='book_urls.csv'):
    updated_rows = []
    try:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                if row['Book URL'] in scraped_urls:
                    row['Status'] = 'Completed'
                updated_rows.append(row)

        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)

        print(f"📝 Updated status for {len(scraped_urls)} URLs in {filename}")
    except Exception as e:
        print(f"❌ Failed to update status: {e}")

# Step 3: Scrape details from each book
def scrape_book_details(book_url, retries=2):
    for attempt in range(retries):
        driver = None
        try:
            driver = get_driver()
            wait = WebDriverWait(driver, 10)
            driver.get(book_url)

            height = driver.execute_script('return document.body.scrollHeight')
            for i in range(0, height + 300, 60):
                driver.execute_script(f'window.scrollTo(0,{i});')
                time.sleep(0.2)

            comments = []
            qas = []

            title = wait.until(EC.presence_of_element_located(
                (By.XPATH, '//*[@id="ts--desktop-details-book-main-info"]/div[1]/h1'))
            ).text.strip()

            price = wait.until(EC.presence_of_element_located(
                (By.CLASS_NAME, 'sell-price'))
            ).text.strip()

            try:
                summary = driver.find_element(
                    By.XPATH, '//*[@id="rokomariBody"]/div[3]/div[5]/div[2]/div[1]/div'
                ).text.strip()
            except:
                summary = 'N/A'

            try:
                for j in range(2, 7):
                    comment_xpath = f'//*[@id="rokomariBody"]/div[3]/div[6]/div[2]/div/div/div/div[{j}]/div[2]/div/div'
                    comment_elements = driver.find_elements(By.XPATH, comment_xpath)
                    for c in comment_elements:
                        text = c.text.strip()
                        if text:
                            comments.append(text)
            except:
                pass

            try:
                qa_cards = driver.find_elements(By.ID, 'ts--common-ques-ans-card')
                for card in qa_cards:
                    qa_text = card.text.strip()
                    if qa_text:
                        qas.append(qa_text)
            except:
                pass

            return {
                'url': book_url,
                'title': title,
                'price': price,
                'summary': summary,
                'comments': comments,
                'qa': qas
            }

        except Exception as e:
            print(f"⚠️ Retry {attempt + 1} for {book_url} failed: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    return None

# Multithreaded detail scraper
def multithread_scrape_book_details(book_urls, max_threads=2):
    print(f"🚀 Scraping {len(book_urls)} book details with {max_threads} threads...")
    results = []
    seen = set()

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(scrape_book_details, url): url for url in book_urls if url not in seen}
        for future in as_completed(futures):
            url = futures[future]
            seen.add(url)
            try:
                data = future.result()
                if data:
                    results.append(data)
                    print(f"✅ Scraped: {data['title'][:30]}...")
            except Exception as e:
                print(f"❌ Failed to scrape {url}: {e}")
    return results

# Save book data to CSV
def save_books_data_to_csv(book_data_list, filename='books_data.csv', append=False):
    file_exists = False
    try:
        with open(filename, 'r', encoding='utf-8-sig'):
            file_exists = True
    except FileNotFoundError:
        pass

    mode = 'a' if append and file_exists else 'w'
    with open(filename, mode, newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'title', 'price', 'summary', 'comments', 'qa', 'url'
        ])
        if not append or not file_exists:
            writer.writeheader()
        for book in book_data_list:
            writer.writerow({
                'title': book.get('title', ''),
                'price': book.get('price', ''),
                'summary': book.get('summary', ''),
                'comments': ' ||| '.join(book.get('comments', [])),
                'qa': ' ||| '.join(book.get('qa', [])),
                'url': book.get('url', '')
            })
    print(f"💾 {'Appended' if append else 'Saved'} {len(book_data_list)} books to {filename}")

# Main run
if __name__ == "__main__":
    start_time = time.time()
    print("🚀 Starting the scraping process...")

    # # Step 1: Author Links
    # author_links = collect_author_links(pages=209)
    #
    # # Step 2: Book URLs
    # all_book_urls = multithread_scrape_books(author_links, max_author_threads=7)
    # save_book_urls_to_csv(all_book_urls)


    # Step 3: Load pending URLs from CSV and scrape details
    # Load only pending URLs
    all_book_urls = load_book_urls_with_status()
    if not all_book_urls:
        print("⚠️ No pending URLs found in CSV. Exiting.")
        exit()

    # Limit or remove [:2] as needed
    book_details = multithread_scrape_book_details(all_book_urls[5511:5610], max_threads=7)

    # Save and merge with previously scraped book data
    save_books_data_to_csv(book_details, filename="books_data.csv", append=True)

    # Mark those URLs as completed
    scraped_urls = [book['url'] for book in book_details if book and book.get('url')]
    mark_urls_as_completed(scraped_urls)

    print(f"✅ Done in {round(time.time() - start_time, 2)} seconds.")
