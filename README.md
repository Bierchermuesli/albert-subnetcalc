# Albert IPv4/IPv6 Subnet Calculator
An advanced subnet calculator for the [Albert Launcher](https://albertlauncher.github.io/). Calculates everything from an IP/prefix: subnet details, sub/supernets, neighbours, random samples, and a quick reference for well-known reserved prefixes.

## Synopsis
```
sc                                       — quick hints using your local interfaces + 'list' shortcut
sc list                                  — browse well-known reserved prefixes
sc <prefix>                              — subnet details (network, hosts, broadcast, exploded, EUI-64, …)
sc <prefix> sub [N]                      — split into next-lower subnets (default N=1)
sc <prefix> sup [N]                      — find containing supernet
sc <prefix> next | prev                  — adjacent same-size subnets
sc <prefix> /YY                          — equivalent to sub/sup to /YY
sc <prefix> rand                         — random subnets one level below
sc <prefix> /YY rand                     — random samples at /YY within prefix
```

## Features

##### Smart empty query
Type `sc ` and the launcher fills with hints driven by your **actual interfaces** (`ip -j addr`), so the examples are immediately useful — Tab on a row pulls the prefix into the calculator. Falls back to RFC 5737 / 3849 documentation prefixes when no local addresses are found (e.g. macOS or no `ip` binary).

##### Well-known prefixes — `sc list`
A curated reference: RFC 5737 TEST-NETs, RFC 3849 v6 docs, RFC 1918, RFC 6598 CGNAT, ULA, link-local, loopback, benchmarking (RFC 2544), multicast, NAT64, RFC 6666 discard. Each row shows the canonical prefix and a freshly-randomized sample at a useful size (`/29` for v4, `/64` for v6) — handy for grabbing a unique example for documentation.

Tab on any row rewrites the input to that prefix so you can keep working.

##### Random subnets — `rand`
`sc 2001:db8::/32 /48 rand` returns N (configurable) random `/48`s within `/32`. Uses `random.getrandbits` so samples are spread across the entire space. Bare `<prefix> rand` defaults to one level lower.

##### Subnetting
- `sc 203.0.113.0/24 sub 5` — split into `/29`s (5 levels lower). Capped at `num_results`; a banner row tells you how many subnets exist in total and suggests `rand` for sampling huge spaces.
- `sc 203.0.113.0/24 /22` — auto-detects whether to sub or sup based on prefix lengths.

##### Supernet
`sc 203.0.113.0/24 sup` — `/23`. `sup 8` — `/16`.

##### Same-size neighbours
`sc 203.0.113.0/24 next|prev` — N adjacent subnets, with safe stop at the address-space edge (no crash on `0.0.0.0/24 prev`).

##### IPv6 details
Network/compressed/exploded/last/netmask. Hosts get reverse pointer, hex, binary. **EUI-64 MAC extraction** when the interface ID has the `ff:fe` marker.

## Installation
Clone into the Albert plugin directory and activate in Albert Python Modules Settings. No external Python packages — uses stdlib `ipaddress`. Local-interface hints rely on `ip` (iproute2, standard on Linux).
```
git clone git@github.com:Bierchermuesli/albert-subnetcalc.git ~/.local/share/albert/python/plugins/subnetcalc
```

## Settings
- **Number of results** — applies to `next`, `prev`, capped result count for `sub`, and the size of `rand` batches.

## Bugs / Feedback
Always welcome.
