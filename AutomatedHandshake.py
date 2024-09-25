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
from selenium.webdriver.common.keys import Keys

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
    try:
        logging.info("Starting to process a new job")
        job.click()
        logging.info("Clicked on job listing")
        
        job_preview = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, ".//div[contains(@aria-label, 'Job Preview')]"))
        )
        logging.info("Job preview loaded")

        try:
            apply_button = WebDriverWait(job_preview, 5).until(
                EC.presence_of_element_located((By.XPATH, ".//span[text()='Apply' or text()='Apply Externally']"))
            )
            logging.info(f"Found apply button with text: {apply_button.text}")
            
            if apply_button.text == "Apply Externally":
                logging.info("External application - skipping")
                return
            elif apply_button.text == "Apply":
                logging.info("Clicking 'Apply' button")
                apply_button.click()
                if process_application(driver):
                    logging.info("Application process completed successfully")
                else:
                    logging.warning("Application process did not complete successfully")
            else:
                logging.warning(f"Unexpected apply button text: {apply_button.text}")
                return

        except TimeoutException:
            logging.warning("Could not find apply button within timeout")
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
    global successful_applications
    try:
        logging.info("Starting application process")
        modal = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, ".//span[contains(@data-hook, 'apply-modal-content')]"))
        )
        logging.info("Application modal found")

        submit_application = WebDriverWait(modal, 10).until(
            EC.element_to_be_clickable((By.XPATH, ".//span[contains(@data-hook, 'submit-application')]"))
        )
        logging.info("Submit application button found")

        # Find all dropdown elements
        dropdowns = modal.find_elements(By.XPATH, ".//div[contains(@class, 'Select-control')]")
        logging.info(f"Found {len(dropdowns)} dropdown(s) in the application form")

        if len(dropdowns) > 1:
            logging.info("Multiple fields detected. Exiting application.")
            click_dismiss_button(driver)
            return False

        if len(dropdowns) == 1:
            logging.info("Single dropdown detected. Attempting to select resume.")
            select_dropdown_option(driver, dropdowns[0])

        logging.info("Waiting before clicking submit button.")
        time.sleep(2)  # Wait a bit before clicking submit
        submit_application.click()
        logging.info("Clicked submit button")

        # Check if application was submitted successfully
        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.XPATH, ".//span[contains(@data-hook, 'apply-modal-content')]"))
            )
            successful_applications += 1
            logging.info(f"Application submitted successfully. Total successful applications: {successful_applications}")
            return True
        except TimeoutException:
            logging.warning("Application submission timed out")
            try:
                error_message = driver.find_element(By.XPATH, "//div[contains(@class, 'error')]").text
                logging.error(f"Error message found: {error_message}")
            except NoSuchElementException:
                logging.info("No error message found on the page")
            click_dismiss_button(driver)
            return False

    except Exception as e:
        logging.error(f"Error in process_application: {str(e)}")
        click_dismiss_button(driver)
        return False

def select_dropdown_option(driver, dropdown_element):
    try:
        logging.info("Starting resume dropdown option selection")
        
        # Check if there's already a selected value
        selected_value = dropdown_element.find_elements(By.XPATH, ".//span[contains(@class, 'Select-value-label')]")
        if selected_value:
            logging.info(f"Dropdown already has a selected value: {selected_value[0].text}")
            return  # If there's a default value, we don't need to do anything

        # Click to open the dropdown
        logging.info("Attempting to click dropdown to open it")
        dropdown_element.click()
        time.sleep(1)  # Wait for the dropdown to open
        logging.info("Clicked to open dropdown")

        # Select the first option (assuming it's the resume)
        options = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'Select-option')]"))
        )
        if options:
            first_option = options[0]
            first_option_text = first_option.text
            logging.info(f"Attempting to select first option: {first_option_text}")
            first_option.click()
            logging.info(f"Clicked first option: {first_option_text}")
            
            # Wait for the selection to be reflected
            WebDriverWait(driver, 10).until(
                EC.text_to_be_present_in_element((By.XPATH, ".//span[contains(@class, 'Select-value-label')]"), first_option_text)
            )
            logging.info("Resume selection confirmed in dropdown")
        else:
            logging.warning("No options found in the resume dropdown")
            dropdown_element.click()  # Close the dropdown if no options found

    except TimeoutException as te:
        logging.error(f"Timeout while trying to interact with resume dropdown: {str(te)}")
    except NoSuchElementException as nse:
        logging.error(f"Could not find expected resume dropdown elements: {str(nse)}")
    except Exception as e:
        logging.error(f"Unexpected error in select_dropdown_option: {str(e)}")

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
