# Data-Scrap-From-Rokomari
# System Design
**Headless Browser Setup**
 The system uses a headless Chrome browser to scrape data without opening a visible browser window. This improves performance and is suitable for automated environments like servers or CI pipelines.

**Multithreading for Fast Scrapping**
Author Book Link Scraping:
 Multiple author pages are processed concurrently using multithreading to collect book URLs faster.

Book Details Scraping:
 Multiple book URLs are processed in parallel to extract book details more efficiently.

**Book URL Status Tracking**
Book URLs are stored in a CSV file (book_urls.csv) with an additional column named Status.
Initially, all book URLs are saved with the status Pending.

**Status-Based Processing**
The system loads only the book URLs with status Pending every time the script runs.
After successfully scraping a book's details, its status in the CSV is updated to Completed.


**Dynamic Scrolling for Book Details**
While scraping book detail pages, the script uses scrollHeight to perform dynamic page scrolling.
 This ensures all dynamically loaded content (e.g., Q&A, reviews) is visible and retrievable by the scraper.

**Data Storage & Merge**
Book details (title, price, summary, comments, and Q&A) are saved to books_data.csv.
New data scraped in subsequent runs are appended to the existing file, preserving previous results.


**Error Handling & Retry Logic**
Each book scraping attempt includes retry logic in case of failure.
Graceful error handling ensures the script continues running even if some books fail to load.

--------------------------------------------------------------------------------------------------------------
**Explanation in Vedio**
Vedio link: https://youtu.be/Q0yT2iZgsNU

--------------------------------------------------------------------------------------------------------------------
**OutPut: Total Scrap => 113258 Data**

**Author Data: 99984**
https://docs.google.com/spreadsheets/d/1W1JhckH36DEdCAmGNplGU0dHdToqBuYpHIya2vcEZFQ/edit?usp=sharing

**Book URL Data: 94331**
https://docs.google.com/spreadsheets/d/1os0UOl7S5JkyLJit0VcerHVruyXxRiKQCxzpZEpG04E/edit?usp=sharing
**
**Book Details Data: 8943**
https://docs.google.com/spreadsheets/d/1GZDRrVb-ytKllPX_qNuGNy5jPkMpntr9wuxSdJglu4A/edit?usp=sharing
