# vics-compilething
Vic's Compilething is makefile generator.  I made it because after screwing around with GNUMake for a few hours I couldn't make it do what I wanted it to do.

It consists of a single Python script that reads a project description file and generates a makefile.  The script has no external dependencies.  The project description file is standard Python.  For example:

```python
from make_makefile import SourceFile
from make_makefile import Context
import os

class MyContext(Context):
	SOURCE_FILES = (
			SourceFile("context/base_context.cpp"),
			SourceFile("context/client_context.cpp"),
			SourceFile("context/context.cpp"),
			)

	INCLUDE_DIRS=(os.path.join(Context.SOURCE_DIR,"include"),)

	LIB_TARGET="HVAC_LIB"

	TAG = LIB_TARGET

def vc_init():
	return MyContext()

```

The above file describes a project that contains three source files and is a shared library.  The ```vc_init``` method returns an instance of the context to the caller.  It is used by the main script to read in the configuration.

Another project may want to use a shared library described in the above configuration.  It would do so as following:

```python
#!/usr/bin/env python

from make_makefile import SourceFile
from make_makefile import Context

import os

class MyContext(Context):
	SOURCE_FILES = (
			SourceFile("bbb_hvac.cpp"),
			)
	TAG = "LOGIC_CORE"

#	INCLUDE_DIRS=(os.path.join(Context.SOURCE_DIR,"include"),None)

	EXE_TARGET=os.path.join(Context.OUTPUT_DIR,"LOGIC_CORE")

	RELATED_PROJECTS=("../HVAC_LIB",)

	Context.LIBRARIES += ["pthread"]



def vc_init():
	return MyContext()

```

Note the ```RELATED_PROJECTS``` line.

All behind the scenes Makefile stuff is magically generated.