import time
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class LoginTest(unittest.TestCase):

    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.maximize_window()
        self.test_username = "testuser_" + str(int(time.time() * 1000) % 10000)
        self.test_password = "Test@12345"
        self.test_email = f"{self.test_username}@test.com"

    def register_user(self):
        """Tự động đăng ký user trước"""
        driver = self.driver
        driver.get("http://127.0.0.1:9999/auth/register")
        
        # Chờ page load
        time.sleep(2)
        
        # Chờ form load
        wait = WebDriverWait(driver, 15)
        username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        
        # Điền thông tin
        username_field.send_keys(self.test_username)
        driver.find_element(By.ID, "email").send_keys(self.test_email)
        driver.find_element(By.ID, "full_name").send_keys("Test User")
        driver.find_element(By.ID, "password").send_keys(self.test_password)
        driver.find_element(By.ID, "passwordconfirm").send_keys(self.test_password)
        
        # Click submit
        submit_btn = driver.find_element(By.CSS_SELECTOR, "#registerForm button[type='submit']")
        submit_btn.click()
        
        # Chờ register success
        time.sleep(3)
        
        # DEBUG: In URL sau register
        print(f"URL after register: {driver.current_url}")

    def test_login(self):
        driver = self.driver

        # Đăng ký user trước
        self.register_user()

        # Route login thực tế trong source
        driver.get("http://127.0.0.1:9999/auth/login")

        # Chờ tối đa 10 giây để username element hiển thị
        wait = WebDriverWait(driver, 10)
        username = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        password = driver.find_element(By.NAME, "password")

        username.send_keys(self.test_username)
        password.send_keys(self.test_password)
        
        # Tìm và click button submit
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()

        time.sleep(3)

        # Kiểm tra sau đăng nhập không còn ở trang login
        self.assertNotEqual(
            driver.current_url,
            "http://127.0.0.1:9999/auth/login"
        )

    def tearDown(self):
        self.driver.quit()


if __name__ == "__main__":
    unittest.main()