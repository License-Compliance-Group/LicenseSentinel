"""License name normalizer
If a need arises to normalize anything else, a Normalizer interface
may be created, handling different kinds of normalization.
"""


def normalize(name: str) -> str | None:
    """Map common license strings to OSADL/SPDX-like keys used 
        by the matrix.
    Args:  
        name (str): The input license string to normalize.  

    Returns:  
        str | None: The normalized OSADL/SPDX-compatible license 
            identifier, or None if not recognized.  

    """
    if name is None:
        return ''
    key = name.strip().lower()
    mapping = {
        # GPL Family
        "gpl-1.0": "GPL-1.0-only",
        "gpl-1.0+": "GPL-1.0-or-later",
        "gnu general public license v1.0 only": "GPL-1.0-only",
        "gnu general public license v1.0 or later": "GPL-1.0-or-later",
        "gpl-2.0": "GPL-2.0-only",
        "gpl-2.0+": "GPL-2.0-or-later",
        "gnu general public license v2.0 only": "GPL-2.0-only",
        "gnu general public license v2.0 or later": "GPL-2.0-or-later",
        "gpl-3.0": "GPL-3.0-only",
        "gpl-3.0+": "GPL-3.0-or-later",
        "gnu general public license v3.0 only": "GPL-3.0-only",
        "gnu general public license v3.0 or later": "GPL-3.0-or-later",
        "gnu general public license (gpl)": "GPL-2.0-only",

        # LGPL Family
        "lgpl-2.0": "LGPL-2.0-only",
        "lgpl-2.0+": "LGPL-2.0-or-later",
        "gnu library general public license v2 only": "LGPL-2.0-only",
        "gnu library general public license v2 or later": "LGPL-2.0-or-later",
        "lgpl-2.1": "LGPL-2.1-only",
        "lgpl-2.1+": "LGPL-2.1-or-later",
        "gnu lesser general public license v2.1 only": "LGPL-2.1-only",
        "gnu lesser general public license v2.1 or later": "LGPL-2.1-or-later",
        "lgpl-3.0": "LGPL-3.0-only",
        "lgpl-3.0+": "LGPL-3.0-or-later",
        "gnu lesser general public license v3.0 only": "LGPL-3.0-only",
        "gnu lesser general public license v3.0 or later": "LGPL-3.0-or-later",

        # AGPL Family
        "agpl-3.0": "AGPL-3.0-only",
        "gnu affero general public license v3.0": "AGPL-3.0-only",
        "gnu affero general public license v3.0 only": "AGPL-3.0-only",
        "gnu affero general public license v3.0 or later": "AGPL-3.0-or-later",

        # Apache Family
        "apache license 1.0": "Apache-1.0",
        "apache license 1.1": "Apache-1.1",
        "apache license 2.0": "Apache-2.0",
        "apache software license": "Apache-2.0",

        # BSD Family
        "bsd zero clause license": "0BSD",
        "bsd 1-clause license": "BSD-1-Clause",
        "bsd 2-clause \"simplified\" license": "BSD-2-Clause",
        "bsd 2-clause": "BSD-2-Clause",
        "bsd-simplified": "BSD-2-Clause",
        "bsd 3-clause \"new\" or \"revised\" license": "BSD-3-Clause",
        "bsd 3-clause": "BSD-3-Clause",
        "bsd license": "BSD-3-Clause",
        "bsd-new": "BSD-3-Clause",
        "bsd 4-clause \"original\" or \"old\" license": "BSD-4-Clause",
        "bsd 4-clause (university of california-specific)": "BSD-4-Clause-UC",
        "bsd 3-clause open mpi variant": "BSD-3-Clause-Open-MPI",
        "bsd-2-clause-freebsd": "BSD-2-Clause-FreeBSD",
        "bsd-2-clause-netbsd": "BSD-2-Clause-NetBSD",
        "bsd-3-clause-attribution": "BSD-3-Clause-Attribution",
        "bsd-3-clause-clear": "BSD-3-Clause-Clear",
        "bsd-3-clause-lbnl": "BSD-3-Clause-LBNL",

        # MIT Family
        "mit license": "MIT",
        "mit no attribution": "MIT-0",
        "cmu license": "MIT-CMU",
        "mit-cmu": "MIT-CMU",
        "cmu-uc": "MIT-CMU",
        "mit-modern-variant": "MIT-Modern-Variant",
        "mit-enna": "MIT-enna",
        "mit-feh": "MIT-feh",
        "mit-wu": "MIT-Wu",

        # Mozilla Family
        "mozilla public license 1.1": "MPL-1.1",
        "mozilla public license 2.0": "MPL-2.0",
        "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
        "mozilla public license 2.0 (no copyleft exception)":
            "MPL-2.0-no-copyleft-exception",

        # Other Common Licenses
        "academic free license v2.0": "AFL-2.0",
        "academic free license v2.1": "AFL-2.1",
        "academic free license v3.0": "AFL-3.0",
        "apple public source license 2.0": "APSL-2.0",
        "artistic license 1.0": "Artistic-1.0",
        "artistic license 1.0 (perl)": "Artistic-1.0-Perl",
        "artistic license 2.0": "Artistic-2.0",
        "bitstream vera font license": "Bitstream-Vera",
        "boost software license 1.0": "BSL-1.0",
        "creative commons attribution 2.5 generic": "CC-BY-2.5",
        "creative commons attribution 3.0 unported": "CC-BY-3.0",
        "common development and distribution license 1.0": "CDDL-1.0",
        "common development and distribution license 1.1": "CDDL-1.1",
        "common public license 1.0": "CPL-1.0",
        "educational community license v1.0": "ECL-1.0",
        "educational community license v2.0": "ECL-2.0",
        "eiffel forum license v2.0": "EFL-2.0",
        "eclipse public license 1.0": "EPL-1.0",
        "eclipse public license 2.0": "EPL-2.0",
        "european union public license 1.1": "EUPL-1.1",
        "european union public license 1.2": "EUPL-1.2",
        "fsf all permissive license": "FSFAP",
        "fsf unlimited license": "FSFUL",
        "freetype project license": "FTL",
        "historical permission notice and disclaimer": "HPND",
        "ibm powerpc initialization and boot software": "IBM-pibs",
        "icu license": "ICU",
        "independent jpeg group license": "IJG",
        "imagemagick license": "ImageMagick",
        "info-zip license": "Info-ZIP",
        "ibm public license v1.0": "IPL-1.0",
        "isc license": "ISC",
        "jasper license": "JasPer-2.0",
        "libpng license": "Libpng",
        "png reference library version 2": "libpng-2.0",
        "libtiff license": "libtiff",
        "minpack license": "Minpack",
        "the miros licence": "MirOS",
        "microsoft public license": "MS-PL",
        "microsoft reciprocal license": "MS-RL",
        "net boolean public license v1": "NBPL-1.0",
        "university of illinois/ncsa open source license": "NCSA",
        "ntp license": "NTP",
        "ogc software license, version 1.0": "OGC-1.0",
        "open ldap public license v2.8": "OLDAP-2.8",
        "openssl license": "OpenSSL",
        "open software license 3.0": "OSL-3.0",
        "php license v3.01": "PHP-3.01",
        "postgresql license": "PostgreSQL",
        "python software foundation license 2.0": "PSF-2.0",
        "python software foundation license": "PSF-2.0",
        "python license 2.0": "Python-2.0",
        "qhull license": "Qhull",
        "rsa message-digest license": "RSA-MD",
        "saxpath license": "Saxpath",
        "sgi free software license b v2.0": "SGI-B-2.0",
        "sleepycat license": "Sleepycat",
        "sml of new jersey license": "SMLNJ",
        "spencer license 86": "Spencer-86",
        "ssh openssh license": "SSH-OpenSSH",
        "ssh short notice": "SSH-short",
        "sunpro license": "SunPro",
        "unicode license v3": "Unicode-3.0",
        "unicode license agreement - data files and software (2015)":
            "Unicode-DFS-2015",
        "unicode license agreement - data files and software (2016)":
            "Unicode-DFS-2016",
        "the unlicense": "Unlicense",
        "universal permissive license v1.0": "UPL-1.0",
        "w3c software notice and license (2002-12-31)": "W3C",
        "w3c software notice and license (1998-07-20)": "W3C-19980720",
        "w3c software notice and document license (2015-05-13)":
            "W3C-20150513",
        "do what the f*ck you want to public license": "WTFPL",
        "x11 license": "X11",
        "xfree86 license 1.1": "XFree86-1.1",
        "zlib license": "Zlib",
        "zlib/libpng license with acknowledgement":
            "zlib-acknowledgement",
        "zope public license 2.0": "ZPL-2.0",
        # Additional common mappings
        "isc": "ISC",
        "cc0-1.0": "CC0-1.0",
        "cc-by-4.0": "CC-BY-4.0",
        "cc-by-sa-4.0": "CC-BY-SA-4.0",
        "beerware": "Beerware",
        "postgresql": "PostgreSQL",
        "public domain": "Unlicense",  # Approximation
    }
    if key in mapping:
        return mapping[key].strip().lower()
    # Already in a likely OSADL/SPDX form
    if any(key.startswith(prefix) for prefix in (
        "apache-", "bsd-", "gpl-", "lgpl-", "mpl-", "mit", "psf")
    ):
        return key
    return key
