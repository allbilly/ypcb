#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "fedora_ddr_full_core.h"

#define WORDS 128
enum fault {NONE, ADDRESS_ALIAS, CHANNEL_ALIAS, STUCK_ZERO, STUCK_ONE, LAST_WORD};
struct memory {
    uint32_t data[2][WORDS];
    enum fault fault;
    unsigned bit;
    unsigned reads, writes, barriers, passes;
};

static uint32_t *location(struct memory *m, unsigned channel, uint32_t word)
{
    assert(channel < 2 && word < WORDS);
    if (m->fault == ADDRESS_ALIAS) word &= ~UINT32_C(16);
    if (m->fault == CHANNEL_ALIAS) channel = 0;
    return &m->data[channel][word];
}

static void store(void *context, unsigned channel, uint32_t word, uint32_t value)
{
    struct memory *m = context;
    ++m->writes;
    *location(m, channel, word) = value;
}

static uint32_t load(void *context, unsigned channel, uint32_t word)
{
    struct memory *m = context;
    uint32_t value = *location(m, channel, word);
    ++m->reads;
    if (m->fault == STUCK_ZERO) value &= ~(UINT32_C(1) << m->bit);
    if (m->fault == STUCK_ONE) value |= UINT32_C(1) << m->bit;
    if (m->fault == LAST_WORD && channel == 1 && word == WORDS - 1) value ^= 1;
    return value;
}

static void barrier(void *context)
{
    struct memory *m = context;
    ++m->barriers;
    /* Both complete channels must be filled before any verification begins. */
    assert(m->writes == 2 * WORDS * m->barriers);
}

static void passed(void *context, unsigned channel, unsigned pattern, uint32_t words)
{
    struct memory *m = context;
    assert(words == WORDS && m->passes == 2 * pattern + channel);
    ++m->passes;
}

static int exercise(enum fault fault, unsigned bit, struct ddr_full_failure *failure)
{
    struct memory m;
    struct ddr_full_io io = {&m, store, load, barrier, 0, passed};
    int result;
    memset(&m, 0, sizeof(m)); m.fault = fault; m.bit = bit;
    result = ddr_full_test(&io, WORDS, failure);
    if (fault == NONE) {
        assert(m.reads == 4 * WORDS && m.writes == 4 * WORDS && m.passes == 4 && m.barriers == 2);
    }
    return result;
}

int main(void)
{
    struct ddr_full_failure failure;
    struct memory m;
    struct ddr_full_io io = {&m, store, load, barrier, 0, passed};
    unsigned bit;
    assert(ddr_full_address(0, 0) == UINT64_C(0x100000000));
    assert(ddr_full_address(1, 0) == UINT64_C(0x180000000));
    assert(ddr_full_address(0, DDR_FULL_WORDS_PER_CHANNEL - 1) == UINT64_C(0x17ffffffc));
    assert(ddr_full_address(1, DDR_FULL_WORDS_PER_CHANNEL - 1) == UINT64_C(0x1fffffffc));
    assert(ddr_full_test(&io, 0, &failure) == -1);
    assert(ddr_full_test(&io, DDR_FULL_WORDS_PER_CHANNEL + 1, &failure) == -1);
    assert(exercise(NONE, 0, &failure) == 1);
    assert(exercise(ADDRESS_ALIAS, 0, &failure) == 0);
    assert(exercise(CHANNEL_ALIAS, 0, &failure) == 0);
    assert(exercise(LAST_WORD, 0, &failure) == 0);
    assert(failure.channel == 1 && failure.word == WORDS - 1);
    for (bit = 0; bit < 32; ++bit) {
        assert(exercise(STUCK_ZERO, bit, &failure) == 0);
        assert(exercise(STUCK_ONE, bit, &failure) == 0);
    }
    puts("PASS: full-range endpoints, range guards, every model word visited, address/channel alias, final-word corruption, all 64 stuck-bit faults");
    return 0;
}
