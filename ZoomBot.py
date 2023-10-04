import os
import time
from io import BytesIO

from PIL import Image
from selenium import webdriver
from selenium.common import NoSuchElementException, WebDriverException, ElementNotInteractableException, \
    ElementClickInterceptedException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


class ZoomBot:

    def __init__(self, zoom_id, pwd, name, fake_camera_file=None, fake_audio_file=None):
        """
        Create new bot and starting browser
        :param zoom_id: Conference identifier
        :param pwd: Symbols in link after pwd=
        :param name: Bot name
        :param fake_camera_file: Path to video for fake camera (only .y4m and .mjpeg)
        :param fake_audio_file: Path to audio for fake microphone (only .wav)
        """
        self.iframe = None
        self.name = name
        self.pwd = pwd
        self.zoom_id = zoom_id
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # for Chrome >= 109
        if fake_camera_file and fake_audio_file:
            chrome_options.add_argument("--use-fake-ui-for-media-stream")
            chrome_options.add_argument("--use-fake-device-for-media-stream")
            chrome_options.add_argument(f'--use-file-for-fake-video-capture={os.path.abspath(fake_camera_file)}')
            chrome_options.add_argument(f'--use-file-for-fake-audio-capture={os.path.abspath(fake_audio_file)}')
        # chrome_options.add_argument("--headless")
        # chrome_options.headless = True # also works
        self.browser = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

    def connect(self):
        """
        Connect bot to the conference
        :return: Exception if bot already connected
        """
        if self.is_connected():
            raise Exception("Bot already connected!")
        self.browser.get(
            f"https://app.zoom.us/wc/{self.zoom_id}/join?fromPWA=1&pwd={self.pwd}&_x_zm_rtaid=ky0nIy0QQVqw_4OiSwg6pA"
            f".1696254987959.616907727bacb1062f9857ce886fdc4f&_x_zm_rhtaid=251")

        self.iframe = WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.ID, "webclient"))
        )
        self.browser.switch_to.frame(self.iframe)

        input_name = WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.ID, "input-for-name"))
        )
        input_name.send_keys(self.name)
        self.browser.find_element(By.CSS_SELECTOR,
                                  "#root > div > div.preview-new-flow > div > div.preview-meeting-info > button").click()

    def disconnect(self):
        """
        Disconnect bot
        :return:
        """
        if not self.iframe or not self.is_connected():
            return
        self.browser.find_element(By.CSS_SELECTOR,
                                  "#foot-bar > div.footer__leave-btn-container > button").click()
        self.browser.find_element(By.CSS_SELECTOR,
                                  "#wc-footer > div.footer__inner.leave-option-container > div:nth-child(2) > div > "
                                  "div > button").click()

    def is_in_wait_room(self) -> bool:
        """
        Check if bot in wait room
        :return: True if bot in wait room else False
        """
        try:
            self.browser.find_element(By.CLASS_NAME, "waiting-room-container")
        except NoSuchElementException:
            return False
        return True

    def is_connected(self) -> bool:
        """
        Check bot is connected
        :return: True if bot connected else False
        """
        try:
            element = self.browser.find_element(By.CSS_SELECTOR, "#wc-container-left >"
                                                                 " div.meeting-info-container.meeting-info-container--left-side")
            screen = element.screenshot_as_base64
        except NoSuchElementException:
            return False
        except WebDriverException:
            return False
        return True

    def wait_to_connect(self, timeout=10) -> bool:
        """
        Waits to be fully connected
        :param timeout: Timeout in seconds
        :return: True if connected. False if the timeout has expired.
        """
        start_time = time.time()
        while not self.is_connected():
            time.sleep(0.5)
            if time.time() - start_time > timeout:
                return False
        return True

    def _move_mouse(self):
        """
        Move mouse to show footer
        :return:
        """
        ActionChains(self.browser) \
            .move_by_offset(13, 15) \
            .move_by_offset(-13, -15) \
            .perform()

    def accept_sound(self):
        """
        Press button accept computer sound
        :return:
        """
        if not self.is_connected():
            raise Exception("Bot doesn't connected!")
        while True:
            try:
                self.browser.find_element(By.CSS_SELECTOR, "#voip-tab > div > button").click()
                break
            except NoSuchElementException:
                break
            except ElementNotInteractableException:
                time.sleep(0.5)
            except ElementClickInterceptedException:
                time.sleep(0.5)

    def turn_microphone(self):
        """
        Turn on microphone if is off else turn off
        :return:
        """
        if not self.is_connected():
            raise Exception("Bot doesn't connected!")
        self.accept_sound()
        self._move_mouse()
        self._wait_and_click_selector("#foot-bar > div:nth-child(1) > div:nth-child(1) > button")

    def turn_camera(self):
        """
        Turn on camera if is off else turn off
        :return:
        """
        if not self.is_connected():
            raise Exception("Bot doesn't connected!")
        self.accept_sound()
        self._move_mouse()
        self._wait_and_click_selector("#foot-bar > div:nth-child(1) > div:nth-child(2) > button")

    def send_message(self, text: str):
        """
        Send message to chat
        :param text: Message text
        :return:
        """
        if not self.is_connected():
            raise Exception("Bot doesn't connected!")
        self._move_mouse()
        try:
            self.browser.find_element(By.CSS_SELECTOR, "#foot-bar > div.footer__btns-container >"
                                                       " div:nth-child(3) > div.footer-chat-button > button").click()
        except NoSuchElementException:
            pass
        self.browser.find_element(By.CSS_SELECTOR,
                                  "#wc-container-right > div > div.wrapper >"
                                  " div > div.chat-rtf-box__editor-outer >"
                                  " div.chat-rtf-box__editor-wrapper > div > div").send_keys(text)
        self.browser.find_element(By.CSS_SELECTOR,
                                  "#wc-container-right > div > div.wrapper > "
                                  "div > div.chat-rtf-box__editor-outer > div.chat-rtf-box__bottom > button").click()

    def get_messages(self) -> list[dict]:
        """
        Get messages from chat
        :return: list of dicts with keys "from", "to", "time", "text"
        """
        if not self.is_connected():
            raise Exception("Bot doesn't connected!")
        self._move_mouse()
        try:
            self.browser.find_element(By.CSS_SELECTOR, "#foot-bar > div.footer__btns-container >"
                                                       " div:nth-child(3) > div.footer-chat-button > button").click()
        except NoSuchElementException:
            pass

        elements = self.browser.find_elements(By.CLASS_NAME, "new-chat-message__container")

        chat = []

        for element in elements:
            mark = element.get_attribute("aria-label")  # Вы Кому Все, 08:48, uu
            from_to, time, message = mark.split(",", 2)
            is_russian = from_to.find(" Кому ") != -1
            from_people, to_people = from_to.split(" Кому " if is_russian else " to ")
            chat.append({"from": from_people.strip(), "to": to_people.strip(),
                         "time": time.strip(), "text": message.strip()})
        return chat

    def screenshot(self) -> Image:
        """
        Get screenshot of screen
        :return: PIL.Image if connected else Exception
        """
        if not self.is_connected():
            raise Exception("Bot doesn't connected!")
        png = self.browser.get_screenshot_as_png()
        return Image.open(BytesIO(png))

    def close(self):
        """
        Close browser
        :return:
        """
        self.browser.close()

    def _wait_and_click_selector(self, selector):
        while True:
            self._move_mouse()
            time.sleep(0.1)
            try:
                self.browser.find_element(By.CSS_SELECTOR, selector).click()
                break
            except ElementClickInterceptedException:
                continue
