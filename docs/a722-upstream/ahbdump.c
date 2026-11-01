// Allocates AHardwareBuffers with different usages and prints their gralloc native_handle
// (numFds, numInts, every int) to see how the Qualcomm gralloc marks UBWC buffers.
#include <android/hardware_buffer.h>
#include <stdio.h>
#include <stdint.h>
typedef struct native_handle { int version; int numFds; int numInts; int data[0]; } native_handle_t;
extern const native_handle_t *AHardwareBuffer_getNativeHandle(const AHardwareBuffer *buffer);
static void one(const char *name, uint64_t usage, uint32_t fmt, uint32_t w, uint32_t h) {
    AHardwareBuffer_Desc d = { .width = w, .height = h, .layers = 1, .format = fmt, .usage = usage };
    AHardwareBuffer *b = NULL;
    int r = AHardwareBuffer_allocate(&d, &b);
    if (r) { printf("%-28s alloc failed %d\n", name, r); return; }
    AHardwareBuffer_Desc o; AHardwareBuffer_describe(b, &o);
    const native_handle_t *nh = AHardwareBuffer_getNativeHandle(b);
    printf("%-28s %ux%u stride %u  version %d numFds %d numInts %d\n", name, o.width, o.height, o.stride, nh->version, nh->numFds, nh->numInts);
    printf("   ints:");
    for (int i = nh->numFds; i < nh->numFds + nh->numInts; i++) printf(" [%d]=0x%08x", i, (uint32_t)nh->data[i]);
    printf("\n");
    AHardwareBuffer_release(b);
}
int main(void) {
    uint64_t gpu = AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE | AHARDWAREBUFFER_USAGE_GPU_FRAMEBUFFER;
    one("gpu rgba8", gpu, AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM, 1172, 686);
    one("gpu+composer rgba8", gpu | AHARDWAREBUFFER_USAGE_COMPOSER_OVERLAY, AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM, 1920, 1080);
    one("gpu+cpu_read_often rgba8", gpu | AHARDWAREBUFFER_USAGE_CPU_READ_OFTEN, AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM, 1172, 686);
    one("cpu only rgba8", AHARDWAREBUFFER_USAGE_CPU_READ_OFTEN | AHARDWAREBUFFER_USAGE_CPU_WRITE_OFTEN, AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM, 256, 256);
    one("gpu rgb565", gpu, AHARDWAREBUFFER_FORMAT_R5G6B5_UNORM, 512, 512);
    one("gpu rgba16f", gpu, AHARDWAREBUFFER_FORMAT_R16G16B16A16_FLOAT, 512, 512);
    uint64_t ubwc = 1ULL << 28; /* GRALLOC_USAGE_PRIVATE_ALLOC_UBWC = AHARDWAREBUFFER_USAGE_VENDOR_0 */
    one("gpu+UBWC rgba8", gpu | ubwc, AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM, 1172, 686);
    one("gpu+composer+UBWC rgba8", gpu | ubwc | AHARDWAREBUFFER_USAGE_COMPOSER_OVERLAY, AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM, 1920, 1080);
    one("gpu+UBWC rgb565", gpu | ubwc, AHARDWAREBUFFER_FORMAT_R5G6B5_UNORM, 512, 512);
    return 0;
}
