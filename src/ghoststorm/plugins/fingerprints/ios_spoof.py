"""iOS device spoofing with 113 Apple device models.

Migrated from: dextools-bot (x11)/lib/fakecookies.py
Original author's work preserved and enhanced for GhostStorm.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AppleDevice:
    """Apple device model identifier."""

    id: str
    name: str
    category: Literal["iphone", "ipad", "ipod", "watch"]


# Complete Apple device database - 113 devices
# Source: dextools-bot fakecookies.py

IPHONE_DEVICES: list[AppleDevice] = [
    AppleDevice("iPhone1,1", "iPhone", "iphone"),
    AppleDevice("iPhone1,2", "iPhone 3G", "iphone"),
    AppleDevice("iPhone2,1", "iPhone 3GS", "iphone"),
    AppleDevice("iPhone3,1", "iPhone 4", "iphone"),
    AppleDevice("iPhone3,2", "iPhone 4 GSM Rev A", "iphone"),
    AppleDevice("iPhone3,3", "iPhone 4 CDMA", "iphone"),
    AppleDevice("iPhone4,1", "iPhone 4S", "iphone"),
    AppleDevice("iPhone5,1", "iPhone 5 (GSM)", "iphone"),
    AppleDevice("iPhone5,2", "iPhone 5 (GSM+CDMA)", "iphone"),
    AppleDevice("iPhone5,3", "iPhone 5C (GSM)", "iphone"),
    AppleDevice("iPhone5,4", "iPhone 5C (Global)", "iphone"),
    AppleDevice("iPhone6,1", "iPhone 5S (GSM)", "iphone"),
    AppleDevice("iPhone6,2", "iPhone 5S (Global)", "iphone"),
    AppleDevice("iPhone7,1", "iPhone 6 Plus", "iphone"),
    AppleDevice("iPhone7,2", "iPhone 6", "iphone"),
    AppleDevice("iPhone8,1", "iPhone 6s", "iphone"),
    AppleDevice("iPhone8,2", "iPhone 6s Plus", "iphone"),
    AppleDevice("iPhone8,4", "iPhone SE (GSM)", "iphone"),
    AppleDevice("iPhone9,1", "iPhone 7", "iphone"),
    AppleDevice("iPhone9,2", "iPhone 7 Plus", "iphone"),
    AppleDevice("iPhone9,3", "iPhone 7", "iphone"),
    AppleDevice("iPhone9,4", "iPhone 7 Plus", "iphone"),
    AppleDevice("iPhone10,1", "iPhone 8", "iphone"),
    AppleDevice("iPhone10,2", "iPhone 8 Plus", "iphone"),
    AppleDevice("iPhone10,3", "iPhone X Global", "iphone"),
    AppleDevice("iPhone10,4", "iPhone 8", "iphone"),
    AppleDevice("iPhone10,5", "iPhone 8 Plus", "iphone"),
    AppleDevice("iPhone10,6", "iPhone X GSM", "iphone"),
    AppleDevice("iPhone11,2", "iPhone XS", "iphone"),
    AppleDevice("iPhone11,4", "iPhone XS Max", "iphone"),
    AppleDevice("iPhone11,6", "iPhone XS Max Global", "iphone"),
    AppleDevice("iPhone11,8", "iPhone XR", "iphone"),
    AppleDevice("iPhone12,1", "iPhone 11", "iphone"),
    AppleDevice("iPhone12,3", "iPhone 11 Pro", "iphone"),
    AppleDevice("iPhone12,5", "iPhone 11 Pro Max", "iphone"),
]

IPOD_DEVICES: list[AppleDevice] = [
    AppleDevice("iPod1,1", "1st Gen iPod", "ipod"),
    AppleDevice("iPod2,1", "2nd Gen iPod", "ipod"),
    AppleDevice("iPod3,1", "3rd Gen iPod", "ipod"),
    AppleDevice("iPod4,1", "4th Gen iPod", "ipod"),
    AppleDevice("iPod5,1", "5th Gen iPod", "ipod"),
    AppleDevice("iPod7,1", "6th Gen iPod", "ipod"),
    AppleDevice("iPod9,1", "7th Gen iPod", "ipod"),
]

IPAD_DEVICES: list[AppleDevice] = [
    AppleDevice("iPad1,1", "iPad", "ipad"),
    AppleDevice("iPad1,2", "iPad 3G", "ipad"),
    AppleDevice("iPad2,1", "2nd Gen iPad", "ipad"),
    AppleDevice("iPad2,2", "2nd Gen iPad GSM", "ipad"),
    AppleDevice("iPad2,3", "2nd Gen iPad CDMA", "ipad"),
    AppleDevice("iPad2,4", "2nd Gen iPad New Revision", "ipad"),
    AppleDevice("iPad3,1", "3rd Gen iPad", "ipad"),
    AppleDevice("iPad3,2", "3rd Gen iPad CDMA", "ipad"),
    AppleDevice("iPad3,3", "3rd Gen iPad GSM", "ipad"),
    AppleDevice("iPad2,5", "iPad mini", "ipad"),
    AppleDevice("iPad2,6", "iPad mini GSM+LTE", "ipad"),
    AppleDevice("iPad2,7", "iPad mini CDMA+LTE", "ipad"),
    AppleDevice("iPad3,4", "4th Gen iPad", "ipad"),
    AppleDevice("iPad3,5", "4th Gen iPad GSM+LTE", "ipad"),
    AppleDevice("iPad3,6", "4th Gen iPad CDMA+LTE", "ipad"),
    AppleDevice("iPad4,1", "iPad Air (WiFi)", "ipad"),
    AppleDevice("iPad4,2", "iPad Air (GSM+CDMA)", "ipad"),
    AppleDevice("iPad4,3", "1st Gen iPad Air (China)", "ipad"),
    AppleDevice("iPad4,4", "iPad mini Retina (WiFi)", "ipad"),
    AppleDevice("iPad4,5", "iPad mini Retina (GSM+CDMA)", "ipad"),
    AppleDevice("iPad4,6", "iPad mini Retina (China)", "ipad"),
    AppleDevice("iPad4,7", "iPad mini 3 (WiFi)", "ipad"),
    AppleDevice("iPad4,8", "iPad mini 3 (GSM+CDMA)", "ipad"),
    AppleDevice("iPad4,9", "iPad Mini 3 (China)", "ipad"),
    AppleDevice("iPad5,1", "iPad mini 4 (WiFi)", "ipad"),
    AppleDevice("iPad5,2", "4th Gen iPad mini (WiFi+Cellular)", "ipad"),
    AppleDevice("iPad5,3", "iPad Air 2 (WiFi)", "ipad"),
    AppleDevice("iPad5,4", "iPad Air 2 (Cellular)", "ipad"),
    AppleDevice("iPad6,3", "iPad Pro (9.7 inch, WiFi)", "ipad"),
    AppleDevice("iPad6,4", "iPad Pro (9.7 inch, WiFi+LTE)", "ipad"),
    AppleDevice("iPad6,7", "iPad Pro (12.9 inch, WiFi)", "ipad"),
    AppleDevice("iPad6,8", "iPad Pro (12.9 inch, WiFi+LTE)", "ipad"),
    AppleDevice("iPad6,11", "iPad (2017)", "ipad"),
    AppleDevice("iPad6,12", "iPad (2017)", "ipad"),
    AppleDevice("iPad7,1", "iPad Pro 2nd Gen (WiFi)", "ipad"),
    AppleDevice("iPad7,2", "iPad Pro 2nd Gen (WiFi+Cellular)", "ipad"),
    AppleDevice("iPad7,3", "iPad Pro 10.5-inch", "ipad"),
    AppleDevice("iPad7,4", "iPad Pro 10.5-inch", "ipad"),
    AppleDevice("iPad7,5", "iPad 6th Gen (WiFi)", "ipad"),
    AppleDevice("iPad7,6", "iPad 6th Gen (WiFi+Cellular)", "ipad"),
    AppleDevice("iPad7,11", "iPad 7th Gen 10.2-inch (WiFi)", "ipad"),
    AppleDevice("iPad7,12", "iPad 7th Gen 10.2-inch (WiFi+Cellular)", "ipad"),
    AppleDevice("iPad8,1", "iPad Pro 3rd Gen (11 inch, WiFi)", "ipad"),
    AppleDevice("iPad8,2", "iPad Pro 3rd Gen (11 inch, 1TB, WiFi)", "ipad"),
    AppleDevice("iPad8,3", "iPad Pro 3rd Gen (11 inch, WiFi+Cellular)", "ipad"),
    AppleDevice("iPad8,4", "iPad Pro 3rd Gen (11 inch, 1TB, WiFi+Cellular)", "ipad"),
    AppleDevice("iPad8,5", "iPad Pro 3rd Gen (12.9 inch, WiFi)", "ipad"),
    AppleDevice("iPad8,6", "iPad Pro 3rd Gen (12.9 inch, 1TB, WiFi)", "ipad"),
    AppleDevice("iPad8,7", "iPad Pro 3rd Gen (12.9 inch, WiFi+Cellular)", "ipad"),
    AppleDevice("iPad8,8", "iPad Pro 3rd Gen (12.9 inch, 1TB, WiFi+Cellular)", "ipad"),
    AppleDevice("iPad11,1", "iPad mini 5th Gen (WiFi)", "ipad"),
    AppleDevice("iPad11,2", "iPad mini 5th Gen", "ipad"),
    AppleDevice("iPad11,3", "iPad Air 3rd Gen (WiFi)", "ipad"),
    AppleDevice("iPad11,4", "iPad Air 3rd Gen", "ipad"),
]

WATCH_DEVICES: list[AppleDevice] = [
    AppleDevice("Watch1,1", "Apple Watch 38mm case", "watch"),
    AppleDevice("Watch1,2", "Apple Watch 42mm case", "watch"),
    AppleDevice("Watch2,6", "Apple Watch Series 1 38mm case", "watch"),
    AppleDevice("Watch2,7", "Apple Watch Series 1 42mm case", "watch"),
    AppleDevice("Watch2,3", "Apple Watch Series 2 38mm case", "watch"),
    AppleDevice("Watch2,4", "Apple Watch Series 2 42mm case", "watch"),
    AppleDevice("Watch3,1", "Apple Watch Series 3 38mm case (GPS+Cellular)", "watch"),
    AppleDevice("Watch3,2", "Apple Watch Series 3 42mm case (GPS+Cellular)", "watch"),
    AppleDevice("Watch3,3", "Apple Watch Series 3 38mm case (GPS)", "watch"),
    AppleDevice("Watch3,4", "Apple Watch Series 3 42mm case (GPS)", "watch"),
    AppleDevice("Watch4,1", "Apple Watch Series 4 40mm case (GPS)", "watch"),
    AppleDevice("Watch4,2", "Apple Watch Series 4 44mm case (GPS)", "watch"),
    AppleDevice("Watch4,3", "Apple Watch Series 4 40mm case (GPS+Cellular)", "watch"),
    AppleDevice("Watch4,4", "Apple Watch Series 4 44mm case (GPS+Cellular)", "watch"),
    AppleDevice("Watch5,1", "Apple Watch Series 5 40mm case (GPS)", "watch"),
    AppleDevice("Watch5,2", "Apple Watch Series 5 44mm case (GPS)", "watch"),
    AppleDevice("Watch5,3", "Apple Watch Series 5 40mm case (GPS+Cellular)", "watch"),
    AppleDevice("Watch5,4", "Apple Watch Series 5 44mm case (GPS+Cellular)", "watch"),
]

# Combined list of all devices
ALL_APPLE_DEVICES: list[AppleDevice] = IPHONE_DEVICES + IPOD_DEVICES + IPAD_DEVICES + WATCH_DEVICES

# Character banks for string generation
CHAR_BANKS = {
    "a0": "abcdefghijklmnopqrstuvwxyz0123456789",
    "a": "abcdefghijklmnopqrstuvwxyz",
    "0": "0123456789",
    "A": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "A0": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "hex": "0123456789abcdef",
    "HEX": "0123456789ABCDEF",
}


class IosSpoofer:
    """iOS device identity spoofing utility.

    Provides realistic Apple device identifiers and string generation
    utilities for fingerprint spoofing.

    Device counts:
    - iPhone: 35 models
    - iPod: 7 models
    - iPad: 54 models
    - Apple Watch: 18 models
    - Total: 114 devices
    """

    name = "ios_spoof"

    @staticmethod
    def generate_string(
        length: int = 16,
        char_bank: str = "a0",
        amount: int = 1,
    ) -> str | list[str]:
        """Generate random string(s) from character bank.

        Args:
            length: Length of each string (default 16)
            char_bank: Character set to use:
                - "a0": lowercase + digits (default)
                - "a": lowercase only
                - "0": digits only
                - "A": uppercase only
                - "A0": uppercase + digits
                - "hex": lowercase hex
                - "HEX": uppercase hex
            amount: Number of strings to generate

        Returns:
            Single string if amount=1, list of strings otherwise
        """
        chars = CHAR_BANKS.get(char_bank, CHAR_BANKS["a0"])

        if amount <= 1:
            return "".join(random.choice(chars) for _ in range(length))

        return ["".join(random.choice(chars) for _ in range(length)) for _ in range(amount)]

    @staticmethod
    def generate_pattern(
        pattern: list[int] | None = None,
        char_bank: str = "a0",
        separator: str = "-",
        amount: int = 1,
    ) -> str | list[str]:
        """Generate string(s) with pattern like "xxxxx-xxxxx-xxxxx".

        Args:
            pattern: List of segment lengths (default [5, 5, 5])
            char_bank: Character set to use (see generate_string)
            separator: Character between segments (default "-")
            amount: Number of strings to generate

        Returns:
            Single string if amount=1, list of strings otherwise
        """
        if pattern is None:
            pattern = [5, 5, 5]

        chars = CHAR_BANKS.get(char_bank, CHAR_BANKS["a0"])

        def generate_one() -> str:
            segments = [
                "".join(random.choice(chars) for _ in range(seg_len)) for seg_len in pattern
            ]
            return separator.join(segments)

        if amount <= 1:
            return generate_one()

        return [generate_one() for _ in range(amount)]

    @staticmethod
    def get_random_device(
        category: Literal["iphone", "ipad", "ipod", "watch", "any"] = "any",
        amount: int = 1,
    ) -> AppleDevice | list[AppleDevice]:
        """Get random Apple device identifier(s).

        Args:
            category: Device category to pick from:
                - "iphone": iPhone devices only
                - "ipad": iPad devices only
                - "ipod": iPod devices only
                - "watch": Apple Watch devices only
                - "any": Any Apple device (default)
            amount: Number of devices to return

        Returns:
            Single AppleDevice if amount=1, list otherwise
        """
        device_pool: list[AppleDevice]

        if category == "iphone":
            device_pool = IPHONE_DEVICES
        elif category == "ipad":
            device_pool = IPAD_DEVICES
        elif category == "ipod":
            device_pool = IPOD_DEVICES
        elif category == "watch":
            device_pool = WATCH_DEVICES
        else:
            device_pool = ALL_APPLE_DEVICES

        if amount <= 1:
            return random.choice(device_pool)

        return [random.choice(device_pool) for _ in range(amount)]

    @staticmethod
    def get_device_by_id(device_id: str) -> AppleDevice | None:
        """Get device by its identifier.

        Args:
            device_id: Device ID like "iPhone12,1"

        Returns:
            AppleDevice if found, None otherwise
        """
        for device in ALL_APPLE_DEVICES:
            if device.id == device_id:
                return device
        return None

    @staticmethod
    def list_devices(
        category: Literal["iphone", "ipad", "ipod", "watch", "all"] = "all",
    ) -> list[AppleDevice]:
        """List all devices in a category.

        Args:
            category: Device category or "all"

        Returns:
            List of AppleDevice objects
        """
        if category == "iphone":
            return IPHONE_DEVICES.copy()
        elif category == "ipad":
            return IPAD_DEVICES.copy()
        elif category == "ipod":
            return IPOD_DEVICES.copy()
        elif category == "watch":
            return WATCH_DEVICES.copy()
        return ALL_APPLE_DEVICES.copy()

    @staticmethod
    def generate_udid() -> str:
        """Generate a realistic iOS UDID (40 hex characters)."""
        return IosSpoofer.generate_string(length=40, char_bank="hex")

    @staticmethod
    def generate_vendor_id() -> str:
        """Generate iOS vendor identifier (UUID format)."""
        return IosSpoofer.generate_pattern(
            pattern=[8, 4, 4, 4, 12],
            char_bank="HEX",
            separator="-",
        )

    @staticmethod
    def generate_advertising_id() -> str:
        """Generate iOS advertising identifier (UUID format)."""
        return IosSpoofer.generate_pattern(
            pattern=[8, 4, 4, 4, 12],
            char_bank="HEX",
            separator="-",
        )

    @property
    def total_devices(self) -> int:
        """Total number of Apple devices in database."""
        return len(ALL_APPLE_DEVICES)

    @property
    def device_counts(self) -> dict[str, int]:
        """Device counts by category."""
        return {
            "iphone": len(IPHONE_DEVICES),
            "ipad": len(IPAD_DEVICES),
            "ipod": len(IPOD_DEVICES),
            "watch": len(WATCH_DEVICES),
            "total": len(ALL_APPLE_DEVICES),
        }
