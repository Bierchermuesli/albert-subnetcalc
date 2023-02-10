# -*- coding: utf-8 -*-

"""Just a Simple IPv4/IPv6 Subnet calculator. Returns all relevant Attributes (Broadcast, First/Last, exploded etc...)
Can also be used for Sub/Supernetting or find previous / next prefixes.

Synopsis: <trigger> [x.x.x.x|x:x::x]/y {next|prev|sub|sup|/YY} {<level>}

Details Args:
next - NEXT aligned subnet with the same Mask
prev - PREVious" aligneda subnet with the same mask
sub - returns next lower SUBbnets e.g. x/24 -> y/25, z/25
sup - find containing higher SUPpernet e.g. x/24s -> x/23

Default one level, can be passed as an additional argument:
x/24 sub 2 -> y/26, z/26 etc..

Instead of sub/sup args, the desired /xx subnet argument is also accepted


"""

from albert import *

import os
import ipaddress
import re

md_iid = "0.5"
md_version = "1.3"
md_id = "sc"
md_name = "SubnetCalc"
md_description = "Calculate IPv4/IPv6 Subnets"
md_license = "MIT"
md_url = "https://github.com/Bierchermuesli/albert-subnetcalc"
md_maintainers = "@Bierchermuesli"
md_lib_dependencies = ["ipaddress"]
md_synopsis = "foobar"


ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])


class Plugin(QueryHandler):

    def id(self):
        return md_id

    def name(self):
        return md_name

    def description(self):
        return md_description

    #default types
    def handleQuery(self, query):

        if query.isValid:
            
            addr = ""
            md_id = "unknown"
            icon = [os.path.dirname(__file__)+"/icon.svg"]

            debug("Subnetcal checking: "+ str(query.string.split()))

            try:
                addr = ipaddress.ip_network(query.string.split()[0],strict=False)
                icon = [os.path.dirname(__file__)+"/ipv"+str(addr.version)+".svg"]
                md_id = "ipv"+str(addr.version)
            except:
                debug("Subnetcal failed: "+ query.string)

                

            
            #without any args
            if addr:
                if len(query.string.split()) ==1:
                    if (addr.version == 4 and addr.prefixlen == 32) or (addr.version == 6 and addr.prefixlen == 128):
                        subtext = "IPv{0} Host".format(str(addr.version))
                        addr.is_host = True
                    else:
                        subtext = "IPv{0} Net".format(str(addr.version))                    
                        addr.is_host = False
                        
                    if addr.is_loopback:    subtext += " Loopback" 
                    if addr.is_global:      subtext += " Global" 
                    if addr.is_private:     subtext += " Private" 
                    if addr.is_multicast:   subtext += " Multicast"
                    if addr.is_multicast:   subtext += " Multicast" 
                    if addr.is_reserved:    subtext += " Reserved" 
                    if addr.is_unspecified: subtext += " Unspecified" 
                    


                    if addr.version == 4: 
                    
                        if addr.is_host:
                            query.add(Item(
                                id = md_id,
                                text = str(addr),
                                icon = icon,
                                subtext = subtext,
                                actions = [
                                    Action("clip","Reverse Pointer {}".format(addr.reverse_pointer), lambda: setClipboardText(str(addr.reverse_pointer)))
                                ]
                            ))
                        else:
                            subtext += ", max hosts {}".format(addr.num_addresses)
                            query.add(Item(
                                id = md_id, 
                                text = str(addr),
                                subtext = subtext,
                                icon = icon,
                                actions = [
                                    Action("clip","Network {}".format(addr.network_address), lambda: setClipboardText(str(addr.network_address))),
                                    Action("clip","Netmask {} (= /{})".format(addr.netmask,addr.prefixlen), lambda: setClipboardText(str(addr.netmask))),
                                    Action("clip","First {}".format(addr.network_address+1), lambda: setClipboardText(str(addr.network_address+1))),
                                    Action("clip","Last {}".format(addr.broadcast_address-1), lambda: setClipboardText(str(addr.broadcast_address-1))),
                                    Action("clip","Broadcast {}".format(addr.broadcast_address), lambda: setClipboardText(str(addr.broadcast_address))),
                                    Action("clip","Widlcard {}".format(addr.hostmask), lambda: setClipboardText(str(addr.hostmask))),
                                    Action("clip","Max Addr {}".format(addr.num_addresses), lambda: setClipboardText(str(addr.num_addresses)))
                                    ]
                            ))
                    #for ipv6
                    else:
                        if addr.is_host:
                            query.add(Item(
                                id = md_id,
                                text = str(addr),
                                icon = icon,
                                subtext = subtext,
                                actions = [
                                    Action("clip","Reverse Pointer {}".format(addr.reverse_pointer), lambda: setClipboardText(str(addr.reverse_pointer))),
                                    Action("clip","Compressed {}".format(addr.compressed), lambda: setClipboardText(str(addr.compressed))),
                                    Action("clip","Exploded {}".format(addr.exploded), lambda: setClipboardText(str(addr.exploded)))
                                ]
                            ))

                        else:

                            subtext += ", contains {} /64".format(2**(64 - addr.prefixlen))

                            query.add(Item(
                                id = md_id,
                                text = str(addr),                   
                                subtext = subtext,
                                icon = icon,        
                                actions = [
                                    Action("clip","Network {}".format(addr.network_address), lambda: setClipboardText(str(addr.network_address))),
                                    Action("clip","Compressed {}".format(addr.compressed), lambda: setClipboardText(str(addr.compressed))),
                                    Action("clip","Exploded {}".format(addr.exploded), lambda: setClipboardText(str(addr.exploded))),
                                    Action("clip","Last {}".format(addr.broadcast_address), lambda: setClipboardText(str(addr.broadcast_address))),
                                    Action("clip","Netmask {} (= /{})".format(addr.netmask,addr.prefixlen), lambda: setClipboardText(str(addr.netmask))),
                                    Action("clip","Widlcard {}".format(addr.hostmask), lambda: setClipboardText(str(addr.hostmask))),
                                    Action("clip","Max Addr {}".format(addr.num_addresses), lambda: setClipboardText(str(addr.num_addresses))),
                                    ]
                            ))
                ### more advanced with further arguments
                else:   
                    #bail out the arguments first: 
                    mode = 'UNDEF'
                    level = 0

                    # <trigger> x.x.x.x |next|prev|sub|sup {#}
                    # Check if NEXT,PREVIOUS SUBneting and SUPerneting with optional desired level
                    if match := re.match('\S+\s+(sub|sup|next|prev)\s*(\d*)',query.string):
                        mode = match.groups()[0]
                        # default one level
                        if match.groups()[1]:
                            level = int(match.groups()[1])
                        else:
                            level = 1
                    # <trigger> x.x.x.x /YY
                    # if desired subnet as CIDR is supplied
                    elif match := re.match('\S+\s/(\d+)',query.string):
                        loookfor = int(match.groups()[0])
                        
                        debug("Looking for: /"+ str(loookfor))

                        #find out direction and level by CIDR
                        # e.g. /24    >     /22 -> sup and 2 levels
                        if addr.prefixlen > loookfor:
                            level = addr.prefixlen - loookfor
                            mode = 'sup'
                        else:
                            level = loookfor - addr.prefixlen
                            mode = 'sub'

                    debug("Choosed Mode:"+ mode + " level:"+ str(level))

                    # Ok, lets calculate...
                    # SUBnet
                    if mode.startswith('sub'):

                        if level > (addr.max_prefixlen-addr.prefixlen):
                            level =  addr.max_prefixlen-addr.prefixlen
                            query.add(Item(
                                    icon = icon,
                                    id = "unknown",
                                    text = "we can't go lower than /{} - {} level ".format(addr.max_prefixlen,ordinal(level))))

                        for idx,i in enumerate(addr.subnets(prefixlen_diff=level)):
                            query.add(Item(
                            id = md_id,
                            text = str(i),
                            subtext = "{} Subnet".format(ordinal(idx+1)),
                            icon = icon,
                            actions = [
                                Action("clip","Copy Network {}".format(i), lambda: setClipboardText(str(i)))
                                ]
                            ))   
                    # next higher "SUPernet"      
                    elif mode.startswith('sup'):

                        if level > (addr.prefixlen): 
                            level = addr.prefixlen
                            query.add(Item(
                                icon = icon,
                                id = "unknown",
                                text = "we can't go higher than /0 - {} level".format(ordinal(level))))

                        for i in range(int(addr.prefixlen) - 8 - level):

                            query.add(Item(
                                id = md_id,
                                text = str(addr.supernet(prefixlen_diff=i+level)),
                                icon = icon,                            
                                subtext = "{} level Supernet".format(ordinal(i+level)),
                                actions = [
                                    Action("clip","Copy Network {}".format(addr.supernet(prefixlen_diff=+level)), str(addr.supernet(prefixlen_diff=i+level)))
                                    ]
                            ))  
                            debug(print(query))

                    #simple "next" aligned subnet with the same Mask
                    elif mode.startswith('next'):                               

                        if addr.version == 4:
                            next_range = ipaddress.IPv4Network(str(addr[-1]+2)+"/"+str(addr.prefixlen),strict=False)
                        else:
                            next_range = ipaddress.IPv6Network(str(addr[-1]+2)+"/"+str(addr.prefixlen),strict=False)

                        query.add(Item(
                            id = md_id,
                            text = str(next_range),
                            icon = icon,                            
                            subtext = "next /{} subnet".format(str(addr.prefixlen)),
                            actions = [
                                Action("clip","Copy Network {}".format(next_range), str(next_range))
                                ]
                        )) 
                    #simple "previous" aligneda subnet with the same mask
                    elif mode.startswith('prev'):

                        if addr.version == 4:
                            prev_range = ipaddress.IPv4Network(str(addr[0]-1)+"/"+str(addr.prefixlen),strict=False)
                        else:
                            prev_range = ipaddress.IPv6Network(str(addr[0]-1)+"/"+str(addr.prefixlen),strict=False)

                        query.add(Item(
                            id = md_id,
                            text = str(prev_range),
                            icon = icon,                     
                            subtext = "previous /{} subnet".format(str(addr.prefixlen)),
                            actions = [
                                Action("clip","Copy Network {}".format(prev_range), str(prev_range))
                                ]
                        )) 
            else:
                query.add(Item(
                    id="unknown",
                    text="no valid IPv4/IPv6 Adress/Subnet",
                    icon = icon,
                    subtext="Query was: %s" % query.string))
