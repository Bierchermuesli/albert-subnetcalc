# -*- coding: utf-8 -*- 

"""An advanced IPv4/IPv6 subnet calculator. Returns all relevant Attributes (Broadcast, First/Last, exploded etc...)
Can also be used for Sub/Supernetting or find previous / next prefixes.

Synopsis: <trigger> [x.x.x.x|x:x::x]/y {next|prev|sub|sup|rand|/YY [rand]} {<level>}

Details Args:
next - NEXT aligned subnet with the same mask
prev - PREVious" aligned subnet with the same mask
sub - returns next lower SUBbnets e.g. x/24 -> y/25, z/25
sup - find containing higher SUPpernet e.g. x/24s -> x/23
rand - random subnets within the prefix (default one level lower)

Default one level, can be passed as an additional argument:
x/24 sub 2 -> y/26, z/26 etc..

Instead of sub/sup args, the desired /xx subnet argument is also accepted:
x/24 /29 -> y/29, z/29 etc...

Random samples at a chosen size:
2001:db8::/64 /80 rand -> 10 random /80s within /64
192.0.2.0/24 rand      -> 10 random /25s within /24

Use 'sc list' to see well-known reserved prefixes (TEST-NET, RFC 1918, etc.).

"""

from albert import *

from pathlib import Path
import ipaddress
import json
import random
import re
import subprocess
import threading
import time


# (name, prefix, rfc, sample_prefixlen)
# sample_prefixlen=None means "no useful sub-sample" (e.g. host loopbacks).
WELL_KNOWN_PREFIXES = [
    ("TEST-NET-1",       "192.0.2.0/24",      "RFC 5737", 29),
    ("TEST-NET-2",       "198.51.100.0/24",   "RFC 5737", 29),
    ("TEST-NET-3",       "203.0.113.0/24",    "RFC 5737", 29),
    ("Documentation v6", "2001:db8::/32",     "RFC 3849", 64),
    ("Private 10",       "10.0.0.0/8",        "RFC 1918", 24),
    ("Private 172.16",   "172.16.0.0/12",     "RFC 1918", 24),
    ("Private 192.168",  "192.168.0.0/16",    "RFC 1918", 24),
    ("Unique Local v6",  "fc00::/7",          "RFC 4193", 64),
    ("CGNAT",            "100.64.0.0/10",     "RFC 6598", 24),
    ("Link-local v4",    "169.254.0.0/16",    "RFC 3927", 24),
    ("Link-local v6",    "fe80::/10",         "RFC 4291", 64),
    ("Loopback v4",      "127.0.0.0/8",       "RFC 6890", 24),
    ("Loopback v6",      "::1/128",           "RFC 4291", None),
    ("Benchmarking",     "198.18.0.0/15",     "RFC 2544", 24),
    ("Multicast v4",     "224.0.0.0/4",       "RFC 5771", None),
    ("Multicast v6",     "ff00::/8",          "RFC 4291", None),
    ("NAT64 well-known", "64:ff9b::/96",      "RFC 6052", None),
    ("Discard v6",       "100::/64",          "RFC 6666", None),
]

md_iid = "5.0"
md_version = "2.4"
md_name = "SubnetCalc"
md_description = "Calculate IPv4/IPv6 Subnets"
md_license = "MIT"
md_url = "https://github.com/Bierchermuesli/albert-subnetcalc"
md_maintainers = ["@Bierchermuesli"]
md_authors = ["@Bierchermuesli"]


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class Plugin(PluginInstance, GeneratorQueryHandler):
    _num_results = 10

    def __init__(self):
        PluginInstance.__init__(self)
        GeneratorQueryHandler.__init__(self)
        self._init_configuration()

        self._default_icon_path = str(Path(__file__).parent / "icon.svg")

        # Cached local-interface networks for empty-query hints. Refreshed in a
        # background thread (see _get_local_networks) so `ip -j addr` never
        # blocks the query pipeline.
        self._local_cache = []
        self._local_cache_ts = 0.0
        self._local_refresh_lock = threading.Lock()

    @property
    def num_results(self):
        return self._num_results

    @num_results.setter
    def num_results(self, value):
        self._num_results = value
        self.writeConfig("num_results", value)

    def _init_configuration(self):
        for key, type_, default in [
            ("num_results", int, self._num_results),
        ]:
            conf = self.readConfig(key, type_)
            if conf is None:
                self.writeConfig(key, default)
                setattr(self, f"_{key}", default)
            else:
                setattr(self, f"_{key}", conf)

    def configWidget(self):
        return [
            {
                "type": "label",
                "text": __doc__
            },
            {
                "type": "spinbox",
                "label": "Number of results for next/prev",
                "property": "num_results",
                "widget_properties": {"minimum": 1, "maximum": 50}
            },
            {
                "type": "label",
                "text": "The number of subnets to calculate and show for the 'next' and 'prev' commands."
            }
        ]

    def defaultTrigger(self):
        return "sc "

    def _icon_factory_for(self, network_or_none):
        """Returns an icon_factory callable. Albert calls it lazily *per item*,
        so each call must construct a fresh Icon — Icon objects can't be
        reused across items.
        """
        if network_or_none is None:
            path = self._default_icon_path
            return lambda: Icon.image(path)
        if network_or_none.version == 6:
            return lambda: Icon.iconified(
                Icon.grapheme("6", brush=Brush(Color(0, 0, 0))),
                background_brush=Brush(Color(102, 165, 203)),
                border_radius=0.25,
                border_width=0,
            )
        return lambda: Icon.iconified(
            Icon.grapheme("4", brush=Brush(Color(0, 0, 0))),
            background_brush=Brush(Color(178, 203, 102)),
            border_radius=0.25,
            border_width=0,
        )

    LOCAL_CACHE_SECONDS = 600  # 10 minutes — interfaces don't churn often

    def _refresh_local_networks(self):
        """Blocking `ip -j addr` call (Linux). Runs on the calling thread — callers
        decide whether that's the query thread (first run only) or a background
        thread (subsequent refreshes). Leaves the cache untouched on failure
        (e.g. macOS or `ip` missing) so callers fall back to static examples.
        Skips host-prefix entries (/32, /128) since they have no useful
        sub/sup/next/rand operations.
        """
        results = []
        try:
            output = subprocess.run(
                ["ip", "-j", "addr"],
                capture_output=True, text=True, timeout=2,
            ).stdout
            for iface in json.loads(output):
                if iface.get("ifname") == "lo":
                    continue
                for addr in iface.get("addr_info", []):
                    if addr.get("family") not in ("inet", "inet6"):
                        continue
                    ip = addr.get("local")
                    plen = addr.get("prefixlen")
                    if not ip or plen is None:
                        continue
                    try:
                        host = ipaddress.ip_address(ip)
                        net = ipaddress.ip_network(f"{ip}/{plen}", strict=False)
                    except ValueError:
                        continue
                    if net.prefixlen >= net.max_prefixlen:
                        continue
                    results.append((iface["ifname"], net, host))
        except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError, OSError):
            pass

        self._local_cache = results
        self._local_cache_ts = time.time()

    def _refresh_local_networks_and_release(self):
        try:
            self._refresh_local_networks()
        finally:
            self._local_refresh_lock.release()

    def _get_local_networks(self):
        """Return [(ifname, network, host)] for non-loopback interfaces, cached
        for LOCAL_CACHE_SECONDS. Only the very first call blocks on `ip -j addr`;
        subsequent refreshes happen in a background thread so `items()` always
        returns immediately, serving the previous cache while it refreshes.
        """
        now = time.time()
        if now - self._local_cache_ts < self.LOCAL_CACHE_SECONDS:
            return self._local_cache

        if self._local_cache_ts == 0.0:
            self._refresh_local_networks()
        elif self._local_refresh_lock.acquire(blocking=False):
            threading.Thread(target=self._refresh_local_networks_and_release, daemon=True).start()

        return self._local_cache

    @staticmethod
    def _random_sample(network, sample_prefixlen):
        """Pick a random subnet of `sample_prefixlen` size within `network`."""
        if sample_prefixlen is None or sample_prefixlen <= network.prefixlen:
            return None
        diff = sample_prefixlen - network.prefixlen
        block_size = network.num_addresses >> diff
        offset = random.getrandbits(diff) * block_size
        return ipaddress.ip_network(
            (network.network_address + offset, sample_prefixlen),
            strict=False,
        )

    def _handle_empty_query(self):
        local = self._get_local_networks()

        # Dedupe by network string (collapse multiple host addrs in the same net),
        # remember which interfaces a given network appears on for the subtext.
        seen = {}
        order = []
        for ifname, net, host in local:
            key = str(net)
            if key in seen:
                if ifname not in seen[key]["ifaces"]:
                    seen[key]["ifaces"].append(ifname)
            else:
                seen[key] = {"net": net, "host": host, "ifaces": [ifname]}
                order.append(key)

        items = []

        # 'list' shortcut — always present, no IP context.
        items.append(StandardItem(
            id="sc-hint-list",
            text="sc list",
            subtext="Browse well-known prefixes (RFC 5737 doc, 1918 private, ULA, …)",
            icon_factory=self._icon_factory_for(None),
            input_action_text="list ",
        ))

        # One "calculate details" hint per detected local network.
        for key in order:
            entry = seen[key]
            net = entry["net"]
            ifaces = ", ".join(entry["ifaces"])
            if net.is_link_local:
                kind = "link-local"
            elif net.is_private:
                kind = "private"
            elif net.is_loopback:
                kind = "loopback"
            else:
                kind = "global"
            items.append(StandardItem(
                id=f"sc-hint-local-{key}",
                text=f"sc {key}",
                subtext=f"{ifaces} — your /{net.prefixlen} ({kind}, host: {entry['host']})",
                icon_factory=self._icon_factory_for(net),
                input_action_text=f"{key} ",
            ))

        # Pick a representative v4/v6 for the command-example rows. Prefer
        # non-link-local; fall back to documentation prefixes if absent.
        local_v4 = next((seen[k]["net"] for k in order if seen[k]["net"].version == 4 and not seen[k]["net"].is_link_local), None)
        local_v6 = next((seen[k]["net"] for k in order if seen[k]["net"].version == 6 and not seen[k]["net"].is_link_local), None)
        if local_v6 is None:
            local_v6 = next((seen[k]["net"] for k in order if seen[k]["net"].version == 6), None)

        v4 = str(local_v4) if local_v4 else "192.0.2.0/24"
        v6 = str(local_v6) if local_v6 else "2001:db8::/32"

        examples = [
            (f"{v4} sub",      local_v4, f"Split {v4} into next-lower subnets — add 'sub N' for deeper levels"),
            (f"{v4} sup",      local_v4, f"Containing supernet of {v4} — add 'sup N' for higher levels"),
            (f"{v4} next",     local_v4, f"Next aligned same-size subnets after {v4}"),
            (f"{v4} prev",     local_v4, f"Previous aligned same-size subnets before {v4}"),
            (f"{v6} /80 rand", local_v6, f"Random /80 samples within {v6} (drop '/80' for one level lower)"),
        ]
        for example, net_for_icon, desc in examples:
            items.append(StandardItem(
                id=f"sc-hint-{example}",
                text=f"sc {example}",
                subtext=desc,
                icon_factory=self._icon_factory_for(net_for_icon),
                input_action_text=f"{example} ",
            ))

        return items

    def _handle_list_query(self):
        items = []
        for name, prefix_str, rfc, sample_prefixlen in WELL_KNOWN_PREFIXES:
            net = ipaddress.ip_network(prefix_str)
            sample = self._random_sample(net, sample_prefixlen)

            subtext_parts = [rfc, prefix_str]
            actions = [
                Action(f"copy-{prefix_str}", f"Copy {prefix_str}",
                       lambda v=prefix_str: setClipboardText(v)),
            ]
            if sample is not None:
                subtext_parts.append(f"sample {sample}")
                actions.append(Action(
                    f"copy-sample-{prefix_str}",
                    f"Copy sample {sample}",
                    lambda v=str(sample): setClipboardText(v),
                ))

            items.append(StandardItem(
                id=f"sc-list-{prefix_str}",
                text=f"{name} — {prefix_str}",
                subtext=", ".join(subtext_parts),
                icon_factory=self._icon_factory_for(net),
                input_action_text=f"{prefix_str} ",
                actions=actions,
            ))
        return items

    def _get_eui64_mac(self, addr: ipaddress.IPv6Address) -> str | None:
        """Check for EUI-64 identifier and return MAC address if found."""
        if addr.packed[11:13] != b'\xff\xfe':
            return None
        
        eui64_bytes = bytearray(addr.packed[8:])
        eui64_bytes[0] ^= 0b00000010

        mac_bytes = eui64_bytes[0:3] + eui64_bytes[3+2:]
        return ':'.join(f'{b:02x}' for b in mac_bytes)

    @staticmethod
    def _is_host(addr):
        return (addr.version == 4 and addr.prefixlen == 32) or \
               (addr.version == 6 and addr.prefixlen == 128)

    def _get_simple_subtext_parts(self, addr):
        is_host = self._is_host(addr)

        parts = [f"IPv{addr.version}"]
        parts.append("Host" if is_host else "Net")

        if addr.is_loopback: parts.append("Loopback")
        if addr.is_global: parts.append("Global")
        if addr.is_private: parts.append("Private")
        if addr.is_multicast: parts.append("Multicast")
        if addr.is_reserved: parts.append("Reserved")
        if addr.is_unspecified: parts.append("Unspecified")
        
        if is_host and addr.version == 6:
            if mac := self._get_eui64_mac(addr.network_address):
                parts.append(f"EUI-64 (MAC: {mac})")

        if not is_host:
            if addr.version == 4:
                parts.append(f"hosts {addr.num_addresses}")
            else:
                parts.append(f"contains {2 ** (64 - addr.prefixlen)} /64s")
                
        return parts

    def _get_simple_actions(self, addr):
        is_host = self._is_host(addr)
        actions = []
        
        if is_host:
            host_addr = addr.network_address
            # Add reverse pointer, compressed, exploded actions first
            actions.append(Action("reverse", f"Reverse Pointer {addr.reverse_pointer}", lambda: setClipboardText(str(addr.reverse_pointer))))
            if addr.version == 6:
                actions.append(Action("compressed", f"Compressed {addr.compressed}", lambda: setClipboardText(str(addr.compressed))))
                actions.append(Action("exploded", f"Exploded {addr.exploded}", lambda: setClipboardText(str(addr.exploded))))
                if mac := self._get_eui64_mac(host_addr):
                    actions.append(Action("copy_mac", f"Copy MAC: {mac}", lambda m=mac: setClipboardText(m)))
            
            # Add hex and bin as last items
            actions.append(Action("hex", f"Hex {host_addr.packed.hex()}", lambda: setClipboardText(str(host_addr.packed.hex()))))
            actions.append(Action("bin", f"Bin {''.join(f'{byte:08b}' for byte in host_addr.packed)}", lambda: setClipboardText(''.join(f'{byte:08b}' for byte in host_addr.packed))))

        else:  # is a network
            if addr.version == 4:
                actions.extend([
                    Action("network", f"Network {addr.network_address}", lambda: setClipboardText(str(addr.network_address))),
                    Action("netmask", f"Netmask {addr.netmask}", lambda: setClipboardText(str(addr.netmask))),
                    Action("first", f"First host {addr.network_address + 1}", lambda: setClipboardText(str(addr.network_address + 1))),
                    Action("last", f"Last host {addr.broadcast_address - 1}", lambda: setClipboardText(str(addr.broadcast_address - 1))),
                    Action("broadcast", f"Broadcast {addr.broadcast_address}", lambda: setClipboardText(str(addr.broadcast_address))),
                    Action("wildcard", f"Wildcard {addr.hostmask}", lambda: setClipboardText(str(addr.hostmask))),
                ])
            else:  # ipv6 network
                actions.extend([
                    Action("network", f"Network {addr.network_address}", lambda: setClipboardText(str(addr.network_address))),
                    Action("compressed", f"Compressed {addr.compressed}", lambda: setClipboardText(str(addr.compressed))),
                    Action("exploded", f"Exploded {addr.exploded}", lambda: setClipboardText(str(addr.exploded))),
                    Action("last", f"Last {addr.broadcast_address}", lambda: setClipboardText(str(addr.broadcast_address))),
                    Action("netmask", f"Netmask {addr.netmask}", lambda: setClipboardText(str(addr.netmask))),
                ])
        return actions

    def _handle_simple_query(self, query_string, addr):
        subtext = ", ".join(self._get_simple_subtext_parts(addr))
        actions = self._get_simple_actions(addr)
        is_host = self._is_host(addr)

        return [StandardItem(
            id=f"sc-{'host' if is_host else 'net'}-{addr}",
            text=str(addr),
            subtext=subtext,
            icon_factory=self._icon_factory_for(addr),
            actions=actions
        )]

    @staticmethod
    def _parse_advanced_query(query_string, addr):
        """Returns (mode, level, target_prefixlen) parsed from the query string."""
        if match := re.match(r"\S+\s+/(\d+)\s+rand\s*$", query_string):
            return "rand", 0, int(match.group(1))
        if match := re.match(r"\S+\s+rand\s*$", query_string):
            return "rand", 0, addr.prefixlen + 1
        if match := re.match(r"\S+\s+(sub|sup|next|prev)\s*(\d*)", query_string):
            mode = match.groups()[0]
            level = int(match.groups()[1]) if match.groups()[1] else 1
            return mode, level, None
        if match := re.match(r"\S+\s+/(\d+)", query_string):
            lookup_prefix = int(match.groups()[0])
            if addr.prefixlen > lookup_prefix:
                return "sup", addr.prefixlen - lookup_prefix, None
            else:
                return "sub", lookup_prefix - addr.prefixlen, None
        return "UNDEF", 0, None

    def _mode_sub(self, addr, level, icon_factory):
        items = []
        if level > (addr.max_prefixlen - addr.prefixlen):
            level = addr.max_prefixlen - addr.prefixlen
            items.append(StandardItem(id="sc-cant-go-lower", icon_factory=icon_factory, text=f"Can't go lower than /{addr.max_prefixlen} - {ordinal(level)} level"))
        total = 1 << level
        if total > self.num_results:
            items.append(StandardItem(
                id="sc-sub-truncated",
                text=f"{total:,} /{addr.prefixlen + level} subnets — showing first {self.num_results}",
                subtext="Increase 'Number of results' in plugin settings, or use 'rand' for random samples",
                icon_factory=icon_factory,
            ))
        for idx, i in enumerate(addr.subnets(prefixlen_diff=level)):
            if idx >= self.num_results:
                break
            items.append(StandardItem(
                id=f"sc-subnet-{i}", text=str(i), subtext=f"{ordinal(idx + 1)} Subnet",
                icon_factory=icon_factory,
                actions=[Action(f"copy-{i}", f"Copy network {i}", lambda r=str(i): setClipboardText(r))]
            ))
        return items

    def _mode_sup(self, addr, level, icon_factory):
        items = []
        if level > addr.prefixlen:
            level = addr.prefixlen
            items.append(StandardItem(id="sc-cant-go-higher", icon_factory=icon_factory, text=f"Can't go higher than /0 - {ordinal(level)} level"))

        supernet = addr.supernet(prefixlen_diff=level)
        items.append(StandardItem(
            id=f"sc-supernet-{supernet}", text=str(supernet), icon_factory=icon_factory,
            subtext=f"{ordinal(level)} level Supernet",
            actions=[Action(f"copy-{supernet}", f"Copy network {supernet}", lambda r=str(supernet): setClipboardText(r))]
        ))
        return items

    def _mode_rand(self, addr, target_prefixlen, icon_factory):
        items = []
        if target_prefixlen is None or target_prefixlen <= addr.prefixlen or target_prefixlen > addr.max_prefixlen:
            items.append(StandardItem(
                id="sc-rand-invalid",
                text=f"Invalid /{target_prefixlen} for random sample",
                subtext=f"Target prefix must be between /{addr.prefixlen + 1} and /{addr.max_prefixlen}",
                icon_factory=icon_factory,
            ))
            return items

        diff = target_prefixlen - addr.prefixlen
        # Cap requested count to the size of the search space when it's small,
        # so we don't loop forever trying to dedupe.
        space = 1 << diff if diff < 30 else self.num_results
        want = min(self.num_results, space)
        seen = set()
        attempts = 0
        while len(seen) < want and attempts < want * 4:
            attempts += 1
            sample = self._random_sample(addr, target_prefixlen)
            key = str(sample)
            if key in seen:
                continue
            seen.add(key)
            items.append(StandardItem(
                id=f"sc-rand-{addr}-{key}",
                text=key,
                subtext=f"Random /{target_prefixlen} in {addr}",
                icon_factory=icon_factory,
                actions=[Action(f"copy-{key}", f"Copy {key}", lambda r=key: setClipboardText(r))],
            ))
        return items

    def _mode_next_prev(self, addr, mode, icon_factory):
        items = []
        for i in range(1, self.num_results + 1):
            offset = i * addr.num_addresses
            if mode == "prev":
                offset = -offset

            try:
                new_net = ipaddress.ip_network(f"{addr[0] + offset}/{addr.prefixlen}", strict=False)
            except (ValueError, ipaddress.AddressValueError):
                items.append(StandardItem(
                    id=f"sc-{mode}-edge",
                    text=f"No more {mode} subnets — address space edge reached",
                    icon_factory=icon_factory,
                    subtext=f"Stopped after {ordinal(i - 1)} /{addr.prefixlen} subnet" if i > 1 else f"{addr} is at the edge"
                ))
                break
            items.append(StandardItem(
                id=f"sc-{mode}-{addr}-{i}", text=str(new_net), icon_factory=icon_factory,
                subtext=f"{mode} {ordinal(i)} /{addr.prefixlen} subnet",
                actions=[Action(f"copy-{mode}-{i}", f"Copy Network {new_net}", lambda r=str(new_net): setClipboardText(r))]
            ))
        return items

    @staticmethod
    def _mode_usage(query_string, icon_factory):
        return [StandardItem(
            id="sc-usage",
            text="Usage: <prefix> {sub|sup|next|prev|rand|/YY [rand]} [N]",
            icon_factory=icon_factory,
            subtext=f"Query was: {query_string}  —  type 'sc list' for well-known prefixes"
        )]

    def _handle_advanced_query(self, query_string, addr):
        icon_factory = self._icon_factory_for(addr)
        mode, level, target_prefixlen = self._parse_advanced_query(query_string, addr)

        if mode == "sub":
            return self._mode_sub(addr, level, icon_factory)
        elif mode == "sup":
            return self._mode_sup(addr, level, icon_factory)
        elif mode == "rand":
            return self._mode_rand(addr, target_prefixlen, icon_factory)
        elif mode in ("next", "prev"):
            return self._mode_next_prev(addr, mode, icon_factory)
        else:
            return self._mode_usage(query_string, icon_factory)

    def items(self, ctx):
        query_string = ctx.query
        if not query_string.strip():
            yield self._handle_empty_query()
            return

        if query_string.strip().lower() == "list":
            yield self._handle_list_query()
            return

        addr = None
        try:
            addr = ipaddress.ip_network(query_string.split()[0], strict=False)
        except Exception as e:
            debug(f"Subnetcal failed to parse: '{query_string}' with error: {e}")

        if not addr:
            yield [StandardItem(
                id="sc-invalid",
                text="No valid IPv4/IPv6 address/subnet",
                subtext=f"Query was: {query_string}",
                icon_factory=self._icon_factory_for(None)
            )]
            return

        if len(query_string.split()) == 1:
            yield self._handle_simple_query(query_string, addr)
        else:
            yield self._handle_advanced_query(query_string, addr)
