"""Proxy aggregator for downloading and managing proxy lists from multiple sources."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

import aiohttp


@dataclass
class ProxySource:
    """A proxy source definition."""

    name: str
    url: str
    proxy_type: str = "http"  # http, socks4, socks5
    scrape_type: str = "raw_txt"  # raw_txt, html_table, proxynova, hidemy, spys, geonode, proxylistorg
    enabled: bool = True


class ProxyAggregator:
    """Aggregates proxies from multiple GitHub and public sources.

    Downloads proxy lists from various sources, deduplicates them,
    and saves to the data/proxies directory.

    Usage:
        ```python
        aggregator = ProxyAggregator()
        count = await aggregator.refresh_all()
        print(f"Downloaded {count} proxies")
        ```
    """

    # Proxy sources - verified working as of 2024
    SOURCES: list[ProxySource] = [
        # ============================================================
        # HTML SCRAPING SOURCES - Require special parsers
        # ============================================================
        # Free-Proxy-List.net Family
        ProxySource("freeproxylist", "https://free-proxy-list.net/", scrape_type="html_table"),
        ProxySource("sslproxies", "https://www.sslproxies.org/", scrape_type="html_table"),
        ProxySource("usproxyorg", "https://www.us-proxy.org/", scrape_type="html_table"),
        ProxySource("ukproxyorg", "https://free-proxy-list.net/uk-proxy.html", scrape_type="html_table"),
        ProxySource("anonproxylist", "https://free-proxy-list.net/anonymous-proxy.html", scrape_type="html_table"),
        ProxySource("socks_proxy", "https://www.socks-proxy.net/", scrape_type="html_table"),
        # ProxyNova
        ProxySource("proxynova", "https://www.proxynova.com/proxy-server-list/", scrape_type="proxynova"),
        ProxySource("proxynova_us", "https://www.proxynova.com/proxy-server-list/country-us/", scrape_type="proxynova"),
        ProxySource("proxynova_uk", "https://www.proxynova.com/proxy-server-list/country-gb/", scrape_type="proxynova"),
        ProxySource("proxynova_de", "https://www.proxynova.com/proxy-server-list/country-de/", scrape_type="proxynova"),
        ProxySource("proxynova_fr", "https://www.proxynova.com/proxy-server-list/country-fr/", scrape_type="proxynova"),
        ProxySource("proxynova_elite", "https://www.proxynova.com/proxy-server-list/elite-proxies/", scrape_type="proxynova"),
        ProxySource("proxynova_anon", "https://www.proxynova.com/proxy-server-list/anonymous-proxies/", scrape_type="proxynova"),
        ProxySource("proxynova_israel", "https://www.proxynova.com/proxy-server-list/country-il/", scrape_type="proxynova"),
        # HideMy.name
        ProxySource("hidemy", "https://hidemy.name/en/proxy-list/?type=hs", scrape_type="hidemy"),
        ProxySource("hidemy_socks4", "https://hidemy.name/en/proxy-list/?type=4", scrape_type="hidemy"),
        ProxySource("hidemy_socks5", "https://hidemy.name/en/proxy-list/?type=5", scrape_type="hidemy"),
        ProxySource("hidemy_anon", "https://hidemy.name/en/proxy-list/?anon=34", scrape_type="hidemy"),
        ProxySource("hidemy_us", "https://hidemy.name/en/proxy-list/?country=US", scrape_type="hidemy"),
        ProxySource("hidemy_uk", "https://hidemy.name/en/proxy-list/?country=GB", scrape_type="hidemy"),
        ProxySource("hidemy_israel", "https://hidemy.name/en/proxy-list/?country=IL", scrape_type="hidemy"),
        # ProxyListPlus
        ProxySource("proxylistplus_1", "https://list.proxylistplus.com/Fresh-HTTP-Proxy-List-1", scrape_type="html_table"),
        ProxySource("proxylistplus_2", "https://list.proxylistplus.com/Fresh-HTTP-Proxy-List-2", scrape_type="html_table"),
        ProxySource("proxylistplus_3", "https://list.proxylistplus.com/Fresh-HTTP-Proxy-List-3", scrape_type="html_table"),
        ProxySource("proxylistplus_4", "https://list.proxylistplus.com/Fresh-HTTP-Proxy-List-4", scrape_type="html_table"),
        ProxySource("proxylistplus_5", "https://list.proxylistplus.com/Fresh-HTTP-Proxy-List-5", scrape_type="html_table"),
        ProxySource("proxylistplus_ssl", "https://list.proxylistplus.com/SSL-List-1", scrape_type="html_table"),
        # FreeProxy.World
        ProxySource("freeproxyworld_1", "https://www.freeproxy.world/?type=http&anonymity=&country=&speed=&port=&page=1", scrape_type="html_table"),
        ProxySource("freeproxyworld_2", "https://www.freeproxy.world/?type=http&anonymity=&country=&speed=&port=&page=2", scrape_type="html_table"),
        ProxySource("freeproxyworld_3", "https://www.freeproxy.world/?type=http&anonymity=&country=&speed=&port=&page=3", scrape_type="html_table"),
        ProxySource("freeproxyworld_https", "https://www.freeproxy.world/?type=https&anonymity=&country=&speed=&port=&page=1", scrape_type="html_table"),
        ProxySource("freeproxyworld_socks4", "https://www.freeproxy.world/?type=socks4&anonymity=&country=&speed=&port=&page=1", scrape_type="html_table"),
        ProxySource("freeproxyworld_socks5", "https://www.freeproxy.world/?type=socks5&anonymity=&country=&speed=&port=&page=1", scrape_type="html_table"),
        ProxySource("freeproxyworld_israel", "https://www.freeproxy.world/?type=&anonymity=&country=IL&speed=&port=&page=1", scrape_type="html_table"),
        # FreeProxy.cz
        ProxySource("freeproxycz_1", "http://free-proxy.cz/en/proxylist/main/1", scrape_type="html_table"),
        ProxySource("freeproxycz_2", "http://free-proxy.cz/en/proxylist/main/2", scrape_type="html_table"),
        ProxySource("freeproxycz_3", "http://free-proxy.cz/en/proxylist/main/3", scrape_type="html_table"),
        ProxySource("freeproxycz_4", "http://free-proxy.cz/en/proxylist/main/4", scrape_type="html_table"),
        ProxySource("freeproxycz_5", "http://free-proxy.cz/en/proxylist/main/5", scrape_type="html_table"),
        ProxySource("freeproxycz_us", "http://free-proxy.cz/en/proxylist/country/US/all/ping/all", scrape_type="html_table"),
        ProxySource("freeproxycz_israel", "http://free-proxy.cz/en/proxylist/country/IL/all/ping/all", scrape_type="html_table"),
        # Spys.one
        ProxySource("spysone_http", "https://spys.one/en/http-proxy-list/", scrape_type="spys"),
        ProxySource("spysone_anon", "https://spys.one/en/anonymous-proxy-list/", scrape_type="spys"),
        ProxySource("spysone_socks", "https://spys.one/en/socks-proxy-list/", scrape_type="spys"),
        ProxySource("spysone_israel", "https://spys.one/free-proxy-list/IL/", scrape_type="spys"),
        # Geonode
        ProxySource("geonode_1", "https://geonode.com/free-proxy-list", scrape_type="geonode"),
        ProxySource("geonode_us", "https://geonode.com/free-proxy-list?country=US", scrape_type="geonode"),
        ProxySource("geonode_uk", "https://geonode.com/free-proxy-list?country=GB", scrape_type="geonode"),
        ProxySource("geonode_israel", "https://geonode.com/free-proxy-list?country=IL", scrape_type="geonode"),
        # Proxy-List.org
        ProxySource("proxylistorg_1", "https://proxy-list.org/english/index.php?p=1", scrape_type="proxylistorg"),
        ProxySource("proxylistorg_2", "https://proxy-list.org/english/index.php?p=2", scrape_type="proxylistorg"),
        ProxySource("proxylistorg_3", "https://proxy-list.org/english/index.php?p=3", scrape_type="proxylistorg"),
        # ============================================================
        # RAW TXT SOURCES - Simple IP:PORT lists
        # ============================================================
        # Tier 1: Massive lists
        ProxySource(
            "mishakorzik",
            "https://raw.githubusercontent.com/mishakorzik/100000-Proxy/main/proxy.txt",
        ),
        ProxySource(
            "ercin_http",
            "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/http.txt",
        ),
        ProxySource(
            "ercin_socks4",
            "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "ercin_socks5",
            "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/socks5.txt",
            "socks5",
        ),
        ProxySource(
            "speedx_http", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
        ),
        ProxySource(
            "speedx_socks4",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "speedx_socks5",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            "socks5",
        ),
        # Tier 2: Fresh/verified lists
        ProxySource(
            "prxchk_http", "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt"
        ),
        ProxySource(
            "prxchk_socks4",
            "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "prxchk_socks5",
            "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt",
            "socks5",
        ),
        ProxySource(
            "monosans", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt"
        ),
        ProxySource(
            "hookzof_socks5",
            "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
            "socks5",
        ),
        # Tier 3: Additional sources
        ProxySource(
            "murong_http", "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/http.txt"
        ),
        ProxySource(
            "murong_socks4",
            "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "murong_socks5",
            "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks5.txt",
            "socks5",
        ),
        ProxySource(
            "seven_http",
            "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/http.txt",
        ),
        ProxySource(
            "seven_socks4",
            "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "seven_socks5",
            "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/socks5.txt",
            "socks5",
        ),
        ProxySource("alii_http", "https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/http.txt"),
        ProxySource(
            "p4p_http", "https://raw.githubusercontent.com/proxy4parsing/proxy-list/main/http.txt"
        ),
        ProxySource(
            "jetkai",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
        ),
        ProxySource(
            "clarketm",
            "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
        ),
        ProxySource(
            "sunny", "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt"
        ),
        # ============================================================
        # LIVE API ENDPOINTS - Updated every 1-30 minutes
        # ============================================================
        # ProxyScrape API - updates every 5 minutes
        ProxySource(
            "proxyscrape_http",
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        ),
        ProxySource(
            "proxyscrape_socks4",
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks4&timeout=10000&country=all",
            "socks4",
        ),
        ProxySource(
            "proxyscrape_socks5",
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all",
            "socks5",
        ),
        # proxy-list.download API - updates daily
        ProxySource(
            "proxylist_dl_http",
            "https://www.proxy-list.download/api/v1/get?type=http",
        ),
        ProxySource(
            "proxylist_dl_https",
            "https://www.proxy-list.download/api/v1/get?type=https",
        ),
        ProxySource(
            "proxylist_dl_socks4",
            "https://www.proxy-list.download/api/v1/get?type=socks4",
            "socks4",
        ),
        ProxySource(
            "proxylist_dl_socks5",
            "https://www.proxy-list.download/api/v1/get?type=socks5",
            "socks5",
        ),
        # Geonode free proxy list API
        ProxySource(
            "geonode_http",
            "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=http",
        ),
        ProxySource(
            "geonode_socks4",
            "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=socks4",
            "socks4",
        ),
        ProxySource(
            "geonode_socks5",
            "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=socks5",
            "socks5",
        ),
        # OpenProxyList
        ProxySource(
            "openproxy_http",
            "https://openproxylist.xyz/http.txt",
        ),
        ProxySource(
            "openproxy_socks4",
            "https://openproxylist.xyz/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "openproxy_socks5",
            "https://openproxylist.xyz/socks5.txt",
            "socks5",
        ),
        # ============================================================
        # GITHUB SOURCES - Auto-updated via GitHub Actions (hourly/daily)
        # ============================================================
        # Proxifly - updates every 5 minutes
        ProxySource(
            "proxifly_http",
            "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
        ),
        ProxySource(
            "proxifly_socks4",
            "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks4/data.txt",
            "socks4",
        ),
        ProxySource(
            "proxifly_socks5",
            "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt",
            "socks5",
        ),
        ProxySource(
            "proxifly_all",
            "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt",
        ),
        # Skillter/ProxyGather - updates every 30 minutes
        ProxySource(
            "skillter_http",
            "https://raw.githubusercontent.com/Skillter/ProxyGather/master/proxies/working-proxies-http.txt",
        ),
        ProxySource(
            "skillter_socks4",
            "https://raw.githubusercontent.com/Skillter/ProxyGather/master/proxies/working-proxies-socks4.txt",
            "socks4",
        ),
        ProxySource(
            "skillter_socks5",
            "https://raw.githubusercontent.com/Skillter/ProxyGather/master/proxies/working-proxies-socks5.txt",
            "socks5",
        ),
        ProxySource(
            "skillter_all",
            "https://raw.githubusercontent.com/Skillter/ProxyGather/master/proxies/working-proxies-all.txt",
        ),
        # officialputuid/KangProxy - daily updates
        ProxySource(
            "kangproxy_http",
            "https://raw.githubusercontent.com/officialputuid/KangProxy/KangProxy/http/http.txt",
        ),
        ProxySource(
            "kangproxy_https",
            "https://raw.githubusercontent.com/officialputuid/KangProxy/KangProxy/https/https.txt",
        ),
        ProxySource(
            "kangproxy_socks4",
            "https://raw.githubusercontent.com/officialputuid/KangProxy/KangProxy/socks4/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "kangproxy_socks5",
            "https://raw.githubusercontent.com/officialputuid/KangProxy/KangProxy/socks5/socks5.txt",
            "socks5",
        ),
        # vakhov/fresh-proxy-list - updates every 5-20 minutes
        ProxySource(
            "vakhov_http",
            "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt",
        ),
        ProxySource(
            "vakhov_https",
            "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/https.txt",
        ),
        ProxySource(
            "vakhov_socks4",
            "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "vakhov_socks5",
            "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/socks5.txt",
            "socks5",
        ),
        # ShiftyTR - hourly updates
        ProxySource(
            "shiftytr",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/proxy.txt",
        ),
        # roosterkid/openproxylist - hourly updates
        ProxySource(
            "roosterkid_http",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
        ),
        ProxySource(
            "roosterkid_socks4",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS4_RAW.txt",
            "socks4",
        ),
        ProxySource(
            "roosterkid_socks5",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
            "socks5",
        ),
        # mmpx12/proxy-list - frequent updates
        ProxySource(
            "mmpx12_http",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
        ),
        ProxySource(
            "mmpx12_https",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/https.txt",
        ),
        ProxySource(
            "mmpx12_socks4",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "mmpx12_socks5",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
            "socks5",
        ),
        # rdavydov/proxy-list
        ProxySource(
            "rdavydov_http",
            "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt",
        ),
        ProxySource(
            "rdavydov_socks4",
            "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "rdavydov_socks5",
            "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks5.txt",
            "socks5",
        ),
        # zloi-user/hideip.me
        ProxySource(
            "hideip_http",
            "https://raw.githubusercontent.com/zloi-user/hideip.me/main/http.txt",
        ),
        ProxySource(
            "hideip_socks4",
            "https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "hideip_socks5",
            "https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks5.txt",
            "socks5",
        ),
        # Zaeem20/FREE_PROXIES_LIST
        ProxySource(
            "zaeem_http",
            "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/http.txt",
        ),
        ProxySource(
            "zaeem_https",
            "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/https.txt",
        ),
        ProxySource(
            "zaeem_socks4",
            "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "zaeem_socks5",
            "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/socks5.txt",
            "socks5",
        ),
        #Proxy-Spider
        ProxySource(
            "proxyspider_http",
            "https://raw.githubusercontent.com/Proxy-Spider/proxy-spider/main/proxies/http/http.txt",
        ),
        ProxySource(
            "proxyspider_socks4",
            "https://raw.githubusercontent.com/Proxy-Spider/proxy-spider/main/proxies/socks4/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "proxyspider_socks5",
            "https://raw.githubusercontent.com/Proxy-Spider/proxy-spider/main/proxies/socks5/socks5.txt",
            "socks5",
        ),
        # im-razvan/proxy_list
        ProxySource(
            "imrazvan_http",
            "https://raw.githubusercontent.com/im-razvan/proxy_list/main/http.txt",
        ),
        ProxySource(
            "imrazvan_socks4",
            "https://raw.githubusercontent.com/im-razvan/proxy_list/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "imrazvan_socks5",
            "https://raw.githubusercontent.com/im-razvan/proxy_list/main/socks5.txt",
            "socks5",
        ),
        # UptimerBot/proxy-list
        ProxySource(
            "uptimer_http",
            "https://raw.githubusercontent.com/UptimerBot/proxy-list/main/proxies/http.txt",
        ),
        ProxySource(
            "uptimer_socks4",
            "https://raw.githubusercontent.com/UptimerBot/proxy-list/main/proxies/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "uptimer_socks5",
            "https://raw.githubusercontent.com/UptimerBot/proxy-list/main/proxies/socks5.txt",
            "socks5",
        ),
        # mertguvencli/http-proxy-list
        ProxySource(
            "mertguvencli",
            "https://raw.githubusercontent.com/mertguvencli/http-proxy-list/main/proxy-list/data.txt",
        ),
        # saschazesiger/Free-Proxies
        ProxySource(
            "saschazesiger_http",
            "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/http.txt",
        ),
        ProxySource(
            "saschazesiger_socks4",
            "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "saschazesiger_socks5",
            "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/socks5.txt",
            "socks5",
        ),
        # caliphdev/Starter-Proxies
        ProxySource(
            "caliphdev_http",
            "https://raw.githubusercontent.com/caliphdev/Starter-Proxies/main/http.txt",
        ),
        ProxySource(
            "caliphdev_socks4",
            "https://raw.githubusercontent.com/caliphdev/Starter-Proxies/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "caliphdev_socks5",
            "https://raw.githubusercontent.com/caliphdev/Starter-Proxies/main/socks5.txt",
            "socks5",
        ),
        # yemixzy/proxy-list
        ProxySource(
            "yemixzy_http",
            "https://raw.githubusercontent.com/yemixzy/proxy-list/main/proxies/http.txt",
        ),
        ProxySource(
            "yemixzy_socks4",
            "https://raw.githubusercontent.com/yemixzy/proxy-list/main/proxies/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "yemixzy_socks5",
            "https://raw.githubusercontent.com/yemixzy/proxy-list/main/proxies/socks5.txt",
            "socks5",
        ),
        # TuanMinPay/live-proxy
        ProxySource(
            "tuanminpay_http",
            "https://raw.githubusercontent.com/TuanMinPay/live-proxy/master/http.txt",
        ),
        ProxySource(
            "tuanminpay_socks4",
            "https://raw.githubusercontent.com/TuanMinPay/live-proxy/master/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "tuanminpay_socks5",
            "https://raw.githubusercontent.com/TuanMinPay/live-proxy/master/socks5.txt",
            "socks5",
        ),
        # rx443/proxy-list
        ProxySource(
            "rx443_http",
            "https://raw.githubusercontent.com/rx443/proxy-list/main/online/http.txt",
        ),
        ProxySource(
            "rx443_https",
            "https://raw.githubusercontent.com/rx443/proxy-list/main/online/https.txt",
        ),
        ProxySource(
            "rx443_socks4",
            "https://raw.githubusercontent.com/rx443/proxy-list/main/online/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "rx443_socks5",
            "https://raw.githubusercontent.com/rx443/proxy-list/main/online/socks5.txt",
            "socks5",
        ),
        # Anonym0usWork1221/Free-Proxies
        ProxySource(
            "anonym0us_http",
            "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/http_proxies.txt",
        ),
        ProxySource(
            "anonym0us_https",
            "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/https_proxies.txt",
        ),
        ProxySource(
            "anonym0us_socks4",
            "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/socks4_proxies.txt",
            "socks4",
        ),
        ProxySource(
            "anonym0us_socks5",
            "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/socks5_proxies.txt",
            "socks5",
        ),
        # zevtyardt/proxy-list
        ProxySource(
            "zevtyardt_http",
            "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt",
        ),
        ProxySource(
            "zevtyardt_socks4",
            "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "zevtyardt_socks5",
            "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/socks5.txt",
            "socks5",
        ),
        # HyperBeats/proxy-list
        ProxySource(
            "hyperbeats_http",
            "https://raw.githubusercontent.com/HyperBeats/proxy-list/main/http.txt",
        ),
        ProxySource(
            "hyperbeats_socks4",
            "https://raw.githubusercontent.com/HyperBeats/proxy-list/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "hyperbeats_socks5",
            "https://raw.githubusercontent.com/HyperBeats/proxy-list/main/socks5.txt",
            "socks5",
        ),
        # Volodichev/proxy-list
        ProxySource(
            "volodichev_http",
            "https://raw.githubusercontent.com/Volodichev/proxy-list/main/http.txt",
        ),
        ProxySource(
            "volodichev_socks4",
            "https://raw.githubusercontent.com/Volodichev/proxy-list/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "volodichev_socks5",
            "https://raw.githubusercontent.com/Volodichev/proxy-list/main/socks5.txt",
            "socks5",
        ),
        # almroot/proxylist
        ProxySource(
            "almroot_http",
            "https://raw.githubusercontent.com/almroot/proxylist/master/list.txt",
        ),
        # aslisk/proxyhttps
        ProxySource(
            "aslisk_https",
            "https://raw.githubusercontent.com/aslisk/proxyhttps/main/https.txt",
        ),
        # B4RC0DE-TM/proxy-list
        ProxySource(
            "b4rc0de_http",
            "https://raw.githubusercontent.com/B4RC0DE-TM/proxy-list/main/HTTP.txt",
        ),
        ProxySource(
            "b4rc0de_socks4",
            "https://raw.githubusercontent.com/B4RC0DE-TM/proxy-list/main/SOCKS4.txt",
            "socks4",
        ),
        ProxySource(
            "b4rc0de_socks5",
            "https://raw.githubusercontent.com/B4RC0DE-TM/proxy-list/main/SOCKS5.txt",
            "socks5",
        ),
        # BlackSnowDot/proxylist
        ProxySource(
            "blacksnowdot_http",
            "https://raw.githubusercontent.com/BlackSnowDot/proxylist-update-every-minute/main/http.txt",
        ),
        ProxySource(
            "blacksnowdot_https",
            "https://raw.githubusercontent.com/BlackSnowDot/proxylist-update-every-minute/main/https.txt",
        ),
        ProxySource(
            "blacksnowdot_socks4",
            "https://raw.githubusercontent.com/BlackSnowDot/proxylist-update-every-minute/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "blacksnowdot_socks5",
            "https://raw.githubusercontent.com/BlackSnowDot/proxylist-update-every-minute/main/socks5.txt",
            "socks5",
        ),
        # fahimscir);/proxybd
        ProxySource(
            "fahimscirp_http",
            "https://raw.githubusercontent.com/fahimscirp/proxybd/master/proxylist/http.txt",
        ),
        ProxySource(
            "fahimscirp_socks4",
            "https://raw.githubusercontent.com/fahimscirp/proxybd/master/proxylist/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "fahimscirp_socks5",
            "https://raw.githubusercontent.com/fahimscirp/proxybd/master/proxylist/socks5.txt",
            "socks5",
        ),
        # hendrikbgr/Free-Proxy-Repo
        ProxySource(
            "hendrikbgr",
            "https://raw.githubusercontent.com/hendrikbgr/Free-Proxy-Repo/master/proxy_list.txt",
        ),
        # Human-Internet/proxy-list
        ProxySource(
            "human_internet_http",
            "https://raw.githubusercontent.com/Human-Internet/proxy-list/main/http.txt",
        ),
        ProxySource(
            "human_internet_socks4",
            "https://raw.githubusercontent.com/Human-Internet/proxy-list/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "human_internet_socks5",
            "https://raw.githubusercontent.com/Human-Internet/proxy-list/main/socks5.txt",
            "socks5",
        ),
        # iptotal/free-proxy-list
        ProxySource(
            "iptotal",
            "https://raw.githubusercontent.com/iptotal/free-proxy-list/master/all.txt",
        ),
        # hanwayTech/free-proxy-list
        ProxySource(
            "hanwaytech_http",
            "https://raw.githubusercontent.com/hanwayTech/free-proxy-list/main/http.txt",
        ),
        ProxySource(
            "hanwaytech_https",
            "https://raw.githubusercontent.com/hanwayTech/free-proxy-list/main/https.txt",
        ),
        ProxySource(
            "hanwaytech_socks4",
            "https://raw.githubusercontent.com/hanwayTech/free-proxy-list/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "hanwaytech_socks5",
            "https://raw.githubusercontent.com/hanwayTech/free-proxy-list/main/socks5.txt",
            "socks5",
        ),
        # MrMarble/proxy-list
        ProxySource(
            "mrmarble_http",
            "https://raw.githubusercontent.com/MrMarble/proxy-list/main/all.txt",
        ),
        # NotUnko/autoproxy
        ProxySource(
            "notunko_http",
            "https://raw.githubusercontent.com/NotUnko/autoproxy/main/http.txt",
        ),
        ProxySource(
            "notunko_socks4",
            "https://raw.githubusercontent.com/NotUnko/autoproxy/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "notunko_socks5",
            "https://raw.githubusercontent.com/NotUnko/autoproxy/main/socks5.txt",
            "socks5",
        ),
        # ObcbO/getproxy
        ProxySource(
            "obcbo_http",
            "https://raw.githubusercontent.com/ObcbO/getproxy/master/http.txt",
        ),
        ProxySource(
            "obcbo_socks4",
            "https://raw.githubusercontent.com/ObcbO/getproxy/master/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "obcbo_socks5",
            "https://raw.githubusercontent.com/ObcbO/getproxy/master/socks5.txt",
            "socks5",
        ),
        # proxy4parsing/proxy-list
        ProxySource(
            "p4p_socks4",
            "https://raw.githubusercontent.com/proxy4parsing/proxy-list/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "p4p_socks5",
            "https://raw.githubusercontent.com/proxy4parsing/proxy-list/main/socks5.txt",
            "socks5",
        ),
        # proxylist-to/proxy-list
        ProxySource(
            "proxylist_to_http",
            "https://raw.githubusercontent.com/proxylist-to/proxy-list/main/http.txt",
        ),
        ProxySource(
            "proxylist_to_socks4",
            "https://raw.githubusercontent.com/proxylist-to/proxy-list/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "proxylist_to_socks5",
            "https://raw.githubusercontent.com/proxylist-to/proxy-list/main/socks5.txt",
            "socks5",
        ),
        # ProxyScraper-dev/proxy-list
        ProxySource(
            "proxyscraper_dev_http",
            "https://raw.githubusercontent.com/ProxyScraper-dev/proxy-list/main/http_proxies.txt",
        ),
        ProxySource(
            "proxyscraper_dev_socks4",
            "https://raw.githubusercontent.com/ProxyScraper-dev/proxy-list/main/socks4_proxies.txt",
            "socks4",
        ),
        ProxySource(
            "proxyscraper_dev_socks5",
            "https://raw.githubusercontent.com/ProxyScraper-dev/proxy-list/main/socks5_proxies.txt",
            "socks5",
        ),
        # Flavien/proxy-list
        ProxySource(
            "flavien_http",
            "https://raw.githubusercontent.com/Flavien/proxy-list/main/http.txt",
        ),
        ProxySource(
            "flavien_socks4",
            "https://raw.githubusercontent.com/Flavien/proxy-list/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "flavien_socks5",
            "https://raw.githubusercontent.com/Flavien/proxy-list/main/socks5.txt",
            "socks5",
        ),
        # saisuiu/Lionkings-Http-Proxys-Proxies
        ProxySource(
            "saisuiu",
            "https://raw.githubusercontent.com/saisuiu/Lionkings-Http-Proxys-Proxies/main/free.txt",
        ),
        # sunny9577/proxy-scraper
        ProxySource(
            "sunny_http",
            "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/http_proxies.txt",
        ),
        ProxySource(
            "sunny_socks4",
            "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/socks4_proxies.txt",
            "socks4",
        ),
        ProxySource(
            "sunny_socks5",
            "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/socks5_proxies.txt",
            "socks5",
        ),
        # TheSpeedX/SOCKS-List (direct socks list)
        ProxySource(
            "speedx_socks_http",
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        ),
        ProxySource(
            "speedx_socks_socks4",
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "speedx_socks_socks5",
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
            "socks5",
        ),
        # UserR3X/proxy-list
        ProxySource(
            "userr3x_http",
            "https://raw.githubusercontent.com/UserR3X/proxy-list/main/online/http.txt",
        ),
        ProxySource(
            "userr3x_https",
            "https://raw.githubusercontent.com/UserR3X/proxy-list/main/online/https.txt",
        ),
        ProxySource(
            "userr3x_socks4",
            "https://raw.githubusercontent.com/UserR3X/proxy-list/main/online/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "userr3x_socks5",
            "https://raw.githubusercontent.com/UserR3X/proxy-list/main/online/socks5.txt",
            "socks5",
        ),
        # Vann-Dev/proxy-list
        ProxySource(
            "vann_http",
            "https://raw.githubusercontent.com/Vann-Dev/proxy-list/main/proxies/http.txt",
        ),
        ProxySource(
            "vann_socks4",
            "https://raw.githubusercontent.com/Vann-Dev/proxy-list/main/proxies/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "vann_socks5",
            "https://raw.githubusercontent.com/Vann-Dev/proxy-list/main/proxies/socks5.txt",
            "socks5",
        ),
        # yoannchb-pro/Proxy-List
        ProxySource(
            "yoannchb_http",
            "https://raw.githubusercontent.com/yoannchb-pro/Proxy-List/main/http.txt",
        ),
        ProxySource(
            "yoannchb_socks4",
            "https://raw.githubusercontent.com/yoannchb-pro/Proxy-List/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "yoannchb_socks5",
            "https://raw.githubusercontent.com/yoannchb-pro/Proxy-List/main/socks5.txt",
            "socks5",
        ),
        # Flavor/proxy-scraper
        ProxySource(
            "flavor_http",
            "https://raw.githubusercontent.com/Flavor/proxy-scraper/main/proxies/http.txt",
        ),
        ProxySource(
            "flavor_socks4",
            "https://raw.githubusercontent.com/Flavor/proxy-scraper/main/proxies/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "flavor_socks5",
            "https://raw.githubusercontent.com/Flavor/proxy-scraper/main/proxies/socks5.txt",
            "socks5",
        ),
        # mtzvlm/proxy-list
        ProxySource(
            "mtzvlm_http",
            "https://raw.githubusercontent.com/mtzvlm/proxy-list/main/http.txt",
        ),
        ProxySource(
            "mtzvlm_socks4",
            "https://raw.githubusercontent.com/mtzvlm/proxy-list/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "mtzvlm_socks5",
            "https://raw.githubusercontent.com/mtzvlm/proxy-list/main/socks5.txt",
            "socks5",
        ),
        # monosans additional endpoints
        ProxySource(
            "monosans_http",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        ),
        ProxySource(
            "monosans_socks4",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "monosans_socks5",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
            "socks5",
        ),
        # Tsprnay/Proxy-lists
        ProxySource(
            "tsprnay_http",
            "https://raw.githubusercontent.com/Tsprnay/Proxy-lists/master/proxies/http.txt",
        ),
        ProxySource(
            "tsprnay_socks4",
            "https://raw.githubusercontent.com/Tsprnay/Proxy-lists/master/proxies/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "tsprnay_socks5",
            "https://raw.githubusercontent.com/Tsprnay/Proxy-lists/master/proxies/socks5.txt",
            "socks5",
        ),
        # ipinfo-github/proxy-list
        ProxySource(
            "ipinfo_http",
            "https://raw.githubusercontent.com/ipinfo-github/proxy-list/main/http.txt",
        ),
        ProxySource(
            "ipinfo_socks4",
            "https://raw.githubusercontent.com/ipinfo-github/proxy-list/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "ipinfo_socks5",
            "https://raw.githubusercontent.com/ipinfo-github/proxy-list/main/socks5.txt",
            "socks5",
        ),
        # MuRongPIG/Proxy-Master (full list)
        ProxySource(
            "murong_all",
            "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/http_checked.txt",
        ),
        # BreakingTechFr/Proxy
        ProxySource(
            "breakingtech_http",
            "https://raw.githubusercontent.com/BreakingTechFr/Proxy/main/http.txt",
        ),
        ProxySource(
            "breakingtech_https",
            "https://raw.githubusercontent.com/BreakingTechFr/Proxy/main/https.txt",
        ),
        ProxySource(
            "breakingtech_socks4",
            "https://raw.githubusercontent.com/BreakingTechFr/Proxy/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "breakingtech_socks5",
            "https://raw.githubusercontent.com/BreakingTechFr/Proxy/main/socks5.txt",
            "socks5",
        ),
        # ErcinDedeoglu/proxies (additional endpoints)
        ProxySource(
            "ercin_https",
            "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/https.txt",
        ),
        # FLAVOR01/http-proxy-list
        ProxySource(
            "flavor01",
            "https://raw.githubusercontent.com/FLAVOR01/http-proxy-list/main/proxy-list/data.txt",
        ),
        # x-o-r-r-o/proxy-list
        ProxySource(
            "xorro_http",
            "https://raw.githubusercontent.com/x-o-r-r-o/proxy-list/main/proxies/http_proxies.txt",
        ),
        ProxySource(
            "xorro_socks4",
            "https://raw.githubusercontent.com/x-o-r-r-o/proxy-list/main/proxies/socks4_proxies.txt",
            "socks4",
        ),
        ProxySource(
            "xorro_socks5",
            "https://raw.githubusercontent.com/x-o-r-r-o/proxy-list/main/proxies/socks5_proxies.txt",
            "socks5",
        ),
        # iplocate/free-proxy-list
        ProxySource(
            "iplocate_http",
            "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/http.txt",
        ),
        ProxySource(
            "iplocate_socks4",
            "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "iplocate_socks5",
            "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/socks5.txt",
            "socks5",
        ),
    ]

    # IP:PORT pattern
    PROXY_PATTERN = re.compile(r"^(\d{1,3}\.){3}\d{1,3}:\d{2,5}$")

    def __init__(
        self,
        output_dir: str | Path | None = None,
        timeout: float = 30.0,
        max_concurrent: int = 50,
    ) -> None:
        """Initialize proxy aggregator.

        Args:
            output_dir: Directory to save proxy files
            timeout: Request timeout in seconds
            max_concurrent: Max concurrent downloads
        """
        if output_dir is None:
            # Default to data/proxies relative to this file
            self.output_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "proxies"
        else:
            self.output_dir = Path(output_dir)

        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def _download_source(
        self,
        session: aiohttp.ClientSession,
        source: ProxySource,
    ) -> list[str]:
        """Download proxies from a single source.

        Args:
            session: aiohttp session
            source: Proxy source to download

        Returns:
            List of proxy strings
        """
        if not source.enabled:
            return []

        async with self._semaphore:
            try:
                async with session.get(source.url) as response:
                    if response.status != 200:
                        return []

                    content = await response.text()
                    lines = content.strip().split("\n")

                    # Filter valid proxies
                    proxies = []
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Extract IP:PORT if present
                            if self.PROXY_PATTERN.match(line):
                                proxies.append(line)
                            elif ":" in line:
                                # Try to extract IP:PORT from formatted lines
                                parts = line.split()
                                if parts and self.PROXY_PATTERN.match(parts[0]):
                                    proxies.append(parts[0])

                    return proxies

            except Exception:
                return []

    async def refresh_all(self, deduplicate: bool = False) -> int:
        """Download proxies from all sources.

        Args:
            deduplicate: Whether to remove duplicate proxies

        Returns:
            Total number of proxies downloaded
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        all_proxies: list[str] = []

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            tasks = [self._download_source(session, source) for source in self.SOURCES]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    all_proxies.extend(result)

        if deduplicate:
            all_proxies = list(set(all_proxies))

        # Save to aggregated.txt
        output_path = self.output_dir / "aggregated.txt"
        with open(output_path, "w") as f:
            f.write("\n".join(all_proxies))

        return len(all_proxies)

    async def refresh_by_type(self) -> dict[str, int]:
        """Download and organize proxies by type.

        Returns:
            Dict of proxy type to count
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        proxies_by_type: dict[str, list[str]] = {
            "http": [],
            "socks4": [],
            "socks5": [],
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for source in self.SOURCES:
                proxies = await self._download_source(session, source)
                proxies_by_type[source.proxy_type].extend(proxies)

        # Save by type
        counts = {}
        for proxy_type, proxies in proxies_by_type.items():
            unique_proxies = list(set(proxies))
            type_dir = self.output_dir / proxy_type
            type_dir.mkdir(exist_ok=True)

            output_path = type_dir / "all.txt"
            with open(output_path, "w") as f:
                f.write("\n".join(unique_proxies))

            counts[proxy_type] = len(unique_proxies)

        return counts

    def get_source_count(self) -> int:
        """Get number of enabled sources."""
        return sum(1 for s in self.SOURCES if s.enabled)

    def add_source(self, name: str, url: str, proxy_type: str = "http") -> None:
        """Add a new proxy source.

        Args:
            name: Source identifier
            url: URL to fetch proxies from
            proxy_type: Type of proxies (http, socks4, socks5)
        """
        self.SOURCES.append(ProxySource(name, url, proxy_type))

    def disable_source(self, name: str) -> bool:
        """Disable a source by name.

        Args:
            name: Source name to disable

        Returns:
            True if source was found and disabled
        """
        for source in self.SOURCES:
            if source.name == name:
                source.enabled = False
                return True
        return False
