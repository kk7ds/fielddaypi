# Field Day Pi Mini-Server

This is a small project to create a very tiny, power-efficient mini-server to support [ARRL Field Day](http://www.arrl.org/field-day) off-grid and operations without internet access. The primary goals/features are:

* Provides a WiFi Access Point for networked logs between operators
* Provides a GPS-synced network time source for log time sync and [FT8](https://physics.princeton.edu/pulsar/k1jt/wsjtx.html) operation
* Provides a small amount of low-performance file-sharing space between operators
* Is very compact and requires little power, suitable for all-day use on battery

The author uses a [Pi Zero W](https://www.raspberrypi.com/products/raspberry-pi-zero-w/) for this purpose, requiring only 5v power input at ~200mA and wireless networking between operator machines.

## Setup

This project is constructed as a set of ansible roles which are used to configure a target Pi. Ideally you would have the Pi already set up and accessible on your local network somewhere, although you can run these directly on the Pi itself.

First, install ansible, git, and clone the project:

    $ apt-get install -y ansible git
    $ git clone https://github.com/kk7ds/fielddaypi

The easiest thing to do is edit the `settings.yaml` file with the minimum settings you need to make. At a minimum, you need to set the `wpakey`.

Then you can run ansible to configure everything:

    $ ansible-playbook -i inventory --extra-vars @settings.yaml playbook.yaml

If you want the file server functionality, you need to determine the device you want to use. If you create an extra partition on the SD card, it will probably look like this:

    data_vol: "/dev/mmcblk0p3"

The device should already have a filesystem on it and be present before you run the commands below. You can also label the filesystem and use `LABEL=foo` as the `data_vol` to more dynamically select the proper device.

You can also run this against a Pi on your network by setting up your inventory file like this:

    [fieldday]
    192.168.1.50 ansible_user=pi

After running ansible and letting it configure everything, reboot the Pi. After that, you should see a new WiFi network called "Field Day" using the WPA2 password you provided. If you enabled the data volume, you should see the machine on the network and can access the "public" share from Windows, Mac, and Linux machines.

## WiFi (Access Point)

This uses the integrated WiFi capability of the Pi Zero W or Pi 3 (and later) boards to provide a Wireless Access Point and network. It will perform fine for a small number of clients in a very close area with low bandwidth demands. Do not expect long range or extreme performance.

It is configured to provide DHCP, DNS, NTP, and (if desired) a small amount of public file sharing space between clients via SMB. The file storage is configured to be fully open and public for easy configuration. Do not expect that to be secure, as anyone on the network can read and write files there.

## WiFi (Client)

The Pi can simultaneously serve as an access point as well as attach to another WiFi network as a client. Simply configure the network client in `/etc/wpa_supplicant/wpa_supplicant.conf` per usual and both will be available. Performance will suffer even more being attached to two networks, but it will work. This can also provide internet access to downstream clients, if the upstream network has it.


## GPS Time Sync

This project expects a 5v GPS with PPS capability to be connected directly to the Pi's GPIO header. The $11 [Neo6M](https://www.amazon.com/gp/product/B07P8YMVNT/) (and compatible) module works well for this and is suited for easy connection and physical mounting to the header with pins. Here is the expected mapping

| Pi pin | GPS pin |
|--------|---------|
| 4      | VCC     |
| 6      | GND     |
| 8 (TX) | RX      |
| 10 (RX)| TX      |
| 12 (GPIO 18) | PPS |

It is important to note that PPS is required to get really good performance in the absence of an internet connection. Without it (or without a suitable view of the sky to deliver solid PPS signaling) you will get time, but it will be off by a couple hundred milliseconds and wander quite a bit. Good enough for logging, but not ideal for FT8. With PPS signaling, the author has observed <= 1ms performance standalone when compared to public NTP servers.

The Pi server provides NTP support over the network, so set the NTP server on your client machines to point to the Pi. For Windows, install [Meinberg NTP](https://www.meinbergglobal.com/english/sw/ntp.htm). Configuration of an NTP client can be done like this:

    server 192.168.5.1 iburst minpoll 3 maxpoll 6

Although the server's integrated DNS server will also redirect any normal `*.pool.ntp.org` hosts to itself, so you may not even need to configure the clients.

You can check the status of the time sync by SSHing into the pi and running two commands:

    $ chronyc sources
    MS Name/IP address         Stratum Poll Reach LastRx Last sample
    ===============================================================================
    #- NMEA                          0   1   377     3  +1926us[+1927us] +/-  100ms
    #* PPS                           0   1   377     3  +3890ns[+4039ns] +/- 4238ns
    $ chronyc sourcestats
    Name/IP Address            NP  NR  Span  Frequency  Freq Skew  Offset  Std Dev
    ==============================================================================
    NMEA                       15  11    28   +244.697    229.486  +1669us  1820us
    PPS                        14   9    26     +0.125      0.279   +220ns  1952ns

This can also be seen in a web browser connecting to the Pi.

In the first section, either `NMEA` or `PPS` should have an asterisk next to it, indicating that the clock is synced to that source. If only `NMEA` is synced, that likely means that you have a good fix, but are not receiving the PPS signaling. If neither is synced, then you do not have a suitable GPS fix, your clock is not synced, and clients will not synchronize to this system. Running `cgps -s` will provide GPS information.
