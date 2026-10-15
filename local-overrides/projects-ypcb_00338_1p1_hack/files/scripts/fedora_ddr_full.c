/* Entire dual-DDR capacity test. Destroys both complete 2 GiB regions.
 * Runs from local BRAM; full-memory access uses the BSP's 36-bit EA opcodes. */
#include "xparameters.h"
#include "xil_cache.h"
#include "xil_printf.h"
#include "xuartlite_l.h"
#include "mb_interface.h"
#include "fedora_ddr_full_core.h"

#if XPAR_MICROBLAZE_ADDR_SIZE != 36 || XPAR_MICROBLAZE_ENDIANNESS != 1
#error This application requires the supplied 36-bit little-endian MicroBlaze.
#endif

static volatile u32 scratch[1024] __attribute__((aligned(64)));

static void memory_write(void *context, unsigned channel, uint32_t word, uint32_t value)
{
    u64 address = ddr_full_address(channel, word);
    (void)context;
    swea(address, value);
}

static uint32_t memory_read(void *context, unsigned channel, uint32_t word)
{
    u64 address = ddr_full_address(channel, word);
    (void)context;
    return lwea(address);
}

static void memory_barrier(void *context)
{
    (void)context;
    __asm__ __volatile__("mbar 1" ::: "memory");
}

static void progress(void *context, unsigned channel, unsigned pattern,
                     unsigned reading, uint32_t words)
{
    (void)context;
    xil_printf("DDR FULL PROGRESS ch=%d pattern=%d phase=%s bytes=%u\r\n",
               channel, pattern, reading ? "READ" : "WRITE", words << 2);
}

static void passed(void *context, unsigned channel, unsigned pattern, uint32_t words)
{
    (void)context;
    xil_printf("DDR FULL PASS ch=%d pattern=%d bytes=%u\r\n", channel, pattern, words << 2);
}

static void memory_test(void)
{
    const struct ddr_full_io io = {0, memory_write, memory_read, memory_barrier, progress, passed};
    struct ddr_full_failure failure = {0, 0, 0, 0, 0};
    int result;
    print("DDR FULL BEGIN bytes_per_channel=2147483648 patterns=2\r\n");
    result = ddr_full_test(&io, DDR_FULL_WORDS_PER_CHANNEL, &failure);
    if (result != 1) {
        u64 address = ddr_full_address(failure.channel, failure.word);
        xil_printf("DDR FULL FAIL ch=%d pattern=%d addr_hi=%08x addr_lo=%08x expected=%08x actual=%08x\r\n",
                   failure.channel, failure.pattern, (u32)(address >> 32), (u32)address,
                   failure.expected, failure.actual);
        print("DDR FULL RESULT FAIL\r\n");
    } else {
        print("DDR FULL RESULT PASS checks=4 bytes_per_channel=2147483648\r\n");
    }
}

int main(void)
{
    unsigned i;
    Xil_DCacheDisable();
    microblaze_disable_interrupts();
    print("YPCB CPU READY diag=2 addr_bits=36\r\n");
    for (i = 0; i < 1024; ++i) scratch[i] = 0x12345678U ^ (i * 0x10204081U);
    for (i = 0; i < 1024; ++i) {
        if (scratch[i] != (0x12345678U ^ (i * 0x10204081U))) {
            print("CPU BRAM FAIL\r\n");
            for (;;) {}
        }
    }
    print("CPU BRAM PASS bytes=4096\r\n");
    print("READY FOR FULL DDR send=f\r\n");
    for (;;) {
        if (XUartLite_RecvByte(XPAR_UARTLITE_0_BASEADDR) == 'f') memory_test();
    }
}
