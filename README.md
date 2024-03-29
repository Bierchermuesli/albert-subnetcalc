# Albert IPv4/IPv6 Subnet Calculator 
This is an advanced subnet calculator for awsome. [Albert Launcher](https://albertlauncher.github.io/). 

This module calculates everything from an IP/Prefix: IP/subnet details, subnet/supernet, subnet neighbours etc.

Synopsis: `sc <trigger> [x.x.x.x|x:x::x]/y {next|prev|sub|sup|/YY} {<level>}`


##### Simple Subnet output
![image](https://user-images.githubusercontent.com/13567009/124381622-a9c62280-dcc3-11eb-8ab4-cab3da8ad468.png)

##### Calculate smaller subnets - this is equivalent to `sc 203.0.113.0/24 sub 5` (/29 is the 5h level)

![image](https://user-images.githubusercontent.com/13567009/124381638-bea2b600-dcc3-11eb-9e12-332a6a3802ab.png)

##### find the more specific *SUP*pernet (you can also type e.g.`sc 203.0.113.0/24 /22`)

![image](https://user-images.githubusercontent.com/13567009/124720996-01a19b00-df09-11eb-838e-25d53edb42a9.png)


##### find next subnet of same size:

![image](https://user-images.githubusercontent.com/13567009/124381719-4f799180-dcc4-11eb-84b3-62d32f63a7f6.png)

##### find previous subnet of same size 

![image](https://user-images.githubusercontent.com/13567009/124381725-53a5af00-dcc4-11eb-831c-4d77bbc3295b.png)

##### IPv6 Works too:
![image](https://user-images.githubusercontent.com/13567009/124381755-7df76c80-dcc4-11eb-883f-fad922c86c38.png)

![image](https://user-images.githubusercontent.com/13567009/124721189-2bf35880-df09-11eb-9e48-0a996d98ea6b.png)


# Installation
Simply clone into the Albert plugin directory and activate in Albert Python Modules Settings. Python3 and use the ipaddress.
```
pip3 install ipaddress
git clone  git@github.com:Bierchermuesli/albert-subnetcalc.git  ~/.local/share/albert/python/plugins/subnetcalc
```
# Bugs / Feedback
always welcome
