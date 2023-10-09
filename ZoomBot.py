import os
import time
from io import BytesIO

import cv2
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
from MediaServer import MediaServer
from threading import Thread
import wave


class MediaDeviceStream:
    def __init__(self, port, video_stream, audio_file):
        self.audio_file = audio_file
        self.video_stream = video_stream
        self.port = port
        self.running = False
        ret, frame = video_stream.read()
        self.media_server = MediaServer(self.port, frame.shape[0], frame.shape[1])
        self.media_server.add_audio_path(self.audio_file)
        self.server_thread = Thread(target=self.media_server.run)
        self.server_thread.daemon = True
        self.reading_thread = Thread(target=self.read_stream)
        self.reading_thread.daemon = True

    def read_stream(self):
        spf = 1 / self.video_stream.get(cv2.CAP_PROP_FPS)
        while self.running:
            start = time.time()
            ret, frame = self.video_stream.read()
            if ret:
                self.media_server.add_next_frame(frame)
            else:
                self.video_stream.set(cv2.CAP_PROP_POS_FRAMES, 0)
            wait_time = spf - (time.time() - start)
            if wait_time > 0:
                time.sleep(wait_time)

    def get_inject_code(self):
        return """var fps = 60;

const canvas = document.createElement("canvas");
canvas.setAttribute('id', 'fake_camera_stream');
const context = canvas.getContext('2d');

const stream = canvas.captureStream(fps);

var audio = new Audio("https://127.0.0.1:PORT/audio_file");
loaded = false;
audio.loop = true;
audio.play();
audio.onloadeddata = function(){
    const audio_stream = audio.captureStream()
    const track = audio_stream.getAudioTracks()[0];
    
    stream.addTrack(track);
    loaded = true;
}


canvas.style.display="none";

var img = new Image;
img.onload = function(){
  canvas.width = this.naturalWidth;
  canvas.height = this.naturalHeight;

  setInterval(draw, 1./fps);

};
img.src = "https://127.0.0.1:PORT/video_stream";

function draw() {
  context.drawImage(img, 0,0);
}

navigator.mediaDevices.getUserMedia = () => Promise.resolve(stream);

document.querySelector("body").appendChild(canvas);
""".replace("PORT", str(self.port))

    def run(self):
        self.running = True
        self.server_thread.start()
        self.reading_thread.start()


class ZoomBot:

    def __init__(self, zoom_id, pwd, name, media_stream=None):
        """
        Create new bot and starting browser
        :param zoom_id: Conference identifier
        :param pwd: Symbols in link after pwd=
        :param name: Bot name
        :param media_stream: MediaDeviceStream object
        """
        self.media_stream = media_stream
        self.iframe = None
        self.name = name
        self.pwd = pwd
        self.zoom_id = zoom_id
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--use-fake-ui-for-media-stream")
        chrome_options.add_argument("--use-fake-device-for-media-stream")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--autoplay-policy=no-user-gesture-required')
        # Optimization
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-client-side-phishing-detection")
        chrome_options.add_argument("--disable-crash-reporter")
        chrome_options.add_argument("--disable-oopr-debug-crash-dump")
        chrome_options.add_argument("--no-crash-upload")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-low-res-tiling")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
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
                                                                 "div.meeting-info-container.meeting-info-container"
                                                                 "--left-side")
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

    def check_accepted(self):
        elem = self.browser.find_element(By.CSS_SELECTOR,
                                         "#foot-bar > div:nth-child(1) > div:nth-child(1) > button")
        if elem.find_element(By.CLASS_NAME,
                             "footer-button-base__button-label").text.find("аудиоконференцию") != -1:
            return False
        return True

    def accept_sound(self):
        """
        Press button accept computer sound
        :return:
        """
        if not self.is_connected():
            raise Exception("Bot doesn't connected!")
        if self.check_accepted():
            return
        while True:
            try:
                self.browser.find_element(By.CSS_SELECTOR, "#voip-tab > div > button").click()
                if not self.check_accepted():
                    self._move_mouse()
                    self._wait_and_click_selector("#foot-bar > div:nth-child(1) > div:nth-child(1) > button")
                    continue
                break
            except NoSuchElementException:
                if not self.check_accepted():
                    self._move_mouse()
                    self._wait_and_click_selector("#foot-bar > div:nth-child(1) > div:nth-child(1) > button")
                    continue
                break
            except ElementNotInteractableException:
                time.sleep(0.5)
            except ElementClickInterceptedException:
                time.sleep(0.5)

    def inject_stream(self):
        """
        Injects Media stream for camera streaming
        :return:
        """
        try:
            self.browser.find_element(By.ID, "fake_camera_stream")
        except NoSuchElementException:
            if self.media_stream:
                self.browser.execute_script(self.media_stream.get_inject_code())

    def check_microphone_turn(self):
        elem = self.browser.find_element(By.CSS_SELECTOR,
                                         "#foot-bar > div:nth-child(1) > div:nth-child(1) > button")
        if elem.find_element(By.CLASS_NAME,
                             "footer-button-base__button-label").text.find("Выключить") != -1:
            return True
        return False

    def turn_microphone(self, state):
        """
        Turn on microphone if is off else turn off
        :return:
        """
        if not self.is_connected():
            raise Exception("Bot doesn't connected!")
        self.inject_stream()
        self.accept_sound()
        self._move_mouse()
        if self.check_microphone_turn() != state:
            self._wait_and_click_selector("#foot-bar > div:nth-child(1) > div:nth-child(1) > button")

    def turn_camera(self):
        """
        Turn on camera if is off else turn off
        :return:
        """
        if not self.is_connected():
            raise Exception("Bot doesn't connected!")
        self.inject_stream()
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
