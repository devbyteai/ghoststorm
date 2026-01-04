"""
TikTok X-Gorgon Signature Algorithm

This is the legacy mobile API signature algorithm used by TikTok.
Status: DEPRECATED (still works on some older endpoints)

How it works:
1. Hash params, data, cookies with MD5 (creates 96 hex chars base string)
2. Split into 24 integers (12 from each 32-char MD5 hash section)
3. Add timestamp bytes (4 bytes from unix timestamp)
4. XOR with 20-byte key
5. Apply bit reversal transformation
6. Output format: "0404b0d30000" + 40 hex chars

Headers produced:
- X-Gorgon: The signature (52 hex chars)
- X-Khronos: Unix timestamp used in signature

Source: https://github.com/gaplan/TikTok-X-Gorgon
"""

import hashlib
import time
from typing import Optional


class Gorgon:
    """TikTok X-Gorgon signature generator."""

    # 20-byte XOR key used in the algorithm
    KEY = [
        223, 119, 185, 64, 185, 155, 132, 131, 209, 185,
        203, 209, 247, 194, 185, 133, 195, 208, 251, 195
    ]

    def __init__(
        self,
        params: str,
        data: Optional[str] = None,
        cookies: Optional[str] = None,
        unix: Optional[int] = None
    ) -> None:
        """
        Initialize Gorgon signature generator.

        Args:
            params: URL query parameters string
            data: POST body data (optional)
            cookies: Cookie string (optional)
            unix: Unix timestamp (optional, uses current time if not provided)
        """
        self.params = params
        self.data = data
        self.cookies = cookies
        self.unix = unix or int(time.time())

    def hash(self, data: str) -> str:
        """Generate MD5 hash of data."""
        try:
            return hashlib.md5(data.encode()).hexdigest()
        except Exception:
            return hashlib.md5(data).hexdigest()

    def get_base_string(self) -> str:
        """
        Build the 96-character base string for encryption.

        Format: MD5(params) + MD5(data) + MD5(cookies)
        Each section is 32 hex chars, totaling 96 chars.
        """
        # Start with hashed params
        base_str = self.hash(self.params)

        # Add hashed data or zeros
        if self.data:
            base_str += self.hash(self.data)
        else:
            base_str += "0" * 32

        # Add hashed cookies or zeros
        if self.cookies:
            base_str += self.hash(self.cookies)
        else:
            base_str += "0" * 32

        return base_str

    def get_value(self) -> dict[str, str]:
        """
        Generate the X-Gorgon and X-Khronos headers.

        Returns:
            Dictionary with 'X-Gorgon' and 'X-Khronos' keys
        """
        base_str = self.get_base_string()
        return self.encrypt(base_str)

    def encrypt(self, data: str) -> dict[str, str]:
        """
        Encrypt the base string to produce X-Gorgon signature.

        Args:
            data: 96-character hex string from get_base_string()

        Returns:
            Dictionary with X-Gorgon and X-Khronos headers
        """
        unix = self.unix
        length = 20
        key = self.KEY

        # Build param_list from base string (24 bytes total)
        param_list = []

        # Extract 12 bytes from the base string (3 sections of 4 bytes each)
        for i in range(0, 12, 4):
            temp = data[8 * i : 8 * (i + 1)]
            for j in range(4):
                h = int(temp[j * 2 : (j + 1) * 2], 16)
                param_list.append(h)

        # Add fixed padding bytes
        param_list.extend([0, 6, 11, 28])

        # Add timestamp bytes (4 bytes from unix timestamp)
        h = int(hex(unix), 16)
        param_list.append((h & 0xFF000000) >> 24)
        param_list.append((h & 0x00FF0000) >> 16)
        param_list.append((h & 0x0000FF00) >> 8)
        param_list.append(h & 0x000000FF)

        # XOR with key
        xor_result_list = []
        for a, b in zip(param_list, key):
            xor_result_list.append(a ^ b)

        # Apply bit transformation
        for i in range(length):
            c = self._reverse(xor_result_list[i])
            d = xor_result_list[(i + 1) % length]
            e = c ^ d
            f = self._rbit_algorithm(e)
            h = (f ^ 0xFFFFFFFF ^ length) & 0xFF
            xor_result_list[i] = h

        # Build result hex string
        result = ""
        for param in xor_result_list:
            result += self._hex_string(param)

        return {
            "X-Gorgon": "0404b0d30000" + result,
            "X-Khronos": str(unix)
        }

    def _rbit_algorithm(self, num: int) -> int:
        """Reverse bits in a byte."""
        result = ""
        tmp_string = bin(num)[2:]

        # Pad to 8 bits
        while len(tmp_string) < 8:
            tmp_string = "0" + tmp_string

        # Reverse the bits
        for i in range(8):
            result += tmp_string[7 - i]

        return int(result, 2)

    def _hex_string(self, num: int) -> str:
        """Convert number to 2-character hex string."""
        tmp_string = hex(num)[2:]
        if len(tmp_string) < 2:
            tmp_string = "0" + tmp_string
        return tmp_string

    def _reverse(self, num: int) -> int:
        """Swap nibbles in a byte."""
        tmp_string = self._hex_string(num)
        return int(tmp_string[1:] + tmp_string[:1], 16)


def generate_signature(
    params: str,
    data: Optional[str] = None,
    cookies: Optional[str] = None,
    unix: Optional[int] = None
) -> dict[str, str]:
    """
    Convenience function to generate X-Gorgon signature.

    Args:
        params: URL query parameters
        data: POST body (optional)
        cookies: Cookie string (optional)
        unix: Unix timestamp (optional)

    Returns:
        Dictionary with X-Gorgon and X-Khronos headers

    Example:
        >>> sig = generate_signature("device_id=123&app_name=musically")
        >>> print(sig['X-Gorgon'])
        '0404b0d30000...'
    """
    return Gorgon(params, data, cookies, unix).get_value()


if __name__ == "__main__":
    # Example usage
    params = "device_id=1234567890&iid=9876543210&device_type=SM-G973N&app_name=musically_go"
    sig = generate_signature(params)
    print(f"X-Gorgon: {sig['X-Gorgon']}")
    print(f"X-Khronos: {sig['X-Khronos']}")
