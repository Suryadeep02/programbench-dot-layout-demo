# Third-party materials and local build dependencies

This source demo does not distribute the Graphviz archive, compiled reference, candidate binaries, container images, or raw copies of external documentation. Task-specific Markdown notes summarize the input/output contract and link to upstream documentation.

## Pinned upstream source

- Graphviz 14.0.4, official release archive SHA-256 `ddac5f15ad1b2ad6d715cc64d6d0e6a366310c09c2c3a11284dafd1630e353b6`.
- The pinned archive's `COPYING` and core headers state **Eclipse Public License 1.0**. The current [Graphviz license page](https://graphviz.org/license/) states EPL 2.0; that current page is not substituted for the actual pinned files.
- The local build instructions extract and retain the pinned archive's `COPYING` and `AUTHORS` beside the task notes. They remain upstream materials, not this author's work.

## Build/runtime dependency inventory

| Material | Evidence and role | Distributed here? |
| --- | --- | --- |
| Graphviz 14.0.4 | Layout implementation; pinned official archive and build recipe | No archive or binary |
| Official GCC image | `gcc@sha256:9188ac751ca24431dc43dbd142a223c98ea74f01d2858e84d30ba342a0d67844`; original Linux/amd64 build and candidate toolchain | No image |
| Expat | Original build enables Expat; reference contains `expat_2.8.3` | No linked binary |
| zlib | Original reference contains upstream zlib copyright text | No linked binary |
| C runtime/toolchain libraries | Static reference contains GLIBC markers; exact linked-component inventory is not established by `ldd` on a static executable | No linked binary |

The [Expat 2.8.3 license](https://raw.githubusercontent.com/libexpat/libexpat/R_2_8_3/expat/COPYING) requires its copyright and permission notice in copies or substantial portions. The [zlib license](https://www.zlib.net/zlib_license.html) and applicable toolchain/runtime licenses also remain relevant to any binary distribution. A static `ldd` result is not a complete dependency or license inventory.

**Local acquisition/build instructions are not binary redistribution clearance.** Before distributing a resulting executable or image, establish its actual linked dependency versions, retain required notices and satisfy applicable source/relinking requirements. This demo deliberately avoids distributing those artifacts while that inventory remains incomplete.

No project-wide license is asserted over upstream material. No endorsement by Graphviz, ProgramBench, an employer or a model provider is implied.
