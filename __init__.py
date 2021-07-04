# -*- coding: utf-8 -*-

"""Just a Simple IPv4/IPv6 Subnet calculator. Returns all relevant Attributes (Broadcast, First/Last, exploded etc...)
Can also be used for Sub/Supernetting or find previous / next prefixes.

Synopsis: <trigger> [x.x.x.x|x:x::x]/y {next|prev|sub|sup|/YY} {<level>}

Details Args:
next - NEXT aligned subnet with the same Mask
prev - PREVious" aligneda subnet with the same mask
sub - returns next lower SUBbnets e.g. x/24 -> y/25, z/25
sup - find containing higher SUPpernet e.g. x/24 -> x/23

Default one level, can be passed as an additional argument:
x/24 sub 2 -> y/26, z/26 etc..

Instead of sub/sup args, the desired /xx subnet argument is also accepted


"""

from albert import *

import os
import ipaddress
import re

__title__ = "SubnetCalc"
__version__ = "0.1.2"
__triggers__ = "sc "
__authors__ = ["Stefan Grosser"]
__py_deps__ = ["ipaddress"]


iconPath = iconLookup('network')

ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])

#default types
def handleQuery(query):
    if query.isTriggered:
        items = []
        query.disableSort()
        addr = ""

        debug("Subnetcal checking: "+ str(query.string.split()))

        try:
            addr = ipaddress.ip_network(query.string.split()[0],strict=False)
        except:
            debug("Subnetcal failed: "+ query.string[0])
            return

        #without any args
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
                    items.append(Item(
                        id = __title__,
                        text = str(addr),
                        icon = os.path.dirname(__file__)+"/ipv"+str(addr.version)+".svg",                        
                        subtext = subtext,
                        actions = [
                            ClipAction("Reverse Pointer {}".format(addr.reverse_pointer), str(addr.reverse_pointer))
                        ]
                    ))
                else:
                    subtext += ", max hosts {}".format(addr.num_addresses)
                    items.append(Item(
                        id = __title__, 
                        text = str(addr),
                        subtext = subtext,
                        icon = os.path.dirname(__file__)+"/ipv"+str(addr.version)+".svg",
                        actions = [
                            ClipAction("Network {}".format(addr.network_address), str(addr.network_address)),
                            ClipAction("Netmask {} (= /{})".format(addr.netmask,addr.prefixlen), str(addr.netmask)),
                            ClipAction("First {}".format(addr.network_address+1), str(addr.network_address+1)),
                            ClipAction("Last {}".format(addr.broadcast_address-1), str(addr.broadcast_address-1)),
                            ClipAction("Broadcast {}".format(addr.broadcast_address), str(addr.broadcast_address)),
                            ClipAction("Widlcard {}".format(addr.hostmask), str(addr.hostmask)),
                            ClipAction("Max Addr {}".format(addr.num_addresses), str(addr.num_addresses)),
                            ]
                    ))
            else:
                if addr.is_host:
                    items.append(Item(
                        id = __title__,
                        text = str(addr),
                        icon = os.path.dirname(__file__)+"/ipv"+str(addr.version)+".svg",                        
                        subtext = subtext,
                        actions = [
                            ClipAction("Reverse Pointer {}".format(addr.reverse_pointer), str(addr.reverse_pointer)),
                            ClipAction("Compressed {}".format(addr.compressed), str(addr.compressed)),
                            ClipAction("Exploded {}".format(addr.exploded), str(addr.exploded))
                        ]
                    ))

                else:

                    subtext += ", contains {} /64".format(2**(64 - addr.prefixlen))

                    items.append(Item(
                        id = __title__,
                        text = str(addr),                   
                        subtext = subtext,
                        icon = os.path.dirname(__file__)+"/ipv"+str(addr.version)+".svg",        
                        actions = [
                            ClipAction("Network {}".format(addr.network_address), str(addr.network_address)),
                            ClipAction("Compressed {}".format(addr.compressed), str(addr.compressed)),
                            ClipAction("Exploded {}".format(addr.exploded), str(addr.exploded)),
                            ClipAction("Last {}".format(addr.broadcast_address), str(addr.broadcast_address)),
                            ClipAction("Netmask {} (= /{})".format(addr.netmask,addr.prefixlen), str(addr.netmask)),
                            ClipAction("Widlcard {}".format(addr.hostmask), str(addr.hostmask)),
                            ClipAction("Max Addr {}".format(addr.num_addresses), str(addr.num_addresses)),
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
                    items.append(Item(
                            icon = os.path.dirname(__file__)+"/ipv"+str(addr.version)+".svg"
                            ,text = "we can't go lower than /{} - {} level ".format(addr.max_prefixlen,ordinal(level))))

                for idx,i in enumerate(addr.subnets(prefixlen_diff=level)):
                    items.append(Item(
                    id = __title__,
                    text = str(i),
                    subtext = "{} Subnet".format(ordinal(idx+1)),
                    icon = os.path.dirname(__file__)+"/ipv"+str(addr.version)+".svg",            
                    actions = [
                        ClipAction("Copy Network {}".format(i), str(i))
                        ]
                    ))   
            # next higher "SUPernet"      
            elif mode.startswith('sup'):

                if level > (addr.prefixlen): 
                    level = addr.prefixlen
                    items.append(Item(icon = os.path.dirname(__file__)+"/ipv"+str(addr.version)+".svg",
                    text = "we can't go higher than /0 - {} level".format(ordinal(level))))

                for i in range(int(addr.prefixlen) - 8 - level):

                    items.append(Item(
                        id = __title__,
                        text = str(addr.supernet(prefixlen_diff=i+level)),
                        icon = os.path.dirname(__file__)+"/ipv"+str(addr.version)+".svg",                            
                        subtext = "{} level Supernet".format(ordinal(i+level)),
                        actions = [
                            ClipAction("Copy Network {}".format(addr.supernet(prefixlen_diff=+level)), str(addr.supernet(prefixlen_diff=i+level)))
                            ]
                    ))  

            #simple "next" aligned subnet with the same Mask
            elif mode.startswith('next'):                               

                if addr.version == 4:
                    next_range = ipaddress.IPv4Network(str(addr[-1]+2)+"/"+str(addr.prefixlen),strict=False)
                else:
                    next_range = ipaddress.IPv6Network(str(addr[-1]+2)+"/"+str(addr.prefixlen),strict=False)

                items.append(Item(
                    id = __title__,
                    text = str(next_range),
                    icon = os.path.dirname(__file__)+"/ipv"+str(addr.version)+".svg",                            
                    subtext = "next /{} subnet".format(str(addr.prefixlen)),
                    actions = [
                        ClipAction("Copy Network {}".format(next_range), str(next_range))
                        ]
                )) 
            #simple "previous" aligneda subnet with the same mask
            elif mode.startswith('prev'):

                if addr.version == 4:
                    prev_range = ipaddress.IPv4Network(str(addr[0]-1)+"/"+str(addr.prefixlen),strict=False)
                else:
                    prev_range = ipaddress.IPv6Network(str(addr[0]-1)+"/"+str(addr.prefixlen),strict=False)

                items.append(Item(
                    id = __title__,
                    text = str(prev_range),
                    icon = os.path.dirname(__file__)+"/ipv"+str(addr.version)+".svg",                         
                    subtext = "previous /{} subnet".format(str(addr.prefixlen)),
                    actions = [
                        ClipAction("Copy Network {}".format(prev_range), str(prev_range))
                        ]
                )) 

            else:
                delay(1)
                debug ("Show Help?")

        return items