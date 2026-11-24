CC          = arm-none-eabi-gcc
GDB         = arm-none-eabi-gdb
QEMU        = qemu-system-arm
QEMU_MACH   = mps2-an385
LED_ADDR    = 0x40028000
LED_MAP     = R:0,B:1,G:2

PLATFORM_DIR = ../platform
DEBUG_DIR    = ../debug

CFLAGS  = -mcpu=cortex-m3 -mthumb -ffreestanding -O0 -g -Wall -I. -Ibsp -I$(PLATFORM_DIR)
LDFLAGS = -T $(PLATFORM_DIR)/linker.ld -nostartfiles -nostdlib

SRCS    = $(PLATFORM_DIR)/startup.c main.c
BUILD_DIR = build
TARGET  = $(BUILD_DIR)/rtos.elf

all: $(TARGET)

$(TARGET): $(SRCS) $(PLATFORM_DIR)/linker.ld $(PLATFORM_DIR)/mps2_an385.h
	mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) $(LDFLAGS) $(SRCS) -o $(TARGET)

run: $(TARGET)
	$(QEMU) -M $(QEMU_MACH) -nographic -kernel $(TARGET)

debug: $(TARGET)
	$(QEMU) -M $(QEMU_MACH) -nographic -s -S -kernel $(TARGET)

inspect: $(TARGET)
	python3 $(DEBUG_DIR)/led_monitor.py \
		--elf $(TARGET) \
		--machine $(QEMU_MACH) \
		--qemu $(QEMU) \
		--gdb $(GDB) \
		--addr $(LED_ADDR) \
		--leds $(LED_MAP)

clean:
	rm -rf $(BUILD_DIR)

kill:
	-killall -9 $(QEMU) 2>/dev/null || true
	-killall -9 $(GDB) 2>/dev/null || true

.PHONY: all run debug inspect clean kill
