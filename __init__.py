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

<<<<<<< HEAD
md_iid = "4.0"
=======
md_iid = "5.0"
>>>>>>> bb88604 (Update to API v5.0)
md_version = "2.3"
md_name = "SubnetCalc"
md_description = "Calculate IPv4/IPv6 Subnets"
md_license = "MIT"
md_url = "https://github.com/Bierchermuesli/albert-subnetcalc"
<<<<<<< HEAD
md_maintainers = "@Bierchermuesli"
md_authors = "@Bierchermuesli"
=======
md_maintainers = ["@Bierchermuesli"]
md_authors = ["@Bierchermuesli"]
>>>>>>> bb88604 (Update to API v5.0)
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

    def _get_eui64_mac(self, addr: ipaddress.IPv6Address) -> str | None:
        """Check for EUI-64 identifier and return MAC address if found."""
        if addr.packed[11:13] != b'\xff\xfe':
            return None
        
        eui64_bytes = bytearray(addr.packed[8:])
        eui64_bytes[0] ^= 0b00000010

        mac_bytes = eui64_bytes[0:3] + eui64_bytes[3+2:]
        return ':'.join(f'{b:02x}' for b in mac_bytes)

    def _get_simple_subtext_parts(self, addr):
        is_host = (addr.version == 4 and addr.prefixlen == 32) or \
                  (addr.version == 6 and addr.prefixlen == 128)
        
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
        is_host = (addr.version == 4 and addr.prefixlen == 32) or \
                  (addr.version == 6 and addr.prefixlen == 128)
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

    def _handle_simple_query(self, query, addr, icon_path):
        subtext = ", ".join(self._get_simple_subtext_parts(addr))
        actions = self._get_simple_actions(addr)
        
        query.add(StandardItem(
            id=md_name,
            text=str(addr),
            subtext=subtext,
            icon_factory=lambda p=icon_path: makeImageIcon(str(p)),
            actions=actions
        ))

    def _handle_advanced_query(self, query, addr, icon_path):
        mode = "UNDEF"
        level = 0
        items = []

        if match := re.match(r"\S+\s+(sub|sup|next|prev)\s*(\d*)", query.string):
            mode = match.groups()[0]
            level = int(match.groups()[1]) if match.groups()[1] else 1
        elif match := re.match(r"\S+\s+/(\d+)", query.string):
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
        elif mode in ["next", "prev"]:
            for i in range(1, self.num_results + 1):
                offset = i * addr.num_addresses
                if mode == "prev":
                    offset = -offset
                
                new_net = ipaddress.ip_network(f"{addr[0] + offset}/{addr.prefixlen}", strict=False)
                items.append(StandardItem(
                    id=f"{mode}_{i}", text=str(new_net), icon_factory=lambda p=icon_path: makeImageIcon(str(p)),
                    subtext=f"{mode} {ordinal(i)} /{addr.prefixlen} subnet",
                    actions=[Action(f"copy_{mode}_{i}", f"Copy Network {new_net}", lambda r=str(new_net): setClipboardText(r))]
                ))
        else:
            items.append(StandardItem(
                id=md_name,
                text="Usage: {next|prev|sub|sup|/YY} {level}",
                icon_factory=lambda p=icon_path: makeImageIcon(str(p)),
                subtext=f"Query was: {query.string}"
            ))
        
        query.add(items)

    def handleTriggerQuery(self, query):
        if not query.isValid:
            return

        addr = None
        icon_path = Path(__file__).parent / "icon.svg"

        try:
            addr = ipaddress.ip_network(query.string.split()[0], strict=False)
            icon_path = Path(__file__).parent / f"ipv{addr.version}.svg"
        except Exception as e:
            debug(f"Subnetcal failed to parse: '{query.string}' with error: {e}")

        if not addr:
            query.add(StandardItem(
                id=md_name,
                text="No valid IPv4/IPv6 address/subnet",
                subtext=f"Query was: {query.string}",
                icon_factory=lambda p=icon_path: makeImageIcon(str(p))
            ))
            return

        if len(query.string.split()) == 1:
            self._handle_simple_query(query, addr, icon_path)
        else:
            self._handle_advanced_query(query, addr, icon_path)