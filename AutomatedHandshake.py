import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# Global counter for successful applications
successful_applications = 0

def setup_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def wait_and_find_element(driver, by, value, timeout=30, retries=3):
    for attempt in range(retries):
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except (TimeoutException, StaleElementReferenceException) as e:
            if attempt == retries - 1:
                logging.error(f"Failed to find element after {retries} attempts: {value}")
                raise
            logging.warning(f"Attempt {attempt + 1} failed, retrying...")
            time.sleep(1)

def safe_click(driver, element, retries=3):
    for attempt in range(retries):
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", element)
            return
        except Exception as e:
            if attempt == retries - 1:
                logging.error(f"Failed to click element after {retries} attempts: {str(e)}")
                raise
            logging.warning(f"Click attempt {attempt + 1} failed, retrying...")
            time.sleep(1)

def login_to_handshake(driver):
    driver.get("https://chapman.joinhandshake.com/login")
    logging.info("Navigated to Handshake login page")

    sso_button = wait_and_find_element(driver, By.XPATH, ".//div[contains(@id, 'sso-name')]")
    safe_click(driver, sso_button)
    logging.info("Clicked SSO login option")

    # Handle Microsoft login
    username_input = wait_and_find_element(driver, By.ID, "i0116")
    username_input.send_keys(os.getenv("HANDSHAKE_EMAIL"))
    logging.info("Entered username")

    next_button = wait_and_find_element(driver, By.ID, "idSIButton9")
    safe_click(driver, next_button)
    logging.info("Clicked Next button")

    password_input = wait_and_find_element(driver, By.ID, "i0118")
    password_input.send_keys(os.getenv("HANDSHAKE_PASSWORD"))
    logging.info("Entered password")

    # Wait for the sign-in button to be clickable
    sign_in_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "idSIButton9"))
    )
    # Use JavaScript to click the button
    driver.execute_script("arguments[0].click();", sign_in_button)
    logging.info("Clicked Sign In button using JavaScript")

    # Handle potential "Stay signed in?" prompt
    try:
        stay_signed_in_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "idSIButton9"))
        )
        driver.execute_script("arguments[0].click();", stay_signed_in_button)
        logging.info("Clicked 'Stay signed in' button using JavaScript")
    except TimeoutException:
        logging.info("No 'Stay signed in' prompt found, continuing...")

    # Wait for redirect to Handshake
    try:
        WebDriverWait(driver, 30).until(
            EC.url_contains("https://chapman.joinhandshake.com")
        )
        logging.info("Successfully logged in to Handshake")
    except TimeoutException:
        logging.error("Failed to redirect to Handshake after login")
        logging.info(f"Current URL: {driver.current_url}")
        raise

def process_job(driver, job):
    global successful_applications
    try:
        job.click()
        job_preview = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, ".//div[contains(@aria-label, 'Job Preview')]"))
        )

        try:
            apply_button = WebDriverWait(job_preview, 5).until(
                EC.presence_of_element_located((By.XPATH, ".//span[text()='Apply' or text()='Apply Externally']"))
            )
            
            if apply_button.text == "Apply Externally":
                return
            elif apply_button.text == "Apply":
                apply_button.click()
                if process_application(driver):
                    successful_applications += 1
            else:
                logging.warning("Unexpected apply button text: " + apply_button.text)
                return

        except TimeoutException:
            return

    except Exception as e:
        logging.error(f"Error processing job: {str(e)}")

def click_dismiss_button(driver):
    try:
        dismiss_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='dismiss' and contains(@class, 'style__dismiss___Zotdc')]"))
        )
        dismiss_button.click()
    except TimeoutException:
        logging.error("Could not find dismiss button")

def process_application(driver):
    try:
        modal = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, ".//span[contains(@data-hook, 'apply-modal-content')]"))
        )

        submit_application = WebDriverWait(modal, 10).until(
            EC.element_to_be_clickable((By.XPATH, ".//span[contains(@data-hook, 'submit-application')]"))
        )

        fieldsets = modal.find_elements(By.TAG_NAME, "fieldset")
        dropdown_count = len([f for f in fieldsets if f.find_elements(By.XPATH, ".//span[contains(@class, 'Select-arrow')]")])

        if dropdown_count > 1:
            click_dismiss_button(driver)
            return False

        if len(fieldsets) == 0:
            submit_application.click()
        elif len(fieldsets) == 1:
            if not fieldsets[0].find_elements(By.TAG_NAME, "svg"):
                recently_added_section = modal.find_elements(By.XPATH, ".//div[starts-with(@class, 'style__suggested___')]")
                if recently_added_section:
                    recently_added_section[0].click()
                else:
                    select_dropdown_option(driver, fieldsets[0])
            submit_application.click()
        else:
            if dropdown_count == 1:
                dropdown_fieldset = next(f for f in fieldsets if f.find_elements(By.XPATH, ".//span[contains(@class, 'Select-arrow')]"))
                select_dropdown_option(driver, dropdown_fieldset)
            submit_application.click()

        # Check if application was submitted successfully
        try:
            WebDriverWait(driver, 5).until(
                EC.invisibility_of_element_located((By.XPATH, ".//span[contains(@data-hook, 'apply-modal-content')]"))
            )
            logging.info(f"Application submitted successfully. Total successful applications: {successful_applications + 1}")
            return True
        except TimeoutException:
            click_dismiss_button(driver)
            return False

    except Exception as e:
        logging.error(f"Error in process_application: {str(e)}")
        click_dismiss_button(driver)
        return False

def select_dropdown_option(driver, fieldset):
    try:
        select_arrow = WebDriverWait(fieldset, 10).until(
            EC.element_to_be_clickable((By.XPATH, ".//span[contains(@class, 'Select-arrow')]"))
        )
        select_arrow.click()
        
        item = WebDriverWait(fieldset, 10).until(
            EC.presence_of_element_located((By.XPATH, ".//div[contains(@class, 'Select-menu-outer')]"))
        )
        options = item.find_elements(By.XPATH, ".//*")
        if len(options) > 3:
            options[3].click()
        else:
            options[0].click()
        
    except Exception as e:
        logging.error(f"Error in select_dropdown_option: {str(e)}")
        raise

def main():
    driver = setup_driver()
    try:
        login_to_handshake(driver)
        
        driver.get("https://app.joinhandshake.com/stu/postings")
        logging.info("Navigated to job postings page")

        first_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, ".//div[contains(@data-hook, 'search-results')]"))
        )

        pagination = first_div.find_element(By.XPATH, ".//div[contains(@class, 'style__pagination___XsvKe')]")
        range_determination = pagination.find_element(By.XPATH, ".//div[contains(@class, 'style__page___skSXd')]")
        range_text = range_determination.text
        total_pages = int(range_text.split("/")[1].strip())
        logging.info(f"Total pages of job listings: {total_pages}")

        for i in range(total_pages):
            jobs = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, ".//a[starts-with(@id, 'posting')]"))
            )
            logging.info(f"Processing page {i+1}/{total_pages} with {len(jobs)} job listings")

            for job in jobs:
                process_job(driver, job)

            if i < total_pages - 1:
                next_page = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, ".//button[contains(@data-hook, 'search-pagination-next')]"))
                )
                next_page.click()
                time.sleep(2)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        logging.info(f"Script execution completed. Total successful applications: {successful_applications}")
        driver.quit()

if __name__ == "__main__":
    main()
