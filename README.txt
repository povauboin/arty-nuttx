Build simple board

./arty_simple.py --with-ethernet

xc3sprog -c nexys4 build/gateware/top.bit

/mnt/data/prog/fpga/milkymist/tools/flterm --kernel ../nuttx/nuttx.bin --port /dev/ttyUSB1
