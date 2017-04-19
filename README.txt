Build simple board

    ./arty_simple.py --with-ethernet

    xc3sprog -c nexys4 build/gateware/top.bit

Serial boot

    /mnt/data/prog/fpga/milkymist/tools/flterm --kernel ../nuttx/nuttx.bin --port /dev/ttyUSB1
        # serialboot

Netboot

    sudo ip addr add 192.168.1.100/24 dev eth0
    sudo iptables -I INPUT -p udp --dport 69 -d 192.168.1.100 -j ACCEPT
    sudo in.tftpd -vvv -L -l -s -u po -a 192.168.1.100 .
        # Will use boot.bin in current dir

    minicom usb1
        # netboot

Compiling nuttx

    nuttx (git master)$ l configs/misoc/include/
    total 12
    -rw-r----- 1 po po 4012 Nov  8 17:00 board.h
    lrwxrwxrwx 1 po po   57 Nov 29 16:09 generated -> ../../../../exo-16-arty/build/software/include/generated//
    drwxr-x--- 1 po po 4096 Nov 29 16:08 generated-sample/
    -rw-r----- 1 po po   11 Nov 29 16:06 .gitignore

   nuttx (git master)$ l configs/misoc/include/generated/
    total 40
    -rw-r----- 1 po po 20282 Apr 19 15:45 csr.h
    -rw-r----- 1 po po   379 Apr 18 20:33 mem.h
    -rw-r----- 1 po po    28 Jan 10 02:18 output_format.ld
    -rw-r----- 1 po po   268 Apr 18 20:33 regions.ld
    -rw-r----- 1 po po  2814 Jan 10 02:18 sdram_phy.h
    -rw-r----- 1 po po   638 Apr 18 20:33 variables.mak

Nuttx

    Initializing SDRAM...
    Memtest OK
    Booting from serial...
    Press Q or ESC to abort boot completely.
    sL5DdSMmkekro
    Timeout
    Booting from network...
    Local IP : 192.168.1.50
    Remote IP: 192.168.1.100
    Successfully downloaded 302172 bytes from boot.bin over TFTP
    Unable to download cmdline.txt over TFTP
    No command line parameters found
    Unable to download initrd.bin over TFTP
    No initial ramdisk found
    Executing booted program.

    NuttShell (NSH)
    nsh>hello
    Hello, World!!
    nsh>help mw
    mw usage:  mw <hex-address>[=<hex-value>][ <hex-byte-count>]
    nsh>mw 0x6000a800=0x80
      6000a800 = 0x00000000 -> 0x00000080
    nsh>mw 0x6000a80c=0x80
      6000a80c = 0x00000000 -> 0x00000080
    nsh>mw 0x6000a810=0x80
      6000a810 = 0x00000000 -> 0x00000080
    nsh>mw 0x6000a818=0x80
      6000a818 = 0x00000000 -> 0x00000080
    nsh>mw 0x6000a820=0x80
      6000a820 = 0x00000000 -> 0x00000080
    nsh>

With 32bits width
    nsh>mw 0x6000a800
      6000a800 = 0x00000000
    nsh>mw 0x6000a800=0xffffff
      6000a800 = 0x00000000 -> 0x00ffffff

Debug

    Manual break (press button)

    lm32-elf-gdb -n ../nuttx/nuttx
