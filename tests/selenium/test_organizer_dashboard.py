import os
import uuid
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException

# ============================================================
# CONFIG
# ============================================================

BASE_URL = "http://127.0.0.1:9999"
REGISTER_URL = f"{BASE_URL}/auth/register"
LOGIN_URL = f"{BASE_URL}/auth/login"

WAIT_TIME = 15


# ============================================================
# FIXTURE - KHỞI TẠO VÀ ĐÓNG CHROME
# ============================================================

@pytest.fixture
def driver():
    """
    Khởi tạo Chrome WebDriver trước mỗi test
    và đóng trình duyệt sau khi test kết thúc.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()


# ============================================================
# TEST CASE - ĐĂNG KÝ & ĐĂNG NHẬP BẰNG ORGANIZER LOGIN
# ============================================================

def test_organizer_registration_and_login(driver):
    """
    Kiểm thử liên hoàn:
    1. Đăng ký tài khoản Organizer mới.
    2. Đăng nhập bằng tài khoản Organizer vừa đăng ký.
    3. Xác minh chuyển hướng thành công đến Organizer Dashboard.
    """
    wait = WebDriverWait(driver, WAIT_TIME)

    # --------------------------------------------------------
    # PHẦN 1: ĐĂNG KÝ TÀI KHOẢN ORGANIZER MỚI
    # --------------------------------------------------------
    print("\n[Step 1] Opening registration page")
    driver.get(REGISTER_URL)

    # Tạo thông tin duy nhất để tránh trùng lặp tài khoản khi chạy test nhiều lần
    unique_suffix = uuid.uuid4().hex[:6]
    test_username = f"org_{unique_suffix}"
    test_email = f"org_{unique_suffix}@example.com"
    test_fullname = f"Ban To Chuc {unique_suffix}"
    test_password = "Password123!"

    print(f"-> Registering new account: Username={test_username}, Email={test_email}")

    # Nhập Username
    username_input = wait.until(
        EC.visibility_of_element_located((By.ID, "username"))
    )
    username_input.clear()
    username_input.send_keys(test_username)

    # Nhập Email
    email_input = driver.find_element(By.ID, "email")
    email_input.clear()
    email_input.send_keys(test_email)

    # Nhập Họ và tên
    fullname_input = driver.find_element(By.ID, "full_name")
    fullname_input.clear()
    fullname_input.send_keys(test_fullname)

    # Chọn vai trò là Ban Tổ Chức (Organizer)
    role_select = Select(driver.find_element(By.ID, "role"))
    role_select.select_by_value("organizer")

    # Nhập Mật khẩu
    password_input = driver.find_element(By.ID, "password")
    password_input.clear()
    password_input.send_keys(test_password)

    # Nhập Xác nhận mật khẩu
    confirm_password_input = driver.find_element(By.ID, "passwordconfirm")
    confirm_password_input.clear()
    confirm_password_input.send_keys(test_password)

    # Click nút Đăng ký
    submit_button = driver.find_element(
        By.CSS_SELECTOR, "#registerForm button[type='submit']"
    )
    submit_button.click()

    # Chờ chuyển trang sau khi đăng ký thành công (Hệ thống chuyển qua verify-email)
    try:
        wait.until(lambda d: "/auth/verify-email" in d.current_url or "/auth/login" in d.current_url)
        print(f"-> Registration successful! Redirected to: {driver.current_url}")
    except TimeoutException:
        pytest.fail(f"Đăng ký bị timeout hoặc không chuyển hướng đúng. URL hiện tại: {driver.current_url}")

    # --------------------------------------------------------
    # PHẦN 2: ĐĂNG NHẬP BẰNG TÀI KHOẢN ORGANIZER VỪA ĐĂNG KÝ
    # --------------------------------------------------------
    print("[Step 2] Opening login page")
    driver.get(LOGIN_URL)

    # Nhập Username
    login_username_input = wait.until(
        EC.visibility_of_element_located((By.ID, "username"))
    )
    login_username_input.clear()
    login_username_input.send_keys(test_username)

    # Nhập Mật khẩu
    login_password_input = driver.find_element(By.ID, "password")
    login_password_input.clear()
    login_password_input.send_keys(test_password)

    # Click nút Đăng nhập
    login_button = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#loginForm button[type='submit']"))
    )
    login_button.click()

    # Chờ đăng nhập và chuyển hướng khỏi trang Login
    try:
        wait.until(lambda d: "/auth/login" not in d.current_url)
    except TimeoutException:
        pytest.fail("Đăng nhập bị timeout hoặc không nhận được phản hồi từ hệ thống.")

    # --------------------------------------------------------
    # PHẦN 3: XÁC MINH ORGANIZER DASHBOARD
    # --------------------------------------------------------
    print("[Step 3] Verifying Organizer Dashboard is displayed")

    # Kiểm tra URL hiện tại có chứa /organizer/dashboard
    assert "/organizer/dashboard" in driver.current_url, (
        f"Đăng nhập thành công nhưng không được dẫn tới Dashboard. URL hiện tại: {driver.current_url}"
    )

    # Kiểm tra Tiêu đề H1 hiển thị đúng "Organizer Dashboard"
    dashboard_title = wait.until(
        EC.visibility_of_element_located((By.TAG_NAME, "h1"))
    )

    assert dashboard_title.text.strip() == "Organizer Dashboard", (
        f"Tiêu đề Dashboard không chính xác. H1 hiện tại: '{dashboard_title.text}'"
    )

    print("\nTC01 PASSED - Registration & Login as Organizer successful!")


if __name__ == "__main__":
    pytest.main(["-v", __file__])