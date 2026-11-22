#!/usr/bin/env python3
"""TEST: TU_LAZY_COMMIT - back app memory with real pages only where resources are bound.

Run from the Mesa tree (cwd = mesa root), after the A8xx series and the AIO scripts.

With TU_LAZY_COMMIT=<n> in the environment (1 = 4 MB, otherwise MB), vkAllocateMemory of plain
memory (no import/export, no capture replay, not host-cached/lazily-allocated/protected) of at
least that size only reserves a KGSL virtual range (VBO, unbound pages read zero). Real memory is
allocated and bound in 64 KiB chunks when an image or buffer is bound to the range, when a sparse
bind uses it as backing, or for the whole object when it is mapped. Games that reserve big
blocks and fill them partly (DOOM: The Dark Ages) then use much less physical memory.

Off unless TU_LAZY_COMMIT is set. KGSL only (needs IOCTL_KGSL_GPUMEM_BIND_RANGES).
"""
import sys

V = "src/freedreno/vulkan/"
MARK = "TU_LAZY_COMMIT"


def edit(path, pairs):
    p = V + path
    s = open(p).read()
    if MARK in s and all(new in s for _, new in pairs):
        print(f"lazy_commit.py: {path}: already applied")
        return
    for old, new in pairs:
        n = s.count(old)
        if n != 1:
            sys.exit(f"lazy_commit.py: {path}: anchor found {n} times:\n{old[:200]}")
        s = s.replace(old, new, 1)
    open(p, "w").write(s)
    print(f"lazy_commit.py: {path}: patched ({len(pairs)} edits)")


# ---------------------------------------------------------------- tu_knl.h
edit("tu_knl.h", [
    ("   bool lazy : 1;\n",
     "   bool lazy : 1;\n"
     "   /* TU_LAZY_COMMIT: virtual BO of a lazily committed tu_device_memory */\n"
     "   bool lazy_commit : 1;\n"),
    ("""   void (*sparse_vma_finish)(struct tu_device *device,
                             struct tu_sparse_vma *vma);
""",
     """   void (*sparse_vma_finish)(struct tu_device *device,
                             struct tu_sparse_vma *vma);
   /* TU_LAZY_COMMIT: bind [bo_offset, +size) of bo at vma_offset, synchronously */
   VkResult (*sparse_vma_bind_range)(struct tu_device *device,
                                     struct tu_sparse_vma *vma,
                                     struct tu_bo *bo, uint64_t bo_offset,
                                     uint64_t vma_offset, uint64_t size);
"""),
    ("""void tu_sparse_vma_finish(struct tu_device *device,
                          struct tu_sparse_vma *vma);
""",
     """void tu_sparse_vma_finish(struct tu_device *device,
                          struct tu_sparse_vma *vma);

/* TU_LAZY_COMMIT */
VkResult tu_sparse_vma_bind_range(struct tu_device *device,
                                  struct tu_sparse_vma *vma,
                                  struct tu_bo *bo, uint64_t bo_offset,
                                  uint64_t vma_offset, uint64_t size);
bool tu_has_sparse_vma_bind_range(struct tu_device *device);
"""),
])

# ---------------------------------------------------------------- tu_knl.cc
edit("tu_knl.cc", [
    ("""void
tu_sparse_vma_finish(struct tu_device *dev,
                     struct tu_sparse_vma *vma)
{
   dev->instance->knl->sparse_vma_finish(dev, vma);
}
""",
     """void
tu_sparse_vma_finish(struct tu_device *dev,
                     struct tu_sparse_vma *vma)
{
   dev->instance->knl->sparse_vma_finish(dev, vma);
}

/* TU_LAZY_COMMIT */
VkResult
tu_sparse_vma_bind_range(struct tu_device *dev,
                         struct tu_sparse_vma *vma,
                         struct tu_bo *bo, uint64_t bo_offset,
                         uint64_t vma_offset, uint64_t size)
{
   return dev->instance->knl->sparse_vma_bind_range(dev, vma, bo, bo_offset,
                                                    vma_offset, size);
}

bool
tu_has_sparse_vma_bind_range(struct tu_device *dev)
{
   return dev->instance->knl->sparse_vma_bind_range != NULL;
}
"""),
    ("""   assert(vma_offset % 4096 == 0);
   assert(bo_offset % 4096 == 0);
   return dev->instance->knl->submit_add_bind(dev, _submit, vma, vma_offset,
                                              bo, bo_offset, size);
""",
     """   assert(vma_offset % 4096 == 0);
   assert(bo_offset % 4096 == 0);
   /* TU_LAZY_COMMIT: sparse binds backed by a lazily committed memory object
    * bind its real chunk BOs, not its virtual range. */
   if (bo && bo->lazy_commit) {
      tu_lazy_commit_submit_bind(dev, _submit, vma, vma_offset, bo, bo_offset,
                                 size);
      return;
   }
   return dev->instance->knl->submit_add_bind(dev, _submit, vma, vma_offset,
                                              bo, bo_offset, size);
"""),
])

# ---------------------------------------------------------------- tu_knl_kgsl.cc
edit("tu_knl_kgsl.cc", [
    ("""static uint32_t
kgsl_align_flag(uint64_t align)
""",
     """/* TU_LAZY_COMMIT: bind part of a BO into part of a virtual range. */
static VkResult
kgsl_sparse_vma_bind_range(struct tu_device *dev,
                           struct tu_sparse_vma *vma,
                           struct tu_bo *bo, uint64_t bo_offset,
                           uint64_t vma_offset, uint64_t size)
{
   struct kgsl_gpumem_bind_range range = {
      .child_offset = bo_offset,
      .target_offset = vma_offset,
      .length = size,
      .child_id = bo->gem_handle,
      .op = KGSL_GPUMEM_RANGE_OP_BIND,
   };

   struct kgsl_gpumem_bind_ranges req = {
      .ranges = static_cast<uint64_t>(reinterpret_cast<uintptr_t>(&range)),
      .ranges_nents = 1,
      .ranges_size = sizeof(range),
      .id = vma->kgsl.virtual_bo->gem_handle,
      .flags = 0,
   };

   int ret = safe_ioctl(dev->physical_device->local_fd,
                        IOCTL_KGSL_GPUMEM_BIND_RANGES, &req);
   if (ret) {
      return vk_errorf(dev, VK_ERROR_OUT_OF_DEVICE_MEMORY,
                       "TU_LAZY_COMMIT: GPUMEM_BIND_RANGES failed (%s)",
                       strerror(errno));
   }

   return VK_SUCCESS;
}

static uint32_t
kgsl_align_flag(uint64_t align)
"""),
    ("""      .sparse_vma_init = kgsl_sparse_vma_init,
      .sparse_vma_finish = kgsl_sparse_vma_finish,
};
""",
     """      .sparse_vma_init = kgsl_sparse_vma_init,
      .sparse_vma_finish = kgsl_sparse_vma_finish,
      .sparse_vma_bind_range = kgsl_sparse_vma_bind_range, /* TU_LAZY_COMMIT */
};
"""),
])

# ---------------------------------------------------------------- tu_device.h
edit("tu_device.h", [
    ("""struct tu_device_memory
{
   struct vk_device_memory vk;
""",
     """/* TU_LAZY_COMMIT */
struct tu_lc_chunk {
   struct tu_bo *bo;     /* real BO backing this 64 KiB chunk, or NULL */
   uint64_t bo_offset;   /* offset of the chunk inside bo */
};

struct tu_lc_bo {
   struct tu_bo *bo;
   uint64_t offset;      /* where bo starts inside the memory object */
};

struct tu_device_memory
{
   struct vk_device_memory vk;
"""),
    ("""   struct tu_bo *bo;

   /* for dedicated allocations */
   struct tu_image *image;
};
""",
     """   struct tu_bo *bo;

   /* for dedicated allocations */
   struct tu_image *image;

   /* TU_LAZY_COMMIT: only a virtual range is reserved at allocation (bo is
    * its virtual BO); real memory is bound in chunks on first use.
    * lazy_mutex protects the chunk table. */
   bool lazy_commit;
   uint32_t lc_nchunks;
   struct tu_lc_chunk *lc_chunks;
   struct util_dynarray lc_bos; /* struct tu_lc_bo */
   uint64_t lc_committed;
   void *lc_map;
   VkMemoryPropertyFlags lc_property;
};
"""),
    ("""VkResult
tu_allocate_lazy_memory(struct tu_device *dev,
                        struct tu_device_memory *mem);
""",
     """VkResult
tu_allocate_lazy_memory(struct tu_device *dev,
                        struct tu_device_memory *mem);

/* TU_LAZY_COMMIT */
VkResult
tu_lazy_commit_range(struct tu_device *dev, struct tu_device_memory *mem,
                     uint64_t offset, uint64_t size);
VkResult
tu_lazy_commit_map(struct tu_device *dev, struct tu_device_memory *mem,
                   void *placed_addr, void **out);
void
tu_lazy_commit_submit_bind(struct tu_device *dev, void *submit,
                           struct tu_sparse_vma *vma, uint64_t vma_offset,
                           struct tu_bo *bo, uint64_t bo_offset,
                           uint64_t size);
"""),
])

# ---------------------------------------------------------------- tu_device.cc
LC_CODE = r'''
/* ---- TU_LAZY_COMMIT ---------------------------------------------------- */

/* commit granularity: TU_LAZY_COMMIT_SHIFT=12..16 (4 KiB..64 KiB), default 16 */
static unsigned
tu_lc_shift_get(void)
{
   static int shift = -1;
   if (shift < 0) {
      const char *e = os_get_option("TU_LAZY_COMMIT_SHIFT");
      long v = e ? strtol(e, NULL, 10) : 16;
      if (v < 12 || v > 16)
         v = 16;
      shift = (int)v;
      fprintf(stderr, "TU_LAZY_COMMIT: commit granularity %u KB\n", 1u << (shift - 10));
   }
   return (unsigned)shift;
}
#define TU_LC_SHIFT tu_lc_shift_get()
#define TU_LC_CHUNK (1ull << TU_LC_SHIFT)

static uint64_t tu_lc_reserved_total, tu_lc_committed_total, tu_lc_next_log;

static uint64_t
tu_lc_min_size(void)
{
   static int64_t lc_min = -1;
   if (lc_min < 0) {
      const char *e = os_get_option("TU_LAZY_COMMIT");
      long mb = e ? strtol(e, NULL, 10) : 0;
      if (mb == 1)
         mb = 4;
      lc_min = mb > 0 ? (int64_t)mb << 20 : 0;
      if (lc_min)
         fprintf(stderr, "TU_LAZY_COMMIT: on for allocations of %ld MB and more\n", mb);
   }
   return lc_min;
}

static void
tu_lc_log(void)
{
   uint64_t c = p_atomic_read(&tu_lc_committed_total);
   if (c >= p_atomic_read(&tu_lc_next_log)) {
      p_atomic_set(&tu_lc_next_log, (c / (256ull << 20) + 1) * (256ull << 20));
      fprintf(stderr, "TU_LAZY_COMMIT: reserved %llu MB, committed %llu MB\n",
              (unsigned long long)(p_atomic_read(&tu_lc_reserved_total) >> 20),
              (unsigned long long)(c >> 20));
   }
}

static bool
tu_lc_eligible(struct tu_device *dev, VkMemoryPropertyFlags prop,
               enum tu_bo_alloc_flags flags, uint64_t client_address,
               uint64_t size)
{
   uint64_t lc_min = tu_lc_min_size();
   if (!lc_min || size < lc_min)
      return false;
   if (!dev->physical_device->has_sparse || !tu_has_sparse_vma_bind_range(dev))
      return false;
   if (client_address ||
       (flags & (TU_BO_ALLOC_REPLAYABLE | TU_BO_ALLOC_SHAREABLE |
                 TU_BO_ALLOC_IMPLICIT_SYNC)))
      return false;
   if (prop & (VK_MEMORY_PROPERTY_LAZILY_ALLOCATED_BIT |
               VK_MEMORY_PROPERTY_HOST_CACHED_BIT |
               VK_MEMORY_PROPERTY_PROTECTED_BIT))
      return false;
   return true;
}

static VkResult
tu_lc_init(struct tu_device *dev, struct tu_device_memory *mem,
           VkMemoryPropertyFlags prop, uint64_t size, uint64_t align)
{
   mtx_init(&mem->lazy_mutex, mtx_plain);
   util_dynarray_init(&mem->lc_bos, NULL);
   /* TU_LAZY_COMMIT_FAULT=1: unbound pages fault (kernel logs the address)
    * instead of reading zero; for finding memory used without a bind. */
   static int lc_fault = -1;
   if (lc_fault < 0) {
      const char *f = os_get_option("TU_LAZY_COMMIT_FAULT");
      lc_fault = f && *f && *f != '0';
      if (lc_fault)
         fprintf(stderr, "TU_LAZY_COMMIT: unbound pages FAULT (debug)\n");
   }
   VkResult result = tu_sparse_vma_init(dev, &mem->vk.base, &mem->lazy_vma,
                                        &mem->iova,
                                        lc_fault ? TU_SPARSE_VMA_NONE
                                                 : TU_SPARSE_VMA_MAP_ZERO,
                                        size, align, 0);
   if (result != VK_SUCCESS) {
      util_dynarray_fini(&mem->lc_bos);
      mtx_destroy(&mem->lazy_mutex);
      return result;
   }

   struct tu_bo *vbo = mem->lazy_vma.kgsl.virtual_bo;
   mem->lc_nchunks = DIV_ROUND_UP(vbo->size, TU_LC_CHUNK);
   mem->lc_chunks = (struct tu_lc_chunk *)
      calloc(mem->lc_nchunks, sizeof(struct tu_lc_chunk));
   if (!mem->lc_chunks) {
      tu_sparse_vma_finish(dev, &mem->lazy_vma);
      util_dynarray_fini(&mem->lc_bos);
      mtx_destroy(&mem->lazy_mutex);
      return vk_error(dev, VK_ERROR_OUT_OF_HOST_MEMORY);
   }

   vbo->lazy_commit = true;
   mem->bo = vbo;
   mem->lc_property = prop;
   mem->lazy_commit = true;
   p_atomic_add(&tu_lc_reserved_total, vbo->size);
   if (lc_fault)
      fprintf(stderr, "TU_LAZY_COMMIT: range iova 0x%llx size %llu KB\n",
              (unsigned long long)mem->iova, (unsigned long long)(vbo->size >> 10));
   return VK_SUCCESS;
}

VkResult
tu_lazy_commit_range(struct tu_device *dev, struct tu_device_memory *mem,
                     uint64_t offset, uint64_t size)
{
   if (!mem->lazy_commit || size == 0)
      return VK_SUCCESS;

   uint64_t vsize = mem->bo->size;
   if (offset >= vsize)
      return VK_SUCCESS;
   if (size == VK_WHOLE_SIZE || size > vsize - offset)
      size = vsize - offset;

   uint32_t first = offset >> TU_LC_SHIFT;
   uint32_t last = (offset + size - 1) >> TU_LC_SHIFT;
   if (last >= mem->lc_nchunks)
      last = mem->lc_nchunks - 1;

   VkResult result = VK_SUCCESS;
   mtx_lock(&mem->lazy_mutex);
   uint32_t i = first;
   while (i <= last) {
      if (mem->lc_chunks[i].bo) {
         i++;
         continue;
      }
      uint32_t j = i;
      while (j <= last && !mem->lc_chunks[j].bo)
         j++;

      uint64_t run_off = (uint64_t)i << TU_LC_SHIFT;
      uint64_t run_end = MIN2((uint64_t)j << TU_LC_SHIFT, vsize);
      uint64_t run_size = run_end - run_off;

      struct tu_bo *bo = NULL;
      result = tu_bo_init_new_explicit_iova(dev, &mem->vk.base, &bo, run_size,
                                            0, 0, mem->lc_property,
                                            TU_BO_ALLOC_NO_FLAGS, NULL,
                                            "lazy commit");
      if (result != VK_SUCCESS)
         break;

      result = tu_add_to_heap(dev, bo); /* frees bo on failure */
      if (result != VK_SUCCESS)
         break;

      result = tu_sparse_vma_bind_range(dev, &mem->lazy_vma, bo, 0, run_off,
                                        run_size);
      if (result != VK_SUCCESS) {
         p_atomic_add(&dev->physical_device->heap.used, -bo->size);
         p_atomic_add(&tu_process_heap_used, -bo->size);
         tu_bo_finish(dev, bo);
         break;
      }

      for (uint32_t k = i; k < j; k++) {
         mem->lc_chunks[k].bo = bo;
         mem->lc_chunks[k].bo_offset = ((uint64_t)k << TU_LC_SHIFT) - run_off;
      }
      struct tu_lc_bo entry = { bo, run_off };
      util_dynarray_append(&mem->lc_bos, entry);
      mem->lc_committed += run_size;
      p_atomic_add(&tu_lc_committed_total, run_size);
      i = j;
   }
   mtx_unlock(&mem->lazy_mutex);

   if (result != VK_SUCCESS)
      fprintf(stderr, "TU_LAZY_COMMIT: commit of %llu KB failed (%d)\n",
              (unsigned long long)(size >> 10), result);
   tu_lc_log();
   return result;
}

VkResult
tu_lazy_commit_map(struct tu_device *dev, struct tu_device_memory *mem,
                   void *placed_addr, void **out)
{
   if (mem->lc_map && (!placed_addr || placed_addr == mem->lc_map)) {
      *out = mem->lc_map;
      return VK_SUCCESS;
   }
   if (mem->lc_map)
      return vk_errorf(dev, VK_ERROR_MEMORY_MAP_FAILED,
                       "Cannot remap memory to a different address");

   uint64_t vsize = mem->bo->size;
   VkResult result = tu_lazy_commit_range(dev, mem, 0, vsize);
   if (result != VK_SUCCESS)
      return result;

   void *base = placed_addr;
   if (!base) {
      base = mmap(NULL, vsize, PROT_NONE,
                  MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
      if (base == MAP_FAILED)
         return vk_error(dev, VK_ERROR_MEMORY_MAP_FAILED);
   }

   mtx_lock(&mem->lazy_mutex);
   util_dynarray_foreach (&mem->lc_bos, struct tu_lc_bo, e) {
      result = tu_bo_map(dev, e->bo, static_cast<char *>(base) + e->offset);
      if (result != VK_SUCCESS)
         break;
   }
   if (result != VK_SUCCESS) {
      util_dynarray_foreach (&mem->lc_bos, struct tu_lc_bo, e) {
         if (e->bo->map)
            tu_bo_unmap(dev, e->bo, placed_addr != NULL);
      }
      if (!placed_addr)
         munmap(base, vsize);
   } else {
      mem->lc_map = base;
   }
   mtx_unlock(&mem->lazy_mutex);

   if (result == VK_SUCCESS)
      *out = base;
   return result;
}

static VkResult
tu_lc_unmap(struct tu_device *dev, struct tu_device_memory *mem, bool reserve)
{
   mtx_lock(&mem->lazy_mutex);
   util_dynarray_foreach (&mem->lc_bos, struct tu_lc_bo, e) {
      if (e->bo->map)
         tu_bo_unmap(dev, e->bo, reserve);
   }
   mem->lc_map = NULL;
   mtx_unlock(&mem->lazy_mutex);
   return VK_SUCCESS;
}

static void
tu_lc_destroy(struct tu_device *dev, struct tu_device_memory *mem)
{
   if (mem->lc_map)
      tu_lc_unmap(dev, mem, false);

   uint64_t vsize = mem->bo->size;
   mem->bo->lazy_commit = false;
   mem->bo = NULL;
   /* Free the virtual range first: that drops its bindings to the chunks. */
   tu_sparse_vma_finish(dev, &mem->lazy_vma);

   util_dynarray_foreach (&mem->lc_bos, struct tu_lc_bo, e) {
      p_atomic_add(&dev->physical_device->heap.used, -e->bo->size);
      p_atomic_add(&tu_process_heap_used, -e->bo->size);
      tu_bo_finish(dev, e->bo);
   }
   p_atomic_add(&tu_lc_committed_total, -mem->lc_committed);
   p_atomic_add(&tu_lc_reserved_total, -vsize);

   util_dynarray_fini(&mem->lc_bos);
   free(mem->lc_chunks);
   mem->lc_chunks = NULL;
   mtx_destroy(&mem->lazy_mutex);
   mem->lazy_commit = false;
}

void
tu_lazy_commit_submit_bind(struct tu_device *dev, void *submit,
                           struct tu_sparse_vma *vma, uint64_t vma_offset,
                           struct tu_bo *bo, uint64_t bo_offset,
                           uint64_t size)
{
   struct tu_device_memory *mem =
      container_of(bo->base, struct tu_device_memory, vk.base);

   if (tu_lazy_commit_range(dev, mem, bo_offset, size) != VK_SUCCESS) {
      /* No memory: leave the range on the zero page rather than fault. */
      dev->instance->knl->submit_add_bind(dev, submit, vma, vma_offset,
                                          NULL, 0, size);
      return;
   }

   /* Chunks never change once committed, so no lock is needed here. */
   uint64_t done = 0;
   while (done < size) {
      uint64_t off = bo_offset + done;
      const struct tu_lc_chunk *c = &mem->lc_chunks[off >> TU_LC_SHIFT];
      uint64_t in_chunk = off & (TU_LC_CHUNK - 1);
      uint64_t len = MIN2(size - done, TU_LC_CHUNK - in_chunk);
      while (done + len < size &&
             mem->lc_chunks[(off + len) >> TU_LC_SHIFT].bo == c->bo)
         len += MIN2(size - done - len, TU_LC_CHUNK);
      dev->instance->knl->submit_add_bind(dev, submit, vma, vma_offset + done,
                                          c->bo, c->bo_offset + in_chunk, len);
      done += len;
   }
}

/* ---- end TU_LAZY_COMMIT ------------------------------------------------ */

static VkResult
_tu_init_memory(struct tu_device *device,
'''

edit("tu_device.cc", [
    ('#include "tu_device.h"\n',
     '#include "tu_device.h"\n\n#include <stdio.h>\n#include <sys/mman.h> /* TU_LAZY_COMMIT */\n'),
    ("\nstatic VkResult\n_tu_init_memory(struct tu_device *device,\n", LC_CODE),
    # free
    ("""static void
_tu_destroy_memory(struct tu_device *device,
                  struct tu_device_memory *mem)
{
""",
     """static void
_tu_destroy_memory(struct tu_device *device,
                  struct tu_device_memory *mem)
{
   if (mem->lazy_commit) { /* TU_LAZY_COMMIT */
      tu_lc_destroy(device, mem);
      return;
   }
"""),
    # allocate
    ("""      result = _tu_init_memory(device, mem, mem_property, alloc_flags,
                               pAllocateInfo->allocationSize, alignment,
                               client_address,
                               name);
   }

   if (result == VK_SUCCESS && !mem->lazy) {""",
     """      if (tu_lc_eligible(device, mem_property, alloc_flags, client_address,
                         pAllocateInfo->allocationSize)) /* TU_LAZY_COMMIT */
         result = tu_lc_init(device, mem, mem_property,
                             pAllocateInfo->allocationSize, alignment);
      else
         result = _tu_init_memory(device, mem, mem_property, alloc_flags,
                                  pAllocateInfo->allocationSize, alignment,
                                  client_address,
                                  name);
   }

   if (result == VK_SUCCESS && !mem->lazy && !mem->lazy_commit) {"""),
    # map
    ("""   result = tu_bo_map(device, mem->bo, placed_addr);
   if (result != VK_SUCCESS)
      return result;

   *ppData = static_cast<char *>(mem->bo->map) + pMemoryMapInfo->offset;
   return VK_SUCCESS;
""",
     """   if (mem->lazy_commit) { /* TU_LAZY_COMMIT */
      void *base;
      result = tu_lazy_commit_map(device, mem, placed_addr, &base);
      if (result != VK_SUCCESS)
         return result;
      *ppData = static_cast<char *>(base) + pMemoryMapInfo->offset;
      return VK_SUCCESS;
   }

   result = tu_bo_map(device, mem->bo, placed_addr);
   if (result != VK_SUCCESS)
      return result;

   *ppData = static_cast<char *>(mem->bo->map) + pMemoryMapInfo->offset;
   return VK_SUCCESS;
"""),
    # unmap
    ("""   if (mem == NULL)
      return VK_SUCCESS;

   return tu_bo_unmap(device, mem->bo, pMemoryUnmapInfo->flags & VK_MEMORY_UNMAP_RESERVE_BIT_EXT);
""",
     """   if (mem == NULL)
      return VK_SUCCESS;

   if (mem->lazy_commit) /* TU_LAZY_COMMIT */
      return tu_lc_unmap(device, mem,
                         pMemoryUnmapInfo->flags & VK_MEMORY_UNMAP_RESERVE_BIT_EXT);

   return tu_bo_unmap(device, mem->bo, pMemoryUnmapInfo->flags & VK_MEMORY_UNMAP_RESERVE_BIT_EXT);
"""),
    # cache sync: lazily committed memory is never host-cached
    ("""      VK_FROM_HANDLE(tu_device_memory, mem, ranges[i].memory);
      tu_bo_sync_cache(device, mem->bo, ranges[i].offset, ranges[i].size, op);
""",
     """      VK_FROM_HANDLE(tu_device_memory, mem, ranges[i].memory);
      if (mem->lazy_commit) /* TU_LAZY_COMMIT: never host-cached */
         continue;
      tu_bo_sync_cache(device, mem->bo, ranges[i].offset, ranges[i].size, op);
"""),
    # commitment
    ("""   VK_FROM_HANDLE(tu_device_memory, memory, _memory);
   *pCommittedMemoryInBytes = memory->lazy_initialized ? memory->size : 0;
""",
     """   VK_FROM_HANDLE(tu_device_memory, memory, _memory);
   if (memory->lazy_commit) { /* TU_LAZY_COMMIT */
      *pCommittedMemoryInBytes = memory->lc_committed;
      return;
   }
   *pCommittedMemoryInBytes = memory->lazy_initialized ? memory->size : 0;
"""),
])

# ---------------------------------------------------------------- tu_image.cc
edit("tu_image.cc", [
    ("""   assert(mem);
   image->mem = mem;
   image->mem_offset = offset;
   image->iova = mem->iova + offset;

   if (image->vk.usage & (VK_IMAGE_USAGE_FRAGMENT_DENSITY_MAP_BIT_EXT |
                          VK_IMAGE_USAGE_HOST_TRANSFER_BIT_EXT)) {
      assert(mem->bo); /* Transient images cannot have these usages */
      if (!mem->bo->map) {
""",
     """   assert(mem);
   image->mem = mem;
   image->mem_offset = offset;
   image->iova = mem->iova + offset;

   if (mem->lazy_commit) { /* TU_LAZY_COMMIT */
      result = tu_lazy_commit_range(device, mem, offset, image->total_size);
      if (result != VK_SUCCESS)
         return result;
   }

   if (mem->lazy_commit &&
       (image->vk.usage & (VK_IMAGE_USAGE_FRAGMENT_DENSITY_MAP_BIT_EXT |
                           VK_IMAGE_USAGE_HOST_TRANSFER_BIT_EXT))) {
      void *base;
      result = tu_lazy_commit_map(device, mem, NULL, &base);
      if (result != VK_SUCCESS)
         return result;
      image->map = static_cast<char *>(base) + offset;
   } else if (image->vk.usage & (VK_IMAGE_USAGE_FRAGMENT_DENSITY_MAP_BIT_EXT |
                          VK_IMAGE_USAGE_HOST_TRANSFER_BIT_EXT)) {
      assert(mem->bo); /* Transient images cannot have these usages */
      if (!mem->bo->map) {
"""),
])

# ---------------------------------------------------------------- tu_buffer.cc
edit("tu_buffer.cc", [
    ("""      if (mem) {
         buffer->bo = mem->bo;
         buffer->vk.device_address = mem->bo->iova + pBindInfos[i].memoryOffset;
""",
     """      if (mem) {
         buffer->bo = mem->bo;
         buffer->vk.device_address = mem->bo->iova + pBindInfos[i].memoryOffset;
         if (mem->lazy_commit) { /* TU_LAZY_COMMIT: address set first */
            VkResult r = tu_lazy_commit_range(dev, mem,
                                              pBindInfos[i].memoryOffset,
                                              buffer->vk.size);
            if (r != VK_SUCCESS) {
               fprintf(stderr, "TU_LAZY_COMMIT: buffer bind of %llu KB could not be backed (%d)\\n",
                       (unsigned long long)(buffer->vk.size >> 10), r);
               if (status)
                  *status->pResult = r;
               return r;
            }
         }
"""),
])

# ---------------------------------------------------------------- TU_BO_CAP_MB / TU_BO_LOG_MB
# Count every real KGSL BO the driver allocates (app memory, lazy-commit chunks and the driver's
# own BOs: shaders, descriptor pools, command streams, suballocators). TU_BO_CAP_MB=<n> refuses
# new BOs beyond n MB (the app gets VK_ERROR_OUT_OF_DEVICE_MEMORY instead of Android killing other
# apps); TU_BO_LOG_MB=<n> (default 8 when the cap is set) logs every BO of at least n MB with its
# name and the running total, plus the total every 256 MB. Imported/exported dma-bufs are not
# counted.
edit("tu_knl.h", [
    ("   bool lazy_commit : 1;\n",
     "   bool lazy_commit : 1;\n"
     "   /* TU_BO_CAP_MB: counted in the driver's BO total */\n"
     "   bool budget_counted : 1;\n"),
])

edit("tu_knl_kgsl.cc", [
    ('#include "util/u_debug.h"\n',
     '#include "util/u_debug.h"\n#include "util/os_misc.h" /* TU_BO_CAP_MB */\n#include <stdio.h>\n'),
    ("""/* TU_LAZY_COMMIT: bind part of a BO into part of a virtual range. */
""",
     """/* TU_BO_CAP_MB / TU_BO_LOG_MB: total of all counted KGSL BOs. */
static uint64_t tu_kgsl_bo_total, tu_kgsl_bo_next_log;
static int64_t tu_kgsl_bo_cap = -1, tu_kgsl_bo_logmin = -1;
static uint32_t tu_kgsl_bo_refusals;

static void
kgsl_bo_budget_init(void)
{
   if (tu_kgsl_bo_cap >= 0)
      return;
   const char *c = os_get_option("TU_BO_CAP_MB");
   const char *l = os_get_option("TU_BO_LOG_MB");
   long cap = c ? strtol(c, NULL, 10) : 0;
   long logmb = l ? strtol(l, NULL, 10) : (cap > 0 ? 8 : 0);
   tu_kgsl_bo_logmin = logmb > 0 ? (int64_t)logmb << 20 : 0;
   tu_kgsl_bo_cap = cap > 0 ? (int64_t)cap << 20 : 0;
   if (cap > 0 || logmb > 0)
      fprintf(stderr, "TU_BO: cap %ld MB, logging BOs of %ld MB and more\\n", cap, logmb);
}

/* TU_LAZY_COMMIT: bind part of a BO into part of a virtual range. */
"""),
    ("""   uint64_t kgsl_flags = 0;

   if (mem_property & VK_MEMORY_PROPERTY_HOST_CACHED_BIT) {""",
     """   kgsl_bo_budget_init(); /* TU_BO_CAP_MB */
   if (tu_kgsl_bo_cap > 0 &&
       p_atomic_read(&tu_kgsl_bo_total) + size > (uint64_t)tu_kgsl_bo_cap) {
      uint32_t n = p_atomic_inc_return(&tu_kgsl_bo_refusals);
      if (n <= 20 || n % 100 == 0)
         fprintf(stderr, "TU_BO: refusing %llu KB '%s' at %llu MB (cap %lld MB, #%u)\\n",
                 (unsigned long long)(size >> 10), name ? name : "?",
                 (unsigned long long)(p_atomic_read(&tu_kgsl_bo_total) >> 20),
                 (long long)(tu_kgsl_bo_cap >> 20), n);
      return vk_errorf(dev, VK_ERROR_OUT_OF_DEVICE_MEMORY, "TU_BO_CAP_MB reached");
   }

   uint64_t kgsl_flags = 0;

   if (mem_property & VK_MEMORY_PROPERTY_HOST_CACHED_BIT) {"""),
    ("""   tu_dump_bo_init(dev, bo);

   VkResult result = VK_SUCCESS;

   if (lazy_vma) {""",
     """   tu_dump_bo_init(dev, bo);

   { /* TU_BO_CAP_MB / TU_BO_LOG_MB */
      bo->budget_counted = true;
      uint64_t total = p_atomic_add_return(&tu_kgsl_bo_total, mmapsize);
      if (tu_kgsl_bo_logmin > 0 && mmapsize >= (uint64_t)tu_kgsl_bo_logmin)
         fprintf(stderr, "TU_BO: +%llu KB '%s' total %llu MB\\n",
                 (unsigned long long)(mmapsize >> 10), name ? name : "?",
                 (unsigned long long)(total >> 20));
      if (tu_kgsl_bo_logmin > 0 && total >= p_atomic_read(&tu_kgsl_bo_next_log)) {
         p_atomic_set(&tu_kgsl_bo_next_log, (total / (256ull << 20) + 1) * (256ull << 20));
         fprintf(stderr, "TU_BO: total %llu MB\\n", (unsigned long long)(total >> 20));
      }
   }

   VkResult result = VK_SUCCESS;

   if (lazy_vma) {"""),
    ("""   if (bo->alias_handle)
      kgsl_bo_destroy_alias(dev, bo);

   struct kgsl_gpumem_free_id req = {
      .id = bo->gem_handle
   };
""",
     """   if (bo->alias_handle)
      kgsl_bo_destroy_alias(dev, bo);

   if (bo->budget_counted) /* TU_BO_CAP_MB */
      p_atomic_add(&tu_kgsl_bo_total, -bo->size);

   struct kgsl_gpumem_free_id req = {
      .id = bo->gem_handle
   };
"""),
])

print("lazy_commit.py: TU_BO cap/log done")

# stdio for the buffer-bind warning
edit("tu_buffer.cc", [
    ('#include "tu_buffer.h"\n', '#include "tu_buffer.h"\n#include <stdio.h> /* TU_LAZY_COMMIT */\n'),
])

# ---------------------------------------------------------------- TU_AS_LBVH
# TU_AS_LBVH=1: build every acceleration structure (also top-level) with LBVH instead of PLOC /
# H-PLOC; LBVH has no inter-workgroup spin waits (PLOC hangs DOOM: The Dark Ages on an A750).
edit("tu_acceleration_structure.cc", [
    ('#include "util/u_hexdump.h"\n',
     '#include "util/u_hexdump.h"\n#include "util/os_misc.h" /* TU_AS_LBVH */\n#include <stdio.h>\n'),
    ("""tu_get_build_config(VkDevice device,
                    struct vk_acceleration_structure_build_state *state)
{
}
""",
     """tu_get_build_config(VkDevice device,
                    struct vk_acceleration_structure_build_state *state)
{
   static int force_lbvh = -1; /* TU_AS_LBVH */
   if (force_lbvh < 0) {
      const char *e = os_get_option("TU_AS_LBVH");
      force_lbvh = e && *e && *e != '0';
      if (force_lbvh)
         fprintf(stderr, "TU_AS_LBVH: all acceleration structure builds use LBVH\\n");
   }
   if (force_lbvh &&
       (state->config.internal_type == VK_INTERNAL_BUILD_TYPE_PLOC ||
        state->config.internal_type == VK_INTERNAL_BUILD_TYPE_HPLOC))
      state->config.internal_type = VK_INTERNAL_BUILD_TYPE_LBVH;
}
"""),
])

print("lazy_commit.py: done")
