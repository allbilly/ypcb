#ifndef FEDORA_DDR_FULL_CORE_H
#define FEDORA_DDR_FULL_CORE_H
#include <stdint.h>

#define DDR_FULL_WORDS_PER_CHANNEL UINT32_C(0x20000000)
#define DDR_FULL_PROGRESS_WORDS UINT32_C(0x01000000)

struct ddr_full_io {
    void *context;
    void (*write)(void *, unsigned, uint32_t, uint32_t);
    uint32_t (*read)(void *, unsigned, uint32_t);
    void (*barrier)(void *);
    void (*progress)(void *, unsigned, unsigned, unsigned, uint32_t);
    void (*passed)(void *, unsigned, unsigned, uint32_t);
};

struct ddr_full_failure {
    unsigned channel;
    unsigned pattern;
    uint32_t word;
    uint32_t expected;
    uint32_t actual;
};

static uint64_t ddr_full_address(unsigned channel, uint32_t word)
{
    return UINT64_C(0x100000000) + ((uint64_t)channel << 31) + ((uint64_t)word << 2);
}

/* Every word of both channels has a distinct value. Fill both channels before
 * reading either: a channel alias must not be hidden by testing one at a time.
 * The complementary pass drives every data bit to both zero and one. */
static uint32_t ddr_full_pattern(unsigned channel, uint32_t word, unsigned pattern)
{
    uint32_t value = (word | ((uint32_t)channel << 29)) ^ UINT32_C(0xa5a55a5a);
    return pattern ? ~value : value;
}

static int ddr_full_test(const struct ddr_full_io *io, uint32_t words,
                         struct ddr_full_failure *failure)
{
    unsigned pattern, channel;
    uint32_t word;
    if (!words || words > DDR_FULL_WORDS_PER_CHANNEL) return -1;
    for (pattern = 0; pattern < 2; ++pattern) {
        for (channel = 0; channel < 2; ++channel) {
            for (word = 0; word < words; ++word) {
                io->write(io->context, channel, word, ddr_full_pattern(channel, word, pattern));
                if (io->progress && ((word + 1) % DDR_FULL_PROGRESS_WORDS == 0 || word + 1 == words))
                    io->progress(io->context, channel, pattern, 0, word + 1);
            }
        }
        io->barrier(io->context);
        for (channel = 0; channel < 2; ++channel) {
            for (word = 0; word < words; ++word) {
                uint32_t expected = ddr_full_pattern(channel, word, pattern);
                uint32_t actual = io->read(io->context, channel, word);
                if (expected != actual) {
                    failure->channel = channel;
                    failure->pattern = pattern;
                    failure->word = word;
                    failure->expected = expected;
                    failure->actual = actual;
                    return 0;
                }
                if (io->progress && ((word + 1) % DDR_FULL_PROGRESS_WORDS == 0 || word + 1 == words))
                    io->progress(io->context, channel, pattern, 1, word + 1);
            }
            if (io->passed) io->passed(io->context, channel, pattern, words);
        }
    }
    return 1;
}
#endif
