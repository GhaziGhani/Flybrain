#!/usr/bin/env bash
# Compile fly_bridge.ino for an Arduino Uno (ATmega328P) without the Arduino IDE,
# using avr-gcc and the official core: https://github.com/arduino/ArduinoCore-avr
#   usage: tools/check_sketch.sh /path/to/ArduinoCore-avr
set -euo pipefail
CORE="${1:?path to ArduinoCore-avr}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$(mktemp -d)"
MCU=atmega328p
DEFS="-DF_CPU=16000000L -DARDUINO=10819 -DARDUINO_AVR_UNO -DARDUINO_ARCH_AVR"
INC="-I$CORE/cores/arduino -I$CORE/variants/standard"
COMMON="-mmcu=$MCU $DEFS $INC -Os -ffunction-sections -fdata-sections -Wall -Wextra"

{ echo '#include <Arduino.h>'; echo '#line 1 "fly_bridge.ino"'; cat "$HERE/arduino/fly_bridge/fly_bridge.ino"; } > "$OUT/sketch.cpp"
avr-g++ $COMMON -std=gnu++11 -fno-exceptions -fno-threadsafe-statics -c "$OUT/sketch.cpp" -o "$OUT/sketch.o"

for f in "$CORE"/cores/arduino/*.c; do avr-gcc $COMMON -std=gnu11 -w -c "$f" -o "$OUT/$(basename "$f").o"; done
for f in "$CORE"/cores/arduino/*.cpp; do avr-g++ $COMMON -std=gnu++11 -fno-exceptions -fno-threadsafe-statics -w -c "$f" -o "$OUT/$(basename "$f").o"; done
for f in "$CORE"/cores/arduino/*.S; do avr-gcc -mmcu=$MCU $DEFS $INC -x assembler-with-cpp -c "$f" -o "$OUT/$(basename "$f").o"; done

avr-gcc -mmcu=$MCU -Os -Wl,--gc-sections -o "$OUT/fly_bridge.elf" "$OUT"/*.o -lm
avr-objcopy -O ihex -R .eeprom "$OUT/fly_bridge.elf" "$OUT/fly_bridge.hex"
avr-size --format=avr --mcu=$MCU "$OUT/fly_bridge.elf"
echo "hex: $OUT/fly_bridge.hex"
