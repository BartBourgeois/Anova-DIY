// Channel maps: which ESP32 pin listens to what. One table per setup, picked by a build flag in platformio.ini.
// The tables in README.md show the same wiring; change both together.
//
// Board: classic ESP32 dev kit with an ESP32-WROOM-32 module. Pins left out on purpose:
//   0, 2, 12, 15  strapping pins (12 high at boot selects 1.8 V flash and the module won't start)
//   5, 14         driven briefly during boot
//   1, 3          USB serial
//   6-11          the module's own flash
//   16, 17        PSRAM on WROVER modules: use a WROOM
// ADC1 (GPIO 32-39) is the only ADC that works while Wi-Fi is on, so every analog channel sits there.
#pragma once
#include <stdint.h>

enum ChanKind : uint8_t { CH_DIGITAL, CH_ANALOG };

struct Chan {
  const char *name;  // what the pin listens to, as it appears in the output
  uint8_t gpio;
  ChanKind kind;
  float scale;       // analog: volts at the probe per volt at the pin (3.0 behind 20k/10k, 2.0 behind 10k/10k)
  float on_v;        // analog: a rise above this (probe volts) is a power-on; 0 = not a power channel
};

#if defined(J8PROBE_SETUP_J8)
// One ESP32 per break-out. The same harness fits break-out A (main board) and break-out B (power board).
// Header pin n = J8 pin n (j8.md). Supply and GND pins are not channels, except the supply's divider tap.
#define SETUP_NAME "j8"
static const Chan CHANS[] = {
  {"J8.1-6", 36, CH_ANALOG, 3.0f, 4.0f},  // supply, through 20k/10k
  {"J8.24", 39, CH_ANALOG, 1.0f, 0},
  {"J8.25", 34, CH_ANALOG, 1.0f, 0},
  {"J8.26", 35, CH_ANALOG, 1.0f, 0},
  {"J8.7", 32, CH_ANALOG, 1.0f, 0},
  {"J8.9", 33, CH_ANALOG, 1.0f, 0},
  {"J8.8", 4, CH_DIGITAL, 0, 0},
  {"J8.12", 13, CH_DIGITAL, 0, 0},
  {"J8.13", 16, CH_DIGITAL, 0, 0},
  {"J8.14", 17, CH_DIGITAL, 0, 0},
  {"J8.15", 18, CH_DIGITAL, 0, 0},
  {"J8.16", 19, CH_DIGITAL, 0, 0},
  {"J8.18", 21, CH_DIGITAL, 0, 0},
  {"J8.20", 22, CH_DIGITAL, 0, 0},
  {"J8.21", 23, CH_DIGITAL, 0, 0},
  {"J8.27", 25, CH_DIGITAL, 0, 0},
  {"J8.28", 26, CH_DIGITAL, 0, 0},
  {"J8.29", 27, CH_DIGITAL, 0, 0},
};
static const char *const BOOT_UART[] = {nullptr};  // no sniffer starts at boot

#elif defined(J8PROBE_SETUP_AUX)
// The main board's other signs of life, next to the j8 probe on break-out A.
#define SETUP_NAME "aux"
static const Chan CHANS[] = {
  {"VIN JP5.1", 39, CH_ANALOG, 3.0f, 4.0f},  // through 20k/10k
  {"3V3 U15.8", 36, CH_ANALOG, 2.0f, 2.9f},  // through 10k/10k
  {"CS U15.1", 4, CH_DIGITAL, 0, 0},         // flash chip select: activity = the CC3220 ROM reads the flash
  {"J29.1", 16, CH_DIGITAL, 0, 0},           // J29 pins 1 and 2 are the signals; pin 3 is GND (J-112)
  {"J29.2", 17, CH_DIGITAL, 0, 0},
};
// Sniffed from boot, so the main board's first power-up is caught without a command. Which J29 pin is the CC3220's
// TX isn't known yet, so both listen.
static const char *const BOOT_UART[] = {"J29.1", "J29.2", nullptr};

#else
#error "Pick a setup: -DJ8PROBE_SETUP_J8 or -DJ8PROBE_SETUP_AUX"
#endif

#ifndef BOOT_UART_BAUD
#define BOOT_UART_BAUD 115200  // TI's SDK examples print at 115200; override with -DBOOT_UART_BAUD=...
#endif
