# HandShake-QuickApply-Bot

This bot automates job applications on the Handshake platform, specifically designed for ASU students. It's particularly useful for Juniors and Seniors looking to apply to multiple jobs in their relevant field quickly and efficiently.

## Features

- **Login Automation**: Automates the login process using credentials stored in environment variables.
- **Job Posting Scraper**: Navigates through job postings and extracts job details.
- **Automated Application**: Applies to job postings where the application requirements are already satisfied or minimal user input is needed.
- **Pagination Handling**: Iterates over multiple pages of job listings.
- **Dynamic Form Handling**: Handles various job application forms, identifying which fields are pre-populated and which require input.
- **Application Tracking**: Counts and logs successful applications, including job titles.

## Prerequisites

Before running the script, ensure you have:

- Python 3.x installed
- Selenium: `pip install selenium`
- WebDriver Manager: `pip install webdriver-manager`
- python-dotenv: `pip install python-dotenv`
- Google Chrome (latest version)

## Environment Setup

Create a `.env` file in the project root directory with your Handshake login details:

```
HANDSHAKE_EMAIL=your_handshake_email
HANDSHAKE_PASSWORD=your_handshake_password
```

## Running the Script

1. Open a terminal and navigate to the project directory.
2. Run the script: `python AutomatedHandshake.py`

## How the Script Works

### Login Process
- The script logs in using the credentials from the `.env` file and navigates to the job postings page.

### Job Posting Scraper
- Identifies all available job postings on the current page.
- Opens each job listing to check application requirements.

### Automated Application Process
1. **Job Title Extraction**: The script extracts the title of each job being processed.
2. **Application Form Analysis**: 
   - Checks the number of form fields (fieldsets) in the application.
   - Counts the number of dropdown menus.
3. **Application Decision**:
   - If there's more than one dropdown, the application is skipped.
   - For applications with no fields or one field, it proceeds to apply.
   - For applications with multiple fields but only one dropdown, it attempts to fill the form.
4. **Form Filling**:
   - Autopopulated fields (indicated by SVG elements) are left as is.
   - For non-autopopulated fields, it either selects a suggested option or chooses from a dropdown.
5. **Submission and Verification**:
   - Clicks the submit button.
   - Waits for the application modal to disappear, confirming successful submission.
6. **Logging**:
   - Successfully submitted applications are logged with the job title and a running count.

### Pagination
- After processing all jobs on a page, the script moves to the next page and repeats the process.

### Error Handling
- If an application can't be submitted or an error occurs, the script logs the issue and moves on to the next job.

## Potential Improvements

- AI Integration: Potential for AI-generated cover letters or personalized application content.
- Enhanced Error Handling: More specific exception handling for robustness.
- User Interface: Develop a GUI for easier operation and monitoring.

## Disclaimer

This script is for educational and personal use only. Ensure that automating job applications complies with Handshake's terms of service. Use at your own discretion.

## Author

Developed by Pernell Louis-Pierre. Revised by Maximillian Ludwick 
