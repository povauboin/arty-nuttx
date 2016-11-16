include ../include/generated/variables.mak
include $(SOC_DIRECTORY)/software/common.mak

OBJECTS=crt0.o gdbstub.o
SEGMENTS=-j .text -j .data -j .rodata

# override optimization flags
CFLAGS+=-Os

all: gdbstub.bin

%.bin: %.elf
	$(OBJCOPY) $(SEGMENTS) -O binary $< $@
	chmod -x $@
	$(PYTHON) -m litex.soc.tools.mkmscimg $@

gdbstub.elf: $(GDBSTUB_DIRECTORY)/linker.ld $(OBJECTS)

%.elf:
	$(LD) $(LDFLAGS) -T $< -N -o $@ \
		$(OBJECTS) \
		-L../libnet \
		-L../libbase \
		-L../libcompiler_rt \
		-lnet -lbase-nofloat -lcompiler_rt
	chmod -x $@

%.o: $(GDBSTUB_DIRECTORY)/%.c
	$(compile)

%.o: $(GDBSTUB_DIRECTORY)/%.S
	$(assemble)

clean:
	rm -f *.o gdbstub.elf gdbstub.bin .*~ *~

.PHONY: all clean main.o
