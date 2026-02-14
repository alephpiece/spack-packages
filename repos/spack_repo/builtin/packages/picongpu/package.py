# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)
from spack.package import *

import os


class Picongpu(Package):
    """PIConGPU: A particle-in-cell code for GPGPUs"""

    homepage = "https://github.com/ComputationalRadiationPhysics/picongpu"
    url = "https://github.com/ComputationalRadiationPhysics/picongpu/archive/refs/tags/0.8.0.tar.gz"
    git = "https://github.com/ComputationalRadiationPhysics/picongpu.git"
    maintainers("ax3l", "psychocoderHPC")

    version("develop", branch="dev", preferred=True)
    version(
        "0.8.0",
        sha256="a4dde10a7fc88ba280a3e3e4e0fc64f931f4fe979855683b1884912a96d476d4",
    )

    # Alpaka computing backends.
    # Accepted values are:
    #   cuda  - Nvidia CUDA (GPUs)
    #   omp2b - OpenMP 2.0 with grid-blocks parallel, sequential block-threads
    #   hip   - AMD HIP (GPUs) - requires ROCm
    variant(
        "backend",
        default="cuda",
        values=("cuda", "omp2b", "hip"),
        multi=False,
        description="Control the computing backend",
    )
    variant(
        "cudacxx",
        default="nvcc",
        values=("nvcc", "clang"),
        multi=False,
        when="backend=cuda",
        description="Device compiler for the CUDA backend",
    )
    variant("adios", default=False, description="Enable the ADIOS plugin")
    variant("hdf5", default=True, description="Enable multiple plugins requiring HDF5")
    variant("isaac", default=False, description="Enable the ISAAC plugin")
    variant("openpmd", default=True, description="Enable openPMD I/O")
    variant("png", default=True, description="Enable the PNG plugin")

    variant(
        "cxxstd",
        default="20",
        values=("17", "20"),
        multi=False,
        description="C++ standard version",
    )

    # CMake is needed both during installation and when users run
    # pic-configure/pic-build after installation.
    depends_on("cmake@3.22.0:", type=["build", "run"], when="@0.8.0")
    depends_on("cmake@3.28.0:", type=["build", "run"], when="@develop")

    depends_on("rsync", type="run")
    depends_on("util-linux", type="run", when="platform=darwin")  # GNU getopt

    # CUDA backend
    depends_on("cuda", when="backend=cuda")
    depends_on("cuda@11.3:", when="@0.8.0 backend=cuda")
    depends_on("cuda@11.8:", when="@develop backend=cuda")

    # HIP backend (ROCm stack)
    # alpaka requires hip; with default vendor RNG enabled it also requires
    # rocrand and hiprand.
    depends_on("hip@5.4:", when="backend=hip")
    depends_on("rocrand", when="backend=hip")
    depends_on("hiprand", when="backend=hip")
    # ROCm/LLVM target for AMD GPUs (gfx906 or higher)
    # This is typically set via amdgpu_target variant on the compiler

    depends_on(
        "boost@1.74.0: cxxstd=17 +math +system +program_options +filesystem +serialization",
        when="cxxstd=17",
    )
    depends_on(
        "boost@1.74.0: cxxstd=20 +math +system +program_options +filesystem +serialization",
        when="cxxstd=20",
    )

    depends_on("mpi@2.3:", type=["link", "run"])

    depends_on("adios2", when="+adios")
    depends_on("hdf5", when="+hdf5")
    depends_on("isaac@1.6.0:", when="+isaac")
    depends_on("isaac-server@1.6.0:", type="run", when="+isaac")
    depends_on("openpmd-api@0.15.0:", when="+openpmd")
    depends_on("pngwriter@0.7.0,develop", when="+png")

    conflicts("cxxstd=17", when="@develop", msg="develop requires C++20")

    conflicts(
        "backend=hip", when="platform=darwin", msg="HIP is not supported on macOS"
    )
    conflicts(
        "backend=hip", when="platform=windows", msg="HIP is not supported on Windows"
    )

    def install(self, spec, prefix):
        path_bin = join_path(prefix, "bin")
        path_etc = join_path(prefix, "etc")
        path_include = join_path(prefix, "include")
        path_lib = join_path(prefix, "lib")
        path_share = join_path(prefix, "share")

        install_tree("bin", path_bin)
        install_tree("buildsystem", join_path(prefix, "buildsystem"))
        install_tree("etc", path_etc)
        install_tree("include", path_include)
        install_tree("lib", path_lib)
        install_tree("src", join_path(prefix, "src"))
        install_tree("share", path_share)
        install_tree("thirdParty", join_path(prefix, "thirdParty"))

        profile_in = join_path(os.path.dirname(__file__), "picongpu.profile")
        profile_out = join_path(path_etc, "picongpu")
        install(profile_in, profile_out)
        filter_file(
            "@PIC_SPACK_COMPILER@",
            str(self.compiler.spec),
            join_path(profile_out, "picongpu.profile"),
        )
        filter_file(
            "@PIC_SPACK_ROOT@",
            str(os.environ["SPACK_ROOT"]),
            join_path(profile_out, "picongpu.profile"),
        )
        # filter_file('@PIC_SPACK_COMPILER@', str(self.compiler.spec),
        #            join_path(profile_out, 'picongpu.profile'))
        # spack load on concretized spec does not work right now, replace with
        # slightly non-concrete spec set a None-defaulted multi-variant to
        # work-around:
        # https://github.com/spack/spack/issues/6314
        spec_list = str(spec).split(" ")
        spec_list = list(filter(lambda x: not x.endswith("="), spec_list))
        sanitized_spec = " ".join(spec_list)
        filter_file(
            "@PIC_SPACK_SPEC@",
            sanitized_spec,
            join_path(profile_out, "picongpu.profile"),
        )

    def setup_run_environment(self, env):
        env.set("PICSRC", self.prefix)
        env.set("PIC_EXAMPLES", join_path(self.prefix, "share/picongpu/examples"))
        env.set(
            "PIC_PROFILE", join_path(self.prefix, "etc", "picongpu", "picongpu.profile")
        )
        if "backend=cuda" in self.spec:
            env.set("PIC_BACKEND", "cuda")
        elif "backend=omp2b" in self.spec:
            env.set("PIC_BACKEND", "omp2b")
        elif "backend=hip" in self.spec:
            env.set("PIC_BACKEND", "hip")

        env.prepend_path("PATH", join_path(self.prefix, "bin"))
        env.prepend_path("PATH", join_path(self.prefix, "src/tools/bin"))
        env.prepend_path("PYTHONPATH", join_path(self.prefix, "lib/python"))
        # optional: default for TBG_SUBMIT, TBG_TPLFILE

        # pre-load depends
        #  https://github.com/LLNL/spack/issues/2378#issuecomment-316364232
        cmake_prefix_path = []
        include_path = []
        ld_library_path = []
        bin_path = []
        for x in self.spec.traverse():
            if str(x).startswith("icet"):
                cmake_prefix_path.append(x.prefix.lib)
            else:
                cmake_prefix_path.append(x.prefix)
            ld_library_path.append(x.prefix.lib)
            bin_path.append(x.prefix.bin)
            include_path.append(x.prefix.include)

        env.prepend_path("CMAKE_PREFIX_PATH", ":".join(cmake_prefix_path))
        env.prepend_path("CPATH", ":".join(include_path))
        env.prepend_path("LD_LIBRARY_PATH", ":".join(ld_library_path))
        env.prepend_path("PATH", ":".join(bin_path))
        # pre-load depending compiler
        cxx_bin = os.path.dirname(self.compiler.cxx)
        cxx_prefix = join_path(cxx_bin, "..")
        cxx_lib = join_path(cxx_prefix, "lib")
        env.prepend_path("LD_LIBRARY_PATH", cxx_lib)
        env.prepend_path("PATH", cxx_bin)
        env.set("CC", self.compiler.cc)
        env.set("CXX", self.compiler.cxx)
