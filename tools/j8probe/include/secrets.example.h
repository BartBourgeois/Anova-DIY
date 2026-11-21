// Copy to secrets.h (gitignored) to join a Wi-Fi network. Without secrets.h the j8 setup opens its own access point,
// "j8probe-XXXXXX" at 192.168.4.1, with the password AP_PASS ("j8probe-ap" unless defined here). The aux setup
// without secrets.h reports over USB only and uses Wi-Fi for scanning.
#pragma once
#define WIFI_SSID "your-network"
#define WIFI_PASS "your-password"
// #define AP_PASS "something-else"
