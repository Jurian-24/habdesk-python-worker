import json

class Simyo:
    def __init__(self, phonenumber: str, password: str):
        self.phonenumber = phonenumber
        self.password = password

    def check_cookie_modal(self, page):
        print("Checking for cookie banners...")
        COOKIE_QUERY = """
        {
            cookie_banner {
                accept_all_button
            }
        }
        """
        try:
            cookie_elements = page.query_elements(COOKIE_QUERY)
            if cookie_elements.cookie_banner and cookie_elements.cookie_banner.accept_all_button:
                cookie_elements.cookie_banner.accept_all_button.click()
                print("Cookies accepted!")
                page.wait_for_timeout(1000)
        except Exception:
            print("No cookie banner found, moving on...")

    def login_to_application(self, page):
        print("Logging in...")

        LOGIN_QUERY = """
        {
            login_form {
                phone_number_input
                password_input
                login_button
            }
        }
        """
        login_elements = page.query_elements(LOGIN_QUERY)
        
        login_elements.login_form.phone_number_input.type(self.phonenumber)
        login_elements.login_form.password_input.type(self.password)
        login_elements.login_form.login_button.click()

        page.wait_for_timeout(2000)

    def get_sim_card_info(self, page):
        print("Navigating to Simyo...")

        page.wait_for_timeout(3000)
        
        page.wait_for_timeout(5000)
        
        print("Navigating to SIM settings...")
        page.goto("https://mijn.simyo.nl/instellingen/simkaart")
        
        page.wait_for_timeout(3000)

        print("Searching for SIM card number...")
        DATA_QUERY = """
        {
            sim_card_number,
            sim_card_type,
            pincode,
            puk_code,
            sim_card_status
        }
        """
        
        try:
            data = page.query_data(DATA_QUERY)
            
            if not data.get("sim_card_number"):
                data = {}
                print("SIM card number not found on the page.")
            else:
                print("SIM card number found!")
                
        except Exception:
            data = {}
            print("An error occurred while searching. Returning empty JSON.")

        with open("sim_data.json", "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

        print("Done! Check the sim_data.json file in your folder.")

    def get_usage_data(self, page):
        page.wait_for_timeout(3000)

        print("going to usage page")
        page.goto("https://mijn.simyo.nl/verbruik")
        page.wait_for_timeout(10000)

        print("searching for the usage")
        DATA_QUERY = """
        {
            verbruik_per_dag[] {
                datum
                totaal_verbruik_mb
                bedrag
                specifieke_sessies[] {
                    tijd
                    verbruik_mb
                }
            }
        }
        """

        try:
            data = page.query_data(DATA_QUERY)
            with open("simyo_usage.json", "w", encoding="utf-8") as file:
                print("writing to file")
                json.dump(data, file, indent=4)
            
        except Exception as e:
            print(e)

    
    def get_usage_from_month(self, page, month_name):
        page.goto("https://mijn.simyo.nl/verbruik")
        
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)

        NAV_QUERY = """
        {
            maand_navigatie {
                huidige_maand_tekst
                vorige_maand_knop
            }
        }
        """

        max_clicks = 12
        clicks = 0
        found = False

        while clicks < max_clicks:
            navigation = page.query_elements(NAV_QUERY)
            current_month = navigation.maand_navigatie.huidige_maand_tekst.text_content().lower()

            if month_name.lower() in current_month:
                print(f"Found {month_name}")
                found = True
                break

            navigation.maand_navigatie.vorige_maand_knop.click()
            page.wait_for_timeout(2000)
            clicks += 1

        if found:
            LOAD_MORE_QUERY = """
            {
                toon_meer_dagen_knop
            }
            """
            
            # check if the load more button still exists
            while True:
                try:
                    ui_elements = page.query_elements(LOAD_MORE_QUERY)
                    
                    if ui_elements and ui_elements.toon_meer_dagen_knop:
                        ui_elements.toon_meer_dagen_knop.click()
                        
                        page.wait_for_timeout(2000)
                    else:
                        break
                except Exception:
                    break

            DATA_QUERY = """
            {
                verbruik_per_dag[] {
                    datum
                    totaal_verbruik_mb
                    bedrag
                    specifieke_sessies[] {
                        tijd
                        verbruik_mb
                    }
                }
            }
            """
            # store the scraped data into a json file
            try:
                data = page.query_data(DATA_QUERY)
                file_name = f"simyo_usage_{month_name}.json"
                
                with open(file_name, "w", encoding="utf-8") as file:
                    json.dump(data, file, indent=4)
                print(f"Data has been stored in file: {file_name}")
                
            except Exception as e:
                print(f"Error while fetching the data: {e}")
        else:
            print(f"{month_name} not found na {max_clicks} attempts")