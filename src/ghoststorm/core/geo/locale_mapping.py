"""Comprehensive country-to-locale-timezone mapping for identity coherence.

Maps ISO 3166-1 alpha-2 country codes to:
- Primary locale (BCP 47)
- Language preferences (for Accept-Language header)
- Primary timezone (IANA)
- Approximate center coordinates
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CountryGeoData:
    """Geographic and locale data for a country."""

    country_code: str
    country_name: str
    primary_locale: str
    languages: tuple[str, ...]
    primary_timezone: str
    timezones: tuple[str, ...]
    latitude: float
    longitude: float

    def get_accept_language(self) -> str:
        """Build Accept-Language header value."""
        return build_accept_language(list(self.languages))


@dataclass
class CoherentLocaleData:
    """Resolved locale data for coherent identity."""

    timezone: str
    locale: str
    languages: list[str]
    accept_language: str
    latitude: float
    longitude: float
    country_code: str
    country_name: str


def build_accept_language(languages: list[str]) -> str:
    """Build Accept-Language header with quality values.

    Example: "en-US, en;q=0.9, es;q=0.8"
    """
    if not languages:
        return "en-US, en;q=0.9"

    parts = []
    for i, lang in enumerate(languages[:5]):  # Max 5 languages
        if i == 0:
            parts.append(lang)
        else:
            q = max(0.5, round(0.9 - (i * 0.1), 1))
            parts.append(f"{lang};q={q}")

    return ", ".join(parts)


# Comprehensive country geo data (100+ countries)
COUNTRY_GEO_DATA: dict[str, CountryGeoData] = {
    # ============================================================================
    # NORTH AMERICA
    # ============================================================================
    "US": CountryGeoData(
        country_code="US",
        country_name="United States",
        primary_locale="en-US",
        languages=("en-US", "en", "es-US"),
        primary_timezone="America/New_York",
        timezones=(
            "America/New_York",
            "America/Chicago",
            "America/Denver",
            "America/Los_Angeles",
            "America/Anchorage",
            "Pacific/Honolulu",
        ),
        latitude=37.0902,
        longitude=-95.7129,
    ),
    "CA": CountryGeoData(
        country_code="CA",
        country_name="Canada",
        primary_locale="en-CA",
        languages=("en-CA", "en", "fr-CA"),
        primary_timezone="America/Toronto",
        timezones=(
            "America/Toronto",
            "America/Vancouver",
            "America/Edmonton",
            "America/Winnipeg",
            "America/Halifax",
        ),
        latitude=56.1304,
        longitude=-106.3468,
    ),
    "MX": CountryGeoData(
        country_code="MX",
        country_name="Mexico",
        primary_locale="es-MX",
        languages=("es-MX", "es", "en"),
        primary_timezone="America/Mexico_City",
        timezones=("America/Mexico_City", "America/Cancun", "America/Tijuana"),
        latitude=23.6345,
        longitude=-102.5528,
    ),
    # ============================================================================
    # SOUTH AMERICA
    # ============================================================================
    "BR": CountryGeoData(
        country_code="BR",
        country_name="Brazil",
        primary_locale="pt-BR",
        languages=("pt-BR", "pt", "en"),
        primary_timezone="America/Sao_Paulo",
        timezones=("America/Sao_Paulo", "America/Manaus", "America/Recife"),
        latitude=-14.235,
        longitude=-51.9253,
    ),
    "AR": CountryGeoData(
        country_code="AR",
        country_name="Argentina",
        primary_locale="es-AR",
        languages=("es-AR", "es", "en"),
        primary_timezone="America/Buenos_Aires",
        timezones=("America/Buenos_Aires",),
        latitude=-38.4161,
        longitude=-63.6167,
    ),
    "CO": CountryGeoData(
        country_code="CO",
        country_name="Colombia",
        primary_locale="es-CO",
        languages=("es-CO", "es", "en"),
        primary_timezone="America/Bogota",
        timezones=("America/Bogota",),
        latitude=4.5709,
        longitude=-74.2973,
    ),
    "CL": CountryGeoData(
        country_code="CL",
        country_name="Chile",
        primary_locale="es-CL",
        languages=("es-CL", "es", "en"),
        primary_timezone="America/Santiago",
        timezones=("America/Santiago",),
        latitude=-35.6751,
        longitude=-71.543,
    ),
    "PE": CountryGeoData(
        country_code="PE",
        country_name="Peru",
        primary_locale="es-PE",
        languages=("es-PE", "es", "en"),
        primary_timezone="America/Lima",
        timezones=("America/Lima",),
        latitude=-9.19,
        longitude=-75.0152,
    ),
    "VE": CountryGeoData(
        country_code="VE",
        country_name="Venezuela",
        primary_locale="es-VE",
        languages=("es-VE", "es", "en"),
        primary_timezone="America/Caracas",
        timezones=("America/Caracas",),
        latitude=6.4238,
        longitude=-66.5897,
    ),
    # ============================================================================
    # WESTERN EUROPE
    # ============================================================================
    "GB": CountryGeoData(
        country_code="GB",
        country_name="United Kingdom",
        primary_locale="en-GB",
        languages=("en-GB", "en"),
        primary_timezone="Europe/London",
        timezones=("Europe/London",),
        latitude=55.3781,
        longitude=-3.436,
    ),
    "DE": CountryGeoData(
        country_code="DE",
        country_name="Germany",
        primary_locale="de-DE",
        languages=("de-DE", "de", "en"),
        primary_timezone="Europe/Berlin",
        timezones=("Europe/Berlin",),
        latitude=51.1657,
        longitude=10.4515,
    ),
    "FR": CountryGeoData(
        country_code="FR",
        country_name="France",
        primary_locale="fr-FR",
        languages=("fr-FR", "fr", "en"),
        primary_timezone="Europe/Paris",
        timezones=("Europe/Paris",),
        latitude=46.2276,
        longitude=2.2137,
    ),
    "IT": CountryGeoData(
        country_code="IT",
        country_name="Italy",
        primary_locale="it-IT",
        languages=("it-IT", "it", "en"),
        primary_timezone="Europe/Rome",
        timezones=("Europe/Rome",),
        latitude=41.8719,
        longitude=12.5674,
    ),
    "ES": CountryGeoData(
        country_code="ES",
        country_name="Spain",
        primary_locale="es-ES",
        languages=("es-ES", "es", "ca", "en"),
        primary_timezone="Europe/Madrid",
        timezones=("Europe/Madrid", "Atlantic/Canary"),
        latitude=40.4637,
        longitude=-3.7492,
    ),
    "PT": CountryGeoData(
        country_code="PT",
        country_name="Portugal",
        primary_locale="pt-PT",
        languages=("pt-PT", "pt", "en"),
        primary_timezone="Europe/Lisbon",
        timezones=("Europe/Lisbon", "Atlantic/Azores"),
        latitude=39.3999,
        longitude=-8.2245,
    ),
    "NL": CountryGeoData(
        country_code="NL",
        country_name="Netherlands",
        primary_locale="nl-NL",
        languages=("nl-NL", "nl", "en"),
        primary_timezone="Europe/Amsterdam",
        timezones=("Europe/Amsterdam",),
        latitude=52.1326,
        longitude=5.2913,
    ),
    "BE": CountryGeoData(
        country_code="BE",
        country_name="Belgium",
        primary_locale="nl-BE",
        languages=("nl-BE", "fr-BE", "de-BE", "en"),
        primary_timezone="Europe/Brussels",
        timezones=("Europe/Brussels",),
        latitude=50.5039,
        longitude=4.4699,
    ),
    "CH": CountryGeoData(
        country_code="CH",
        country_name="Switzerland",
        primary_locale="de-CH",
        languages=("de-CH", "fr-CH", "it-CH", "en"),
        primary_timezone="Europe/Zurich",
        timezones=("Europe/Zurich",),
        latitude=46.8182,
        longitude=8.2275,
    ),
    "AT": CountryGeoData(
        country_code="AT",
        country_name="Austria",
        primary_locale="de-AT",
        languages=("de-AT", "de", "en"),
        primary_timezone="Europe/Vienna",
        timezones=("Europe/Vienna",),
        latitude=47.5162,
        longitude=14.5501,
    ),
    "IE": CountryGeoData(
        country_code="IE",
        country_name="Ireland",
        primary_locale="en-IE",
        languages=("en-IE", "en", "ga"),
        primary_timezone="Europe/Dublin",
        timezones=("Europe/Dublin",),
        latitude=53.1424,
        longitude=-7.6921,
    ),
    # ============================================================================
    # NORTHERN EUROPE (SCANDINAVIA)
    # ============================================================================
    "SE": CountryGeoData(
        country_code="SE",
        country_name="Sweden",
        primary_locale="sv-SE",
        languages=("sv-SE", "sv", "en"),
        primary_timezone="Europe/Stockholm",
        timezones=("Europe/Stockholm",),
        latitude=60.1282,
        longitude=18.6435,
    ),
    "NO": CountryGeoData(
        country_code="NO",
        country_name="Norway",
        primary_locale="nb-NO",
        languages=("nb-NO", "no", "en"),
        primary_timezone="Europe/Oslo",
        timezones=("Europe/Oslo",),
        latitude=60.472,
        longitude=8.4689,
    ),
    "DK": CountryGeoData(
        country_code="DK",
        country_name="Denmark",
        primary_locale="da-DK",
        languages=("da-DK", "da", "en"),
        primary_timezone="Europe/Copenhagen",
        timezones=("Europe/Copenhagen",),
        latitude=56.2639,
        longitude=9.5018,
    ),
    "FI": CountryGeoData(
        country_code="FI",
        country_name="Finland",
        primary_locale="fi-FI",
        languages=("fi-FI", "fi", "sv-FI", "en"),
        primary_timezone="Europe/Helsinki",
        timezones=("Europe/Helsinki",),
        latitude=61.9241,
        longitude=25.7482,
    ),
    "IS": CountryGeoData(
        country_code="IS",
        country_name="Iceland",
        primary_locale="is-IS",
        languages=("is-IS", "is", "en"),
        primary_timezone="Atlantic/Reykjavik",
        timezones=("Atlantic/Reykjavik",),
        latitude=64.9631,
        longitude=-19.0208,
    ),
    # ============================================================================
    # EASTERN EUROPE
    # ============================================================================
    "PL": CountryGeoData(
        country_code="PL",
        country_name="Poland",
        primary_locale="pl-PL",
        languages=("pl-PL", "pl", "en"),
        primary_timezone="Europe/Warsaw",
        timezones=("Europe/Warsaw",),
        latitude=51.9194,
        longitude=19.1451,
    ),
    "CZ": CountryGeoData(
        country_code="CZ",
        country_name="Czech Republic",
        primary_locale="cs-CZ",
        languages=("cs-CZ", "cs", "en"),
        primary_timezone="Europe/Prague",
        timezones=("Europe/Prague",),
        latitude=49.8175,
        longitude=15.473,
    ),
    "HU": CountryGeoData(
        country_code="HU",
        country_name="Hungary",
        primary_locale="hu-HU",
        languages=("hu-HU", "hu", "en"),
        primary_timezone="Europe/Budapest",
        timezones=("Europe/Budapest",),
        latitude=47.1625,
        longitude=19.5033,
    ),
    "RO": CountryGeoData(
        country_code="RO",
        country_name="Romania",
        primary_locale="ro-RO",
        languages=("ro-RO", "ro", "en"),
        primary_timezone="Europe/Bucharest",
        timezones=("Europe/Bucharest",),
        latitude=45.9432,
        longitude=24.9668,
    ),
    "BG": CountryGeoData(
        country_code="BG",
        country_name="Bulgaria",
        primary_locale="bg-BG",
        languages=("bg-BG", "bg", "en"),
        primary_timezone="Europe/Sofia",
        timezones=("Europe/Sofia",),
        latitude=42.7339,
        longitude=25.4858,
    ),
    "SK": CountryGeoData(
        country_code="SK",
        country_name="Slovakia",
        primary_locale="sk-SK",
        languages=("sk-SK", "sk", "en"),
        primary_timezone="Europe/Bratislava",
        timezones=("Europe/Bratislava",),
        latitude=48.669,
        longitude=19.699,
    ),
    "HR": CountryGeoData(
        country_code="HR",
        country_name="Croatia",
        primary_locale="hr-HR",
        languages=("hr-HR", "hr", "en"),
        primary_timezone="Europe/Zagreb",
        timezones=("Europe/Zagreb",),
        latitude=45.1,
        longitude=15.2,
    ),
    "SI": CountryGeoData(
        country_code="SI",
        country_name="Slovenia",
        primary_locale="sl-SI",
        languages=("sl-SI", "sl", "en"),
        primary_timezone="Europe/Ljubljana",
        timezones=("Europe/Ljubljana",),
        latitude=46.1512,
        longitude=14.9955,
    ),
    "RS": CountryGeoData(
        country_code="RS",
        country_name="Serbia",
        primary_locale="sr-RS",
        languages=("sr-RS", "sr", "en"),
        primary_timezone="Europe/Belgrade",
        timezones=("Europe/Belgrade",),
        latitude=44.0165,
        longitude=21.0059,
    ),
    "UA": CountryGeoData(
        country_code="UA",
        country_name="Ukraine",
        primary_locale="uk-UA",
        languages=("uk-UA", "uk", "ru", "en"),
        primary_timezone="Europe/Kiev",
        timezones=("Europe/Kiev",),
        latitude=48.3794,
        longitude=31.1656,
    ),
    "RU": CountryGeoData(
        country_code="RU",
        country_name="Russia",
        primary_locale="ru-RU",
        languages=("ru-RU", "ru", "en"),
        primary_timezone="Europe/Moscow",
        timezones=("Europe/Moscow", "Asia/Yekaterinburg", "Asia/Novosibirsk", "Asia/Vladivostok"),
        latitude=61.524,
        longitude=105.3188,
    ),
    "BY": CountryGeoData(
        country_code="BY",
        country_name="Belarus",
        primary_locale="be-BY",
        languages=("be-BY", "ru-BY", "en"),
        primary_timezone="Europe/Minsk",
        timezones=("Europe/Minsk",),
        latitude=53.7098,
        longitude=27.9534,
    ),
    # ============================================================================
    # SOUTHERN EUROPE / MEDITERRANEAN
    # ============================================================================
    "GR": CountryGeoData(
        country_code="GR",
        country_name="Greece",
        primary_locale="el-GR",
        languages=("el-GR", "el", "en"),
        primary_timezone="Europe/Athens",
        timezones=("Europe/Athens",),
        latitude=39.0742,
        longitude=21.8243,
    ),
    "TR": CountryGeoData(
        country_code="TR",
        country_name="Turkey",
        primary_locale="tr-TR",
        languages=("tr-TR", "tr", "en"),
        primary_timezone="Europe/Istanbul",
        timezones=("Europe/Istanbul",),
        latitude=38.9637,
        longitude=35.2433,
    ),
    "CY": CountryGeoData(
        country_code="CY",
        country_name="Cyprus",
        primary_locale="el-CY",
        languages=("el-CY", "tr-CY", "en"),
        primary_timezone="Asia/Nicosia",
        timezones=("Asia/Nicosia",),
        latitude=35.1264,
        longitude=33.4299,
    ),
    "MT": CountryGeoData(
        country_code="MT",
        country_name="Malta",
        primary_locale="mt-MT",
        languages=("mt-MT", "en-MT", "en"),
        primary_timezone="Europe/Malta",
        timezones=("Europe/Malta",),
        latitude=35.9375,
        longitude=14.3754,
    ),
    # ============================================================================
    # EAST ASIA
    # ============================================================================
    "JP": CountryGeoData(
        country_code="JP",
        country_name="Japan",
        primary_locale="ja-JP",
        languages=("ja-JP", "ja", "en"),
        primary_timezone="Asia/Tokyo",
        timezones=("Asia/Tokyo",),
        latitude=36.2048,
        longitude=138.2529,
    ),
    "KR": CountryGeoData(
        country_code="KR",
        country_name="South Korea",
        primary_locale="ko-KR",
        languages=("ko-KR", "ko", "en"),
        primary_timezone="Asia/Seoul",
        timezones=("Asia/Seoul",),
        latitude=35.9078,
        longitude=127.7669,
    ),
    "CN": CountryGeoData(
        country_code="CN",
        country_name="China",
        primary_locale="zh-CN",
        languages=("zh-CN", "zh", "en"),
        primary_timezone="Asia/Shanghai",
        timezones=("Asia/Shanghai", "Asia/Urumqi"),
        latitude=35.8617,
        longitude=104.1954,
    ),
    "TW": CountryGeoData(
        country_code="TW",
        country_name="Taiwan",
        primary_locale="zh-TW",
        languages=("zh-TW", "zh", "en"),
        primary_timezone="Asia/Taipei",
        timezones=("Asia/Taipei",),
        latitude=23.6978,
        longitude=120.9605,
    ),
    "HK": CountryGeoData(
        country_code="HK",
        country_name="Hong Kong",
        primary_locale="zh-HK",
        languages=("zh-HK", "zh-TW", "en-HK", "en"),
        primary_timezone="Asia/Hong_Kong",
        timezones=("Asia/Hong_Kong",),
        latitude=22.3193,
        longitude=114.1694,
    ),
    "MO": CountryGeoData(
        country_code="MO",
        country_name="Macau",
        primary_locale="zh-MO",
        languages=("zh-MO", "pt-MO", "en"),
        primary_timezone="Asia/Macau",
        timezones=("Asia/Macau",),
        latitude=22.1987,
        longitude=113.5439,
    ),
    "MN": CountryGeoData(
        country_code="MN",
        country_name="Mongolia",
        primary_locale="mn-MN",
        languages=("mn-MN", "mn", "en"),
        primary_timezone="Asia/Ulaanbaatar",
        timezones=("Asia/Ulaanbaatar",),
        latitude=46.8625,
        longitude=103.8467,
    ),
    # ============================================================================
    # SOUTHEAST ASIA
    # ============================================================================
    "SG": CountryGeoData(
        country_code="SG",
        country_name="Singapore",
        primary_locale="en-SG",
        languages=("en-SG", "en", "zh-SG", "ms-SG"),
        primary_timezone="Asia/Singapore",
        timezones=("Asia/Singapore",),
        latitude=1.3521,
        longitude=103.8198,
    ),
    "MY": CountryGeoData(
        country_code="MY",
        country_name="Malaysia",
        primary_locale="ms-MY",
        languages=("ms-MY", "ms", "en-MY", "zh-MY"),
        primary_timezone="Asia/Kuala_Lumpur",
        timezones=("Asia/Kuala_Lumpur",),
        latitude=4.2105,
        longitude=101.9758,
    ),
    "TH": CountryGeoData(
        country_code="TH",
        country_name="Thailand",
        primary_locale="th-TH",
        languages=("th-TH", "th", "en"),
        primary_timezone="Asia/Bangkok",
        timezones=("Asia/Bangkok",),
        latitude=15.870,
        longitude=100.9925,
    ),
    "VN": CountryGeoData(
        country_code="VN",
        country_name="Vietnam",
        primary_locale="vi-VN",
        languages=("vi-VN", "vi", "en"),
        primary_timezone="Asia/Ho_Chi_Minh",
        timezones=("Asia/Ho_Chi_Minh",),
        latitude=14.0583,
        longitude=108.2772,
    ),
    "ID": CountryGeoData(
        country_code="ID",
        country_name="Indonesia",
        primary_locale="id-ID",
        languages=("id-ID", "id", "en"),
        primary_timezone="Asia/Jakarta",
        timezones=("Asia/Jakarta", "Asia/Makassar", "Asia/Jayapura"),
        latitude=-0.7893,
        longitude=113.9213,
    ),
    "PH": CountryGeoData(
        country_code="PH",
        country_name="Philippines",
        primary_locale="fil-PH",
        languages=("fil-PH", "en-PH", "en"),
        primary_timezone="Asia/Manila",
        timezones=("Asia/Manila",),
        latitude=12.8797,
        longitude=121.774,
    ),
    "MM": CountryGeoData(
        country_code="MM",
        country_name="Myanmar",
        primary_locale="my-MM",
        languages=("my-MM", "my", "en"),
        primary_timezone="Asia/Yangon",
        timezones=("Asia/Yangon",),
        latitude=21.9162,
        longitude=95.956,
    ),
    "KH": CountryGeoData(
        country_code="KH",
        country_name="Cambodia",
        primary_locale="km-KH",
        languages=("km-KH", "km", "en"),
        primary_timezone="Asia/Phnom_Penh",
        timezones=("Asia/Phnom_Penh",),
        latitude=12.5657,
        longitude=104.991,
    ),
    "LA": CountryGeoData(
        country_code="LA",
        country_name="Laos",
        primary_locale="lo-LA",
        languages=("lo-LA", "lo", "en"),
        primary_timezone="Asia/Vientiane",
        timezones=("Asia/Vientiane",),
        latitude=19.8563,
        longitude=102.4955,
    ),
    "BN": CountryGeoData(
        country_code="BN",
        country_name="Brunei",
        primary_locale="ms-BN",
        languages=("ms-BN", "ms", "en"),
        primary_timezone="Asia/Brunei",
        timezones=("Asia/Brunei",),
        latitude=4.5353,
        longitude=114.7277,
    ),
    # ============================================================================
    # SOUTH ASIA
    # ============================================================================
    "IN": CountryGeoData(
        country_code="IN",
        country_name="India",
        primary_locale="hi-IN",
        languages=("hi-IN", "en-IN", "en"),
        primary_timezone="Asia/Kolkata",
        timezones=("Asia/Kolkata",),
        latitude=20.5937,
        longitude=78.9629,
    ),
    "PK": CountryGeoData(
        country_code="PK",
        country_name="Pakistan",
        primary_locale="ur-PK",
        languages=("ur-PK", "en-PK", "en"),
        primary_timezone="Asia/Karachi",
        timezones=("Asia/Karachi",),
        latitude=30.3753,
        longitude=69.3451,
    ),
    "BD": CountryGeoData(
        country_code="BD",
        country_name="Bangladesh",
        primary_locale="bn-BD",
        languages=("bn-BD", "bn", "en"),
        primary_timezone="Asia/Dhaka",
        timezones=("Asia/Dhaka",),
        latitude=23.685,
        longitude=90.3563,
    ),
    "LK": CountryGeoData(
        country_code="LK",
        country_name="Sri Lanka",
        primary_locale="si-LK",
        languages=("si-LK", "ta-LK", "en"),
        primary_timezone="Asia/Colombo",
        timezones=("Asia/Colombo",),
        latitude=7.8731,
        longitude=80.7718,
    ),
    "NP": CountryGeoData(
        country_code="NP",
        country_name="Nepal",
        primary_locale="ne-NP",
        languages=("ne-NP", "ne", "en"),
        primary_timezone="Asia/Kathmandu",
        timezones=("Asia/Kathmandu",),
        latitude=28.3949,
        longitude=84.124,
    ),
    # ============================================================================
    # MIDDLE EAST
    # ============================================================================
    "AE": CountryGeoData(
        country_code="AE",
        country_name="United Arab Emirates",
        primary_locale="ar-AE",
        languages=("ar-AE", "ar", "en"),
        primary_timezone="Asia/Dubai",
        timezones=("Asia/Dubai",),
        latitude=23.4241,
        longitude=53.8478,
    ),
    "SA": CountryGeoData(
        country_code="SA",
        country_name="Saudi Arabia",
        primary_locale="ar-SA",
        languages=("ar-SA", "ar", "en"),
        primary_timezone="Asia/Riyadh",
        timezones=("Asia/Riyadh",),
        latitude=23.8859,
        longitude=45.0792,
    ),
    "IL": CountryGeoData(
        country_code="IL",
        country_name="Israel",
        primary_locale="he-IL",
        languages=("he-IL", "he", "ar-IL", "en"),
        primary_timezone="Asia/Jerusalem",
        timezones=("Asia/Jerusalem",),
        latitude=31.0461,
        longitude=34.8516,
    ),
    "QA": CountryGeoData(
        country_code="QA",
        country_name="Qatar",
        primary_locale="ar-QA",
        languages=("ar-QA", "ar", "en"),
        primary_timezone="Asia/Qatar",
        timezones=("Asia/Qatar",),
        latitude=25.3548,
        longitude=51.1839,
    ),
    "KW": CountryGeoData(
        country_code="KW",
        country_name="Kuwait",
        primary_locale="ar-KW",
        languages=("ar-KW", "ar", "en"),
        primary_timezone="Asia/Kuwait",
        timezones=("Asia/Kuwait",),
        latitude=29.3117,
        longitude=47.4818,
    ),
    "BH": CountryGeoData(
        country_code="BH",
        country_name="Bahrain",
        primary_locale="ar-BH",
        languages=("ar-BH", "ar", "en"),
        primary_timezone="Asia/Bahrain",
        timezones=("Asia/Bahrain",),
        latitude=26.0667,
        longitude=50.5577,
    ),
    "OM": CountryGeoData(
        country_code="OM",
        country_name="Oman",
        primary_locale="ar-OM",
        languages=("ar-OM", "ar", "en"),
        primary_timezone="Asia/Muscat",
        timezones=("Asia/Muscat",),
        latitude=21.4735,
        longitude=55.9754,
    ),
    "JO": CountryGeoData(
        country_code="JO",
        country_name="Jordan",
        primary_locale="ar-JO",
        languages=("ar-JO", "ar", "en"),
        primary_timezone="Asia/Amman",
        timezones=("Asia/Amman",),
        latitude=30.5852,
        longitude=36.2384,
    ),
    "LB": CountryGeoData(
        country_code="LB",
        country_name="Lebanon",
        primary_locale="ar-LB",
        languages=("ar-LB", "ar", "fr", "en"),
        primary_timezone="Asia/Beirut",
        timezones=("Asia/Beirut",),
        latitude=33.8547,
        longitude=35.8623,
    ),
    "IR": CountryGeoData(
        country_code="IR",
        country_name="Iran",
        primary_locale="fa-IR",
        languages=("fa-IR", "fa", "en"),
        primary_timezone="Asia/Tehran",
        timezones=("Asia/Tehran",),
        latitude=32.4279,
        longitude=53.688,
    ),
    "IQ": CountryGeoData(
        country_code="IQ",
        country_name="Iraq",
        primary_locale="ar-IQ",
        languages=("ar-IQ", "ar", "ku", "en"),
        primary_timezone="Asia/Baghdad",
        timezones=("Asia/Baghdad",),
        latitude=33.2232,
        longitude=43.6793,
    ),
    # ============================================================================
    # OCEANIA
    # ============================================================================
    "AU": CountryGeoData(
        country_code="AU",
        country_name="Australia",
        primary_locale="en-AU",
        languages=("en-AU", "en"),
        primary_timezone="Australia/Sydney",
        timezones=(
            "Australia/Sydney",
            "Australia/Melbourne",
            "Australia/Brisbane",
            "Australia/Perth",
            "Australia/Adelaide",
        ),
        latitude=-25.2744,
        longitude=133.7751,
    ),
    "NZ": CountryGeoData(
        country_code="NZ",
        country_name="New Zealand",
        primary_locale="en-NZ",
        languages=("en-NZ", "en", "mi"),
        primary_timezone="Pacific/Auckland",
        timezones=("Pacific/Auckland",),
        latitude=-40.9006,
        longitude=174.886,
    ),
    # ============================================================================
    # AFRICA
    # ============================================================================
    "ZA": CountryGeoData(
        country_code="ZA",
        country_name="South Africa",
        primary_locale="en-ZA",
        languages=("en-ZA", "en", "af", "zu"),
        primary_timezone="Africa/Johannesburg",
        timezones=("Africa/Johannesburg",),
        latitude=-30.5595,
        longitude=22.9375,
    ),
    "EG": CountryGeoData(
        country_code="EG",
        country_name="Egypt",
        primary_locale="ar-EG",
        languages=("ar-EG", "ar", "en"),
        primary_timezone="Africa/Cairo",
        timezones=("Africa/Cairo",),
        latitude=26.8206,
        longitude=30.8025,
    ),
    "NG": CountryGeoData(
        country_code="NG",
        country_name="Nigeria",
        primary_locale="en-NG",
        languages=("en-NG", "en", "ha", "yo", "ig"),
        primary_timezone="Africa/Lagos",
        timezones=("Africa/Lagos",),
        latitude=9.082,
        longitude=8.6753,
    ),
    "KE": CountryGeoData(
        country_code="KE",
        country_name="Kenya",
        primary_locale="sw-KE",
        languages=("sw-KE", "en-KE", "en"),
        primary_timezone="Africa/Nairobi",
        timezones=("Africa/Nairobi",),
        latitude=-0.0236,
        longitude=37.9062,
    ),
    "MA": CountryGeoData(
        country_code="MA",
        country_name="Morocco",
        primary_locale="ar-MA",
        languages=("ar-MA", "ar", "fr", "en"),
        primary_timezone="Africa/Casablanca",
        timezones=("Africa/Casablanca",),
        latitude=31.7917,
        longitude=-7.0926,
    ),
    "DZ": CountryGeoData(
        country_code="DZ",
        country_name="Algeria",
        primary_locale="ar-DZ",
        languages=("ar-DZ", "ar", "fr", "en"),
        primary_timezone="Africa/Algiers",
        timezones=("Africa/Algiers",),
        latitude=28.0339,
        longitude=1.6596,
    ),
    "TN": CountryGeoData(
        country_code="TN",
        country_name="Tunisia",
        primary_locale="ar-TN",
        languages=("ar-TN", "ar", "fr", "en"),
        primary_timezone="Africa/Tunis",
        timezones=("Africa/Tunis",),
        latitude=33.8869,
        longitude=9.5375,
    ),
    "GH": CountryGeoData(
        country_code="GH",
        country_name="Ghana",
        primary_locale="en-GH",
        languages=("en-GH", "en"),
        primary_timezone="Africa/Accra",
        timezones=("Africa/Accra",),
        latitude=7.9465,
        longitude=-1.0232,
    ),
    "ET": CountryGeoData(
        country_code="ET",
        country_name="Ethiopia",
        primary_locale="am-ET",
        languages=("am-ET", "am", "en"),
        primary_timezone="Africa/Addis_Ababa",
        timezones=("Africa/Addis_Ababa",),
        latitude=9.145,
        longitude=40.4897,
    ),
    "TZ": CountryGeoData(
        country_code="TZ",
        country_name="Tanzania",
        primary_locale="sw-TZ",
        languages=("sw-TZ", "en-TZ", "en"),
        primary_timezone="Africa/Dar_es_Salaam",
        timezones=("Africa/Dar_es_Salaam",),
        latitude=-6.369,
        longitude=34.8888,
    ),
    "UG": CountryGeoData(
        country_code="UG",
        country_name="Uganda",
        primary_locale="en-UG",
        languages=("en-UG", "en", "sw"),
        primary_timezone="Africa/Kampala",
        timezones=("Africa/Kampala",),
        latitude=1.3733,
        longitude=32.2903,
    ),
    # ============================================================================
    # CENTRAL ASIA
    # ============================================================================
    "KZ": CountryGeoData(
        country_code="KZ",
        country_name="Kazakhstan",
        primary_locale="kk-KZ",
        languages=("kk-KZ", "ru-KZ", "en"),
        primary_timezone="Asia/Almaty",
        timezones=("Asia/Almaty", "Asia/Aqtobe"),
        latitude=48.0196,
        longitude=66.9237,
    ),
    "UZ": CountryGeoData(
        country_code="UZ",
        country_name="Uzbekistan",
        primary_locale="uz-UZ",
        languages=("uz-UZ", "uz", "ru", "en"),
        primary_timezone="Asia/Tashkent",
        timezones=("Asia/Tashkent",),
        latitude=41.3775,
        longitude=64.5853,
    ),
    # ============================================================================
    # CARIBBEAN / CENTRAL AMERICA
    # ============================================================================
    "CU": CountryGeoData(
        country_code="CU",
        country_name="Cuba",
        primary_locale="es-CU",
        languages=("es-CU", "es"),
        primary_timezone="America/Havana",
        timezones=("America/Havana",),
        latitude=21.5218,
        longitude=-77.7812,
    ),
    "DO": CountryGeoData(
        country_code="DO",
        country_name="Dominican Republic",
        primary_locale="es-DO",
        languages=("es-DO", "es", "en"),
        primary_timezone="America/Santo_Domingo",
        timezones=("America/Santo_Domingo",),
        latitude=18.7357,
        longitude=-70.1627,
    ),
    "PR": CountryGeoData(
        country_code="PR",
        country_name="Puerto Rico",
        primary_locale="es-PR",
        languages=("es-PR", "es", "en-PR", "en"),
        primary_timezone="America/Puerto_Rico",
        timezones=("America/Puerto_Rico",),
        latitude=18.2208,
        longitude=-66.5901,
    ),
    "JM": CountryGeoData(
        country_code="JM",
        country_name="Jamaica",
        primary_locale="en-JM",
        languages=("en-JM", "en"),
        primary_timezone="America/Jamaica",
        timezones=("America/Jamaica",),
        latitude=18.1096,
        longitude=-77.2975,
    ),
    "PA": CountryGeoData(
        country_code="PA",
        country_name="Panama",
        primary_locale="es-PA",
        languages=("es-PA", "es", "en"),
        primary_timezone="America/Panama",
        timezones=("America/Panama",),
        latitude=8.538,
        longitude=-80.7821,
    ),
    "CR": CountryGeoData(
        country_code="CR",
        country_name="Costa Rica",
        primary_locale="es-CR",
        languages=("es-CR", "es", "en"),
        primary_timezone="America/Costa_Rica",
        timezones=("America/Costa_Rica",),
        latitude=9.7489,
        longitude=-83.7534,
    ),
    "GT": CountryGeoData(
        country_code="GT",
        country_name="Guatemala",
        primary_locale="es-GT",
        languages=("es-GT", "es"),
        primary_timezone="America/Guatemala",
        timezones=("America/Guatemala",),
        latitude=15.7835,
        longitude=-90.2308,
    ),
    "EC": CountryGeoData(
        country_code="EC",
        country_name="Ecuador",
        primary_locale="es-EC",
        languages=("es-EC", "es", "en"),
        primary_timezone="America/Guayaquil",
        timezones=("America/Guayaquil", "Pacific/Galapagos"),
        latitude=-1.8312,
        longitude=-78.1834,
    ),
    "UY": CountryGeoData(
        country_code="UY",
        country_name="Uruguay",
        primary_locale="es-UY",
        languages=("es-UY", "es", "en"),
        primary_timezone="America/Montevideo",
        timezones=("America/Montevideo",),
        latitude=-32.5228,
        longitude=-55.7658,
    ),
    "PY": CountryGeoData(
        country_code="PY",
        country_name="Paraguay",
        primary_locale="es-PY",
        languages=("es-PY", "es", "gn"),
        primary_timezone="America/Asuncion",
        timezones=("America/Asuncion",),
        latitude=-23.4425,
        longitude=-58.4438,
    ),
    "BO": CountryGeoData(
        country_code="BO",
        country_name="Bolivia",
        primary_locale="es-BO",
        languages=("es-BO", "es", "qu", "ay"),
        primary_timezone="America/La_Paz",
        timezones=("America/La_Paz",),
        latitude=-16.2902,
        longitude=-63.5887,
    ),
}


# ============================================================================
# LOOKUP FUNCTIONS
# ============================================================================


def get_coherent_locale_data(
    country_code: str,
    timezone: str | None = None,
) -> CoherentLocaleData:
    """Get coherent locale data for a country.

    Args:
        country_code: ISO 3166-1 alpha-2 country code (e.g., "US", "JP")
        timezone: Optional specific timezone to use (must be valid for country)

    Returns:
        CoherentLocaleData with all locale information
    """
    country_code = country_code.upper()

    # Get country data or fallback to US
    data = COUNTRY_GEO_DATA.get(country_code, COUNTRY_GEO_DATA["US"])

    # Use provided timezone if valid for country, otherwise use primary
    if timezone and timezone in data.timezones:
        tz = timezone
    else:
        tz = data.primary_timezone

    return CoherentLocaleData(
        timezone=tz,
        locale=data.primary_locale,
        languages=list(data.languages),
        accept_language=build_accept_language(list(data.languages)),
        latitude=data.latitude,
        longitude=data.longitude,
        country_code=data.country_code,
        country_name=data.country_name,
    )


def get_coherent_locale_from_locale(locale: str) -> CoherentLocaleData:
    """Get coherent locale data from a locale string.

    Args:
        locale: BCP 47 locale (e.g., "en-US", "ja-JP")

    Returns:
        CoherentLocaleData matching the locale
    """
    # Extract country code from locale
    parts = locale.replace("_", "-").split("-")
    if len(parts) >= 2:
        country_code = parts[-1].upper()
    else:
        country_code = "US"

    # Check if we have data for this country
    if country_code in COUNTRY_GEO_DATA:
        return get_coherent_locale_data(country_code)

    # Fallback to US
    return get_coherent_locale_data("US")


def get_timezone_for_country(country_code: str) -> str:
    """Get primary timezone for a country."""
    country_code = country_code.upper()
    data = COUNTRY_GEO_DATA.get(country_code, COUNTRY_GEO_DATA["US"])
    return data.primary_timezone


def get_locale_for_country(country_code: str) -> str:
    """Get primary locale for a country."""
    country_code = country_code.upper()
    data = COUNTRY_GEO_DATA.get(country_code, COUNTRY_GEO_DATA["US"])
    return data.primary_locale


def get_coords_for_country(country_code: str) -> tuple[float, float]:
    """Get approximate center coordinates for a country."""
    country_code = country_code.upper()
    data = COUNTRY_GEO_DATA.get(country_code, COUNTRY_GEO_DATA["US"])
    return (data.latitude, data.longitude)


def is_valid_country(country_code: str) -> bool:
    """Check if country code is valid and has data."""
    return country_code.upper() in COUNTRY_GEO_DATA
