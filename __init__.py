# -*- coding: utf-8 -*-

"""An advanced IPv4/IPv6 subnet calculator. Returns all relevant Attributes (Broadcast, First/Last, exploded etc...)
Can also be used for Sub/Supernetting or find previous / next prefixes.

Synopsis: <trigger> [x.x.x.x|x:x::x]/y {next|prev|sub|sup|/YY} {<level>}

Details Args:
next - NEXT aligned subnet with the same mask
prev - PREVious" aligned subnet with the same mask
sub - returns next lower SUBbnets e.g. x/24 -> y/25, z/25
sup - find containing higher SUPpernet e.g. x/24s -> x/23

Default one level, can be passed as an additional argument:
x/24 sub 2 -> y/26, z/26 etc..

Instead of sub/sup args, the desired /xx subnet argument is also accepted:
x/24 /29 -> y/29, z/29 etc...

"""

from albert import *

from pathlib import Path
import ipaddress
import re

md_iid = "4.0"
md_version = "2.0"
md_name = "SubnetCalc"
md_description = "Calculate IPv4/IPv6 Subnets"
md_license = "MIT"
md_url = "https://github.com/Bierchermuesli/albert-subnetcalc"
md_maintainers = "@Bierchermuesli"
md_authors = "@Bierchermuesli"
md_lib_dependencies = ["ipaddress"]


ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4])


class Plugin(PluginInstance, TriggerQueryHandler):
    _num_results = 10

    def __init__(self):
        PluginInstance.__init__(self)
        TriggerQueryHandler.__init__(self)
        self._init_configuration()

    @property
    def num_results(self):
        return self._num_results

    @num_results.setter
    def num_results(self, value):
        self._num_results = value
        self.writeConfig("num_results", value)

    def _init_configuration(self):
        conf = self.readConfig("num_results", int)
        if conf is None:
            self.writeConfig("num_results", self._num_results)
        else:
            self._num_results = conf

    def configWidget(self):
        return [
            {
                "type": "label",
                "text": __doc__,
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

    # default types
    def handleTriggerQuery(self, query):
        if not query.isValid:
            return

        addr = None
        icon_path = Path(__file__).parent / "icon.svg"

        try:
            addr = ipaddress.ip_network(query.string.split()[0], strict=False)
            icon_path = Path(__file__).parent / f"ipv{addr.version}.svg"
        except:
            debug(f"Subnetcal failed to parse: {query.string}")

        if not addr:
            query.add(StandardItem(
                id=md_name,
                text="No valid IPv4/IPv6 address/subnet",
                subtext=f"Query was: {query.string}",
                icon_factory=lambda p=icon_path: makeImageIcon(str(p))
            ))
            return

        # --- Handle simple query (single address/network) ---
        if len(query.string.split()) == 1:
            is_host = (addr.version == 4 and addr.prefixlen == 32) or \
                      (addr.version == 6 and addr.prefixlen == 128)

            subtext_parts = [f"IPv{addr.version}"]
            if is_host:
                subtext_parts.append("Host")
            else:
                subtext_parts.append("Net")

            if addr.is_loopback: subtext_parts.append("Loopback")
            if addr.is_global: subtext_parts.append("Global")
            if addr.is_private: subtext_parts.append("Private")
            if addr.is_multicast: subtext_parts.append("Multicast")
            if addr.is_reserved: subtext_parts.append("Reserved")
            if addr.is_unspecified: subtext_parts.append("Unspecified")

            actions = []
            if is_host:
                host_addr = addr.network_address
                actions.extend([
                    Action("reverse", f"Reverse Pointer {addr.reverse_pointer}", lambda: setClipboardText(str(addr.reverse_pointer))),
                    Action("hex", f"Hex {host_addr.packed.hex()}", lambda: setClipboardText(str(host_addr.packed.hex()))),
                    Action("bin", f"Bin {''.join(f'{byte:08b}' for byte in host_addr.packed)}", lambda: setClipboardText(''.join(f'{byte:08b}' for byte in host_addr.packed)))
                ])
                if addr.version == 6:
                    actions.insert(1, Action("compressed", f"Compressed {addr.compressed}", lambda: setClipboardText(str(addr.compressed))))
                    actions.insert(2, Action("exploded", f"Exploded {addr.exploded}", lambda: setClipboardText(str(addr.exploded))))
            else: # is a network
                if addr.version == 4:
                    subtext_parts.append(f"hosts {addr.num_addresses}")
                    actions.extend([
                        Action("network", f"Network {addr.network_address}", lambda: setClipboardText(str(addr.network_address))),
                        Action("netmask", f"Netmask {addr.netmask}", lambda: setClipboardText(str(addr.netmask))),
                        Action("first", f"First {addr.network_address + 1}", lambda: setClipboardText(str(addr.network_address + 1))),
                        Action("last", f"Last {addr.broadcast_address - 1}", lambda: setClipboardText(str(addr.broadcast_address - 1))),
                        Action("broadcast", f"Broadcast {addr.broadcast_address}", lambda: setClipboardText(str(addr.broadcast_address))),
                        Action("wildcard", f"Wildcard {addr.hostmask}", lambda: setClipboardText(str(addr.hostmask))),
                    ])
                else: # ipv6 network
                    subtext_parts.append(f"contains {2 ** (64 - addr.prefixlen)} /64s")
                    actions.extend([
                        Action("network", f"Network {addr.network_address}", lambda: setClipboardText(str(addr.network_address))),
                        Action("compressed", f"Compressed {addr.compressed}", lambda: setClipboardText(str(addr.compressed))),
                        Action("exploded", f"Exploded {addr.exploded}", lambda: setClipboardText(str(addr.exploded))),
                        Action("last", f"Last {addr.broadcast_address}", lambda: setClipboardText(str(addr.broadcast_address))),
                        Action("netmask", f"Netmask {addr.netmask}", lambda: setClipboardText(str(addr.netmask))),
                    ])
            
            query.add(StandardItem(
                id=md_name,
                text=str(addr),
                subtext=", ".join(subtext_parts),
                icon_factory=lambda p=icon_path: makeImageIcon(str(p)),
                actions=actions
            ))
            return

        # --- Handle advanced queries (sub/sup/next/prev) ---
        else:
            mode = "UNDEF"
            level = 0
            items = []

            if match := re.match(r"\S+\s+(sub|sup|next|prev)\s*(\d*)", query.string):
                mode = match.groups()[0]
                level = int(match.groups()[1]) if match.groups()[1] else 1
            elif match := re.match(r"\S+\s/(\d+)", query.string):
                lookup_prefix = int(match.groups()[0])
                if addr.prefixlen > lookup_prefix:
                    level = addr.prefixlen - lookup_prefix
                    mode = "sup"
                else:
                    level = lookup_prefix - addr.prefixlen
                    mode = "sub"

            if mode == "sub":
                if level > (addr.max_prefixlen - addr.prefixlen):
                    level = addr.max_prefixlen - addr.prefixlen
                    items.append(StandardItem(id=md_name, icon_factory=lambda p=icon_path: makeImageIcon(str(p)), text=f"Can't go lower than /{addr.max_prefixlen} - {ordinal(level)} level"))
                for idx, i in enumerate(addr.subnets(prefixlen_diff=level)):
                    items.append(StandardItem(
                        id=f"subnet_{i}", text=str(i), subtext=f"{ordinal(idx + 1)} Subnet",
                        icon_factory=lambda p=icon_path: makeImageIcon(str(p)),
                        actions=[Action(f"copy_{i}", f"Copy network {i}", lambda r=str(i): setClipboardText(r))]
                    ))
            elif mode == "sup":
                if level > addr.prefixlen:
                    level = addr.prefixlen
                    items.append(StandardItem(id=md_name, icon_factory=lambda p=icon_path: makeImageIcon(str(p)), text=f"Can't go higher than /0 - {ordinal(level)} level"))
                
                supernet = addr.supernet(prefixlen_diff=level)
                items.append(StandardItem(
                    id=f"supernet_{supernet}", text=str(supernet), icon_factory=lambda p=icon_path: makeImageIcon(str(p)),
                    subtext=f"{ordinal(level)} level Supernet",
                    actions=[Action(f"copy_{supernet}", f"Copy network {supernet}", lambda r=str(supernet): setClipboardText(r))]
                ))
            elif mode == "next":
                for i in range(1, self.num_results + 1):
                    next_range = ipaddress.ip_network(f"{addr[0] + i * addr.num_addresses}/{addr.prefixlen}", strict=False)
                    items.append(StandardItem(
                        id=f"next_{i}", text=str(next_range), icon_factory=lambda p=icon_path: makeImageIcon(str(p)),
                        subtext=f"next {ordinal(i)} /{addr.prefixlen} subnet",
                        actions=[Action(f"copy_next_{i}", f"Copy Network {next_range}", lambda r=str(next_range): setClipboardText(r))]
                    ))
            elif mode == "prev":
                for i in range(1, self.num_results + 1):
                    prev_range = ipaddress.ip_network(f"{addr[0] - i * addr.num_addresses}/{addr.prefixlen}", strict=False)
                    items.append(StandardItem(
                        id=f"prev_{i}", text=str(prev_range), icon_factory=lambda p=icon_path: makeImageIcon(str(p)),
                        subtext=f"previous {ordinal(i)} /{addr.prefixlen} subnet",
                        actions=[Action(f"copy_prev_{i}", f"Copy network {prev_range}", lambda r=str(prev_range): setClipboardText(r))]
                    ))
            else:
                items.append(StandardItem(
                    id=md_name,
                    text="Usage: {next|prev|sub|sup|/YY} {level}",
                    icon_factory=lambda p=icon_path: makeImageIcon(str(p)),
                    subtext=f"Query was: {query.string}"
                ))
            
            query.add(items)
