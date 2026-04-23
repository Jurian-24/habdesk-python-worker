import test
from playwright.sync_api import sync_playwright

from simyo import Simyo

PHONENUMBER = "0612658350"
PASSWORD = "75874wP5:"

def main():
    with sync_playwright() as playwright, playwright.chromium.launch(headless=False) as browser:
        page = test.wrap(browser.new_page())
        
        simyo = Simyo(PHONENUMBER, PASSWORD)

        print("Naar Simyo navigeren...")
        page.goto("https://mijn.simyo.nl/")
        
        simyo.check_cookie_modal(page)
        simyo.login_to_application(page)

        
        # simyo.get_usage_data(page)
        simyo.get_usage_from_month(page, "februari")
        
        # simyo.get_sim_card_info(page)

        print("Script is helemaal klaar. Browser sluit af.")