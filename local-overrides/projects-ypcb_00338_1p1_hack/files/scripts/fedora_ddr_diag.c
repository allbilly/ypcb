/* JTAG-only CPU/DDR bring-up, using the supplied standalone BSP.
 * DDR tests destroy the first 4096 bytes of each channel. */
#include "xparameters.h"
#include "xil_cache.h"
#include "xil_printf.h"
#include "xil_testmem.h"
#include "xuartlite_l.h"
#include "xgpio.h"

#if XPAR_MICROBLAZE_ADDR_SIZE != 36 || XPAR_MICROBLAZE_ENDIANNESS != 1
#error This application requires the supplied 36-bit little-endian MicroBlaze.
#endif

static volatile u32 scratch[1024] __attribute__((aligned(64)));
static XGpio leds;

static int bram_test(void)
{
    unsigned i;
    for (i = 0; i < 1024; ++i) scratch[i] = 0x12345678U ^ (i * 0x10204081U);
    for (i = 0; i < 1024; ++i)
        if (scratch[i] != (0x12345678U ^ (i * 0x10204081U))) return 0;
    return 1;
}

static int report(unsigned channel, unsigned width, s32 status)
{
    xil_printf("DDR CH%d %d-bit %s\r\n", channel, width,
               status == 0 ? "PASS" : "FAIL");
    return status == 0;
}

static void memory_test(void)
{
    unsigned ch;
    int ok = 1;
    print("DDR BEGIN bytes_per_channel=4096\r\n");
    Xil_DCacheDisable();
    for (ch = 0; ch < 2; ++ch) {
        /* Split extended address: CH0 0x100000000, CH1 0x180000000.
         * The BSP emits LWEA/SWEA and the byte/halfword counterparts. */
        u32 low = ch ? 0x80000000U : 0U;
        ok &= report(ch, 32, Xil_TestMem32(low, 1, 1024, 0xAAAA5555,
                                         XIL_TESTMEM_ALLMEMTESTS));
        ok &= report(ch, 16, Xil_TestMem16(low, 1, 2048, 0xAA55,
                                         XIL_TESTMEM_ALLMEMTESTS));
        ok &= report(ch, 8, Xil_TestMem8(low, 1, 4096, 0xA5,
                                       XIL_TESTMEM_ALLMEMTESTS));
    }
    XGpio_DiscreteWrite(&leds, 1, ok ? 2 : 1);
    print(ok ? "DDR RESULT PASS checks=6\r\n" : "DDR RESULT FAIL\r\n");
}

int main(void)
{
    Xil_DCacheDisable();
    microblaze_disable_interrupts();
    print("YPCB CPU READY diag=1 addr_bits=36\r\n");
    if (!bram_test()) {
        print("CPU BRAM FAIL\r\n");
        for (;;) {}
    }
    print("CPU BRAM PASS bytes=4096\r\n");
    if (XGpio_Initialize(&leds, XPAR_GPIO_0_DEVICE_ID) != 0) {
        print("GPIO INIT FAIL\r\n");
        for (;;) {}
    }
    XGpio_SetDataDirection(&leds, 1, 0);
    XGpio_DiscreteWrite(&leds, 1, 4);
    print("READY FOR DDR send=m\r\n");
    for (;;) {
        if (XUartLite_RecvByte(XPAR_UARTLITE_0_BASEADDR) == 'm') memory_test();
    }
}
