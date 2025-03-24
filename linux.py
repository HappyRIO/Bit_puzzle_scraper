import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException
import time
import csv
import os
from dotenv import load_dotenv

# Define your Telegram bot token and chat ID
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PROGRAM_ID = os.getenv("PROGRAM_ID")
# Load stored Bitcoin wallet address and parameters
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
THREADS = os.getenv("THREADS")
SEARCH_MODE = os.getenv("SEARCH_MODE")
RANGE_START = os.getenv("RANGE_START")
RANGE_END = os.getenv("RANGE_END")

# Function to send message to Telegram
def send_telegram_message(message, chat_id):
    print(f"Sending message to Telegram: {message[:10]}")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.get(url, params=params)
    return response

# Function to get the latest updates from the bot
def get_telegram_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": offset}
    response = requests.get(url, params=params)
    return response.json()

def format_number(number: str) -> str:
    return f"{number[0]}.....{number[-20:]}"

# Setup Selenium WebDriver
options = webdriver.ChromeOptions()
options.binary_location = "/usr/bin/google-chrome" 
options.add_argument("--headless")  # Run in headless mode
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
# driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)

# Open the website
driver.get("https://privatekeys.pw/scanner?bitcoin")
time.sleep(3)

try:
    # Check if the element exists and click it
    button = driver.find_element(By.CLASS_NAME, "fc-button-label")
    button.click()
except NoSuchElementException:
    print("Element with class 'fc-button-label' not found.")

# driver.find_element(By.CSS_SELECTOR, ".scanner-advanced.btn.btn-outline-secondary").click()
button = driver.find_element(By.CSS_SELECTOR, ".scanner-advanced.btn.btn-outline-secondary")
driver.execute_script("arguments[0].click();", button)

# Enter the Bitcoin wallet address
payout_address = driver.find_element(By.ID, "address")
payout_address.clear()
payout_address.send_keys(WALLET_ADDRESS)

# Set search parameters
threads_input = driver.find_element(By.ID, "workers")
threads_input.clear()
threads_input.send_keys(THREADS)
range = driver.find_elements(By.ID, "start-key")
if len(range) >= 2:
    range[0].clear()
    range[0].send_keys(RANGE_START)  # First occurrence
    range[1].clear()
    range[1].send_keys(RANGE_END)    # Second occurrence
else:
    print("Error: Expected at least two elements with ID 'start-key', but found", len(range))

# radio_button = driver.find_element(By.ID, "modeRandom")
# radio_button.click() 
radio_button = driver.find_element(By.ID, "modeRandom")
driver.execute_script("arguments[0].click();", radio_button)

form = driver.find_element(By.CLASS_NAME, "scanner")
form.submit()
time.sleep(2)

# Prepare CSV file
csv_filename = "scan_results.csv"
found_keys_filename = "found_keys.txt"

with open(csv_filename, "w", newline="") as csvfile:
    fieldnames = ["Timestamp", "Status", "Keys Scanned", "Current Key", "Found Keys"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

# Store the latest progress
latest_progress = {}

offset = None
count = 0
# Monitoring loop
while True:
    time.sleep(10)  # Wait before each update
    if count == 60:
        count = 0
    count += 1
    # Get real-time data
    status = driver.find_element(By.CLASS_NAME, "scanner-status").text
    keys_scanned = driver.find_element(By.CLASS_NAME, "scanner-total").text
    current_key = driver.find_element(By.CLASS_NAME, "scanner-current-key").text
    found_keys = driver.find_element(By.CLASS_NAME, "scanner-found").text
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Save data to CSV
    print(f"Monitoring... {count}")
    if count == 1:
        with open(csv_filename, "a", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerow({
                "Timestamp": timestamp,
                "Status": status,
                "Keys Scanned": keys_scanned,
                "Current Key": current_key,
                "Found Keys": found_keys
            })
    
    # Update latest progress
    latest_progress = {
        "Timestamp": timestamp,
        "Status": status,
        "Keys Scanned": keys_scanned,
        "Current Key": current_key,
        "Found Keys": found_keys
    }
    
    # If a key is found, save immediately and send result to Telegram
    if found_keys.lower() != "none":
        with open(found_keys_filename, "a") as keyfile:
            keyfile.write(f"{timestamp}: {found_keys}\n")
        print(f"Key found: {found_keys}")
        
        # Send success message to Telegram
        result_message = f"Key Found: {found_keys}\nTimestamp: {timestamp}"
        send_telegram_message(result_message, CHAT_ID)
        break  # Exit loop if a key is found
    
    updates = get_telegram_updates(offset)
    if "result" in updates:
        for update in updates["result"]:
            offset = update["update_id"] + 1  # Move the offset forward to avoid receiving the same message multiple times
            message_text = update["message"]["text"]
            user_id = update["message"]["from"]["id"]  # Get the user ID
            if message_text == "/progress" and user_id == int(CHAT_ID):
                formatted_number = format_number(latest_progress['Current Key'])
                progress_message = (
                    f"<b>🔧 Machine Name 🔧</b> <i>{PROGRAM_ID}</i>\n\n"
                    f"<b>📊 Progress Update 📊</b>\n"
                    f"🕒 <b>Timestamp:</b>       {latest_progress['Timestamp']}\n"
                    f"✅ <b>Status:</b>                {latest_progress['Status']}\n"
                    f"🔑 <b>Keys Scanned:</b>  {latest_progress['Keys Scanned']}\n"
                    f"🔍 <b>Current Key:</b>      {formatted_number}\n"
                    f"💎 <b>Found Keys:</b>      <code>{latest_progress['Found Keys']}</code>"
                )
                send_telegram_message(progress_message, CHAT_ID)

# Close browser
driver.quit()
