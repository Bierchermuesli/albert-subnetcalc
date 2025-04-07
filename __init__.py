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

md_iid = "3.0"
md_version = "1.6"
md_name = "SubnetCalc"
md_description = "Calculate IPv4/IPv6 Subnets"
md_license = "MIT"
md_url = "https://github.com/Bierchermuesli/albert-subnetcalc"
md_maintainers = "@Bierchermuesli"
md_lib_dependencies = ["ipaddress"]


ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4])


class Plugin(PluginInstance, TriggerQueryHandler):
    def __init__(self):
        PluginInstance.__init__(self)
        TriggerQueryHandler.__init__(self)

    def defaultTrigger(self):
        return "sc "

    # default types
    def handleTriggerQuery(self, query):
        if query.isValid:
            addr = False

            debug("Subnetcal checking: " + str(query.string.split()))
            icon = [f"file:{Path(__file__).parent}/icon.svg"]
            # icon = [f"gen:?text=IPv?&fontscalar=0.3"]

            try:
                addr = ipaddress.ip_network(query.string.split()[0], strict=False)
                icon = [f"file:{Path(__file__).parent}/ipv{addr.version}.svg"]
                # icon = [f"gen:?text=IPv{addr.version}&fontscalar=0.3"]
            except:
                debug("Subnetcal failed: " + query.string)

            # without any args
            if addr:
                if len(query.string.split()) == 1:
                    if (addr.version == 4 and addr.prefixlen == 32) or (addr.version == 6 and addr.prefixlen == 128):
                        subtext = f"IPv{addr.version} Host"
                        addr.is_host = True
                        addr.hex = addr.hosts()[0].packed.hex()
                        addr.bin = ''.join(f'{byte:08b}' for byte in addr.hosts()[0].packed)
                    else:
                        subtext = f"IPv{addr.version} Net"
                        addr.is_host = False

                    if addr.is_loopback:
                        subtext += " Loopback"
                    if addr.is_global:
                        subtext += " Global"
                    if addr.is_private:
                        subtext += " Private"
                    if addr.is_multicast:
                        subtext += " Multicast"
                    if addr.is_multicast:
                        subtext += " Multicast"
                    if addr.is_reserved:
                        subtext += " Reserved"
                    if addr.is_unspecified:
                        subtext += " Unspecified"

                    if addr.version == 4:
                        if addr.is_host:
                            query.add(
                                StandardItem(
                                    text=str(addr),
                                    iconUrls=icon,
                                    subtext=subtext,
                                    actions=[
                                        Action("reverse", f"Reverse Pointer {addr.reverse_pointer}", lambda: setClipboardText(str(addr.reverse_pointer))),
                                        Action("hex", f"Hex {addr.hex}", lambda: setClipboardText(str(addr.hex))),
                                        Action("bin", f"Bin {addr.bin}", lambda: setClipboardText(str(addr.bin)))
                                        ],
                                )
                            )
                        else:
                            subtext += f", max hosts {addr.num_addresses}"
                            query.add(
                                StandardItem(
                                    text=str(addr),
                                    subtext=subtext,
                                    iconUrls=icon,
                                    actions=[
                                        Action("network", f"Network {addr.network_address}", lambda: setClipboardText(str(addr.network_address))),
                                        Action("netmask", f"Netmask {addr.netmask} (= /{addr.prefixlen})", lambda: setClipboardText(str(addr.netmask))),
                                        Action("first", f"First {addr.network_address + 1}", lambda: setClipboardText(str(addr.network_address + 1))),
                                        Action("last", f"Last {addr.broadcast_address - 1}", lambda: setClipboardText(str(addr.broadcast_address - 1))),
                                        Action("broadcast", f"Broadcast {addr.broadcast_address}", lambda: setClipboardText(str(addr.broadcast_address))),
                                        Action("wildcard", f"Widlcard {addr.hostmask}", lambda: setClipboardText(str(addr.hostmask))),
                                        Action("max", f"Max Addr {addr.num_addresses}", lambda: setClipboardText(str(addr.num_addresses))),
                                        Action("networkhex", f"Network Hex {addr.network_address.packed.hex()}", lambda: setClipboardText(str(addr.network_address.packed.hex()))),
                                        Action("netmaskhex", f"Mask Hex {addr.netmask.packed.hex()} (= /{addr.prefixlen})", lambda: setClipboardText(str(addr.netmask.packed.hex()))),
                                    ],
                                )
                            )
                    # for ipv6
                    else:
                        if addr.is_host:
                            query.add(
                                StandardItem(
                                    text=str(addr),
                                    iconUrls=icon,
                                    subtext=subtext,
                                    actions=[
                                        Action("reverse", f"Reverse Pointer {addr.reverse_pointer}", lambda: setClipboardText(str(addr.reverse_pointer))),
                                        Action("compressed", f"Compressed {addr.compressed}", lambda: setClipboardText(str(addr.compressed))),
                                        Action("exploded", f"Exploded {addr.exploded}", lambda: setClipboardText(str(addr.exploded))),
                                        Action("hex", f"Hex {addr.hex}", lambda: setClipboardText(str(addr.hex))),
                                        Action("bin", f"Bin {addr.bin}", lambda: setClipboardText(str(addr.bin)))
                                    ],
                                )
                            )

                        else:
                            subtext += f", contains {2 ** (64 - addr.prefixlen)} /64"
                            query.add(
                                StandardItem(
                                    text=str(addr),
                                    subtext=subtext,
                                    iconUrls=icon,
                                    actions=[
                                        Action("network", f"Network {addr.network_address}", lambda: setClipboardText(str(addr.network_address))),
                                        Action("compressed", f"Compressed {addr.compressed}", lambda: setClipboardText(str(addr.compressed))),
                                        Action("exploded", f"Exploded {addr.exploded}", lambda: setClipboardText(str(addr.exploded))),
                                        Action("last", f"Last {addr.broadcast_address}", lambda: setClipboardText(str(addr.broadcast_address))),
                                        Action("netmask", f"Netmask {addr.netmask} (= /{addr.prefixlen})", lambda: setClipboardText(str(addr.netmask))),
                                        Action("wildcard", f"Widlcard {addr.hostmask}", lambda: setClipboardText(str(addr.hostmask))),
                                        Action("max", f"Max Addr {addr.num_addresses}", lambda: setClipboardText(str(addr.num_addresses))),
                                        Action("networkhex", f"Network Hex {addr.network_address.packed.hex()}", lambda: setClipboardText(str(addr.network_address.packed.hex()))),
                                        Action("netmaskhex", f"Mask Hex {addr.netmask.packed.hex()} (= /{addr.prefixlen})", lambda: setClipboardText(str(addr.netmask.packed.hex()))),                                        

                                    ],
                                )
                            )
                ### more advanced with further arguments
                else:
                    # bail out the arguments first:
                    mode = "UNDEF"
                    level = 0

                    # <trigger> x.x.x.x |next|prev|sub|sup {#}
                    # Check if NEXT,PREVIOUS SUBneting and SUPerneting with optional desired level
                    if match := re.match(r"\S+\s+(sub|sup|next|prev)\s*(\d*)", query.string):
                        mode = match.groups()[0]
                        # default one level
                        if match.groups()[1]:
                            level = int(match.groups()[1])
                        else:
                            level = 1
                    # <trigger> x.x.x.x /YY
                    # if desired subnet as CIDR is supplied
                    elif match := re.match(r"\S+\s/(\d+)", query.string):
                        loookfor = int(match.groups()[0])

                        debug("Looking for: /" + str(loookfor))

                        # find out direction and level by CIDR
                        # e.g. /24    >     /22 -> sup and 2 levels
                        if addr.prefixlen > loookfor:
                            level = addr.prefixlen - loookfor
                            mode = "sup"
                        else:
                            level = loookfor - addr.prefixlen
                            mode = "sub"

                    debug("Choosed Mode:" + mode + " level:" + str(level))

                    # Ok, lets calculate...
                    # SUBnet
                    if mode.startswith("sub"):
                        if level > (addr.max_prefixlen - addr.prefixlen):
                            level = addr.max_prefixlen - addr.prefixlen
                            query.add(StandardItem(iconUrls=icon, id="unknown", text=f"we can't go lower than /{addr.max_prefixlen} - {ordinal(level)} level "))

                        for idx, i in enumerate(addr.subnets(prefixlen_diff=level)):
                            query.add(
                                StandardItem(
                                    id=f"subnet_{i}",
                                    text=str(i),
                                    subtext=f"{ordinal(idx + 1)} Subnet",
                                    iconUrls=icon,
                                    actions=[Action(f"subnet_{i}_copy", f"Copy network {i}", lambda r=str(i): setClipboardText(r))],
                                )
                            )
                    # next higher "SUPernet"
                    elif mode.startswith("sup"):
                        if level > (addr.prefixlen):
                            level = addr.prefixlen
                            query.add(StandardItem(iconUrls=icon, text=f"we can't go higher than /0 - {ordinal(level)} level"))

                        for i in range(int(addr.prefixlen) - 8 - level):
                            query.add(
                                StandardItem(
                                    id=f"supernet_{i + level}",
                                    text=str(addr.supernet(prefixlen_diff=i + level)),
                                    iconUrls=icon,
                                    subtext=f"{ordinal(i + level)} level Supernet",
                                    actions=[
                                        Action(
                                            f"supernet_{i + level}_copy",
                                            f"Copy network {addr.supernet(prefixlen_diff=i + level)}",
                                            lambda r=str(addr.supernet(prefixlen_diff=i + level)): setClipboardText(r),
                                        )
                                    ],
                                )
                            )
                            debug(query.string)

                    # simple "next" aligned subnet with the same mask
                    elif mode.startswith("next"):
                        for i in range(1, 10):
                            if addr.version == 4:
                                next_range = ipaddress.IPv4Network(str(addr[0] + i * addr.num_addresses) + "/" + str(addr.prefixlen), strict=False)
                            else:
                                next_range = ipaddress.IPv6Network(str(addr[0] + i * addr.num_addresses) + "/" + str(addr.prefixlen), strict=False)

                            query.add(
                                StandardItem(
                                    text=str(next_range),
                                    iconUrls=icon,
                                    subtext=f"next {ordinal(i)} /{addr.prefixlen} subnet",
                                    actions=[Action(f"next_{i}", f"Copy Network {next_range}", lambda r=str(next_range): setClipboardText(r))],
                                )
                            )
                    # simple "previous" aligned subnets with the same mask
                    elif mode.startswith("prev"):
                        for i in range(1, 10):
                            if addr.version == 4:
                                prev_range = ipaddress.IPv4Network(str(addr[0] - i * addr.num_addresses) + "/" + str(addr.prefixlen), strict=False)
                            else:
                                prev_range = ipaddress.IPv6Network(str(addr[0] - i * addr.num_addresses) + "/" + str(addr.prefixlen), strict=False)

                            query.add(
                                StandardItem(
                                    text=str(prev_range),
                                    iconUrls=icon,
                                    subtext=f"previous {ordinal(i)} /{addr.prefixlen} subnet",
                                    actions=[Action(f"prev_{i}", f"Copy network {prev_range}", lambda r=str(prev_range): setClipboardText(r))],
                                )
                            )
                    else:
                        query.add(StandardItem(text="desired /xx prefix or next|prev|sub|sup", iconUrls=icon, subtext="Query was: %s" % query.string))
            else:
                query.add(StandardItem(text="no valid IPv4/IPv6 address/subnet", iconUrls=icon, subtext="Query was: %s" % query.string))
