# microbit-spacepyew

SpacePyew! is a small shooter for the micro:bit V2 in micro:bit micropython using the 5x5 LED matrix as a screen and optionally the elecfreaks joystick:bit as input device.
With each hit, the target will be a little bit harder to hit. And it beeps and blinks.

https://user-images.githubusercontent.com/920565/221620164-71e5e233-4ac9-4c82-8ae0-9bf30b56293e.mp4

## Software Dependencies

SpacePyew! requires the micro:bit V2 micropython runtime from https://github.com/microbit-foundation/micropython-microbit-v2 for the SoundEffect API.
This runtime is also what seems to be used on https://python.microbit.org/v/3.
I tested using the 2.1.1 release  (https://github.com/microbit-foundation/micropython-microbit-v2/releases/download/v2.1.1/micropython-microbit-v2.1.1.hex).
If you use the Mu editor to flash, you need to set this up as a custom micropython firmware .hex in the options.

## Hardware

SpacePyew! uses the:

* micro:bit 5x5 LED matrix as a screen
* micro:bit V2 speaker to put out some beep-boop sounds
* micro:bit A and B buttons for basic controls
* joystick:bit joystick and buttons for more comfortable controls
* joystick:bit rumble/vibration motor for fire and impact feeling

## Controls:

* A - move up
* B - fire
* joystick:bit analog Y axis - move up/down
* joystick:bit D - move up
* joystick:bit E - move down
* joystick:bit F - fire
* joystick:bit C - increase difficulty

## Notes on code and features

The code is rather over-engineered and close to the size limits for the main.py of the micro:bit V2 because it contains:
* auto-calibration for joystick:bit analog Y axis
* rumble PWM effect system for joystick:bit vibration motor
* joystick:bit GPIO button polling with debouncing
* real-time game loop and game object system
* smart evasion movement rules for target
* increasing difficulty with number of hits
* sparkling animations
* double buffering like LED display system to avoid flicker
* no code comments because we only have <30kB for main.py on the micro:bit
    
## Links

* https://codewith.mu/
* https://shop.elecfreaks.com/products/elecfreaks-micro-bit-joystick-bit-v2-kit
* http://wiki.elecfreaks.com/en/microbit/expansion-board/joystick-bit-v2/

