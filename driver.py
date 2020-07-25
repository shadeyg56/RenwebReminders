from selenium import webdriver
import private


class CustomDriver(webdriver.Firefox):
    def __init__(self):
        super().__init__(executable_path="drivers/geckodriver.exe")

    def login(self, user, password):
        self.get(private.loginurl)  # url's are privated because they contain location info
        self.find_element_by_id("username").send_keys(user)
        self.find_element_by_id("password").send_keys(password)
        self.find_element_by_id("UserType_Student").click()
        self.find_element_by_id("submit").click()

    def fetch_pics(self, dayn, user):
        self.get(private.homework_url)
        # searches for all children of a specific div
        elements = self.find_elements_by_css_selector('div.pwr_middle_content > *')
        links = [x for x in elements]
        day = 0
        days = {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: []}
        words = {"sunday": 1, "monday": 2, "tuesday": 3, "wednesday": 4, "thrusday": 5, "friday": 6, "saturday": 7}
        for element in links:
            # if it reaches this class, then it's the next day
            if element.get_attribute("class") == "pwr_date_hr":
                day += 1
            # each entry is under one of these 2 classes
            if element.get_attribute("class").startswith("pwr_card_content pwr_centered lessonplans") or element.get_attribute("class") == "pwr_card_content pwr_centered lessonplans nomargin":
                days[day].append(element)
        #loop through all of the days and take a screenshot if it's the given day
        for key in days:
            n = 0
            for element in days[key]:
                if key == words[dayn]:
                    element.screenshot(f"pics/{user}{key}day{n}.png")
                    n += 1
