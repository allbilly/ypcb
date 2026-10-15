// Trace Xilinx cable libusb calls without logging proprietary firmware bytes.
// Build: cc -shared -fPIC -o dlc10_usb_trace.so dlc10_usb_trace.c -ldl
// Use: LD_PRELOAD=/absolute/path/dlc10_usb_trace.so hw_server ...
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <libusb-1.0/libusb.h>

typedef int (*ctrl_fn_t)(libusb_device_handle *, uint8_t, uint8_t,
		uint16_t, uint16_t, unsigned char *, uint16_t, unsigned int);
static ctrl_fn_t real_ctrl;
static int (*real_reset)(libusb_device_handle *);
static int (*real_submit)(struct libusb_transfer *);

static void *real_symbol(void *handle, const char *name)
{
	static void *(*real_dlsym)(void *, const char *);
	if (!real_dlsym)
		real_dlsym = dlvsym(RTLD_NEXT, "dlsym", "GLIBC_2.34");
	return real_dlsym(handle, name);
}

// hw_server resolves libusb through an explicit dlopen handle. Intercept
// dlsym so those calls are captured too; ordinary LD_PRELOAD alone misses it.
void *dlsym(void *handle, const char *name)
{
	void *original = real_symbol(handle, name);
	if (strcmp(name, "libusb_control_transfer") == 0) {
		real_ctrl = (ctrl_fn_t)original;
		return (void *)libusb_control_transfer;
	}
	if (strcmp(name, "libusb_reset_device") == 0) {
		real_reset = (int (*)(libusb_device_handle *))original;
		return (void *)libusb_reset_device;
	}
	if (strcmp(name, "libusb_submit_transfer") == 0) {
		real_submit = (int (*)(struct libusb_transfer *))original;
		return (void *)libusb_submit_transfer;
	}
	return original;
}

static uint32_t fnv1a32(const unsigned char *data, unsigned int length)
{
	uint32_t hash = 2166136261u;
	for (unsigned int i = 0; i < length; i++) {
		hash ^= data[i];
		hash *= 16777619u;
	}
	return hash;
}

int libusb_control_transfer(libusb_device_handle *handle,
		uint8_t bmRequestType, uint8_t bRequest, uint16_t wValue,
		uint16_t wIndex, unsigned char *data, uint16_t wLength,
		unsigned int timeout)
{
	if (!real_ctrl)
		real_ctrl = (ctrl_fn_t)real_symbol(RTLD_NEXT, "libusb_control_transfer");
	const int out = !(bmRequestType & LIBUSB_ENDPOINT_IN);
	const uint32_t out_hash = out && data && wLength ?
			fnv1a32(data, wLength) : 0;
	const unsigned int out_first = out && data && wLength ? data[0] : 0;
	int rc = real_ctrl(handle, bmRequestType, bRequest, wValue,
			wIndex, data, wLength, timeout);
	const uint32_t in_hash = !out && rc > 0 && data ?
			fnv1a32(data, (unsigned int)rc) : 0;
	if (bRequest == 0xA0 || bRequest == 0xA3) {
		fprintf(stderr,
				"DLC10_USB ctrl type=%02x req=%02x value=%04x index=%04x len=%u timeout=%u rc=%d hash=%08x first=%02x\n",
				bmRequestType, bRequest, wValue, wIndex, wLength,
				timeout, rc, out ? out_hash : in_hash, out_first);
		fflush(stderr);
	}
	return rc;
}

int libusb_reset_device(libusb_device_handle *handle)
{
	if (!real_reset)
		real_reset = (int (*)(libusb_device_handle *))real_symbol(
				RTLD_NEXT, "libusb_reset_device");
	fprintf(stderr, "DLC10_USB reset begin\n");
	int rc = real_reset(handle);
	fprintf(stderr, "DLC10_USB reset rc=%d\n", rc);
	fflush(stderr);
	return rc;
}

int libusb_submit_transfer(struct libusb_transfer *transfer)
{
	if (!real_submit)
		real_submit = (int (*)(struct libusb_transfer *))real_symbol(
				RTLD_NEXT, "libusb_submit_transfer");
	if (transfer && transfer->type == LIBUSB_TRANSFER_TYPE_CONTROL) {
		struct libusb_control_setup *setup =
				libusb_control_transfer_get_setup(transfer);
		if (setup->bRequest != 0xA0 && setup->bRequest != 0xA3)
			return real_submit(transfer);
		const unsigned char *data = libusb_control_transfer_get_data(transfer);
		const uint16_t len = libusb_le16_to_cpu(setup->wLength);
		const uint32_t hash = !(setup->bmRequestType & LIBUSB_ENDPOINT_IN) &&
				data && len ? fnv1a32(data, len) : 0;
		fprintf(stderr,
				"DLC10_USB submit-ctrl type=%02x req=%02x value=%04x index=%04x len=%u timeout=%u hash=%08x first=%02x\n",
				setup->bmRequestType, setup->bRequest,
				libusb_le16_to_cpu(setup->wValue),
				libusb_le16_to_cpu(setup->wIndex), len,
				transfer->timeout, hash,
				data && len ? data[0] : 0);
		fflush(stderr);
	}
	return real_submit(transfer);
}
