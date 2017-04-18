Build simple board

    ./arty_simple.py --with-ethernet

    xc3sprog -c nexys4 build/gateware/top.bit

Serial boot

    /mnt/data/prog/fpga/milkymist/tools/flterm --kernel ../nuttx/nuttx.bin --port /dev/ttyUSB1
        # serialboot

Netboot

    sudo ip addr add 192.168.1.100 dev eth0
    sudo iptables -I INPUT -p udp --dport 69 -d 192.168.1.100 -j ACCEPT
    sudo in.tftpd -vvv -L -l -s -u po -a 192.168.1.100 .
        # Will use boot.bin in current dir

    minicom usb1
        # netboot
