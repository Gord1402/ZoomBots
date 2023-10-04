# ZoomBot

ZoomBot is a Python class that allows you to create a bot to connect to Zoom conferences and perform various actions, such as turning on/off the camera and microphone, sending messages to the chat, and taking screenshots.

## Installation

To use ZoomBot, you need to have Python 3.8 or later installed on your machine. You also need to install the following packages:

- `selenium`
- `Pillow`

You can install these packages using pip:


`pip install selenium Pillow`


## Usage

To use ZoomBot, you first need to create an instance of the class with the following parameters:

- `zoom_id`: The conference identifier.
- `pwd`: The symbols in the link after pwd=.
- `name`: The name of the bot.
- `fake_camera_file` (optional): The path to a video file for a fake camera (only .y4m and .mjpeg files are supported).
- `fake_audio_file` (optional): The path to an audio file for a fake microphone (only .wav files are supported).

Once you have created an instance of the class, you can connect to the conference using the connect method. You can then perform various actions using the other methods provided by the class.

## Methods

The following methods are available in the ZoomBot class:

- `connect()`: Connects the bot to the conference.
- `disconnect()`: Disconnects the bot from the conference.
- `is_in_wait_room() -> bool`: Returns True if the bot is in the wait room, otherwise False.
- `is_connected() -> bool`: Returns True if the bot is connected to the conference, otherwise False.
- `wait_to_connect(timeout=10) -> bool`: Waiting for connection and return True. return False if the timeout has expired.
- `_move_mouse()`: Moves the mouse to show the footer.
- `accept_sound()`: Presses the button to accept computer sound.
- `turn_microphone()`: Turns the microphone on or off.
- `turn_camera()`: Turns the camera on or off.
- `send_message(text:str)`: Sends a message to the chat.
- `get_messages() -> list[dict]`: Returns a list of dictionaries with information about the messages in the chat. Each dictionary has the following keys: "from", "to", "time", and "text".
- `screenshot()` -> Image: Takes a screenshot of the screen and returns a PIL.Image object.
- `close()`: Closes the browser.

## Example

Here is an example of how to use ZoomBot:

```python
from ZoomBot import ZoomBot

bot = ZoomBot(zoom_id="123456789", pwd="abcd1234", name="My Bot")
bot.connect()

bot.wait_to_connect()

# Turn on camera and microphone
bot.turn_camera()
bot.turn_microphone()

# Send a message to the chat
bot.send_message("Hello, everyone!")

# Take a screenshot
screenshot = bot.screenshot()
screenshot.show()

bot.disconnect()
bot.close()
```

## License

ZoomBot is licensed under the MIT License. See [LICENSE](LICENSE) for more information.
