// Standalone JTAG-SMT2-NC TDI -> TDO electrical loopback test.
//
// IMPORTANT: Disconnect TCK/TMS/TDI/TDO from the FPGA before running this.
// Keep only SMT2 GND, VREF (1.8 V here), VDD and USB connected, then place a
// jumper directly between the SMT2 TDI and TDO pads.

#include <libftdi1/ftdi.h>

#include <array>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <thread>

namespace {

constexpr int kVid = 0x0403;
constexpr int kPid = 0x6014;
constexpr char kDefaultSerial[] = "210251A08870";

bool write_all(ftdi_context *ftdi, const unsigned char *data, int length)
{
	int sent = 0;
	while (sent < length) {
		const int ret = ftdi_write_data(ftdi,
			const_cast<unsigned char *>(data + sent), length - sent);
		if (ret < 0) {
			std::fprintf(stderr, "FTDI write failed: %s\n",
				ftdi_get_error_string(ftdi));
			return false;
		}
		sent += ret;
	}
	return true;
}

bool read_exact(ftdi_context *ftdi, unsigned char *data, int length)
{
	const auto deadline = std::chrono::steady_clock::now() +
		std::chrono::seconds(2);
	int received = 0;
	while (received < length && std::chrono::steady_clock::now() < deadline) {
		const int ret = ftdi_read_data(ftdi, data + received,
			length - received);
		if (ret < 0) {
			std::fprintf(stderr, "FTDI read failed: %s\n",
				ftdi_get_error_string(ftdi));
			return false;
		}
		received += ret;
		if (ret == 0)
			std::this_thread::sleep_for(std::chrono::milliseconds(1));
	}
	if (received != length) {
		std::fprintf(stderr, "FTDI read timeout: received %d of %d bytes\n",
			received, length);
		return false;
	}
	return true;
}

void print_pattern(const unsigned char *data, int length)
{
	for (int i = 0; i < length; ++i)
		std::printf("%02x", data[i]);
}

} // namespace

int main(int argc, char **argv)
{
	const bool external_test = argc >= 2 &&
		std::strcmp(argv[1], "--i-confirm-jtag-isolated") == 0;
	const bool internal_self_test = argc >= 2 &&
		std::strcmp(argv[1], "--internal-mpsse-self-test") == 0;
	if (!external_test && !internal_self_test) {
		std::fprintf(stderr,
			"REFUSING TO RUN. First disconnect SMT2 TCK/TMS/TDI/TDO from "
			"the FPGA, keep GND/VREF/VDD connected, and jumper SMT2 TDI "
			"directly to SMT2 TDO.\n\n"
			"Then run:\n  %s --i-confirm-jtag-isolated [serial]\n\n"
			"Developer-only FT232H self-test (does not test SMT2 TDO):\n"
			"  %s --internal-mpsse-self-test [serial]\n",
			argv[0], argv[0]);
		return 2;
	}

	const char *serial = argc >= 3 ? argv[2] : kDefaultSerial;
	ftdi_context *ftdi = ftdi_new();
	if (ftdi == nullptr) {
		std::fprintf(stderr, "Unable to allocate libftdi context\n");
		return 1;
	}

	int result = 1;
	if (ftdi_set_interface(ftdi, INTERFACE_A) < 0 ||
		ftdi_usb_open_desc(ftdi, kVid, kPid, nullptr, serial) < 0) {
		std::fprintf(stderr, "Unable to open SMT2 serial %s: %s\n", serial,
			ftdi_get_error_string(ftdi));
		ftdi_free(ftdi);
		return 1;
	}

	if (ftdi_usb_reset(ftdi) < 0 ||
		ftdi_set_bitmode(ftdi, 0x00, BITMODE_RESET) < 0 ||
		ftdi_tcioflush(ftdi) < 0 ||
		ftdi_set_latency_timer(ftdi, 2) < 0 ||
		ftdi_set_bitmode(ftdi, 0xfb, BITMODE_MPSSE) < 0) {
		std::fprintf(stderr, "Unable to initialize MPSSE: %s\n",
			ftdi_get_error_string(ftdi));
		goto close_device;
	}

	std::this_thread::sleep_for(std::chrono::milliseconds(50));
	ftdi_tcioflush(ftdi);

	// Same GPIO setup as openFPGALoader's jtag-smt2-nc cable profile:
	// low value/direction 0xe8/0xeb, high value/direction 0x00/0x60.
	// TCK = 60 MHz / (2 * (1 + 299)) = 100 kHz.
	{
		const unsigned char setup[] = {
			DIS_DIV_5, 0x97, 0x8d,
			TCK_DIVISOR, 0x2b, 0x01,
			SET_BITS_LOW, 0xe8, 0xeb,
			SET_BITS_HIGH, 0x00, 0x60,
		};
		if (!write_all(ftdi, setup, sizeof(setup)))
			goto reset_device;
	}
	if (internal_self_test) {
		const unsigned char loopback_start = LOOPBACK_START;
		if (!write_all(ftdi, &loopback_start, 1))
			goto reset_device;
	}

	{
		constexpr std::array<std::array<unsigned char, 4>, 4> patterns{{
			{{0x55, 0xaa, 0x55, 0xaa}},
			{{0xaa, 0x55, 0xaa, 0x55}},
			{{0x00, 0xff, 0x00, 0xff}},
			{{0xff, 0x00, 0xff, 0x00}},
		}};
		bool all_match = true;

		for (const auto &pattern : patterns) {
			// 0x39: bytes out on falling TCK, TDO sampled on rising TCK,
			// LSB-first. Length is encoded as byte_count - 1.
			unsigned char command[] = {
				static_cast<unsigned char>(MPSSE_DO_READ | MPSSE_DO_WRITE |
					MPSSE_WRITE_NEG | MPSSE_LSB),
				0x03, 0x00,
				pattern[0], pattern[1], pattern[2], pattern[3],
				SEND_IMMEDIATE,
			};
			unsigned char received[4] = {};
			if (!write_all(ftdi, command, sizeof(command)) ||
				!read_exact(ftdi, received, sizeof(received))) {
				all_match = false;
				break;
			}

			std::printf("sent=");
			print_pattern(pattern.data(), pattern.size());
			std::printf(" read=");
			print_pattern(received, sizeof(received));
			const bool match = std::memcmp(pattern.data(), received,
				pattern.size()) == 0;
			std::printf(" %s\n", match ? "MATCH" : "MISMATCH");
			all_match &= match;
		}

		if (all_match) {
			std::puts(internal_self_test
				? "PASS: FT232H MPSSE engine and test utility work."
				: "PASS: SMT2 external TDO receive path works.");
			result = 0;
		} else {
			std::puts("FAIL: SMT2 did not read back its transmitted pattern.");
		}
	}

reset_device:
	if (internal_self_test) {
		const unsigned char loopback_end = LOOPBACK_END;
		write_all(ftdi, &loopback_end, 1);
	}
	// Return all FTDI GPIOs to inputs before closing.
	{
		const unsigned char safe[] = {
			SET_BITS_LOW, 0xff, 0x00,
			SET_BITS_HIGH, 0xff, 0x00,
		};
		write_all(ftdi, safe, sizeof(safe));
	}
	ftdi_set_bitmode(ftdi, 0x00, BITMODE_RESET);

close_device:
	ftdi_usb_close(ftdi);
	ftdi_free(ftdi);
	return result;
}
