#!/usr/bin/env python3
import os
import struct
import argparse

from litex.gen import *
from litex.gen.genlib.resetsync import AsyncResetSynchronizer

from litex.boards.platforms import arty

from litex.soc.integration.soc_core import mem_decoder
from litex.soc.integration.soc_sdram import *
from litex.soc.cores.flash import spi_flash
from litex.soc.cores.uart.core import RS232PHY, UART
from litex.soc.cores.spi import SPIMaster
from litex.soc.integration.builder import *
from litex.soc.interconnect import wishbone
from litex.soc.interconnect.wishbonebridge import WishboneStreamingBridge
from litex.soc.interconnect.stream import *

from litedram.modules import MT41K128M16
from litedram.phy import a7ddrphy
from litedram.core.controller import ControllerSettings
from litedram.frontend.bist import LiteDRAMBISTGenerator
from litedram.frontend.bist import LiteDRAMBISTChecker

from liteeth.phy import LiteEthPHY
from liteeth.core.mac import LiteEthMAC

from core_leds import RGBLeds

class _CRG(Module):
    def __init__(self, platform):
        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_sys4x = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys4x_dqs = ClockDomain(reset_less=True)
        self.clock_domains.cd_clk200 = ClockDomain()
        self.clock_domains.cd_clk50 = ClockDomain()

        clk100 = platform.request("clk100")
        rst = platform.request("cpu_reset")

        pll_locked = Signal()
        pll_fb = Signal()
        self.pll_sys = Signal()
        pll_sys4x = Signal()
        pll_sys4x_dqs = Signal()
        pll_clk200 = Signal()
        pll_clk50 = Signal()
        self.specials += [
            Instance("PLLE2_BASE",
                     p_STARTUP_WAIT="FALSE", o_LOCKED=pll_locked,

                     # VCO @ 1600 MHz
                     p_REF_JITTER1=0.01, p_CLKIN1_PERIOD=10.0,
                     p_CLKFBOUT_MULT=16, p_DIVCLK_DIVIDE=1,
                     i_CLKIN1=clk100, i_CLKFBIN=pll_fb, o_CLKFBOUT=pll_fb,

                     # 100 MHz
                     p_CLKOUT0_DIVIDE=16, p_CLKOUT0_PHASE=0.0,
                     o_CLKOUT0=self.pll_sys,

                     # 400 MHz
                     p_CLKOUT1_DIVIDE=4, p_CLKOUT1_PHASE=0.0,
                     o_CLKOUT1=pll_sys4x,

                     # 400 MHz dqs
                     p_CLKOUT2_DIVIDE=4, p_CLKOUT2_PHASE=90.0,
                     o_CLKOUT2=pll_sys4x_dqs,

                     # 200 MHz
                     p_CLKOUT3_DIVIDE=8, p_CLKOUT3_PHASE=0.0,
                     o_CLKOUT3=pll_clk200,

                     # 50MHz
                     p_CLKOUT4_DIVIDE=32, p_CLKOUT4_PHASE=0.0,
                     o_CLKOUT4=pll_clk50
            ),
            Instance("BUFG", i_I=self.pll_sys, o_O=self.cd_sys.clk),
            Instance("BUFG", i_I=pll_sys4x, o_O=self.cd_sys4x.clk),
            Instance("BUFG", i_I=pll_sys4x_dqs, o_O=self.cd_sys4x_dqs.clk),
            Instance("BUFG", i_I=pll_clk200, o_O=self.cd_clk200.clk),
            Instance("BUFG", i_I=pll_clk50, o_O=self.cd_clk50.clk),
            AsyncResetSynchronizer(self.cd_sys, ~pll_locked | ~rst),
            AsyncResetSynchronizer(self.cd_clk200, ~pll_locked | rst),
            AsyncResetSynchronizer(self.cd_clk50, ~pll_locked | ~rst),
        ]

        reset_counter = Signal(4, reset=15)
        ic_reset = Signal(reset=1)
        self.sync.clk200 += \
            If(reset_counter != 0,
                reset_counter.eq(reset_counter - 1)
            ).Else(
                ic_reset.eq(0)
            )
        self.specials += Instance("IDELAYCTRL", i_REFCLK=ClockSignal("clk200"), i_RST=ic_reset)

        eth_clk = Signal()
        self.specials += [
            Instance("BUFR", p_BUFR_DIVIDE="4", i_CE=1, i_CLR=0, i_I=clk100, o_O=eth_clk),
            Instance("BUFG", i_I=eth_clk, o_O=platform.request("eth_ref_clk")),
        ]

class DbgSoC(SoCSDRAM):
    csr_map = {
        "uartdbg_phy": 14,
        "uartdbg": 15,
    }
    csr_map.update(SoCSDRAM.csr_map)

    interrupt_map = {
        "uartdbg": 3,
    }
    interrupt_map.update(SoCSDRAM.interrupt_map)

    mem_map = {
        "gdbstub_rom": 0x20000000,
    }
    mem_map.update(SoCSDRAM.mem_map)

    def __init__(self, platform, *args, gdbstub_rom_size=0x2000, **kwargs):
        SoCSDRAM.__init__(self, platform, *args,
                          cpu_debug_address=self.mem_map["gdbstub_rom"],
                          **kwargs)

        # gdbstub rom
        self.gdbstub_rom_size = gdbstub_rom_size
        self.submodules.gdbstub_rom = wishbone.SRAM(self.gdbstub_rom_size, read_only=True)
        self.register_mem(
            "gdbstub_rom", self.mem_map["gdbstub_rom"],
            self.gdbstub_rom.bus, self.gdbstub_rom_size
        )

        self.submodules.uartdbg_phy = RS232PHY(platform.request("serial", 1),
                                               self.clk_freq, self.uart_baudrate)
        self.submodules.uartdbg = UART(self.uartdbg_phy)

        # break button
        prv = Signal(1, reset=1)
        button = platform.request('user_btn', 0)
        self.sync += [
            prv.eq(button),
            If(button & ~prv,
                self.cpu_or_bridge.ext_break.eq(1),
            ).Else(
                self.cpu_or_bridge.ext_break.eq(0),
            )
        ]

    def initialize_gdbstub_rom(self, data):
        self.gdbstub_rom.mem.init = data

class BaseSoC(DbgSoC):
    default_platform = "arty"

    csr_map = {
        "spiflash":  16,
        "ddrphy":    17,
        "dna":       18,
        "xadc":      19,
        "leds":      20,
        "rgb_leds":  21,
        "generator": 22,
        "checker":   23,
        "spi":       24,
    }
    csr_map.update(DbgSoC.csr_map)

    def __init__(self,
                 platform,
                 **kwargs):
        clk_freq = 100*1000000
        DbgSoC.__init__(self, platform, clk_freq,
            integrated_rom_size=0x8000,
            integrated_sram_size=0x8000,
            **kwargs)

        self.submodules.crg = _CRG(platform)

        # sdram
        self.submodules.ddrphy = a7ddrphy.A7DDRPHY(platform.request("ddram"))
        self.add_constant("A7DDRPHY_BITSLIP", 2)
        self.add_constant("A7DDRPHY_DELAY", 6)
        sdram_module = MT41K128M16(self.clk_freq, "1:4")
        self.register_sdram(self.ddrphy,
                            sdram_module.geom_settings,
                            sdram_module.timing_settings,
                            controller_settings=ControllerSettings(cmd_buffer_depth=8))

        # leds
        self.submodules.rgb_leds = RGBLeds(platform.request("rgb_leds"))

class MiniSoC(BaseSoC):
    csr_map = {
        "ethphy": 30,
        "ethmac": 31
    }
    csr_map.update(BaseSoC.csr_map)

    interrupt_map = {
        "ethmac": 2,
    }
    interrupt_map.update(BaseSoC.interrupt_map)

    mem_map = {
        "ethmac": 0x30000000,  # (shadow @0xb0000000)
    }
    mem_map.update(BaseSoC.mem_map)

    def __init__(self, *args, **kwargs):
        BaseSoC.__init__(self, *args, **kwargs)

        self.submodules.ethphy = LiteEthPHY(self.platform.request("eth_clocks"),
                                            self.platform.request("eth"))
        self.submodules.ethmac = LiteEthMAC(phy=self.ethphy, dw=32, interface="wishbone")
        self.add_wb_slave(mem_decoder(self.mem_map["ethmac"]), self.ethmac.bus)
        self.add_memory_region("ethmac", self.mem_map["ethmac"] | self.shadow_base, 0x2000)

        self.crg.cd_sys.clk.attr.add("keep")
        self.ethphy.crg.cd_eth_rx.clk.attr.add("keep")
        self.ethphy.crg.cd_eth_tx.clk.attr.add("keep")

        self.platform.add_period_constraint(self.crg.cd_sys.clk, 40.0)
        self.platform.add_period_constraint(self.ethphy.crg.cd_eth_rx.clk, 40.0)
        self.platform.add_period_constraint(self.ethphy.crg.cd_eth_tx.clk, 40.0)

        self.platform.add_false_path_constraints(
            self.crg.cd_sys.clk,
            self.ethphy.crg.cd_eth_rx.clk,
            self.ethphy.crg.cd_eth_tx.clk)

    def configure_ip(self, ip_type, ip):
        for i, e in enumerate(ip):
            s = ip_type + str(i + 1)
            s = s.upper()
            self.add_constant(s, e)

class DbgBuilder(Builder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_software_package(
            "gdbstub",
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "gdbstub")
        )

    def _initialize_rom(self):
        super()._initialize_rom()
        bios_file = os.path.join(self.output_dir, "software", "gdbstub",
                                 "gdbstub.bin")
        if self.soc.gdbstub_rom_size:
            with open(bios_file, "rb") as boot_file:
                boot_data = []
                while True:
                    w = boot_file.read(4)
                    if not w:
                        break
                    boot_data.append(struct.unpack(">I", w)[0])
            self.soc.initialize_gdbstub_rom(boot_data)

def main():
    parser = argparse.ArgumentParser(description="Arty LiteX SoC")
    builder_args(parser)
    soc_sdram_args(parser)
    parser.add_argument("--with-ethernet", action="store_true",
                        help="enable Ethernet support")
    parser.add_argument("--nocompile-gateware", action="store_true")
    args = parser.parse_args()

    platform = arty.Platform()
    cls = MiniSoC if args.with_ethernet else BaseSoC
    soc = cls(platform, **soc_sdram_argdict(args))
    builder = DbgBuilder(soc, output_dir="build",
                      compile_gateware=not args.nocompile_gateware,
                      csr_csv="build/csr.csv")
    vns = builder.build()

if __name__ == "__main__":
    main()
